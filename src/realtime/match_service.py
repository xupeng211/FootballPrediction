"""
实时比赛状态监控服务

Realtime Match Status Monitoring Service

监控比赛状态变化并提供实时更新推送
Monitors match status changes and provides real-time update push functionality
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from .events import (
    EventType,
    RealtimeEvent,
    create_match_score_changed_event,
    create_match_score_changed_event,
    create_system_alert_event
)
from .manager import get_websocket_manager
from .subscriptions import get_subscription_manager


class MatchStatus(str, Enum):
    """比赛状态枚举"""
    UPCOMING = "upcoming"       # 即将开始
    LIVE = "live"              # 进行中
    HALFTIME = "halftime"      # 中场休息
    FULLTIME = "fulltime"      # 已结束
    POSTPONED = "postponed"    # 推迟
    CANCELLED = "cancelled"    # 取消


@dataclass
class MatchInfo:
    """比赛信息"""
    match_id: int
    home_team: str
    away_team: str
    league: str
    status: MatchStatus
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    minute: Optional[int] = None
    start_time: Optional[datetime] = None
    current_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    subscribers: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()

    def update_score(self, home_score: int, away_score: int, minute: Optional[int] = None) -> bool:
        """更新比分，返回是否有变化"""
        score_changed = (
            self.home_score != home_score or
            self.away_score != away_score
        )

        self.home_score = home_score
        self.away_score = away_score
        if minute is not None:
            self.minute = minute
        self.last_update = datetime.now()

        return score_changed

    def update_status(self, status: MatchStatus) -> bool:
        """更新状态，返回是否有变化"""
        if self.status != status:
            old_status = self.status
            # 记录状态变化（用于日志或调试）
            logger.debug(f"Status changed from {old_status} to {status}")
            self.status = status
            self.last_update = datetime.now()
            return True
        return False

    def get_display_score(self) -> str:
        """获取显示比分"""
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score} : {self.away_score}"
        return "VS"

    def is_live(self) -> bool:
        """判断是否为直播状态"""
        return self.status in [MatchStatus.LIVE, MatchStatus.HALFTIME]

    def get_duration(self) -> Optional[timedelta]:
        """获取比赛时长"""
        if self.start_time and self.current_time:
            return self.current_time - self.start_time
        return None


class RealtimeMatchService:
    """实时比赛服务"""

    def __init__(self):
        self.websocket_manager = get_websocket_manager()
        self.subscription_manager = get_subscription_manager()
        self.logger = logging.getLogger(f"{__name__}.RealtimeMatchService")

        # 比赛数据存储
        self.matches: Dict[int, MatchInfo] = {}
        self.league_matches: Dict[str, Set[int]] = {}

        # 监控配置
        self.monitoring_interval = 30  # 30秒检查一次
        self.live_update_interval = 10  # 直播比赛10秒更新一次
        self.max_matches = 1000  # 最大监控比赛数

        # 运行状态
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.live_update_task: Optional[asyncio.Task] = None

        # 启动监控
        self.start_monitoring()

        self.logger.info("RealtimeMatchService initialized")

    def start_monitoring(self) -> None:
        """启动监控"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.live_update_task = asyncio.create_task(self._live_update_loop())
            self.logger.info("Match monitoring started")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.live_update_task:
            self.live_update_task.cancel()
        self.logger.info("Match monitoring stopped")

    async def add_match(
        self,
        match_id: int,
        home_team: str,
        away_team: str,
        league: str,
        status: MatchStatus = MatchStatus.UPCOMING,
        start_time: Optional[datetime] = None
    ) -> bool:
        """
        添加比赛到监控列表

        Args:
            match_id: 比赛ID
            home_team: 主队
            away_team: 客队
            league: 联赛
            status: 比赛状态
            start_time: 开始时间

        Returns:
            是否添加成功
        """
        if len(self.matches) >= self.max_matches:
            await self._cleanup_old_matches()

        match = MatchInfo(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            league=league,
            status=status,
            start_time=start_time
        )

        self.matches[match_id] = match

        # 更新联赛索引
        if league not in self.league_matches:
            self.league_matches[league] = set()
        self.league_matches[league].add(match_id)

        # 发送比赛添加事件
        event = RealtimeEvent(
            event_type=EventType.MATCH_STARTED,
            data={
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "league": league,
                "status": status.value,
                "start_time": start_time.isoformat() if start_time else None,
                "timestamp": datetime.now().isoformat()
            },
            source="match_service"
        )
        await self.websocket_manager.publish_event(event)

        self.logger.info(f"Added match to monitoring: {match_id} - {home_team} vs {away_team}")
        return True

    async def update_match_score(
        self,
        match_id: int,
        home_score: int,
        away_score: int,
        minute: Optional[int] = None
    ) -> bool:
        """
        更新比赛比分

        Args:
            match_id: 比赛ID
            home_score: 主队得分
            away_score: 客队得分
            minute: 比赛分钟

        Returns:
            是否更新成功
        """
        if match_id not in self.matches:
            return False

        match = self.matches[match_id]
        score_changed = match.update_score(home_score, away_score, minute)

        if score_changed:
            # 发送比分变化事件
            event = create_match_score_changed_event(
                match_id=match.match_id,
                home_team=match.home_team,
                away_team=match.away_team,
                league=match.league,
                home_score=home_score,
                away_score=away_score,
                minute=minute
            )
            await self.websocket_manager.publish_event(event)

            self.logger.info(f"Score updated for match {match_id}: {home_score}-{away_score}")

        return score_changed

    async def update_match_status(
        self,
        match_id: int,
        status: MatchStatus,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        更新比赛状态

        Args:
            match_id: 比赛ID
            status: 新状态
            current_time: 当前时间

        Returns:
            是否更新成功
        """
        if match_id not in self.matches:
            return False

        match = self.matches[match_id]
        status_changed = match.update_status(status)

        if current_time:
            match.current_time = current_time

        if status_changed:
            # 发送状态变化事件
            event = RealtimeEvent(
                event_type=EventType.MATCH_STATUS_CHANGED,
                data={
                    "match_id": match.match_id,
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "league": match.league,
                    "old_status": match.status.value,
                    "new_status": status.value,
                    "current_score": match.get_display_score(),
                    "minute": match.minute,
                    "timestamp": datetime.now().isoformat()
                },
                source="match_service"
            )
            await self.websocket_manager.publish_event(event)

            self.logger.info(f"Status updated for match {match_id}: {status.value}")

        return status_changed

    async def get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛信息"""
        if match_id not in self.matches:
            return None

        match = self.matches[match_id]
        return {
            "match_id": match.match_id,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
            "status": match.status.value,
            "home_score": match.home_score,
            "away_score": match.away_score,
            "minute": match.minute,
            "display_score": match.get_display_score(),
            "is_live": match.is_live(),
            "start_time": match.start_time.isoformat() if match.start_time else None,
            "last_update": match.last_update.isoformat() if match.last_update else None,
            "subscribers": len(match.subscribers)
        }

    async def get_league_matches(self, league: str) -> List[Dict[str, Any]]:
        """获取联赛的所有比赛"""
        if league not in self.league_matches:
            return []

        matches = []
        for match_id in self.league_matches[league]:
            if match_id in self.matches:
                match_info = await self.get_match_info(match_id)
                if match_info:
                    matches.append(match_info)

        return matches

    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """获取所有直播比赛"""
        live_matches = []
        for match in self.matches.values():
            if match.is_live():
                match_info = await self.get_match_info(match.match_id)
                if match_info:
                    live_matches.append(match_info)

        return live_matches

    async def subscribe_to_match(self, match_id: int, user_id: str) -> bool:
        """订阅比赛更新"""
        if match_id not in self.matches:
            return False

        self.matches[match_id].subscribers.add(user_id)
        self.logger.info(f"User {user_id} subscribed to match {match_id}")
        return True

    async def unsubscribe_from_match(self, match_id: int, user_id: str) -> bool:
        """取消订阅比赛更新"""
        if match_id not in self.matches:
            return False

        self.matches[match_id].subscribers.discard(user_id)
        self.logger.info(f"User {user_id} unsubscribed from match {match_id}")
        return True

    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        total_matches = len(self.matches)
        live_matches = sum(1 for match in self.matches.values() if match.is_live())
        upcoming_matches = sum(1 for match in self.matches.values() if match.status == MatchStatus.UPCOMING)
        completed_matches = sum(1 for match in self.matches.values() if match.status == MatchStatus.FULLTIME)

        return {
            "service_name": "realtime_match_service",
            "total_matches": total_matches,
            "live_matches": live_matches,
            "upcoming_matches": upcoming_matches,
            "completed_matches": completed_matches,
            "tracked_leagues": len(self.league_matches),
            "total_subscribers": sum(len(match.subscribers) for match in self.matches.values()),
            "is_monitoring": self.is_monitoring,
            "monitoring_interval": self.monitoring_interval,
            "live_update_interval": self.live_update_interval
        }

    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.monitoring_interval)
                await self._check_match_updates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

    async def _live_update_loop(self) -> None:
        """直播更新循环"""
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.live_update_interval)
                await self._update_live_matches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in live update loop: {e}")

    async def _check_match_updates(self) -> None:
        """检查比赛更新（模拟实现）"""
        # 这里应该调用外部API获取最新的比赛数据
        # 现在只是模拟一些随机更新
        current_time = datetime.now()

        for match in list(self.matches.values()):
            if match.status == MatchStatus.UPCOMING:
                # 检查是否应该开始
                if match.start_time and current_time >= match.start_time:
                    await self.update_match_status(match.match_id, MatchStatus.LIVE, current_time)

            elif match.status == MatchStatus.LIVE:
                # 模拟比赛进行中的更新
                if not match.minute:
                    match.minute = 1
                else:
                    match.minute += 1

                # 随机模拟进球
                if match.minute % 15 == 0 and match.home_score is not None:
                    import random
                    if random.random() < 0.3:  # 30%概率进球
                        if random.random() < 0.5:
                            new_home_score = match.home_score + 1
                            new_away_score = match.away_score or 0
                        else:
                            new_home_score = match.home_score or 0
                            new_away_score = (match.away_score or 0) + 1

                        await self.update_match_score(
                            match.match_id,
                            new_home_score,
                            new_away_score,
                            match.minute
                        )

                # 模拟中场休息和结束
                if match.minute == 45:
                    await self.update_match_status(match.match_id, MatchStatus.HALFTIME, current_time)
                elif match.minute == 46:
                    await self.update_match_status(match.match_id, MatchStatus.LIVE, current_time)
                elif match.minute >= 90:
                    await self.update_match_status(match.match_id, MatchStatus.FULLTIME, current_time)

    async def _update_live_matches(self) -> None:
        """更新直播比赛信息"""
        live_matches = [match for match in self.matches.values() if match.is_live()]

        if live_matches:
            # 发送直播状态更新事件
            event = RealtimeEvent(
                event_type=EventType.ANALYTICS_UPDATED,
                data={
                    "metric_name": "live_matches_count",
                    "value": len(live_matches),
                    "previous_value": None,
                    "match_ids": [match.match_id for match in live_matches],
                    "timestamp": datetime.now().isoformat()
                },
                source="match_service"
            )
            await self.websocket_manager.publish_event(event)

    async def _cleanup_old_matches(self) -> None:
        """清理旧比赛"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        old_matches = [
            match_id for match_id, match in self.matches.items()
            if match.last_update and match.last_update < cutoff_time
        ]

        for match_id in old_matches:
            match = self.matches[match_id]
            # 从联赛索引中移除
            if match.league in self.league_matches:
                self.league_matches[match.league].discard(match_id)
                if not self.league_matches[match.league]:
                    del self.league_matches[match.league]

            # 删除比赛
            del self.matches[match_id]

        if old_matches:
            self.logger.info(f"Cleaned up {len(old_matches)} old matches")

    async def broadcast_system_alert(
        self,
        message: str,
        alert_type: str = "info",
        severity: str = "low",
        component: str = "match_service"
    ) -> None:
        """广播系统告警"""
        alert_event = create_system_alert_event(
            alert_type=alert_type,
            message=message,
            component=component,
            severity=severity
        )

        await self.websocket_manager.publish_event(alert_event)


# 全局服务实例
_global_match_service: Optional[RealtimeMatchService] = None


def get_realtime_match_service() -> RealtimeMatchService:
    """获取全局实时比赛服务实例"""
    global _global_match_service
    if _global_match_service is None:
        _global_match_service = RealtimeMatchService()
    return _global_match_service


# 便捷函数
async def add_match_to_monitoring(
    match_id: int,
    home_team: str,
    away_team: str,
    league: str,
    status: str = "upcoming"
) -> bool:
    """添加比赛到监控"""
    service = get_realtime_match_service()
    return await service.add_match(
        match_id, home_team, away_team, league, MatchStatus(status)
    )


async def update_match_score(
    match_id: int,
    home_score: int,
    away_score: int,
    minute: Optional[int] = None
) -> bool:
    """更新比赛比分"""
    service = get_realtime_match_service()
    return await service.update_match_score(match_id, home_score, away_score, minute)


async def get_live_matches() -> List[Dict[str, Any]]:
    """获取直播比赛"""
    service = get_realtime_match_service()
    return await service.get_live_matches()