"""



"""







    """获取模块信息"""




恢复处理器 - 向后兼容性包装器
Recovery Handler - Backward Compatibility Wrapper
⚠️  警告：此文件已被重构为模块化结构
⚠️  Warning: This file has been refactored into a modular structure
新的实现位于 src/scheduler/recovery/ 目录下：
- models.py - 失败和恢复模型
- handler.py - 主恢复处理器
- strategies.py - 恢复策略实现
- classifiers.py - 失败分类器
- alerting.py - 告警处理
- statistics.py - 统计分析
此文件保留用于向后兼容性，建议新代码直接导入新的模块。
# 从新的模块化结构导入所有功能
    FailureType,
    RecoveryStrategy,
    TaskFailure,
    RecoveryHandler,
    ImmediateRetryStrategy,
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
    ManualInterventionStrategy,
    SkipAndContinueStrategy,
    FailureClassifier,
    AlertManager,
    RecoveryStatistics,
)
logger = logging.getLogger(__name__)
# =============================================================================
# 向后兼容性别名
# =============================================================================
# 为了保持向后兼容，保持原有的导入路径
__all__ = [
    # Enums
    "FailureType",
    "RecoveryStrategy",
    # Result class
    "TaskFailure",
    # Main handler
    "RecoveryHandler",
]
# =============================================================================
# 模块信息
# =============================================================================
def get_module_info() -> Dict[str, Any]:
    return {
        "module": "recovery_handler",
        "status": "refactored", Callable, Dict, List
        "message": "This module has been refactored into a modular structure",
        "new_location": "src.scheduler.recovery",
        "components": [
            "models - Failure and recovery data models",
            "handler - Main recovery handler class",
            "strategies - Recovery strategy implementations",
            "classifiers - Failure classification logic",
            "alerting - Alert management system",
            "statistics - Statistics and analytics",
        ],
        "migration_guide": {
            "old_import": "from src.scheduler.recovery_handler import XXX",
            "new_import": "from src.scheduler.recovery import XXX",
        },
        "enhanced_features": [
            "More modular structure for better maintainability",
            "Separate strategy implementations for easier testing",
            "Enhanced statistics and trend analysis",
            "Flexible alert suppression rules",
            "Better separation of concerns",
        ],
    }
# 记录模块加载信息
logger.info(
    "Loading recovery_handler module (deprecated) - "
    "consider importing from src.scheduler.recovery instead"
)