"""
Celery应用配置增强测试

覆盖 celery_app.py 模块的核心功能：
- 应用配置和验证
- 任务路由和队列配置
- 定时任务调度配置
- 重试机制配置
"""

from unittest.mock import Mock, patch
import pytest
import os

pytestmark = pytest.mark.unit


class TestCeleryAppConfiguration:
    """Celery应用配置测试类"""

    @pytest.fixture
    def mock_env_vars(self):
        """模拟环境变量"""
        env_patches = {
            "REDIS_URL": "redis://localhost:6379/1",
            "CELERY_BROKER_URL": "redis://localhost:6379/2",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/3"
        }

        with patch.dict(os.environ, env_patches):
            yield env_patches

    def test_celery_app_import(self, mock_env_vars):
        """测试Celery应用导入"""
        from src.tasks.celery_app import app
        assert app is not None
        assert app.main == "football_prediction_tasks"

    def test_basic_configuration(self, mock_env_vars):
        """测试基本配置"""
        from src.tasks.celery_app import app

        # 验证序列化配置
        assert app.conf.task_serializer == "json"
        assert app.conf.accept_content == ["json"]
        assert app.conf.result_serializer == "json"

        # 验证时区配置
        assert app.conf.timezone == "UTC"
        assert app.conf.enable_utc is True

        # 验证超时配置
        assert app.conf.task_soft_time_limit == 300
        assert app.conf.task_time_limit == 600

    @pytest.mark.parametrize("broker_url,result_backend", [
        ("redis://localhost:6379/0", "redis://localhost:6379/0"),
        ("redis://localhost:6379/1", "redis://localhost:6379/1"),
        ("redis://user:pass@localhost:6379/0", "redis://user:pass@localhost:6379/0"),
    ])
    def test_redis_configuration(self, broker_url, result_backend, mock_env_vars):
        """参数化测试Redis配置"""
        with patch.dict(os.environ, {
            "REDIS_URL": broker_url,
            "CELERY_BROKER_URL": broker_url,
            "CELERY_RESULT_BACKEND": result_backend
        }):
            # 重新导入模块以应用新环境变量
            import importlib
            import sys

            if 'src.tasks.celery_app' in sys.modules:
                importlib.reload(sys.modules['src.tasks.celery_app'])

            from src.tasks.celery_app import app
            assert app.conf.broker_url == broker_url
            assert app.conf.result_backend == result_backend

    @pytest.mark.parametrize("task_name,expected_queue", [
        ("tasks.data_collection_tasks.collect_fixtures_task", "fixtures"),
        ("tasks.data_collection_tasks.collect_odds_task", "odds"),
        ("tasks.data_collection_tasks.collect_scores_task", "scores"),
        ("tasks.maintenance_tasks.quality_check_task", "maintenance"),
        ("tasks.maintenance_tasks.cleanup_error_logs_task", "maintenance"),
        ("tasks.streaming_tasks.consume_kafka_streams_task", "streaming"),
        ("tasks.streaming_tasks.stream_health_check_task", "streaming"),
        ("tasks.backup_tasks.daily_full_backup_task", "backup"),
        ("tasks.backup_tasks.hourly_incremental_backup_task", "backup"),
        ("tasks.unknown_task", "default"),  # 默认队列
    ])
    def test_task_routing(self, task_name, expected_queue, mock_env_vars):
        """参数化测试任务路由配置"""
        from src.tasks.celery_app import app

        # 首先尝试精确匹配
        route = app.conf.task_routes.get(task_name)
        if route is None:
            # 如果没有精确匹配，尝试模式匹配
            for pattern, config in app.conf.task_routes.items():
                if pattern.endswith(".*") and task_name.startswith(pattern[:-2]):
                    route = config
                    break

        # 如果仍然没有匹配，使用默认队列
        if route is None:
            route = {"queue": "default"}

        assert route["queue"] == expected_queue

    def test_queue_configuration(self, mock_env_vars):
        """测试队列配置"""
        from src.tasks.celery_app import app

        expected_queues = ["default", "fixtures", "odds", "scores", "maintenance", "backup"]
        actual_queues = list(app.conf.task_queues.keys())

        for queue in expected_queues:
            assert queue in actual_queues, f"Queue {queue} not found in configuration"

        # 验证队列配置结构
        for queue_name, queue_config in app.conf.task_queues.items():
            assert "exchange" in queue_config
            assert "routing_key" in queue_config
            assert queue_config["exchange"] == queue_name
            assert queue_config["routing_key"] == queue_name

    @pytest.mark.parametrize("config_key,expected_value", [
        ("worker_prefetch_multiplier", 1),
        ("task_acks_late", True),
        ("worker_disable_rate_limits", True),
        ("task_soft_time_limit", 300),
        ("task_time_limit", 600),
        ("result_expires", 3600),
        ("result_compression", "zlib"),
        ("task_track_started", True),
        ("task_send_events", True),
        ("task_default_queue", "default"),
    ])
    def test_worker_configuration(self, config_key, expected_value, mock_env_vars):
        """参数化测试工作进程配置"""
        from src.tasks.celery_app import app

        assert app.conf[config_key] == expected_value

    def test_beat_schedule_exists(self, mock_env_vars):
        """测试定时任务调度配置存在"""
        from src.tasks.celery_app import app

        assert hasattr(app.conf, 'beat_schedule')
        beat_schedule = app.conf.beat_schedule

        # 验证关键定时任务存在
        expected_tasks = [
            "collect-daily-fixtures",
            "collect-odds-regular",
            "collect-live-scores",
            "hourly-quality-check",
            "daily-error-cleanup",
            "consume-kafka-streams",
            "stream-health-check",
            "stream-data-processing",
            "daily-full-backup",
            "incremental-backup",
            "weekly-wal-archive",
            "daily-backup-cleanup"
        ]

        for task_name in expected_tasks:
            assert task_name in beat_schedule, f"Task {task_name} not found in beat schedule"

    def test_beat_schedule_task_configurations(self, mock_env_vars):
        """测试定时任务具体配置"""
        from src.tasks.celery_app import app
        from celery.schedules import crontab, schedule

        beat_schedule = app.conf.beat_schedule

        # 测试每日赛程采集任务
        fixtures_task = beat_schedule["collect-daily-fixtures"]
        assert fixtures_task["task"] == "tasks.data_collection_tasks.collect_fixtures_task"
        assert isinstance(fixtures_task["schedule"], crontab)
        assert fixtures_task["options"]["queue"] == "fixtures"
        assert fixtures_task["kwargs"]["days_ahead"] == 30

        # 测试赔率采集任务
        odds_task = beat_schedule["collect-odds-regular"]
        assert odds_task["task"] == "tasks.data_collection_tasks.collect_odds_task"
        assert odds_task["schedule"] == 300.0  # 5分钟
        assert odds_task["options"]["queue"] == "odds"

        # 测试实时比分采集任务
        scores_task = beat_schedule["collect-live-scores"]
        assert scores_task["task"] == "tasks.data_collection_tasks.collect_scores_task"
        assert scores_task["schedule"] == 120.0  # 2分钟
        assert scores_task["options"]["queue"] == "scores"
        assert scores_task["kwargs"]["live_only"] is True

    def test_streaming_tasks_schedule(self, mock_env_vars):
        """测试流处理任务调度配置"""
        from src.tasks.celery_app import app

        beat_schedule = app.conf.beat_schedule

        # 测试Kafka流消费任务
        consume_task = beat_schedule["consume-kafka-streams"]
        assert consume_task["task"] == "tasks.streaming_tasks.consume_kafka_streams_task"
        assert consume_task["schedule"] == 60.0  # 1分钟
        assert consume_task["options"]["queue"] == "streaming"
        assert consume_task["kwargs"]["batch_size"] == 100
        assert consume_task["kwargs"]["timeout"] == 50.0

        # 测试流处理健康检查任务
        health_task = beat_schedule["stream-health-check"]
        assert health_task["task"] == "tasks.streaming_tasks.stream_health_check_task"
        assert health_task["schedule"] == 600.0  # 10分钟
        assert health_task["options"]["queue"] == "streaming"

        # 测试流数据处理任务
        processing_task = beat_schedule["stream-data-processing"]
        assert processing_task["task"] == "tasks.streaming_tasks.stream_data_processing_task"
        assert processing_task["schedule"] == 300.0  # 5分钟
        assert processing_task["kwargs"]["processing_duration"] == 280

    def test_backup_tasks_schedule(self, mock_env_vars):
        """测试备份任务调度配置"""
        from src.tasks.celery_app import app
        from celery.schedules import crontab

        beat_schedule = app.conf.beat_schedule

        # 测试每日全量备份任务
        full_backup = beat_schedule["daily-full-backup"]
        assert full_backup["task"] == "tasks.backup_tasks.daily_full_backup_task"
        assert isinstance(full_backup["schedule"], crontab)
        assert full_backup["options"]["queue"] == "backup"
        assert full_backup["kwargs"]["database_name"] == "football_prediction"

        # 测试增量备份任务
        incremental_backup = beat_schedule["incremental-backup"]
        assert incremental_backup["task"] == "tasks.backup_tasks.hourly_incremental_backup_task"
        assert isinstance(incremental_backup["schedule"], crontab)
        assert incremental_backup["options"]["queue"] == "backup"

        # 测试WAL归档任务
        wal_archive = beat_schedule["weekly-wal-archive"]
        assert wal_archive["task"] == "tasks.backup_tasks.weekly_wal_archive_task"
        assert isinstance(wal_archive["schedule"], crontab)
        assert wal_archive["options"]["queue"] == "backup"


