"""Celery 应用配置.

基于 Redis 的任务队列系统,支持:
- 多队列任务路由
- 定时任务调度
- 任务重试机制
- 监控指标收集

基于 DATA_DESIGN.md 第3节《任务调度系统》设计.
"""

import logging
import os

from celery import Celery
from celery.schedules import crontab

# 配置日志记录器（用于测试支持）
logger = logging.getLogger(__name__)


# 模拟的数据库管理器类（用于测试支持）
class DatabaseManager:
    """类文档字符串."""

    pass  # 添加pass语句
    """数据库管理器模拟类,用于支持测试"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self.logger = logging.getLogger(f"{__name__}.DatabaseManager")

    def get_connection(self):
        """函数文档字符串."""
        # 添加pass语句
        """获取数据库连接"""
        return None

    def close_connection(self):
        """函数文档字符串."""
        # 添加pass语句
        """关闭数据库连接"""


# 模拟的Redis管理器类（用于测试支持）
class RedisManager:
    """类文档字符串."""

    pass  # 添加pass语句
    """Redis管理器模拟类,用于支持测试"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self.logger = logging.getLogger(f"{__name__}.RedisManager")

    def get_redis_client(self):
        """函数文档字符串."""
        # 添加pass语句
        """获取Redis客户端"""
        return None

    def close_connection(self):
        """函数文档字符串."""
        # 添加pass语句
        """关闭Redis连接"""


# 创建 Celery 应用实例
app = Celery("football_prediction_tasks")

# Redis 配置（作为消息代理和结果后端）
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# 更新配置
app.conf.update(
    # 消息代理配置
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    # 序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区配置
    timezone="UTC",
    enable_utc=True,
    # 任务路由配置
    task_routes={
        "collect_fotmob_data": {"queue": "default"},
        "collect_daily_fixtures": {"queue": "fixtures"},
        "collect_odds_data": {"queue": "odds"},
        "collect_live_scores": {"queue": "scores"},
        "tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "tasks.streaming_tasks.*": {"queue": "streaming"},
        "tasks.backup_tasks.*": {"queue": "backup"},
    },
    # 工作进程配置
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    # 任务超时配置
    task_soft_time_limit=300,  # 5分钟软超时
    task_time_limit=600,  # 10分钟硬超时
    # 结果后端配置
    result_expires=3600,  # 结果1小时后过期
    result_compression="zlib",  # 结果压缩
    # 任务追踪配置
    task_track_started=True,
    task_send_events=True,
    # 队列配置
    task_default_queue="default",
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "fixtures": {
            "exchange": "fixtures",
            "routing_key": "fixtures",
        },
        "odds": {
            "exchange": "odds",
            "routing_key": "odds",
        },
        "scores": {
            "exchange": "scores",
            "routing_key": "scores",
        },
        "maintenance": {
            "exchange": "maintenance",
            "routing_key": "maintenance",
        },
        "backup": {
            "exchange": "backup",
            "routing_key": "backup",
        },
        "features": {
            "exchange": "features",
            "routing_key": "features",
        },
    },
)

# 定时任务配置（Celery Beat）
app.conf.beat_schedule = {
    # 每日赛程采集 - 凌晨2:00
    "collect-daily-fixtures": {
        "task": "collect_daily_fixtures",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "fixtures"},
    },
    # 赔率采集 - 每5分钟
    "collect-odds-regular": {
        "task": "collect_odds_data",
        "schedule": 300.0,  # 5分钟
        "options": {"queue": "odds"},
    },
    # 实时比分采集 - 每2分钟
    "collect-live-scores": {
        "task": "collect_live_scores",
        "schedule": 120.0,  # 2分钟
        "options": {"queue": "scores"},
        "kwargs": {"match_ids": None},  # 采集所有进行中的比赛
    },
    # 数据质量检查 - 每小时
    "hourly-quality-check": {
        "task": "src.tasks.maintenance_tasks.quality_check_task",
        "schedule": crontab(minute=0),  # 每小时
        "options": {"queue": "maintenance"},
    },
    # 错误日志清理 - 每日凌晨4:00
    "daily-error-cleanup": {
        "task": "src.tasks.maintenance_tasks.cleanup_logs_task",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "maintenance"},
        "kwargs": {"days_to_keep": 7},
    },
    # 完整数据管道 - 每日凌晨3:30执行（在采集后，清理前）
    "daily-complete-pipeline": {
        "task": "tasks.pipeline_tasks.complete_data_pipeline",
        "schedule": crontab(hour=3, minute=30),
        "options": {"queue": "features"},
    },
    # 特征计算任务 - 每小时检查一次是否有新数据需要特征计算
    "hourly-feature-calculation": {
        "task": "tasks.pipeline_tasks.trigger_feature_calculation_for_new_matches",
        "schedule": crontab(minute=30),  # 每小时30分执行
        "options": {"queue": "features"},
    },
    # 注意：streaming_tasks 和 backup_tasks 模块暂时禁用
    # 相关任务将在模块修复后重新启用
}

# 显式导入存在的任务模块，确保任务被正确注册
import src.tasks.data_collection_tasks
import src.tasks.pipeline_tasks
import src.tasks.maintenance_tasks
import src.tasks.streaming_tasks
# import src.tasks.backup_tasks  # 暂时禁用，该模块存在导入错误

# 自动发现任务模块 (只导入存在的模块)
app.autodiscover_tasks(
    [
        "src.tasks.data_collection_tasks",
        "src.tasks.pipeline_tasks",
        "src.tasks.maintenance_tasks",
        "src.tasks.streaming_tasks",
        # "src.tasks.backup_tasks",  # 暂时禁用
    ]
)

# 为了向后兼容，提供 celery_app 别名
celery_app = app


class TaskRetryConfig:
    """类文档字符串."""

    pass  # 添加pass语句
    """任务重试配置"""

    # 默认重试配置
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 60  # 秒

    # 各类任务的重试配置
    TASK_RETRY_CONFIGS = {
        "collect_fixtures_task": {
            "max_retries": 3,
            "retry_delay": 300,  # 5分钟
            "retry_backoff": True,
            "retry_jitter": True,
        },
        "collect_odds_task": {
            "max_retries": 3,
            "retry_delay": 60,  # 1分钟
            "retry_backoff": True,
            "retry_jitter": False,
        },
        "collect_scores_task": {
            "max_retries": 3,
            "retry_delay": 30,  # 30秒
            "retry_backoff": False,  # 实时数据不需要退避
            "retry_jitter": False,
        },
    }

    @classmethod
    def get_retry_config(cls, task_name: str) -> dict:
        """获取任务的重试配置."""
        return cls.TASK_RETRY_CONFIGS.get(
            task_name,
            {
                "max_retries": cls.DEFAULT_MAX_RETRIES,
                "retry_delay": cls.DEFAULT_RETRY_DELAY,
                "retry_backoff": False,
                "retry_jitter": False,
            },
        )


# 任务监控配置
TASK_MONITORING = {
    "enable_metrics": True,
    "metrics_export_interval": 30,  # 秒
    "error_threshold": 0.1,  # 10% 错误率阈值
    "latency_threshold": 300,  # 5分钟延迟阈值
}
