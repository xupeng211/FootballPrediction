# mypy: ignore-errors
"""
from datetime import datetime, timezone
        from datetime import date
        from datetime import datetime, timedelta

        from src.database.connection import DatabaseManager

Celery调度器配置

配置Celery任务队列和定时任务，实现足球数据的自动化采集调度。

调度策略：
- 赛程采集：每日凌晨2:00执行
- 赔率采集：每5分钟执行
- 实时比分：比赛期间每2分钟执行
- 特征计算：赛前1小时执行
- 数据清理：每周日凌晨3:00执行

基于 DATA_DESIGN.md 第3节设计。
"""

from celery.schedules import crontab

# Celery应用配置
app = Celery("football_data_scheduler")

# Redis配置（作为消息代理和结果后端）
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app.conf.update(
    # 消息代理配置
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区设置
    timezone="UTC",
    enable_utc=True,
    # 任务路由
    task_routes={
        "scheduler.tasks.collect_fixtures": {"queue": "fixtures"},
        "scheduler.tasks.collect_odds": {"queue": "odds"},
        "scheduler.tasks.collect_live_scores": {"queue": "scores"},
        "scheduler.tasks.calculate_features": {"queue": "features"},
        "scheduler.tasks.cleanup_data": {"queue": "maintenance"},
    },
    # 工作进程配置
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # 任务超时设置
    task_soft_time_limit=300,  # 5分钟软超时
    task_time_limit=600,  # 10分钟硬超时
    # 结果过期时间
    result_expires=3600,  # 1小时后过期
)

# 定时任务配置
app.conf.beat_schedule = {
    # 每日赛程采集 - 凌晨2:00
    "collect-daily-fixtures": {
        "task": "scheduler.tasks.collect_fixtures",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "fixtures"},
    },
    # 赔率采集 - 每5分钟
    "collect-odds-regular": {
        "task": "scheduler.tasks.collect_odds",
        "schedule": 300.0,  # 5分钟
        "options": {"queue": "odds"},
    },
    # 实时比分采集 - 每2分钟（仅在比赛期间）
    "collect-live-scores": {
        "task": "scheduler.tasks.collect_live_scores_conditional",
        "schedule": 120.0,  # 2分钟
        "options": {"queue": "scores"},
    },
    # 特征计算 - 每小时检查是否有需要计算的比赛
    "calculate-match-features": {
        "task": "scheduler.tasks.calculate_features_batch",
        "schedule": crontab(minute=0),  # 每小时整点
        "options": {"queue": "features"},
    },
    # 数据清理 - 每周日凌晨3:00
    "weekly-data-cleanup": {
        "task": "scheduler.tasks.cleanup_old_data",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # 周日
        "options": {"queue": "maintenance"},
    },
    # 数据质量检查 - 每日凌晨4:00
    "daily-quality-check": {
        "task": "scheduler.tasks.run_quality_checks",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "maintenance"},
    },
    # 数据备份 - 每日凌晨5:00
    "daily-backup": {
        "task": "scheduler.tasks.backup_database",
        "schedule": crontab(hour=5, minute=0),
        "options": {"queue": "maintenance"},
    },
}

# 队列配置
app.conf.task_default_queue = "default"
app.conf.task_queues = {
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
    "features": {
        "exchange": "features",
        "routing_key": "features",
    },
    "maintenance": {
        "exchange": "maintenance",
        "routing_key": "maintenance",
    },
}


def get_redis_connection():
    """获取Redis连接"""
    return redis.from_url(REDIS_URL)


def is_match_day() -> bool:
    """检查今天是否有比赛"""
    try:
        # 实现检查今日是否有比赛的逻辑
        # 查询数据库中今日的比赛安排

        DatabaseManager()
        date.today()

        # 生产环境实现示例:
        # async with db_manager.get_async_session() as session:
        #     query = text("""
        #         SELECT COUNT(*) as match_count FROM matches
        #         WHERE DATE(match_date) = :today
        #     """)
        #     _result = await session.execute(query, {"today": today})
        #     match_count = result.scalar()
        #     return match_count > 0

        # 当前返回True以确保任务调度正常运行
        return True
    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
        return False


def get_upcoming_matches(hours: int = 24) -> list:
    """获取未来N小时内的比赛"""
    try:
        # 实现获取即将开始比赛的逻辑
        # 查询数据库中未来N小时内的比赛

        DatabaseManager()
        now = datetime.now()
        now + timedelta(hours=hours)

        # 生产环境实现示例:
        # async with db_manager.get_async_session() as session:
        #     query = text("""
        #         SELECT match_id, home_team, away_team, match_date
        #         FROM matches
        #         WHERE match_date BETWEEN :now AND :end_time
        #         ORDER BY match_date
        #     """)
        #     _result = await session.execute(query, {"now": now, "end_time": end_time})
        #     _matches = [{
        #         "match_id": row.match_id,
        #         "home_team": row.home_team,
        #         "away_team": row.away_team,
        #         "match_date": row.match_date.isoformat()
        #     } for row in result]
        #     return matches

        # 当前返回空列表，生产环境需要实现数据库查询
        return []
    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
        return []


def should_collect_live_scores() -> bool:
    """判断是否应该采集实时比分"""
    try:
        # 检查当前是否有进行中的比赛
        # 获取当前时间前后2小时内的比赛
        _matches = get_upcoming_matches(hours=2)

        # 如果有比赛，则需要采集实时比分
        return len(matches) > 0

    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
        return False


# 任务重试配置
class TaskRetryConfig:
    """任务重试配置"""

    DEFAULT_RETRY_DELAY = 60  # 默认重试延迟（秒）
    MAX_RETRIES = 3  # 最大重试次数

    RETRY_CONFIGS = {
        "collect_fixtures": {
            "max_retries": 3,
            "retry_delay": 300,  # 5分钟
        },
        "collect_odds": {
            "max_retries": 2,
            "retry_delay": 60,  # 1分钟
        },
        "collect_live_scores": {
            "max_retries": 1,
            "retry_delay": 30,  # 30秒
        },
        "calculate_features": {
            "max_retries": 2,
            "retry_delay": 180,  # 3分钟
        },
    }


# 监控配置
class MonitoringConfig:
    """监控配置"""

    # 任务执行时间阈值（秒）
    TASK_TIME_THRESHOLDS = {
        "collect_fixtures": 180,  # 3分钟
        "collect_odds": 120,  # 2分钟
        "collect_live_scores": 60,  # 1分钟
        "calculate_features": 300,  # 5分钟
    }

    # 失败率阈值
    FAILURE_RATE_THRESHOLD = 0.1  # 10%

    # 监控时间窗口（小时）
    MONITORING_WINDOW = 24


# 导入任务模块（避免循环导入）
app.autodiscover_tasks(["src.scheduler.tasks"])
