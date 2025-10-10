"""
数据收集任务
Data Collection Tasks

提供各种数据收集任务的定义和执行。
"""

# 导入所有必要的类，保持向后兼容
from .data_collectors import (
    DataCollector,
    FixturesCollector,
    HistoricalDataCollector,
    DataCollectionOrchestrator,
)

from .data_collection_core import (
    DataCollectionTask,
    collect_fixtures_task,
    collect_odds_task,
    collect_scores_task,
    manual_collect_all_data,
    emergency_data_collection_task,
    collect_historical_data_task,
    validate_collected_data,
)

# 导出所有公共接口
__all__ = [
    # 类
    "DataCollectionTask",
    "DataCollector",
    "FixturesCollector",
    "HistoricalDataCollector",
    "DataCollectionOrchestrator",
    # 任务
    "collect_fixtures_task",
    "collect_odds_task",
    "collect_scores_task",
    "manual_collect_all_data",
    "emergency_data_collection_task",
    "collect_historical_data_task",
    # 函数
    "validate_collected_data",
]
