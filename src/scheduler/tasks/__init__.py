"""
调度任务模块
Scheduler Tasks Module

提供所有Celery调度任务的模块化结构。
"""

from .base import BaseDataTask
from .collection import collect_fixtures, collect_odds, collect_live_scores_conditional
from .features import calculate_features_batch
from .maintenance import cleanup_data, backup_database
from .quality import run_quality_checks
from .predictions import generate_predictions
from .processing import process_bronze_to_silver

# 为了向后兼容性，添加任务别名
calculate_features_task = calculate_features_batch
collect_fixtures_task = collect_fixtures
collect_odds_task = collect_odds
generate_predictions_task = generate_predictions
process_data_task = process_bronze_to_silver

__all__ = [
    # 基础类
    "BaseDataTask",

    # 数据采集任务
    "collect_fixtures",
    "collect_odds",
    "collect_live_scores_conditional",

    # 特征计算任务
    "calculate_features_batch",

    # 维护任务
    "cleanup_data",
    "backup_database",

    # 质量检查任务
    "run_quality_checks",

    # 预测任务
    "generate_predictions",

    # 数据处理任务
    "process_bronze_to_silver",

    # 任务别名（向后兼容）
    "calculate_features_task",
    "collect_fixtures_task",
    "collect_odds_task",
    "generate_predictions_task",
    "process_data_task",
]