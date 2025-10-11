"""
告警聚合器
Alert Aggregator

聚合和去重相似的告警，减少告警噪音。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from .models import Alert

logger = logging.getLogger(__name__)


class AlertAggregator:
    """告警聚合器"""

    def __init__(self, aggregation_window: timedelta = timedelta(minutes=5)):
        """
        初始化告警聚合器

        Args:
            aggregation_window: 聚合时间窗口
        """
        self.aggregation_window = aggregation_window
        self.alert_groups: Dict[str, List[Alert]] = {}
        self.active_groups: Set[str] = set()

    def add_alert(self, alert: Alert) -> Optional[Alert]:
        """
        添加告警到聚合器

        Args:
            alert: 告警对象

        Returns:
            Optional[Alert]: 如果告警被聚合返回None，否则返回原始告警
        """
        group_key = self._generate_group_key(alert)

        # 检查是否应该聚合
        if self._should_aggregate(alert, group_key):
            return self._aggregate_alert(alert, group_key)

        # 创建新的告警组
        if group_key not in self.alert_groups:
            self.alert_groups[group_key] = []

        self.alert_groups[group_key].append(alert)
        self.active_groups.add(group_key)

        # 清理过期的告警组
        self._cleanup_expired_groups()

        return alert

    def _generate_group_key(self, alert: Alert) -> str:
        """
        生成告警组的键

        Args:
            alert: 告警对象

        Returns:
            str: 组键
        """
        # 基于标题、来源和级别生成键
        return f"{alert.title}:{alert.source}:{alert.level.value}"

    def _should_aggregate(self, alert: Alert, group_key: str) -> bool:
        """
        检查告警是否应该被聚合

        Args:
            alert: 告警对象
            group_key: 组键

        Returns:
            bool: 是否应该聚合
        """
        if group_key not in self.alert_groups:
            return False

        group = self.alert_groups[group_key]
        if not group:
            return False

        # 检查时间窗口
        latest_alert = max(group, key=lambda a: a.timestamp)
        time_diff = alert.timestamp - latest_alert.timestamp

        return time_diff <= self.aggregation_window

    def _aggregate_alert(self, alert: Alert, group_key: str) -> Optional[Alert]:
        """
        聚合告警

        Args:
            alert: 新告警
            group_key: 组键

        Returns:
            Optional[Alert]: 聚合后的告警或None
        """
        group = self.alert_groups[group_key]

        # 添加到组中
        group.append(alert)

        # 如果是第一次聚合，生成聚合告警
        if len(group) == 2:  # 第二个相同告警触发聚合
            return self._create_aggregated_alert(group)

        return None  # 后续相同告警被静默聚合

    def _create_aggregated_alert(self, alerts: List[Alert]) -> Alert:
        """
        创建聚合告警

        Args:
            alerts: 告警列表

        Returns:
            Alert: 聚合告警
        """
        first_alert = alerts[0]
        count = len(alerts)

        # 创建聚合告警
        aggregated = Alert(
            title=f"[聚合] {first_alert.title}",
            message=f"告警已聚合 {count} 次。{first_alert.message}",
            level=first_alert.level,
            source="alert_aggregator",
            context={
                "original_source": first_alert.source,
                "aggregation_count": count,
                "first_occurrence": first_alert.timestamp.isoformat(),
                "last_occurrence": max(a.timestamp for a in alerts).isoformat(),
                "aggregated_alerts": [a.id for a in alerts],
            },
        )

        return aggregated

    def _cleanup_expired_groups(self) -> None:
        """清理过期的告警组"""
        now = datetime.utcnow()
        expired_groups = []

        for group_key, alerts in self.alert_groups.items():
            if not alerts:
                expired_groups.append(group_key)
                continue

            # 检查组中所有告警是否都已过期
            latest_alert = max(alerts, key=lambda a: a.timestamp)
            if now - latest_alert.timestamp > self.aggregation_window * 2:
                expired_groups.append(group_key)

        for group_key in expired_groups:
            del self.alert_groups[group_key]
            self.active_groups.discard(group_key)

    def get_active_groups(self) -> Dict[str, List[Alert]]:
        """
        获取活跃的告警组

        Returns:
            Dict[str, List[Alert]]: 活跃告警组
        """
        return {
            key: alerts
            for key, alerts in self.alert_groups.items()
            if key in self.active_groups and alerts
        }

    def get_aggregation_statistics(self) -> Dict[str, any]:  # type: ignore
        """
        获取聚合统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_alerts = sum(len(alerts) for alerts in self.alert_groups.values())
        total_groups = len(self.alert_groups)
        active_groups_count = len(self.active_groups)

        # 计算聚合效果
        aggregated_alerts = sum(
            len(alerts) - 1 for alerts in self.alert_groups.values() if len(alerts) > 1
        )

        return {
            "total_alerts": total_alerts,
            "total_groups": total_groups,
            "active_groups": active_groups_count,
            "aggregated_alerts": aggregated_alerts,
            "aggregation_ratio": (
                aggregated_alerts / total_alerts if total_alerts > 0 else 0
            ),
            "aggregation_window_seconds": int(self.aggregation_window.total_seconds()),
        }

    def resolve_group(self, group_key: str, message: str = "") -> bool:
        """
        解决整个告警组

        Args:
            group_key: 组键
            message: 解决消息

        Returns:
            bool: 是否成功解决
        """
        if group_key not in self.alert_groups:
            return False

        for alert in self.alert_groups[group_key]:
            alert.resolve()
            alert.context["resolution_message"] = message

        self.active_groups.discard(group_key)
        return True

    def get_group_history(self, group_key: str) -> List[Alert]:
        """
        获取告警组历史

        Args:
            group_key: 组键

        Returns:
            List[Alert]: 告警历史
        """
        return self.alert_groups.get(group_key, [])

    def clear_all_groups(self) -> None:
        """清空所有告警组"""
        self.alert_groups.clear()
        self.active_groups.clear()
