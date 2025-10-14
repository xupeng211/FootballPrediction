from typing import Any, Dict, List, Optional, Union
"""
足球预测系统任务调度模块

基于 Celery 实现的分布式任务队列系统，用于：
- 定时数据采集（比分数据、赔率数据）
- 数据处理和特征计算
- 系统维护和数据清理
- 错误重试和日志记录

主要功能：
- 支持多队列任务分发
- API失败自动重试3次
- 完整的错误日志记录
- 可配置的调度周期
- Prometheus指标导出
"""

from .celery_app import app as celery_app
from .data_collection_tasks import (
    collect_fixtures_task,
    collect_odds_task,
    collect_scores_task,
)
from .error_logger import TaskErrorLogger
from .monitoring import TaskMonitor

__all__ = [
    "celery_app",
    "collect_fixtures_task",
    "collect_odds_task",
    "collect_scores_task",
    "TaskErrorLogger",
    "TaskMonitor",
]
