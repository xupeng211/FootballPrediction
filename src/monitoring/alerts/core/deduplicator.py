"""
告警去重器
Alert Deduplicator

实现告警的去重和抑制逻辑，从AlertManager中提取相关功能。
Extracted from AlertManager to handle deduplication and suppression logic.
"""

import hashlib
import logging
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
            def fingerprint(self) -> str:
                import hashlib
                content = f"{self.title}:{self.source}:{self.level.value}"
                return hashlib.md5(content.encode()).hexdigest()

            @property
            def type(self):
                from enum import Enum
                class AlertType(Enum):
                    SYSTEM = "system"
                return AlertType.SYSTEM

            @property
            def severity(self):
                return self.level

            def get_age(self):
                return datetime.utcnow() - self.created_at

logger = logging.getLogger(__name__)


class SuppressionRule:
    """
    抑制规则
    Suppression Rule

    定义告警抑制的规则。
    Defines rules for alert suppression.

    Attributes:
        rule_id (str): 规则ID / Rule ID
        name (str): 规则名称 / Rule name
        condition (Dict[str, Any]): 抑制条件 / Suppression condition
        reason (str): 抑制原因 / Suppression reason
        duration (Optional[timedelta]): 抑制持续时间 / Suppression duration
        enabled (bool): 是否启用 / Whether enabled
        created_at (datetime): 创建时间 / Creation time
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        condition: Dict[str, Any],
        reason: str = "",
        duration: Optional[timedelta] = None,
        enabled: bool = True
    ):
        """
        初始化抑制规则
        Initialize Suppression Rule

        Args:
            rule_id: 规则ID / Rule ID
            name: 规则名称 / Rule name
            condition: 抑制条件 / Suppression condition
            reason: 抑制原因 / Suppression reason
            duration: 抑制持续时间 / Suppression duration
            enabled: 是否启用 / Whether enabled
        """
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.reason = reason or f"Suppressed by rule: {name}"
        self.duration = duration
        self.enabled = enabled
        self.created_at = datetime.utcnow()
        self.suppressed_count = 0
        self.last_suppressed_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """
        检查规则是否过期
        Check if Rule is Expired

        Returns:
            bool: 是否过期 / Whether expired
        """
        if not self.duration:
            return False

        return datetime.utcnow() - self.created_at > self.duration

    def matches(self, alert: Alert) -> bool:
        """
        检查告警是否匹配抑制条件
        Check if Alert Matches Suppression Condition

        Args:
            alert: 告警对象 / Alert object

        Returns:
            bool: 是否匹配 / Whether matches
        """
        if not self.enabled or self.is_expired():
            return False

        return self._match_condition(alert, self.condition)

    def _match_condition(self, alert: Alert, condition: Dict[str, Any]) -> bool:
        """
        匹配条件
        Match Condition

        Args:
            alert: 告警对象 / Alert object
            condition: 条件字典 / Condition dictionary

        Returns:
            bool: 是否匹配 / Whether matches
        """
        for key, value in condition.items():
            if key == "source" and alert.source != value:
                return False
            elif key == "level" and alert.level.value != value:
                return False
            elif key == "severity" and alert.severity.value != value:
                return False
            elif key == "type" and alert.type.value != value:
                return False
            elif key == "labels" and not self._match_labels(alert.labels, value):
                return False
            elif key == "title_contains" and value not in alert.title:
                return False
            elif key == "message_contains" and value not in alert.message:
                return False
            elif key == "age_gt" and alert.get_age() <= timedelta(seconds=value):
                return False
            elif key == "age_lt" and alert.get_age() >= timedelta(seconds=value):
                return False

        return True

    def _match_labels(self, alert_labels: Dict[str, str], rule_labels: Dict[str, str]) -> bool:
        """
        匹配标签
        Match Labels

        Args:
            alert_labels: 告警标签 / Alert labels
            rule_labels: 规则标签 / Rule labels

        Returns:
            bool: 是否匹配 / Whether matches
        """
        for key, value in rule_labels.items():
            if alert_labels.get(key) != value:
                return False
        return True

    def record_suppression(self):
        """记录抑制事件"""
        self.suppressed_count += 1
        self.last_suppressed_at = datetime.utcnow()

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
            "reason": self.reason,
            "enabled": self.enabled,
            "suppressed_count": self.suppressed_count,
            "last_suppressed_at": self.last_suppressed_at.isoformat() if self.last_suppressed_at else None,
            "created_at": self.created_at.isoformat(),
            "is_expired": self.is_expired(),
            "condition": self.condition
        }


class DeduplicationCache:
    """
    去重缓存
    Deduplication Cache

    管理告警指纹的缓存，用于去重。
    Manages alert fingerprint cache for deduplication.

    Attributes:
        cache (Dict[str, datetime]): 指纹缓存 / Fingerprint cache
        window (timedelta): 去重时间窗口 / Deduplication time window
        max_size (int): 最大缓存大小 / Maximum cache size
    """

    def __init__(self, window: timedelta = timedelta(minutes=5), max_size: int = 10000):
        """
        初始化去重缓存
        Initialize Deduplication Cache

        Args:
            window: 去重时间窗口 / Deduplication time window
            max_size: 最大缓存大小 / Maximum cache size
        """
        self.cache: Dict[str, datetime] = {}
        self.window = window
        self.max_size = max_size
        self.logger = logging.getLogger(__name__)

    def is_duplicate(self, fingerprint: str) -> bool:
        """
        检查是否是重复告警
        Check if Alert is Duplicate

        Args:
            fingerprint: 告警指纹 / Alert fingerprint

        Returns:
            bool: 是否重复 / Whether duplicate
        """
        now = datetime.utcnow()

        # 检查缓存中是否有相同的指纹
        if fingerprint in self.cache:
            last_time = self.cache[fingerprint]
            if now - last_time < self.window:
                return True

        # 更新缓存
        self.cache[fingerprint] = now

        # 清理过期和超限的缓存项
        self._cleanup_cache()

        return False

    def _cleanup_cache(self):
        """清理缓存"""
        now = datetime.utcnow()

        # 清理过期项
        expired_keys = [
            key for key, time in self.cache.items()
            if now - time > self.window
        ]
        for key in expired_keys:
            del self.cache[key]

        # 如果仍然超过最大大小，清理最旧的项
        if len(self.cache) > self.max_size:
            # 按时间排序，删除最旧的项
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1])
            excess_count = len(self.cache) - self.max_size

            for key, _ in sorted_items[:excess_count]:
                del self.cache[key]

        self.logger.debug(f"Cache cleanup completed. Current size: {len(self.cache)}")

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.logger.info("Deduplication cache cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        Get Cache Statistics

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "window_seconds": self.window.total_seconds(),
            "utilization": len(self.cache) / self.max_size if self.max_size > 0 else 0
        }


class AlertDeduplicator:
    """
    告警去重器
    Alert Deduplicator

    负责告警的去重和抑制功能。
    Handles alert deduplication and suppression functionality.

    Attributes:
        suppression_rules (Dict[str, SuppressionRule]): 抑制规则 / Suppression rules
        deduplication_cache (DeduplicationCache): 去重缓存 / Deduplication cache
        logger: 日志记录器 / Logger
    """

    def __init__(self, deduplication_window: timedelta = timedelta(minutes=5)):
        """
        初始化告警去重器
        Initialize Alert Deduplicator

        Args:
            deduplication_window: 去重时间窗口 / Deduplication time window
        """
        self.suppression_rules: Dict[str, SuppressionRule] = {}
        self.deduplication_cache = DeduplicationCache(deduplication_window)
        self.logger = logging.getLogger(__name__)

        # 初始化默认抑制规则
        self._init_default_suppression_rules()

    def _init_default_suppression_rules(self):
        """初始化默认抑制规则"""
        # 抑制测试环境告警
        self.add_suppression_rule(SuppressionRule(
            rule_id="suppress_test_env",
            name="抑制测试环境告警",
            condition={"labels": {"environment": "test"}},
            reason="测试环境告警被抑制"
        ))

        # 抑制调试级别的告警
        self.add_suppression_rule(SuppressionRule(
            rule_id="suppress_debug_level",
            name="抑制调试级别告警",
            condition={"level": "debug"},
            reason="调试级别告警被抑制"
        ))

        # 抑制特定源的告警
        self.add_suppression_rule(SuppressionRule(
            rule_id="suppress_health_checks",
            name="抑制健康检查告警",
            condition={"source": "health_check"},
            reason="健康检查告警被抑制"
        ))

    def add_suppression_rule(self, rule: SuppressionRule):
        """
        添加抑制规则
        Add Suppression Rule

        Args:
            rule: 抑制规则 / Suppression rule
        """
        self.suppression_rules[rule.rule_id] = rule
        self.logger.info(f"Added suppression rule: {rule.rule_id}")

    def remove_suppression_rule(self, rule_id: str):
        """
        移除抑制规则
        Remove Suppression Rule

        Args:
            rule_id: 规则ID / Rule ID
        """
        if rule_id in self.suppression_rules:
            del self.suppression_rules[rule_id]
            self.logger.info(f"Removed suppression rule: {rule_id}")

    def enable_suppression_rule(self, rule_id: str):
        """
        启用抑制规则
        Enable Suppression Rule

        Args:
            rule_id: 规则ID / Rule ID
        """
        if rule_id in self.suppression_rules:
            self.suppression_rules[rule_id].enabled = True
            self.logger.info(f"Enabled suppression rule: {rule_id}")

    def disable_suppression_rule(self, rule_id: str):
        """
        禁用抑制规则
        Disable Suppression Rule

        Args:
            rule_id: 规则ID / Rule ID
        """
        if rule_id in self.suppression_rules:
            self.suppression_rules[rule_id].enabled = False
            self.logger.info(f"Disabled suppression rule: {rule_id}")

    def is_suppressed(self, alert: Alert) -> Tuple[bool, Optional[str]]:
        """
        检查告警是否被抑制
        Check if Alert is Suppressed

        Args:
            alert: 告警对象 / Alert object

        Returns:
            Tuple[bool, Optional[str]]: 是否被抑制和原因 / Whether suppressed and reason
        """
        for rule in self.suppression_rules.values():
            if rule.matches(alert):
                rule.record_suppression()
                reason = rule.reason
                self.logger.info(f"Alert suppressed by rule {rule.rule_id}: {reason}")
                return True, reason

        return False, None

    def is_duplicate(self, alert: Alert) -> bool:
        """
        检查是否是重复告警
        Check if Alert is Duplicate

        Args:
            alert: 告警对象 / Alert object

        Returns:
            bool: 是否重复 / Whether duplicate
        """
        return self.deduplication_cache.is_duplicate(alert.fingerprint)

    def should_process_alert(self, alert: Alert) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该处理告警
        Determine if Alert Should be Processed

        Args:
            alert: 告警对象 / Alert object

        Returns:
            Tuple[bool, Optional[str]]: 是否应该处理和原因 / Whether should process and reason
        """
        # 首先检查抑制
        suppressed, suppression_reason = self.is_suppressed(alert)
        if suppressed:
            return False, suppression_reason

        # 然后检查重复
        if self.is_duplicate(alert):
            return False, "Duplicate alert"

        return True, None

    def get_suppression_rule(self, rule_id: str) -> Optional[SuppressionRule]:
        """
        获取抑制规则
        Get Suppression Rule

        Args:
            rule_id: 规则ID / Rule ID

        Returns:
            Optional[SuppressionRule]: 抑制规则 / Suppression rule
        """
        return self.suppression_rules.get(rule_id)

    def get_all_suppression_rules(self) -> List[SuppressionRule]:
        """
        获取所有抑制规则
        Get All Suppression Rules

        Returns:
            List[SuppressionRule]: 抑制规则列表 / List of suppression rules
        """
        return list(self.suppression_rules.values())

    def get_enabled_suppression_rules(self) -> List[SuppressionRule]:
        """
        获取启用的抑制规则
        Get Enabled Suppression Rules

        Returns:
            List[SuppressionRule]: 启用的抑制规则列表 / List of enabled suppression rules
        """
        return [rule for rule in self.suppression_rules.values() if rule.enabled]

    def cleanup_expired_rules(self):
        """清理过期的抑制规则"""
        expired_rules = [
            rule_id for rule_id, rule in self.suppression_rules.items()
            if rule.is_expired()
        ]

        for rule_id in expired_rules:
            del self.suppression_rules[rule_id]
            self.logger.info(f"Removed expired suppression rule: {rule_id}")

        if expired_rules:
            self.logger.info(f"Cleaned up {len(expired_rules)} expired suppression rules")

    def clear_deduplication_cache(self):
        """清空去重缓存"""
        self.deduplication_cache.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取去重器统计信息
        Get Deduplicator Statistics

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        total_suppressions = sum(
            rule.suppressed_count for rule in self.suppression_rules.values()
        )

        active_suppressions = len([
            rule for rule in self.suppression_rules.values()
            if rule.enabled and not rule.is_expired()
        ])

        return {
            "suppression_rules": {
                "total": len(self.suppression_rules),
                "enabled": active_suppressions,
                "disabled": len(self.suppression_rules) - active_suppressions,
                "total_suppressions": total_suppressions
            },
            "deduplication_cache": self.deduplication_cache.get_statistics(),
            "recent_suppressions": [
                {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "count": rule.suppressed_count,
                    "last_suppressed": rule.last_suppressed_at.isoformat() if rule.last_suppressed_at else None
                }
                for rule in sorted(
                    self.suppression_rules.values(),
                    key=lambda x: x.last_suppressed_at or datetime.min,
                    reverse=True
                )[:5]
            ]
        }