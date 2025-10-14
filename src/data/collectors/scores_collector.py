"""
实时比分采集器

实现足球比赛实时比分和事件数据的采集逻辑。
支持WebSocket连接和HTTP轮询两种采集模式。

采集策略：
- WebSocket实时推送（优先）
- HTTP轮询备份（2分钟间隔）
- 比赛状态管理（开始/进行/结束）
- 关键事件记录（进球、红牌、换人等）

基于 DATA_DESIGN.md 第1.1节设计。
"""

from typing import Any,  Dict[str, Any],  Any, List[Any], Optional, Any
from datetime import datetime
from enum import Enum
import asyncio

from .base_collector import DataCollector, CollectionResult


class MatchStatus(Enum):
    """比赛状态枚举"""

    NOT_STARTED = "not_started"
    FIRST_HALF = "first_half"
    HALF_TIME = "half_time"
    SECOND_HALF = "second_half"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class EventType(Enum):
    """比赛事件类型枚举"""

    GOAL = "goal"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    SUBSTITUTION = "substitution"
    PENALTY = "penalty"
    OWN_GOAL = "own_goal"
    VAR_DECISION = "var_decision"


class ScoresCollector(DataCollector):
    """
    实时比分采集器

    负责采集比赛的实时比分、状态变化和关键事件，
    支持WebSocket实时推送和HTTP轮询两种模式。
    """

    def __init__(
        self,
        data_source: str = "scores_api",
        api_key: Optional[str] = None,
        base_url: str = "https://api.football-data.org/v4",
        websocket_url: Optional[str] = None,
        polling_interval: int = 120,  # 轮询间隔（秒）
        **kwargs,
    ):
        """
        初始化实时比分采集器

        Args:
            data_source: 数据源名称
            api_key: API密钥
            base_url: HTTP API基础URL
            websocket_url: WebSocket连接URL
            polling_interval: 轮询间隔（秒）
        """
        super().__init__(data_source, **kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.websocket_url = websocket_url
        self.polling_interval = polling_interval

        # 实时数据：记录当前进行中的比赛
        self._active_matches: Set[str] = set()  # type: ignore
        # 事件跟踪：记录已处理的事件ID，避免重复
        self._processed_events: Set[str] = set()  # type: ignore
        # WebSocket连接状态
        self._websocket_connected = False

    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """实时比分采集器不处理赛程数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="fixtures",
            records_collected=0,
            success_count=0,
            error_count=0,
            status="skipped",
        )

    async def collect_odds(self, **kwargs) -> CollectionResult:
        """实时比分采集器不处理赔率数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="odds",
            records_collected=0,
            success_count=0,
            error_count=0,
            status="skipped",
        )

    async def collect_live_scores(
        self,
        match_ids: Optional[List[str] = None,
        use_websocket: bool = True,
        **kwargs,
    ) -> CollectionResult:
        """
        采集实时比分数据

        实时采集策略：
        - 优先使用WebSocket连接获取实时推送
        - WebSocket失败时回退到HTTP轮询
        - 比赛状态变化检测和记录
        - 关键事件去重和存储

        Args:
            match_ids: 需要监控的比赛ID列表
            use_websocket: 是否使用WebSocket连接

        Returns:
            CollectionResult: 采集结果
        """
        collected_data = []
        success_count = 0
        error_count = 0
        error_messages = []

        try:
            # 获取当前进行中的比赛
            if not match_ids:
                match_ids = await self._get_live_matches()

            if not match_ids:
                self.logger.info("No live matches found")
                return CollectionResult(
                    data_source=self.data_source,
                    collection_type="live_scores",
                    records_collected=0,
                    success_count=0,
                    error_count=0,
                    status="success",
                )

            self.logger.info(
                f"Starting live scores collection for {len(match_ids)} matches"
            )
            self._active_matches.update(match_ids)

            # 选择采集模式
            if use_websocket and self.websocket_url:
                try:
                    # WebSocket实时模式
                    scores_data = await self._collect_via_websocket(match_ids)
                    collected_data.extend(scores_data)
                    success_count = len(scores_data)

                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    error_count += 1
                    error_messages.append(f"WebSocket failed: {str(e)}")
                    self.logger.warning(
                        f"WebSocket collection failed: {str(e)}, falling back to polling"
                    )

                    # 回退到轮询模式
                    scores_data = await self._collect_via_polling(match_ids)
                    collected_data.extend(scores_data)
                    success_count = len(scores_data)
            else:
                # HTTP轮询模式
                scores_data = await self._collect_via_polling(match_ids)
                collected_data.extend(scores_data)
                success_count = len(scores_data)

            # 保存到Bronze层原始数据表
            if collected_data:
                await self._save_to_bronze_layer("raw_scores_data", collected_data)

            # 确定最终状态
            total_collected = len(collected_data)
            if error_count == 0:
                status = "success"
            elif success_count > 0:
                status = "partial"
            else:
                status = "failed"

            _result = CollectionResult(
                data_source=self.data_source,
                collection_type="live_scores",
                records_collected=total_collected,
                success_count=success_count,
                error_count=error_count,
                status=status,
                error_message="; ".join(error_messages[:5]) if error_messages else None,
                collected_data=collected_data,
            )

            self.logger.info(
                f"Live scores collection completed: "
                f"collected={total_collected}, success={success_count}, errors={error_count}"
            )

            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Live scores collection failed: {str(e)}")
            return CollectionResult(
                data_source=self.data_source,
                collection_type="live_scores",
                records_collected=0,
                success_count=0,
                error_count=1,
                status="failed",
                error_message=str(e),
            )

    async def _collect_websocket_scores(
        self, match_ids: List[str]
    ) -> List[Dict[str, Any]:
        """
        通过WebSocket采集实时比分数据

        Args:
            match_ids: 比赛ID列表

        Returns:
            List[Dict[str, Any]: 比分数据列表
        """
        return await self._collect_via_websocket(match_ids)

    async def _get_live_matches(self) -> List[str]:
        """
        获取当前进行中的比赛列表

        Returns:
            List[str]: 进行中的比赛ID列表
        """
        try:
            # 目前返回空列表作为占位符
            return []
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to get live matches: {str(e)}")
            return []

    async def _collect_via_websocket(
        self,
        match_ids: List[str],
        duration: int = 3600,  # 连接持续时间（秒）
    ) -> List[Dict[str, Any]:
        """
        通过WebSocket采集实时数据

        Args:
            match_ids: 需要监控的比赛ID列表
            duration: 连接持续时间（秒）

        Returns:
            List[Dict[str, Any]: 采集到的实时数据
        """
        collected_data = []

        try:
            if not self.websocket_url:
                raise ValueError("WebSocket URL not configured")

            self.logger.info(f"Connecting to WebSocket: {self.websocket_url}")

            async with websockets.connect(self.websocket_url) as websocket:  # type: ignore
                self._websocket_connected = True

                # 订阅指定比赛的实时数据
                subscribe_message = {
                    "action": "subscribe",
                    "matches": match_ids,
                    "api_key": self.api_key,
                }
                await websocket.send(json.dumps(subscribe_message))  # type: ignore

                # 设置接收超时
                end_time = asyncio.get_event_loop().time() + duration

                while asyncio.get_event_loop().time() < end_time:
                    try:
                        # 等待消息，设置超时
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)

                        # 解析实时数据
                        _data = json.loads(message)  # type: ignore
                        if data.get("type") == "match_update":
                            cleaned_data = await self._clean_live_data(data)
                            if cleaned_data:
                                collected_data.append(cleaned_data)

                    except asyncio.TimeoutError:
                        # 发送心跳保持连接
                        await websocket.ping()
                        continue

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"WebSocket collection failed: {str(e)}")
            self._websocket_connected = False
            raise

        finally:
            self._websocket_connected = False

        return collected_data

    async def _collect_via_polling(self, match_ids: List[str]) -> List[Dict[str, Any]:
        """
        通过HTTP轮询采集实时数据

        Args:
            match_ids: 需要监控的比赛ID列表

        Returns:
            List[Dict[str, Any]: 采集到的实时数据
        """
        collected_data = []

        try:
            for match_id in match_ids:
                try:
                    # 获取比赛实时信息
                    match_data = await self._get_match_live_data(match_id)
                    if match_data:
                        cleaned_data = await self._clean_live_data(match_data)
                        if cleaned_data:
                            collected_data.append(cleaned_data)

                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    self.logger.error(
                        f"Failed to collect live data for match {match_id}: {str(e)}"
                    )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Polling collection failed: {str(e)}")
            raise

        return collected_data

    async def _get_match_live_data(self, match_id: str) -> Optional[Dict[str, Any]:
        """
        获取指定比赛的实时数据

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]: 比赛实时数据，失败返回None
        """
        try:
            url = f"{self.base_url}/matches/{match_id}"
            headers = {"X-Auth-Token": self.api_key} if self.api_key else {}

            response = await self._make_request(url=url, headers=headers)
            return response

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to get live data for match {match_id}: {str(e)}")
            return None

    async def _clean_live_data(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]:
        """
        清洗和标准化实时比分数据

        Args:
            raw_data: 原始实时数据

        Returns:
            Optional[Dict[str, Any]: 清洗后的数据，无效则返回None
        """
        try:
            # 基础字段验证
            if not raw_data.get("id"):
                self.logger.warning(f"Missing 'id' field in raw_data: {raw_data}")
                return None

            # 提取比赛状态和比分
            match_id = str(raw_data["id"])
            status = raw_data.get(str("status"), "UNKNOWN")

            # 比分数据
            score = raw_data.get(str("score"), {})
            home_score = score.get(str("fullTime"), {}).get("home")
            away_score = score.get(str("fullTime"), {}).get("away")

            # 比赛时间
            minute = raw_data.get("minute")

            # 最近事件
            events = []
            for event in raw_data.get(str("events"), []):
                event_data = {
                    "minute": event.get("minute"),
                    "type": event.get("type"),
                    "player": event.get(str("player"), {}).get("name"),
                    "team": event.get(str("team"), {}).get("name"),
                }
                events.append(event_data)

            cleaned_data = {
                "external_match_id": match_id,
                "status": status,
                "home_score": home_score,
                "away_score": away_score,
                "minute": minute,
                "events": events,
                "raw_data": raw_data,
                "collected_at": datetime.now().isoformat(),
                "processed": False,
            }

            return cleaned_data

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to clean live data: {str(e)}")
            return None

    def _is_match_finished(self, status: str) -> bool:
        """
        检查比赛是否已结束

        Args:
            status: 比赛状态

        Returns:
            bool: 是否已结束
        """
        finished_statuses = ["FINISHED", "COMPLETED", "CANCELLED", "POSTPONED"]
        return status.upper() in finished_statuses

    async def start_continuous_monitoring(
        self, match_ids: Optional[List[str] = None, use_websocket: bool = True
    ) -> None:
        """
        启动持续监控模式（后台任务）

        Args:
            match_ids: 需要监控的比赛ID列表
            use_websocket: 是否使用WebSocket连接
        """
        self.logger.info("Starting continuous live scores monitoring...")

        while True:
            try:
                # 获取当前需要监控的比赛
                if not match_ids:
                    current_matches = await self._get_live_matches()

                else:
                    current_matches = match_ids

                if current_matches:
                    _result = await self.collect_live_scores(
                        match_ids=current_matches, use_websocket=use_websocket
                    )

                    if result.status == "failed":
                        self.logger.error(f"Monitoring failed: {result.error_message}")

                # 等待下一次轮询
                await asyncio.sleep(self.polling_interval)

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(f"Continuous monitoring error: {str(e)}")
                await asyncio.sleep(self.polling_interval)
