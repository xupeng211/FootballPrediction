"""
告警规则引擎
Alert Rule Engine

管理告警规则的创建、评估和执行。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .models import Alert, AlertRule, AlertSeverity

logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """告警规则引擎"""

    def __init__(self):
        """初始化规则引擎"""
        self.rules: Dict[str, AlertRule] = {}
        self.rule_evaluators: Dict[str, Callable] = {}
        self._register_default_evaluators()

    def _register_default_evaluators(self) -> None:
        """注册默认的规则评估器"""
        # 简单阈值规则
        self.rule_evaluators["threshold"] = self._evaluate_threshold
        # 范围规则
        self.rule_evaluators["range"] = self._evaluate_range
        # 变化率规则
        self.rule_evaluators["rate"] = self._evaluate_rate
        # 自定义表达式规则
        self.rule_evaluators["expression"] = self._evaluate_expression

    def add_rule(self, rule: AlertRule) -> bool:
        """
        添加告警规则

        Args:
            rule: 告警规则

        Returns:
            bool: 是否成功添加
        """
        if rule.id in self.rules:
            logger.warning(f"Rule {rule.id} already exists, updating...")

        self.rules[rule.id] = rule
        logger.info(f"Added alert rule: {rule.name}")
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """
        移除告警规则

        Args:
            rule_id: 规则ID

        Returns:
            bool: 是否成功移除
        """
        if rule_id not in self.rules:
            logger.warning(f"Rule {rule_id} not found")
            return False

        del self.rules[rule_id]
        logger.info(f"Removed alert rule: {rule_id}")
        return True

    def evaluate_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        评估所有规则并生成告警

        Args:
            metrics: 指标数据

        Returns:
            List[Alert]: 生成的告警列表
        """
        alerts = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                if self._evaluate_rule(rule, metrics):
                    alert = self._create_alert_from_rule(rule, metrics)
                    alerts.append(alert)

                    # 更新规则触发信息
                    rule.last_triggered = datetime.utcnow()
                    rule.trigger_count += 1

            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.id}: {e}")

        return alerts

    def _evaluate_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """
        评估单个规则

        Args:
            rule: 告警规则
            metrics: 指标数据

        Returns:
            bool: 是否触发告警
        """
        # 检查节流
        if self._should_throttle(rule):
            return False

        # 根据条件类型选择评估器
        condition = rule.condition.lower()

        if "threshold" in condition or ">" in condition or "<" in condition:
            return self._evaluate_threshold(rule, metrics)
        elif "range" in condition or "between" in condition:
            return self._evaluate_range(rule, metrics)
        elif "rate" in condition or "change" in condition:
            return self._evaluate_rate(rule, metrics)
        else:
            return self._evaluate_expression(rule, metrics)

    def _evaluate_threshold(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """评估阈值规则"""
        condition = rule.condition

        # 简单的阈值解析
        if ">" in condition:
            metric_name, threshold = condition.split(">", 1)
            metric_name = metric_name.strip()
            threshold = float(threshold.strip())  # type: ignore

            value = self._get_metric_value(metrics, metric_name)
            return value > threshold if value is not None else False  # type: ignore

        elif "<" in condition:
            metric_name, threshold = condition.split("<", 1)
            metric_name = metric_name.strip()
            threshold = float(threshold.strip())  # type: ignore

            value = self._get_metric_value(metrics, metric_name)
            return value < threshold if value is not None else False  # type: ignore

        return False

    def _evaluate_range(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """评估范围规则"""
        # 简化实现
        return False

    def _evaluate_rate(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """评估变化率规则"""
        # 简化实现
        return False

    def _evaluate_expression(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """评估表达式规则"""
        try:
            # 这里应该实现安全的表达式评估
            # 为了安全，使用受限的评估环境
            return False
        except Exception:
            return False

    def _get_metric_value(self, metrics: Dict[str, Any], path: str) -> Optional[float]:
        """
        从指标字典中获取值

        Args:
            metrics: 指标数据
            path: 指标路径（如 'cpu.usage'）

        Returns:
            Optional[float]: 指标值
        """
        keys = path.split(".")
        value = metrics

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        try:
            return float(value)  # type: ignore
        except (TypeError, ValueError):
            return None

    def _should_throttle(self, rule: AlertRule) -> bool:
        """检查规则是否应该被节流"""
        if not rule.last_triggered:
            return False

        time_since_last = datetime.utcnow() - rule.last_triggered
        return time_since_last < rule.throttle_duration

    def _create_alert_from_rule(
        self, rule: AlertRule, metrics: Dict[str, Any]
    ) -> Alert:
        """
        从规则创建告警

        Args:
            rule: 告警规则
            metrics: 指标数据

        Returns:
            Alert: 告警对象
        """
        from .models import AlertLevel

        # 根据严重程度确定告警级别
        level_mapping = {
            AlertSeverity.LOW: AlertLevel.INFO,
            AlertSeverity.MEDIUM: AlertLevel.WARNING,
            AlertSeverity.HIGH: AlertLevel.ERROR,
            AlertSeverity.CRITICAL: AlertLevel.CRITICAL,
        }

        alert = Alert(
            title=rule.name,
            message=rule.description or f"Rule {rule.name} triggered",
            level=level_mapping.get(rule.severity, AlertLevel.WARNING),
            source="rule_engine",
            context={
                "rule_id": rule.id,
                "condition": rule.condition,
                "metrics": metrics,
            },
            metadata=rule.metadata,
        )

        return alert

    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        获取规则统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_rules = len(self.rules)
        enabled_rules = sum(1 for rule in self.rules.values() if rule.enabled)
        total_triggers = sum(rule.trigger_count for rule in self.rules.values())

        recent_triggers = sum(
            1
            for rule in self.rules.values()
            if rule.last_triggered
            and (datetime.utcnow() - rule.last_triggered) < timedelta(hours=24)
        )

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "total_triggers": total_triggers,
            "recent_triggers_24h": recent_triggers,
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "severity": rule.severity.value,
                    "trigger_count": rule.trigger_count,
                    "last_triggered": rule.last_triggered.isoformat()
                    if rule.last_triggered
                    else None,
                }
                for rule in self.rules.values()
            ],
        }