class TestTaskRetryConfiguration:
    """任务重试配置测试类"""

    def test_retry_config_class_import(self):
        """测试重试配置类导入"""
        from src.tasks.celery_app import TaskRetryConfig
        assert TaskRetryConfig is not None

    def test_default_retry_config(self):
        """测试默认重试配置"""
        from src.tasks.celery_app import TaskRetryConfig

        default_config = TaskRetryConfig.get_retry_config("unknown_task")

        assert default_config["max_retries"] == 3
        assert default_config["retry_delay"] == 60
        assert default_config["retry_backoff"] is False
        assert default_config["retry_jitter"] is False

    @pytest.mark.parametrize("task_name,expected_max_retries,expected_delay,expected_backoff", [
        ("collect_fixtures_task", 3, 300, True),
        ("collect_odds_task", 3, 60, True),
        ("collect_scores_task", 3, 30, False),
        ("unknown_task", 3, 60, False),  # 默认配置
    ])
    def test_task_specific_retry_config(
        self, task_name, expected_max_retries, expected_delay, expected_backoff
    ):
        """参数化测试特定任务的重试配置"""
        from src.tasks.celery_app import TaskRetryConfig

        config = TaskRetryConfig.get_retry_config(task_name)

        assert config["max_retries"] == expected_max_retries
        assert config["retry_delay"] == expected_delay
        assert config["retry_backoff"] == expected_backoff
        assert "retry_jitter" in config  # 验证配置完整性

    def test_retry_config_attributes(self):
        """测试重试配置类属性"""
        from src.tasks.celery_app import TaskRetryConfig

        # 验证类常量
        assert TaskRetryConfig.DEFAULT_MAX_RETRIES == 3
        assert TaskRetryConfig.DEFAULT_RETRY_DELAY == 60

        # 验证配置字典存在
        assert hasattr(TaskRetryConfig, 'TASK_RETRY_CONFIGS')
        assert isinstance(TaskRetryConfig.TASK_RETRY_CONFIGS, dict)

        # 验证配置包含预期任务
        expected_tasks = ["collect_fixtures_task", "collect_odds_task", "collect_scores_task"]
        for task in expected_tasks:
            assert task in TaskRetryConfig.TASK_RETRY_CONFIGS


