"""
Celery调度任务
Celery Scheduler Tasks

实现足球数据采集和处理的定时任务。

⚠️ 注意:此文件已重构为模块化结构。
为了向后兼容性,这里保留了原始的导入接口。
建议使用:from src.scheduler.tasks import <task_name>

基于 DATA_DESIGN.md 第3节设计.
"""

from .tasks import (  # 为了向后兼容性,从新的模块化结构中导入所有任务; 基础类; 数据采集任务; 特征计算任务; 维护任务; 质量检查任务; 预测任务; 数据处理任务; 任务别名（向后兼容）
    BaseDataTask, backup_database, calculate_features_batch,
    calculate_features_task, cleanup_data, collect_fixtures,
    collect_fixtures_task, collect_live_scores_conditional, collect_odds,
    collect_odds_task, generate_predictions, generate_predictions_task,
    process_bronze_to_silver, process_data_task, run_quality_checks)

# 重新导出以保持原始接口
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

# 原始实现已移至 src/scheduler/tasks/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有任务:
# - collect_fixtures: 采集赛程数据
# - collect_odds: 采集赔率数据
# - collect_live_scores_conditional: 条件性实时比分采集
# - calculate_features_batch: 批量计算特征
# - cleanup_data: 数据清理
# - backup_database: 数据库备份
# - run_quality_checks: 数据质量检查
# - generate_predictions: 生成预测
# - process_bronze_to_silver: Bronze到Silver数据处理
