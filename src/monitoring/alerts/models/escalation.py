"""
escalation.py
escalation

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 escalation 导入已弃用。"
    "请从 src/monitoring/alerts/models/escalation_mod 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
from ............src.monitoring.alerts.models.escalation_mod import escalation_rules
from ............src.monitoring.alerts.models.escalation_mod import escalation_engine
from ............src.monitoring.alerts.models.escalation_mod import notification
from ............src.monitoring.alerts.models.escalation_mod import escalation

# 导出所有类
__all__ = [
    "escalation_rules", "escalation_engine", "notification", "escalation"
]
