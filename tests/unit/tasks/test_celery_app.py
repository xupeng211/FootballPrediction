"""
Celery应用配置测试
"""

import os
import pytest
from unittest.mock import Mock, patch

from src.tasks.celery_app import app, TaskRetryConfig, TASK_MONITORING


class TestCeleryApp:
    """测试Celery应用配置"""

    def test_app_configuration(self):
        """测试应用基本配置"""
        assert app.main == "football_prediction_tasks"
        assert app.conf.broker_url is not None
        assert app.conf.result_backend is not None
        assert app.conf.task_serializer == "json"
        assert app.conf.accept_content == ["json"]
        assert app.conf.result_serializer == "json"

    def test_task_routes_configuration(self):
        """测试任务路由配置"""
        expected_routes = {
            "tasks.data_collection_tasks.collect_fixtures_task": {"queue": "fixtures"},
            "tasks.data_collection_tasks.collect_odds_task": {"queue": "odds"},
            "tasks.data_collection_tasks.collect_scores_task": {"queue": "scores"},
            "tasks.maintenance_tasks.*": {"queue": "maintenance"},
            "tasks.streaming_tasks.*": {"queue": "streaming"},
            "tasks.backup_tasks.*": {"queue": "backup"},
        }

        assert app.conf.task_routes == expected_routes

    def test_queue_configuration(self):
        """测试队列配置"""
        expected_queues = ["default", "fixtures", "odds", "scores", "maintenance", "backup"]

        for queue_name in expected_queues:
            assert queue_name in app.conf.task_queues

    def test_timeout_configuration(self):
        """测试超时配置"""
        assert app.conf.task_soft_time_limit == 300  # 5分钟
        assert app.conf.task_time_limit == 600  # 10分钟

    def test_beat_schedule_configuration(self):
        """测试定时任务配置"""
        expected_schedules = [
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

        for schedule_name in expected_schedules:
            assert schedule_name in app.conf.beat_schedule

    def test_worker_configuration(self):
        """测试工作进程配置"""
        assert app.conf.worker_prefetch_multiplier == 1
        assert app.conf.task_acks_late is True
        assert app.conf.worker_disable_rate_limits is True

    def test_result_configuration(self):
        """测试结果配置"""
        assert app.conf.result_expires == 3600  # 1小时
        assert app.conf.result_compression == "zlib"
        assert app.conf.task_track_started is True
        assert app.conf.task_send_events is True


class TestTaskRetryConfig:
    """测试任务重试配置"""

    def test_default_retry_config(self):
        """测试默认重试配置"""
        config = TaskRetryConfig.get_retry_config("nonexistent_task")

        assert config["max_retries"] == TaskRetryConfig.DEFAULT_MAX_RETRIES
        assert config["retry_delay"] == TaskRetryConfig.DEFAULT_RETRY_DELAY
        assert config["retry_backoff"] is False
        assert config["retry_jitter"] is False

    def test_collect_fixtures_retry_config(self):
        """测试赛程采集任务重试配置"""
        config = TaskRetryConfig.get_retry_config("collect_fixtures_task")

        assert config["max_retries"] == 3
        assert config["retry_delay"] == 300  # 5分钟
        assert config["retry_backoff"] is True
        assert config["retry_jitter"] is True

    def test_collect_odds_retry_config(self):
        """测试赔率采集任务重试配置"""
        config = TaskRetryConfig.get_retry_config("collect_odds_task")

        assert config["max_retries"] == 3
        assert config["retry_delay"] == 60  # 1分钟
        assert config["retry_backoff"] is True
        assert config["retry_jitter"] is False

    def test_collect_scores_retry_config(self):
        """测试比分采集任务重试配置"""
        config = TaskRetryConfig.get_retry_config("collect_scores_task")

        assert config["max_retries"] == 3
        assert config["retry_delay"] == 30  # 30秒
        assert config["retry_backoff"] is False  # 实时数据不需要退避
        assert config["retry_jitter"] is False

    def test_task_retry_configs_structure(self):
        """测试任务重试配置结构"""
        assert "collect_fixtures_task" in TaskRetryConfig.TASK_RETRY_CONFIGS
        assert "collect_odds_task" in TaskRetryConfig.TASK_RETRY_CONFIGS
        assert "collect_scores_task" in TaskRetryConfig.TASK_RETRY_CONFIGS

        # 验证配置项完整性
        for task_name, config in TaskRetryConfig.TASK_RETRY_CONFIGS.items():
            assert "max_retries" in config
            assert "retry_delay" in config
            assert "retry_backoff" in config
            assert "retry_jitter" in config


class TestTaskMonitoring:
    """测试任务监控配置"""

    def test_monitoring_enabled(self):
        """测试监控已启用"""
        assert TASK_MONITORING["enable_metrics"] is True

    def test_metrics_export_interval(self):
        """测试指标导出间隔"""
        assert TASK_MONITORING["metrics_export_interval"] == 30  # 秒

    def test_error_threshold(self):
        """测试错误率阈值"""
        assert TASK_MONITORING["error_threshold"] == 0.1  # 10%

    def test_latency_threshold(self):
        """测试延迟阈值"""
        assert TASK_MONITORING["latency_threshold"] == 300  # 5分钟


class TestCeleryAppWithEagerMode:
    """测试Celery应用的Eager模式（用于测试）"""

    @pytest.fixture(autouse=True)
    def setup_eager_mode(self):
        """设置Eager模式用于测试"""
        # 保存原始配置
        original_always_eager = app.conf.task_always_eager
        original_eager_propagates = app.conf.task_eager_propagates

        # 设置Eager模式
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = True

        yield

        # 恢复原始配置
        app.conf.task_always_eager = original_always_eager
        app.conf.task_eager_propagates = original_eager_propagates

    def test_app_in_eager_mode(self):
        """测试应用在Eager模式下"""
        assert app.conf.task_always_eager is True
        assert app.conf.task_eager_propagates is True

    def test_task_execution_in_eager_mode(self):
        """测试在Eager模式下执行任务"""
        # 这里可以添加具体的任务测试
        # 由于需要具体的任务实现，这里只是验证Eager模式设置
        pass

    def test_environment_variables_configuration(self):
        """测试环境变量配置"""
        # 测试Redis URL环境变量存在性
        from src.tasks.celery_app import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
        assert CELERY_BROKER_URL is not None
        assert CELERY_RESULT_BACKEND is not None
        assert "redis://" in CELERY_BROKER_URL
        assert "redis://" in CELERY_RESULT_BACKEND

    def test_database_manager_mock(self):
        """测试数据库管理器模拟类"""
        from src.tasks.celery_app import DatabaseManager

        db_manager = DatabaseManager()
        assert db_manager.get_connection() is None
        # 应该能调用close_connection而不出错
        db_manager.close_connection()

    def test_redis_manager_mock(self):
        """测试Redis管理器模拟类"""
        from src.tasks.celery_app import RedisManager

        redis_manager = RedisManager()
        assert redis_manager.get_redis_client() is None
        # 应该能调用close_connection而不出错
        redis_manager.close_connection()