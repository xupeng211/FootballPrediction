"""
告警管理器
Alert Manager

告警系统的核心管理器，协调各个组件。
Alert system core manager that coordinates various components.

注意：此文件已被拆分为多个模块以提供更好的组织结构。
Warning: This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出新的核心模块中的AlertManager类。
For backward compatibility, this file re-exports the AlertManager class from the new core module.

建议直接使用: from src.monitoring.alerts.core import AlertManager
Recommended: from src.monitoring.alerts.core import AlertManager
"""


# 发出弃用警告
warnings.warn(
    "从 alert_manager_mod.manager 导入已弃用。"
    "请从 src.monitoring.alerts.core import AlertManager。"
    "Direct imports from alert_manager_mod.manager are deprecated. "
    "Please import AlertManager from src.monitoring.alerts.core instead.",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块重新导出AlertManager
# Import moved to top

try:
except ImportError:
    # 如果导入失败，创建一个基本的占位符

    logger = logging.getLogger(__name__)

    class AlertManager:
        """
        占位符告警管理器
        Placeholder Alert Manager

        当无法导入新的核心模块时使用。
        Used when the new core module cannot be imported.
        """

        def __init__(self, config: Optional[Dict[str, Any]] = None):
            """初始化占位符管理器"""
            self.config = config or {}
            self.logger = logging.getLogger(__name__)
            self.logger.warning("Using placeholder AlertManager - core module not available")

        async def start(self):
            """启动占位符管理器"""
            pass

        async def stop(self):
            """停止占位符管理器"""
            pass

        async def create_alert(self, *args, **kwargs):
            """创建告警（占位符）"""
            self.logger.warning("create_alert called on placeholder AlertManager")

            return None

        # 添加其他必要的方法占位符...
        def get_alert(self, alert_id: str):
            return None

        def get_active_alerts(self):
            return []

        def get_statistics(self):
            return {"error": "Placeholder AlertManager"}

# 保持向后兼容的导入
if 'AlertManager' in globals():
    # 导出AlertManager和相关的类型（如果可用）
    __all__ = ['AlertManager']

    # 尝试导出相关的枚举和模型
    # Import moved to top

    try:
            Alert, AlertLevel, AlertStatus, AlertRule,
            AlertSeverity, AlertType, AlertChannel
        )
        __all__.extend([
            'Alert', 'AlertLevel', 'AlertStatus', 'AlertRule',
            'AlertSeverity', 'AlertType', 'AlertChannel'
        ])
    except ImportError:
        pass