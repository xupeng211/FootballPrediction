"""
改进的实时比分收集器
Improved Real-time Scores Collector

提供高性能的实时比分数据收集功能，支持：
- 多数据源集成
- WebSocket实时推送
- 数据去重和验证
- 异常处理和重试
- 性能优化

Provides high-performance real-time scores collection with:
- Multi-source integration
- WebSocket real-time push
- Data deduplication and validation
- Error handling and retry
- Performance optimization
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import websockets
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager, CacheKeyManager
from src.database.models import Match, MatchStatus, RawScoresData
from src.utils.retry import RetryConfig, retry
from src.utils.time_utils import utc_now, parse_datetime

logger = logging.getLogger(__name__)


class ScoresCollector:
    """
    实时比分收集器
    Real-time Scores Collector

    从多个数据源收集实时比分数据，支持WebSocket和HTTP轮询。
    Collects real-time scores from multiple sources, supporting WebSocket and HTTP polling.
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

        # API端点
        self.api_endpoints = {
            "football_api": os.getenv("FOOTBALL_API_URL", "https://api.football-data.org/v4"),
            "api_sports": os.getenv("API_SPORTS_URL", "https://v3.football.api-sports.io"),
            "scorebat": os.getenv("SCOREBAT_URL", "https://www.scorebat.com/video/api/v1"),
        }

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

    async def collect_match_score(self, match_id: int, force: bool = False) -> Optional[Dict[str, Any]]:
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
            # 从API获取最新数据
            score_data = await self._fetch_match_score_from_api(match_id)

            if score_data:
                # 验证和处理数据
                processed_data = await self._process_score_data(match_id, score_data)

                if processed_data:
                    # 更新缓存
                    self.match_cache[match_id] = processed_data
                    self.last_update_cache[match_id] = utc_now()

                    # 保存到数据库
                    await self._save_score_data(processed_data)

                    # 发送到Redis频道（实时通知）
                    await self._publish_score_update(processed_data)

                    return processed_data

            return None

        except Exception as e:
            logger.error(f"收集比赛 {match_id} 比分失败: {e}")
            return None

    async def collect_live_matches(self) -> List[Dict[str, Any]]:
        """
        收集所有进行中的比赛比分

        Returns:
            List[Dict[str, Any]]: 比分数据列表
        """
        try:
            # 获取进行中的比赛
            live_matches = await self._get_live_matches()

            if not live_matches:
                return []

            # 批量收集比分
            tasks = [self.collect_match_score(match["id"]) for match in live_matches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            scores = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"收集比赛 {live_matches[i]['id']} 比分失败: {result}")
                elif result:
                    scores.append(result)

            return scores

        except Exception as e:
            logger.error(f"收集进行中比赛比分失败: {e}")
            return []

    async def _websocket_listener(self):
        """WebSocket监听器"""
        if not self.websocket_url:
            return

        logger.info(f"启动WebSocket监听: {self.websocket_url}")

        while self.running:
            try:
                async with websockets.connect(self.websocket_url) as websocket:
                    logger.info("WebSocket连接已建立")

                    # 发送认证信息
                    if self.api_key:
                        await websocket.send(json.dumps({
                            "type": "auth",
                            "token": self.api_key
                        }))

                    # 监听消息
                    async for message in websocket:
                        if not self.running:
                            break

                        try:
                            data = json.loads(message)
                            await self._handle_websocket_message(data)
                            self.stats["websocket_messages"] += 1
                        except json.JSONDecodeError:
                            logger.warning(f"无效的WebSocket消息: {message}")
                        except Exception as e:
                            logger.error(f"处理WebSocket消息失败: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭，尝试重连...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                await asyncio.sleep(10)

    async def _http_poller(self):
        """HTTP轮询器"""
        logger.info("启动HTTP轮询")

        while self.running:
            try:
                # 收集进行中的比赛
                await self.collect_live_matches()
                self.stats["api_calls"] += 1

                # 等待下次轮询
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"HTTP轮询失败: {e}")
                await asyncio.sleep(5)

    async def _handle_websocket_message(self, data: Dict[str, Any]):
        """处理WebSocket消息"""
        try:
            async with self.processing_lock:
                message_type = data.get("type")

                if message_type == "score_update":
                    match_id = data.get("match_id")
                    score_data = data.get("data")

                    if match_id and score_data:
                        # 处理比分更新
                        processed_data = await self._process_score_data(match_id, score_data)
                        if processed_data:
                            await self._save_score_data(processed_data)
                            await self._publish_score_update(processed_data)

                elif message_type == "match_event":
                    # 处理比赛事件（进球、红牌等）
                    await self._handle_match_event(data)

        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")

    async def _fetch_match_score_from_api(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从API获取比赛比分"""
        # 尝试多个数据源
        for source_name, base_url in self.api_endpoints.items():
            try:
                score_data = await self._fetch_from_source(source_name, match_id)
                if score_data:
                    return score_data
            except Exception as e:
                logger.warning(f"从 {source_name} 获取比赛 {match_id} 比分失败: {e}")
                continue

        return None

    @retry(lambda: None)
    async def _fetch_from_source(self, source: str, match_id: int) -> Optional[Dict[str, Any]]:
        """从指定数据源获取数据"""
        if source == "football_api":
            return await self._fetch_from_football_api(match_id)
        elif source == "api_sports":
            return await self._fetch_from_api_sports(match_id)
        elif source == "scorebat":
            return await self._fetch_from_scorebat(match_id)

        return None

    async def _fetch_from_football_api(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从Football-Data API获取比分"""
        if not self.api_key:
            return None

        url = f"{self.api_endpoints['football_api']}/matches/{match_id}"
        headers = {"X-Auth-Token": self.api_key}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._transform_football_api_data(data)
                else:
                    logger.warning(f"Football API请求失败: {response.status}")
                    return None

    async def _fetch_from_api_sports(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从API-Sports获取比分"""
        if not self.api_key:
            return None

        url = f"{self.api_endpoints['api_sports']}/fixtures?id={match_id}&live=all"
        headers = {"x-apisports-key": self.api_key}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("response"):
                        return self._transform_api_sports_data(data["response"][0])
                return None

    async def _fetch_from_scorebat(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从Scorebat获取比分（简化实现）"""
        # Scorebat主要提供视频，这里作为备用数据源
        return None

    def _transform_football_api_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换Football API数据格式"""
        match = data.get("match", {})
        score = match.get("score", {})

        return {
            "match_id": match.get("id"),
            "home_score": score.get("fullTime", {}).get("home", 0),
            "away_score": score.get("fullTime", {}).get("away", 0),
            "home_half_score": score.get("halfTime", {}).get("home", 0),
            "away_half_score": score.get("halfTime", {}).get("away", 0),
            "match_time": match.get("utcDate"),
            "match_status": match.get("status"),
            "last_updated": utc_now().isoformat(),
            "events": [],  # 可从其他端点获取
        }

    def _transform_api_sports_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换API-Sports数据格式"""
        return {
            "match_id": data.get("fixture", {}).get("id"),
            "home_score": data.get("goals", {}).get("home", 0),
            "away_score": data.get("goals", {}).get("away", 0),
            "home_half_score": data.get("score", {}).get("halftime", {}).get("home", 0),
            "away_half_score": data.get("score", {}).get("halftime", {}).get("away", 0),
            "match_time": data.get("fixture", {}).get("date"),
            "match_status": data.get("fixture", {}).get("status", {}).get("long"),
            "last_updated": utc_now().isoformat(),
            "events": data.get("events", []),
        }

    async def _process_score_data(self, match_id: int, score_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理和验证比分数据"""
        try:
            # 获取数据库中的比赛信息
            match = await self.db_session.get(Match, match_id)
            if not match:
                logger.warning(f"比赛 {match_id} 不存在于数据库中")
                return None

            # 验证数据完整性
            if not all(k in score_data for k in ["home_score", "away_score", "match_status"]):
                logger.warning(f"比赛 {match_id} 比分数据不完整")
                return None

            # 更新比赛状态
            old_status = match.match_status
            new_status = self._map_status(score_data["match_status"])

            processed_data = {
                "match_id": match_id,
                "home_score": int(score_data["home_score"]),
                "away_score": int(score_data["away_score"]),
                "home_half_score": int(score_data.get("home_half_score", 0)),
                "away_half_score": int(score_data.get("away_half_score", 0)),
                "match_status": new_status.value,
                "match_time": parse_datetime(score_data.get("match_time")),
                "last_updated": parse_datetime(score_data.get("last_updated")),
                "events": score_data.get("events", []),
                "previous_status": old_status.value,
            }

            # 检查是否有实质性更新
            if self._has_significant_change(match, processed_data):
                return processed_data

            return None

        except Exception as e:
            logger.error(f"处理比赛 {match_id} 比分数据失败: {e}")
            return None

    def _map_status(self, api_status: str) -> MatchStatus:
        """映射API状态到内部状态"""
        status_mapping = {
            "SCHEDULED": MatchStatus.SCHEDULED,
            "TIMED": MatchStatus.SCHEDULED,
            "POSTPONED": MatchStatus.POSTPONED,
            "CANCELED": MatchStatus.CANCELLED,
            "IN_PLAY": MatchStatus.IN_PROGRESS,
            "LIVE": MatchStatus.IN_PROGRESS,
            "PAUSED": MatchStatus.PAUSED,
            "FINISHED": MatchStatus.FINISHED,
            "AWARDED": MatchStatus.FINISHED,
        }

        return status_mapping.get(api_status.upper(), MatchStatus.SCHEDULED)

    def _has_significant_change(self, match: Match, new_data: Dict[str, Any]) -> bool:
        """检查是否有实质性变化"""
        # 比分变化
        if match.home_score != new_data["home_score"] or match.away_score != new_data["away_score"]:
            return True

        # 状态变化
        if match.match_status != new_data["match_status"]:
            return True

        # 半场比分变化
        if match.home_half_score != new_data["home_half_score"] or match.away_half_score != new_data["away_half_score"]:
            return True

        return False

    async def _save_score_data(self, score_data: Dict[str, Any]):
        """保存比分数据到数据库"""
        try:
            start_time = utc_now()

            # 更新比赛表
            stmt = update(Match).where(Match.id == score_data["match_id"]).values(
                home_score=score_data["home_score"],
                away_score=score_data["away_score"],
                home_half_score=score_data["home_half_score"],
                away_half_score=score_data["away_half_score"],
                match_status=score_data["match_status"],
                updated_at=utc_now(),
            )

            await self.db_session.execute(stmt)

            # 保存原始数据（用于审计和分析）
            raw_data = RawScoresData(
                match_id=score_data["match_id"],
                source="real_time_collector",
                data=score_data,
                collected_at=score_data["last_updated"],
            )
            self.db_session.add(raw_data)

            await self.db_session.commit()

            # 更新统计
            self.stats["total_updates"] += 1
            self.stats["successful_updates"] += 1

            processing_time = (utc_now() - start_time).total_seconds()
            self.stats["average_processing_time"] = (
                self.stats["average_processing_time"] * (self.stats["successful_updates"] - 1) + processing_time
            ) / self.stats["successful_updates"]

            logger.debug(f"保存比赛 {score_data['match_id']} 比分数据成功")

        except Exception as e:
            await self.db_session.rollback()
            self.stats["failed_updates"] += 1
            logger.error(f"保存比分数据失败: {e}")
            raise

    async def _publish_score_update(self, score_data: Dict[str, Any]):
        """发布比分更新到Redis"""
        try:
            channel = f"scores:match:{score_data['match_id']}"
            message = {
                "type": "score_update",
                "match_id": score_data["match_id"],
                "home_score": score_data["home_score"],
                "away_score": score_data["away_score"],
                "status": score_data["match_status"],
                "timestamp": utc_now().isoformat(),
            }

            await self.redis_manager.client.publish(channel, json.dumps(message))

            # 发布到全局频道
            await self.redis_manager.client.publish(
                "scores:global_updates",
                json.dumps(message)
            )

        except Exception as e:
            logger.error(f"发布比分更新失败: {e}")

    async def _handle_match_event(self, event_data: Dict[str, Any]):
        """处理比赛事件（进球、红牌等）"""
        # 实现事件处理逻辑
        pass

    async def _get_live_matches(self) -> List[Dict[str, Any]]:
        """获取进行中的比赛"""
        query = select(Match).where(
            or_(
                Match.match_status == MatchStatus.IN_PROGRESS,
                Match.match_status == MatchStatus.PAUSED,
            )
        ).order_by(Match.match_time)

        result = await self.db_session.execute(query)
        matches = result.scalars().all()

        return [
            {
                "id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "match_time": match.match_time,
                "current_score": f"{match.home_score}-{match.away_score}",
            }
            for match in matches
        ]

    async def _cleanup_cache(self):
        """清理过期缓存"""
        while self.running:
            try:
                # 清理超过1小时未更新的缓存
                cutoff_time = utc_now() - timedelta(hours=1)

                expired_matches = [
                    match_id for match_id, last_update in self.last_update_cache.items()
                    if last_update < cutoff_time
                ]

                for match_id in expired_matches:
                    self.match_cache.pop(match_id, None)
                    self.last_update_cache.pop(match_id, None)

                if expired_matches:
                    logger.debug(f"清理了 {len(expired_matches)} 个过期缓存")

                # 每小时执行一次清理
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理缓存失败: {e}")
                await asyncio.sleep(300)

    def get_stats(self) -> Dict[str, Any]:
        """获取收集统计信息"""
        return {
            **self.stats,
            "running": self.running,
            "cached_matches": len(self.match_cache),
            "success_rate": (
                self.stats["successful_updates"] / self.stats["total_updates"]
                if self.stats["total_updates"] > 0
                else 0.0
            ),
        }


class ScoresCollectorManager:
    """比分收集器管理器"""

    def __init__(self):
        self.collectors: Dict[int, ScoresCollector] = {}
        self.redis_manager = RedisManager()

    async def get_collector(self, session_id: int) -> ScoresCollector:
        """获取或创建收集器实例"""
        if session_id not in self.collectors:
            from src.database.connection import get_async_session
            async with get_async_session() as session:
                collector = ScoresCollector(session, self.redis_manager)
                self.collectors[session_id] = collector
        return self.collectors[session_id]

    async def start_all(self):
        """启动所有收集器"""
        for collector in self.collectors.values():
            await collector.start_collection()

    async def stop_all(self):
        """停止所有收集器"""
        for collector in self.collectors.values():
            await collector.stop_collection()

    def remove_collector(self, session_id: int):
        """移除收集器"""
        if session_id in self.collectors:
            del self.collectors[session_id]


# 全局管理器实例
_scores_manager: Optional[ScoresCollectorManager] = None


def get_scores_manager() -> ScoresCollectorManager:
    """获取全局比分收集器管理器"""
    global _scores_manager
    if _scores_manager is None:
        _scores_manager = ScoresCollectorManager()
    return _scores_manager