class TestTaskMonitoringConfiguration:
    """任务监控配置测试类"""

    def test_monitoring_configuration(self):
        """测试监控配置"""
        from src.tasks.celery_app import TASK_MONITORING

        assert TASK_MONITORING["enable_metrics"] is True
        assert TASK_MONITORING["metrics_export_interval"] == 30
        assert TASK_MONITORING["error_threshold"] == 0.1
        assert TASK_MONITORING["latency_threshold"] == 300

    def test_monitoring_config_values(self):
        """测试监控配置值的有效性"""
        from src.tasks.celery_app import TASK_MONITORING

        # 验证数值范围合理
        assert TASK_MONITORING["metrics_export_interval"] > 0
        assert 0 < TASK_MONITORING["error_threshold"] < 1
        assert TASK_MONITORING["latency_threshold"] > 0


class TestMockClasses:
    """模拟类测试类"""

    def test_database_manager_mock(self):
        """测试数据库管理器模拟类"""
        from src.tasks.celery_app import DatabaseManager

        db_manager = DatabaseManager()

        # 验证方法存在且可调用
        assert hasattr(db_manager, 'get_connection')
        assert hasattr(db_manager, 'close_connection')

        # 验证方法调用不抛出异常
        result = db_manager.get_connection()
        assert result is None  # 模拟类返回None

        db_manager.close_connection()  # 应该不抛出异常

    def test_redis_manager_mock(self):
        """测试Redis管理器模拟类"""
        from src.tasks.celery_app import RedisManager

        redis_manager = RedisManager()

        # 验证方法存在且可调用
        assert hasattr(redis_manager, 'get_redis_client')
        assert hasattr(redis_manager, 'close_connection')

        # 验证方法调用不抛出异常
        result = redis_manager.get_redis_client()
        assert result is None  # 模拟类返回None

        redis_manager.close_connection()  # 应该不抛出异常

    def test_mock_classes_have_logger(self):
        """测试模拟类有日志记录器"""
        from src.tasks.celery_app import DatabaseManager, RedisManager

        db_manager = DatabaseManager()
        redis_manager = RedisManager()

        # 验证logger属性存在
        assert hasattr(db_manager, 'logger')
        assert hasattr(redis_manager, 'logger')

        # 验证logger名称格式正确
        assert "DatabaseManager" in db_manager.logger.name
        assert "RedisManager" in redis_manager.logger.name


class TestAutodiscoverConfiguration:
    """自动发现配置测试类"""

    def test_autodiscover_tasks_configuration(self):
        """测试自动发现任务配置"""
        from src.tasks.celery_app import app

        # 验证自动发现配置存在
        # 注意：实际的任务发现会在运行时进行，这里主要验证配置存在
        assert hasattr(app, 'autodiscover_tasks')

        # 验证应用配置正确
        assert app.main == "football_prediction_tasks"

    def test_task_module_structure(self):
        """测试任务模块结构"""
        import src.tasks
        import os

        # 验证tasks模块存在
        assert hasattr(src.tasks, 'celery_app')

        # 验证任务文件存在（由于__init__.py中可能没有导入所有模块）
        tasks_dir = os.path.dirname(src.tasks.__file__)
        expected_files = [
            'streaming_tasks.py',
            'data_collection_tasks.py',
            'maintenance_tasks.py',
            'backup_tasks.py'
        ]

        for filename in expected_files:
            filepath = os.path.join(tasks_dir, filename)
            assert os.path.exists(filepath), f"Task file {filename} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.tasks.celery_app", "--cov-report=term-missing"])