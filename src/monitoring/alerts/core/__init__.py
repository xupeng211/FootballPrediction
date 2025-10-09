"""
告警核心模块
Alert Core Module

导出告警系统的所有核心组件。
Exports all core components of the alert system.
"""

# 规则引擎
from .rule_engine import (
    AlertRuleEngine,
    RuleEvaluationContext,
)

# 去重器
from .deduplicator import (
    AlertDeduplicator,
    SuppressionRule,
    DeduplicationCache,
)

# 聚合器
from .aggregator import (
    AlertAggregator,
    AlertGroup,
    AggregationRule,
)

# 调度器
from .scheduler import (
    AlertScheduler,
    ScheduledTask,
    AlertTaskFactory,
)

# 主告警管理器
from .alert_manager import (
    AlertManager,
)

__all__ = [
    # 规则引擎
    "AlertRuleEngine",
    "RuleEvaluationContext",

    # 去重器
    "AlertDeduplicator",
    "SuppressionRule",
    "DeduplicationCache",

    # 聚合器
    "AlertAggregator",
    "AlertGroup",
    "AggregationRule",

    # 调度器
    "AlertScheduler",
    "ScheduledTask",
    "AlertTaskFactory",

    # 主告警管理器
    "AlertManager",
]