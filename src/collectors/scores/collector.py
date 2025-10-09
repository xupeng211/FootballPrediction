"""
比分收集器
Scores Collector

实时比分收集器主类。
"""





logger = logging.getLogger(__name__)


class ScoresCollector:
    """
    实时比分收集器
    Real-time Scores Collector

    从多个数据源收集实时比分数据，支持WebSocket和HTTP轮询。
    """

    def __init__(
        self,
        db_session: AsyncSession,
        redis_manager: RedisManager,
        api_key: Optional[str] = None,
        websocket_url: Optional[str] = None,
        poll_interval: int = 30,
    ):
        """
        初始化比分收集器

        Args:
            db_session: 数据库会话
            redis_manager: Redis管理器
            api_key: API密钥
            websocket_url: WebSocket服务URL
            poll_interval: HTTP轮询间隔（秒）
        """
        self.db_session = db_session
        self.redis_manager = redis_manager
        self.cache_manager = CacheKeyManager()

        # 配置
        self.api_key = api_key or os.getenv("FOOTBALL_API_TOKEN")
        self.websocket_url = websocket_url or os.getenv("SCORES_WEBSOCKET_URL")
        self.poll_interval = poll_interval

        # 初始化组件
        self.source_manager = ScoreSourceManager(self.api_key)
        self.processor = ScoreDataProcessor(db_session)
        self.publisher = ScoreUpdatePublisher(redis_manager)

        # 状态管理
        self.running = False
        self.websocket_task: Optional[asyncio.Task] = None
        self.poll_task: Optional[asyncio.Task] = None
        self.processing_lock = asyncio.Lock()

        # 数据缓存
        self.match_cache: Dict[int, Dict[str, Any]] = {}
        self.last_update_cache: Dict[int, datetime] = {}

        # 性能统计
        self.stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "websocket_messages": 0,
            "api_calls": 0,
            "average_processing_time": 0.0,
        }

        # 重试配置
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
        )

    async def start_collection(self):
        """启动实时比分收集"""
        if self.running:
            logger.warning("比分收集器已在运行")
            return

        self.running = True
        logger.info("启动实时比分收集器")

        # 启动WebSocket监听（如果配置了）
        if self.websocket_url:
            self.websocket_task = asyncio.create_task(self._websocket_listener())

        # 启动HTTP轮询
        self.poll_task = asyncio.create_task(self._http_poller())

        # 清理过期缓存
        asyncio.create_task(self._cleanup_cache())

    async def stop_collection(self):
        """停止实时比分收集"""
        self.running = False
        logger.info("停止实时比分收集器")

        # 取消任务
        if self.websocket_task:
            self.websocket_task.cancel()
            try:
                await self.websocket_task
            except asyncio.CancelledError:
                pass

        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

    async def collect_match_score(
        self, match_id: int, force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        收集指定比赛的比分数据

        Args:
            match_id: 比赛ID
            force: 是否强制更新

        Returns:
            Optional[Dict[str, Any]]: 比分数据
        """
        # 检查缓存
        if not force and match_id in self.match_cache:
            last_update = self.last_update_cache.get(match_id, utc_now())
            if utc_now() - last_update < timedelta(minutes=1):
                return self.match_cache[match_id]

        try:
            start_time = utc_now()

            # 从API获取最新数据
            score_data = await self.source_manager.fetch_match_score(match_id)

            if score_data:
                # 验证和处理数据
                processed_data = await self.processor.process_score_data(
                    match_id, score_data
                )

                if processed_data:
                    # 更新缓存
                    self.match_cache[match_id] = processed_data
                    self.last_update_cache[match_id] = utc_now()

                    # 保存到数据库
                    await self._save_score_data(processed_data)

                    # 发送到Redis频道（实时通知）
                    await self.publisher.publish_score_update(processed_data)

                    # 更新统计
                    self.stats["successful_updates"] += 1
                    processing_time = (utc_now() - start_time).total_seconds()
                    self._update_processing_time(processing_time)

                    return processed_data

            self.stats["failed_updates"] += 1
            return None

        except Exception as e:
            self.stats["failed_updates"] += 1
            logger.error(f"收集比赛 {match_id} 比分失败: {e}")
            return None
        finally:
            self.stats["total_updates"] += 1

    async def collect_live_matches(self) -> List[Dict[str, Any]]:
        """
        收集所有实时比赛的比分

        Returns:
            List[Dict[str, Any]]: 实时比赛列表
        """
        live_matches = []
        try:
            # 获取所有进行中的比赛
            from sqlalchemy import select

            result = await self.db_session.execute(
                select(Match).where(Match.match_status == "IN_PROGRESS")
            )
            matches = result.scalars().all()

            # 并发收集比分
            tasks = [
                self.collect_match_score(match.id) for match in matches[:50]
            ]  # 限制并发数
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for match, result in zip(matches, results):
                if isinstance(result, dict):
                    live_matches.append(
                        {
                            "match_id": match.id,
                            "home_team": match.home_team.name
                            if match.home_team
                            else "",
                            "away_team": match.away_team.name
                            if match.away_team
                            else "",
                            "home_score": result["home_score"],
                            "away_score": result["away_score"],
                            "match_status": result["match_status"],
                            "match_time": match.match_time.isoformat()
                            if match.match_time
                            else "",
                        }
                    )

            # 发布实时比赛列表
            await self.publisher.publish_live_matches_list(live_matches)

        except Exception as e:
            logger.error(f"收集实时比赛列表失败: {e}")

        return live_matches

    async def _websocket_listener(self):
        """WebSocket监听器"""
        if not self.websocket_url:
            return

        logger.info(f"启动WebSocket监听: {self.websocket_url}")

        while self.running:
            try:
                async with websockets.connect(self.websocket_url) as websocket:
                    while self.running:
                        message = await websocket.recv()
                        self.stats["websocket_messages"] += 1

                        try:
                            data = json.loads(message)
                            await self._handle_websocket_message(data)
                        except json.JSONDecodeError as e:
                            logger.warning(f"解析WebSocket消息失败: {e}")

            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                # 等待后重试
                await asyncio.sleep(5)

    async def _http_poller(self):
        """HTTP轮询器"""
        logger.info(f"启动HTTP轮询，间隔: {self.poll_interval}秒")

        while self.running:
            try:
                # 获取需要更新的比赛
                matches = await self._get_matches_to_poll()

                # 并发更新
                tasks = [self.collect_match_score(match.id) for match in matches[:20]]
                await asyncio.gather(*tasks, return_exceptions=True)

            except Exception as e:
                logger.error(f"HTTP轮询失败: {e}")

            # 等待下次轮询
            await asyncio.sleep(self.poll_interval)

    async def _handle_websocket_message(self, data: Dict[str, Any]):
        """处理WebSocket消息"""
        async with self.processing_lock:
            try:
                if data.get("type") == "score_update":
                    match_id = data.get("match_id")
                    if match_id:
                        # 立即处理WebSocket消息
                        await self.collect_match_score(match_id, force=True)

                elif data.get("type") == "match_event":
                    await self._handle_match_event(data)

            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")

    async def _save_score_data(self, score_data: Dict[str, Any]):
        """保存比分数据到数据库"""
        try:
            # 保存到原始数据表
            raw_data = RawScoresData(
                match_id=score_data["match_id"],
                source="collector",
                data=json.dumps(score_data),
                created_at=utc_now(),
            )
            self.db_session.add(raw_data)

            # 更新比赛表
            from sqlalchemy import update

            stmt = (
                update(Match)
                .where(Match.id == score_data["match_id"])
                .values(
                    home_score=score_data["home_score"],
                    away_score=score_data["away_score"],
                    home_half_score=score_data["home_half_score"],
                    away_half_score=score_data["away_half_score"],
                    match_status=score_data["match_status"],
                    updated_at=utc_now(),
                )
            )
            await self.db_session.execute(stmt)
            await self.db_session.commit()

            logger.debug(f"保存比分数据: 比赛 {score_data['match_id']}")

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"保存比分数据失败: {e}")
            raise

    async def _handle_match_event(self, event_data: Dict[str, Any]):
        """处理比赛事件"""
        match_id = event_data.get("match_id")
        if match_id:
            await self.publisher.publish_match_event(match_id, event_data)

    async def _get_matches_to_poll(self) -> List[Match]:
        """获取需要轮询的比赛"""
        from sqlalchemy import select

        # 获取最近24小时内的比赛
        start_time = utc_now() - timedelta(hours=24)
        end_time = utc_now() + timedelta(hours=6)

        result = await self.db_session.execute(
            select(Match)
            .where(
                Match.match_time.between(start_time, end_time),
                or_(
                    Match.match_status == "SCHEDULED",
                    Match.match_status == "IN_PROGRESS",
                ),
            )
            .order_by(Match.match_time)
            .limit(100)
        )
        return result.scalars().all()

    async def _cleanup_cache(self):
        """清理过期缓存"""
        while self.running:
            try:
                # 清理超过5分钟的缓存
                cutoff = utc_now() - timedelta(minutes=5)
                expired_matches = [
                    match_id
                    for match_id, last_update in self.last_update_cache.items()
                    if last_update < cutoff
                ]

                for match_id in expired_matches:
                    self.match_cache.pop(match_id, None)
                    self.last_update_cache.pop(match_id, None)

                if expired_matches:
                    logger.debug(f"清理过期缓存: {len(expired_matches)} 个比赛")

            except Exception as e:
                logger.error(f"清理缓存失败: {e}")

            # 每小时清理一次
            await asyncio.sleep(3600)

    def _update_processing_time(self, processing_time: float):
        """更新平均处理时间"""
        current_avg = self.stats["average_processing_time"]
        total_updates = self.stats["successful_updates"]

        if total_updates == 1:
            self.stats["average_processing_time"] = processing_time
        else:
            # 计算移动平均
            self.stats["average_processing_time"] = (
                current_avg * (total_updates - 1) + processing_time
            ) / total_updates

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.stats,
            "running": self.running,
            "cached_matches": len(self.match_cache),
            "cache_size_mb": sum(len(str(v)) for v in self.match_cache.values())
            / (1024 * 1024),
        }
from datetime import datetime, timedelta
from typing import Dict
from typing import Optional
import asyncio
import json
import os

from sqlalchemy import or_
import websockets

from .data_sources import ScoreSourceManager
from .processor import ScoreDataProcessor
from .publisher import ScoreUpdatePublisher
from src.cache.redis_manager import CacheKeyManager
from src.database.models import Match, RawScoresData
from src.utils.retry import RetryConfig
from src.utils.time_utils import utc_now

