"""
数据采集任务模块
Data Collection Tasks Module

提供各种数据采集任务的实现。
"""

from .base import DataCollectionTask, CollectionTaskMixin
from .fixtures import collect_fixtures_task
from .odds import collect_odds_task
from .scores import collect_scores_task
from .historical import collect_historical_data_task
from .emergency import manual_collect_all_data, emergency_data_collection_task
from .validation import validate_collected_data, DataValidator, DataValidationError

# 为了向后兼容
collect_all_data_task = manual_collect_all_data

__all__ = [
    "DataCollectionTask",
    "CollectionTaskMixin",
    "collect_fixtures_task",
    "collect_odds_task",
    "collect_scores_task",
    "collect_historical_data_task",
    "manual_collect_all_data",
    "emergency_data_collection_task",
    "collect_all_data_task",
    "validate_collected_data",
    "DataValidator",
    "DataValidationError",
]