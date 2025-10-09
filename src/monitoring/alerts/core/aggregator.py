"""
告警聚合器
Alert Aggregator

实现告警的聚合、分组功能，从AlertManager中提取相关逻辑。
Extracted from AlertManager to handle alert aggregation and grouping logic.
"""

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

# 尝试从不同位置导入模型
try:
    from ..models import Alert, AlertStatus
except ImportError:
    try:
        from monitoring.alerts.models import Alert, AlertStatus
    except ImportError:
        # 创建基本类型
        from enum import Enum
        from datetime import datetime
        from typing import Any, Dict, Optional

        class AlertStatus(Enum):
            ACTIVE = "active"
            RESOLVED = "resolved"
            SUPPRESSED = "suppressed"
            SILENCED = "silenced"

        class Alert:
            def __init__(self, alert_id: str, title: str, message: str, level: Any, source: str, **kwargs):
                self.alert_id = alert_id
                self.title = title
                self.message = message
                self.level = level
                self.source = source
                self.status = AlertStatus.ACTIVE
                self.created_at = datetime.utcnow()
                self.labels = kwargs.get('labels', {})

            @property
            def type(self):
                from enum import Enum
                class AlertType(Enum):
                    SYSTEM = "system"
                return AlertType.SYSTEM

            @property
            def severity(self):
                return self.level

            def is_active(self) -> bool:
                return self.status == AlertStatus.ACTIVE

            def is_resolved(self) -> bool:
                return self.status == AlertStatus.RESOLVED

logger = logging.getLogger(__name__)


class AggregationRule:
    """
    聚合规则
    Aggregation Rule

    定义告警聚合的规则。
    Defines rules for alert aggregation.

    Attributes:
        rule_id (str): 规则ID / Rule ID
        name (str): 规则名称 / Rule name
        group_by (List[str]): 分组字段 / Grouping fields
        window (timedelta): 聚合时间窗口 / Aggregation time window
        threshold (int): 聚合阈值 / Aggregation threshold
        enabled (bool): 是否启用 / Whether enabled
        created_at (datetime): 创建时间 / Creation time
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        group_by: List[str],
        window: timedelta = timedelta(minutes=10),
        threshold: int = 5,
        enabled: bool = True
    ):
        """
        初始化聚合规则
        Initialize Aggregation Rule

        Args:
            rule_id: 规则ID / Rule ID
            name: 规则名称 / Rule name
            group_by: 分组字段 / Grouping fields
            window: 聚合时间窗口 / Aggregation time window
            threshold: 聚合阈值 / Aggregation threshold
            enabled: 是否启用 / Whether enabled
        """
        self.rule_id = rule_id
        self.name = name
        self.group_by = group_by
        self.window = window
        self.threshold = threshold
        self.enabled = enabled
        self.created_at = datetime.utcnow()
        self.aggregated_count = 0
        self.last_aggregated_at: Optional[datetime] = None

    def should_aggregate(self, alert: Alert, existing_group: 'AlertGroup') -> bool:
        """
        判断是否应该聚合到现有组
        Determine if Should Aggregate to Existing Group

        Args:
            alert: 告警对象 / Alert object
            existing_group: 现有告警组 / Existing alert group

        Returns:
            bool: 是否应该聚合 / Whether should aggregate
        """
        if not self.enabled:
            return False

        # 检查时间窗口
        if alert.created_at < existing_group.created_at + self.window:
            # 检查分组条件
            return self._belongs_to_group(alert, existing_group)

        return False

    def _belongs_to_group(self, alert: Alert, group: 'AlertGroup') -> bool:
        """
        检查告警是否属于组
        Check if Alert Belongs to Group

        Args:
            alert: 告警对象 / Alert object
            group: 告警组 / Alert group

        Returns:
            bool: 是否属于 / Whether belongs
        """
        for group_by in self.group_by:
            if group_by == "source" and alert.source != group.labels.get("source"):
                return False
            elif group_by == "level" and alert.level.value != group.labels.get("level"):
                return False
            elif group_by == "type" and alert.type.value != group.labels.get("type"):
                return False
            elif group_by.startswith("labels."):
                label_key = group_by[7:]  # 移除 "labels." 前缀
                if alert.labels.get(label_key) != group.labels.get(label_key):
                    return False

        return True

    def generate_group_key(self, alert: Alert) -> str:
        """
        生成分组键
        Generate Group Key

        Args:
            alert: 告警对象 / Alert object

        Returns:
            str: 分组键 / Group key
        """
        key_parts = [self.rule_id]

        for group_by in self.group_by:
            if group_by == "source":
                key_parts.append(alert.source)
            elif group_by == "level":
                key_parts.append(alert.level.value)
            elif group_by == "type":
                key_parts.append(alert.type.value)
            elif group_by.startswith("labels."):
                label_key = group_by[7:]
                key_parts.append(alert.labels.get(label_key, ""))

        return "|".join(key_parts)

    def should_trigger_aggregated_alert(self, group: 'AlertGroup') -> bool:
        """
        检查是否应该触发聚合告警
        Check if Should Trigger Aggregated Alert

        Args:
            group: 告警组 / Alert group

        Returns:
            bool: 是否应该触发 / Whether should trigger
        """
        return group.get_active_count() >= self.threshold

    def record_aggregation(self):
        """记录聚合事件"""
        self.aggregated_count += 1
        self.last_aggregated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        Convert to Dictionary

        Returns:
            Dict[str, Any]: 字典表示 / Dictionary representation
        """
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "group_by": self.group_by,
            "window_seconds": self.window.total_seconds(),
            "threshold": self.threshold,
            "enabled": self.enabled,
            "aggregated_count": self.aggregated_count,
            "last_aggregated_at": self.last_aggregated_at.isoformat() if self.last_aggregated_at else None,
            "created_at": self.created_at.isoformat()
        }


