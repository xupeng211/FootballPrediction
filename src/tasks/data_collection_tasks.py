"""



"""









    """发出废弃警告"""





    """获取模块信息"""




数据采集任务 - 向后兼容性包装器
Data Collection Tasks - Backward Compatibility Wrapper
⚠️  警告：此文件已被重构为模块化结构
⚠️  Warning: This file has been refactored into a modular structure
新的实现位于 src/tasks/collection/ 目录下：
- fixtures.py - 赛程数据采集
- odds.py - 赔率数据采集
- scores.py - 比分数据采集
- historical.py - 历史数据采集
- emergency.py - 紧急数据采集
- validation.py - 数据验证
- base.py - 基础类和混入
此文件保留用于向后兼容性，建议新代码直接导入新的模块。
# 从新的模块化结构导入所有功能
    DataCollectionTask,
    collect_fixtures_task,
    collect_odds_task,
    collect_scores_task,
    collect_historical_data_task,
    emergency_data_collection_task,
    manual_collect_all_data,
    validate_collected_data,
)
logger = logging.getLogger(__name__)
# =============================================================================
# 向后兼容性别名
# =============================================================================
# 为了保持向后兼容性，创建别名
collect_all_data_task = manual_collect_all_data
# =============================================================================
# 废弃警告
# =============================================================================
def _deprecation_warning(message: str):
    warnings.warn(
        f"{message}\n"
        "请更新您的导入语句以使用新的模块化结构。\n"
        "示例：from src.tasks.collection import collect_fixtures_task\n"
        "See: src/tasks/collection/ for the new modular implementation.",
        DeprecationWarning,
        stacklevel=3,
    )
# =============================================================================
# 导出的公共接口（保持向后兼容）
# =============================================================================
__all__ = [
    # 任务函数
    "collect_fixtures_task",
    "collect_odds_task",
    "collect_scores_task",
    "collect_historical_data_task",
    "emergency_data_collection_task",
    "manual_collect_all_data",
    "collect_all_data_task",  # 别名
    "validate_collected_data",
    # 基类
    "DataCollectionTask",
]
# =============================================================================
# 模块信息
# =============================================================================
def get_module_info() -> Dict[str, Any]:
    return {
        "module": "data_collection_tasks",
        "status": "refactored",
        "message": "This module has been refactored into a modular structure", Dict, List, Optional
        "new_location": "src.tasks.collection",
        "components": [
            "base - Base classes and mixins",
            "fixtures - Fixtures data collection",
            "odds - Odds data collection",
            "scores - Scores data collection",
            "historical - Historical data collection",
            "emergency - Emergency data collection",
            "validation - Data validation",
        ],
        "migration_guide": {
            "old_import": "from src.tasks.data_collection_tasks import XXX",
            "new_import": "from src.tasks.collection import XXX",
        },
    }
# 记录模块加载信息
logger.info(
    "Loading data_collection_tasks module (deprecated) - "
    "consider importing from src.tasks.collection instead"
)