class AlertGroup:
    """
    告警组
    Alert Group

    表示一组相关的告警。
    Represents a group of related alerts.

    Attributes:
        group_id (str): 组ID / Group ID
        name (str): 组名 / Group name
        alerts (List[Alert]): 告警列表 / List of alerts
        created_at (datetime): 创建时间 / Creation time
        updated_at (datetime): 更新时间 / Update time
        status (AlertStatus): 组状态 / Group status
        labels (Dict[str, str]): 组标签 / Group labels
    """

    def __init__(self, group_id: str, name: str, labels: Optional[Dict[str, str]] = None):
        """
        初始化告警组
        Initialize Alert Group

        Args:
            group_id: 组ID / Group ID
            name: 组名 / Group name
            labels: 组标签 / Group labels
        """
        self.group_id = group_id
        self.name = name
        self.alerts: List[Alert] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.status = AlertStatus.ACTIVE
        self.labels = labels or {}

    def add_alert(self, alert: Alert):
        """
        添加告警
        Add Alert

        Args:
            alert: 告警对象 / Alert object
        """
        if alert not in self.alerts:
            self.alerts.append(alert)
            self.updated_at = datetime.utcnow()

    def remove_alert(self, alert: Alert):
        """
        移除告警
        Remove Alert

        Args:
            alert: 告警对象 / Alert object
        """
        if alert in self.alerts:
            self.alerts.remove(alert)
            self.updated_at = datetime.utcnow()

    def get_active_count(self) -> int:
        """
        获取活跃告警数量
        Get Active Alert Count

        Returns:
            int: 活跃告警数量 / Active alert count
        """
        return sum(1 for alert in self.alerts if alert.is_active())

    def get_resolved_count(self) -> int:
        """
        获取已解决告警数量
        Get Resolved Alert Count

        Returns:
            int: 已解决告警数量 / Resolved alert count
        """
        return sum(1 for alert in self.alerts if alert.is_resolved())

    def get_highest_severity(self) -> Optional[str]:
        """
        获取最高严重级别
        Get Highest Severity

        Returns:
            Optional[str]: 最高严重级别 / Highest severity
        """
        if not self.alerts:
            return None

        severity_order = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        highest = None
        highest_level = 0

        for alert in self.alerts:
            if alert.is_active():
                level = severity_order.get(alert.severity.value, 0)
                if level > highest_level:
                    highest = alert.severity.value
                    highest_level = level

        return highest

    def update_status(self):
        """更新组状态"""
        active_count = self.get_active_count()
        if active_count == 0:
            self.status = AlertStatus.RESOLVED
        else:
            self.status = AlertStatus.ACTIVE

    def get_sources(self) -> Set[str]:
        """
        获取告警源
        Get Alert Sources

        Returns:
            Set[str]: 告警源集合 / Set of alert sources
        """
        return set(alert.source for alert in self.alerts)

    def get_levels(self) -> Set[str]:
        """
        获取告警级别
        Get Alert Levels

        Returns:
            Set[str]: 告警级别集合 / Set of alert levels
        """
        return set(alert.level.value for alert in self.alerts)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        Convert to Dictionary

        Returns:
            Dict[str, Any]: 字典表示 / Dictionary representation
        """
        return {
            "group_id": self.group_id,
            "name": self.name,
            "status": self.status.value,
            "alert_count": len(self.alerts),
            "active_count": self.get_active_count(),
            "resolved_count": self.get_resolved_count(),
            "highest_severity": self.get_highest_severity(),
            "sources": list(self.get_sources()),
            "levels": list(self.get_levels()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "labels": self.labels,
        }


class AlertAggregator:
    """
    告警聚合器
    Alert Aggregator

    负责告警的聚合、分组功能。
    Handles alert aggregation and grouping functionality.

    Attributes:
        groups (Dict[str, AlertGroup]): 告警组 / Alert groups
        aggregation_rules (Dict[str, AggregationRule]): 聚合规则 / Aggregation rules
        logger: 日志记录器 / Logger
    """

    def __init__(self):
        """初始化告警聚合器"""
        self.groups: Dict[str, AlertGroup] = {}
        self.aggregation_rules: Dict[str, AggregationRule] = {}
        self.logger = logging.getLogger(__name__)

        # 初始化默认聚合规则
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认聚合规则"""
        # 按源聚合
        self.add_aggregation_rule(AggregationRule(
            rule_id="by_source",
            name="按源聚合",
            group_by=["source"],
            window=timedelta(minutes=15),
            threshold=5
        ))

        # 按级别聚合
        self.add_aggregation_rule(AggregationRule(
            rule_id="by_level",
            name="按级别聚合",
            group_by=["level"],
            window=timedelta(minutes=10),
            threshold=3
        ))

        # 按服务标签聚合
        self.add_aggregation_rule(AggregationRule(
            rule_id="by_service",
            name="按服务聚合",
            group_by=["labels.service"],
            window=timedelta(minutes=20),
            threshold=4
        ))

        # 按源和级别聚合
        self.add_aggregation_rule(AggregationRule(
            rule_id="by_source_level",
            name="按源和级别聚合",
            group_by=["source", "level"],
            window=timedelta(minutes=12),
            threshold=3
        ))

    def add_aggregation_rule(self, rule: AggregationRule):
        """
        添加聚合规则
        Add Aggregation Rule

        Args:
            rule: 聚合规则 / Aggregation rule
        """
        self.aggregation_rules[rule.rule_id] = rule
        self.logger.info(f"Added aggregation rule: {rule.rule_id}")

    def remove_aggregation_rule(self, rule_id: str):
        """
        移除聚合规则
        Remove Aggregation Rule

        Args:
            rule_id: 规则ID / Rule ID
        """
        if rule_id in self.aggregation_rules:
            del self.aggregation_rules[rule_id]
            self.logger.info(f"Removed aggregation rule: {rule_id}")

    def enable_aggregation_rule(self, rule_id: str):
        """
        启用聚合规则
        Enable Aggregation Rule

        Args:
            rule_id: 规则ID / Rule ID
        """
        if rule_id in self.aggregation_rules:
            self.aggregation_rules[rule_id].enabled = True
            self.logger.info(f"Enabled aggregation rule: {rule_id}")

    def disable_aggregation_rule(self, rule_id: str):
        """
        禁用聚合规则
        Disable Aggregation Rule

        Args:
            rule_id: 规则ID / Rule ID
        """
        if rule_id in self.aggregation_rules:
            self.aggregation_rules[rule_id].enabled = False
            self.logger.info(f"Disabled aggregation rule: {rule_id}")

    def aggregate_alert(self, alert: Alert) -> List[AlertGroup]:
        """
        聚合告警
        Aggregate Alert

        Args:
            alert: 告警对象 / Alert object

        Returns:
            List[AlertGroup]: 受影响的告警组 / Affected alert groups
        """
        affected_groups = []

        for rule in self.aggregation_rules.values():
            if not rule.enabled:
                continue

            # 查找匹配的现有组
            existing_group = self._find_matching_group(alert, rule)
            if existing_group:
                existing_group.add_alert(alert)
                affected_groups.append(existing_group)

                # 检查是否需要触发聚合告警
                if rule.should_trigger_aggregated_alert(existing_group):
                    self._trigger_aggregated_alert(existing_group, rule)
            else:
                # 创建新组
                new_group = self._create_group(alert, rule)
                if new_group:
                    affected_groups.append(new_group)

        return affected_groups

    def _find_matching_group(self, alert: Alert, rule: AggregationRule) -> Optional[AlertGroup]:
        """
        查找匹配的现有组
        Find Matching Existing Group

        Args:
            alert: 告警对象 / Alert object
            rule: 聚合规则 / Aggregation rule

        Returns:
            Optional[AlertGroup]: 匹配的告警组 / Matching alert group
        """
        for group in self.groups.values():
            if rule.should_aggregate(alert, group):
                return group
        return None

    def _create_group(self, alert: Alert, rule: AggregationRule) -> Optional[AlertGroup]:
        """
        创建新的告警组
        Create New Alert Group

        Args:
            alert: 告警对象 / Alert object
            rule: 聚合规则 / Aggregation rule

        Returns:
            Optional[AlertGroup]: 新的告警组 / New alert group
        """
        # 生成分组键和组ID
        group_key = rule.generate_group_key(alert)
        group_id = f"group_{hashlib.md5(group_key.encode()).hexdigest()[:8]}"

        # 创建组名
        group_name = f"Aggregated Alert ({rule.name})"

        # 生成组标签
        group_labels = {"aggregation_rule": rule.rule_id}
        for group_by in rule.group_by:
            if group_by == "source":
                group_labels["source"] = alert.source
            elif group_by == "level":
                group_labels["level"] = alert.level.value
            elif group_by == "type":
                group_labels["type"] = alert.type.value
            elif group_by.startswith("labels."):
                label_key = group_by[7:]
                if label_key in alert.labels:
                    group_labels[label_key] = alert.labels[label_key]

        # 创建告警组
        group = AlertGroup(group_id, group_name, group_labels)
        group.add_alert(alert)

        # 添加到组集合
        self.groups[group_id] = group

        self.logger.debug(f"Created new alert group: {group_id}")
        return group

    def _trigger_aggregated_alert(self, group: AlertGroup, rule: AggregationRule):
        """
        触发聚合告警
        Trigger Aggregated Alert

        Args:
            group: 告警组 / Alert group
            rule: 聚合规则 / Aggregation rule
        """
        rule.record_aggregation()

        self.logger.info(
            f"Aggregated alert triggered for group {group.group_id}: "
            f"{group.get_active_count()} alerts (rule: {rule.rule_id})"
        )

    def get_group(self, group_id: str) -> Optional[AlertGroup]:
        """
        获取告警组
        Get Alert Group

        Args:
            group_id: 组ID / Group ID

        Returns:
            Optional[AlertGroup]: 告警组 / Alert group
        """
        return self.groups.get(group_id)

    def get_all_groups(self) -> List[AlertGroup]:
        """
        获取所有告警组
        Get All Alert Groups

        Returns:
            List[AlertGroup]: 告警组列表 / List of alert groups
        """
        return list(self.groups.values())

    def get_active_groups(self) -> List[AlertGroup]:
        """
        获取活跃告警组
        Get Active Alert Groups

        Returns:
            List[AlertGroup]: 活跃告警组列表 / List of active alert groups
        """
        return [group for group in self.groups.values() if group.status == AlertStatus.ACTIVE]

    def remove_old_groups(self, older_than: timedelta = timedelta(hours=24)):
        """
        移除旧的告警组
        Remove Old Alert Groups

        Args:
            older_than: 时间阈值 / Time threshold
        """
        now = datetime.utcnow()
        to_remove = []

        for group_id, group in self.groups.items():
            if now - group.updated_at > older_than and group.status == AlertStatus.RESOLVED:
                to_remove.append(group_id)

        for group_id in to_remove:
            del self.groups[group_id]
            self.logger.info(f"Removed old alert group: {group_id}")

        if to_remove:
            self.logger.info(f"Removed {len(to_remove)} old alert groups")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取聚合统计信息
        Get Aggregation Statistics

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        total_groups = len(self.groups)
        active_groups = len(self.get_active_groups())
        total_alerts = sum(len(group.alerts) for group in self.groups.values())
        total_active_alerts = sum(group.get_active_count() for group in self.groups.values())

        return {
            "groups": {
                "total": total_groups,
                "active": active_groups,
                "resolved": total_groups - active_groups,
            },
            "alerts": {
                "total": total_alerts,
                "active": total_active_alerts,
                "resolved": total_alerts - total_active_alerts,
            },
            "rules": {
                "total": len(self.aggregation_rules),
                "enabled": len([r for r in self.aggregation_rules.values() if r.enabled]),
                "disabled": len([r for r in self.aggregation_rules.values() if not r.enabled]),
                "total_aggregations": sum(r.aggregated_count for r in self.aggregation_rules.values())
            }
        }