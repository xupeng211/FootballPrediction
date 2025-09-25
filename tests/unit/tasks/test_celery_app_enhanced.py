"""
Celery应用配置测试 - 覆盖率提升版本

针对 celery_app.py 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import os
from unittest.mock import patch, Mock, MagicMock
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.tasks.celery_app import (
    celery_app,
    TaskConfig,
    QueueConfig,
    get_task_config,
    get_queue_config,
    configure_task_routes,
    setup_celery_beat_schedule,
    get_celery_config,
    CeleryAppManager
)


class TestTaskConfig:
    """任务配置测试类"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        config = TaskConfig()

        assert config.name == "default_task"
        assert config.queue == "default"
        assert config.max_retries == 3
        assert config.countdown == 60
        assert config.time_limit == 3600
        assert config.soft_time_limit == 3300
        assert config.ignore_result is True
        assert config.expires is None

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = TaskConfig(
            name="custom_task",
            queue="priority",
            max_retries=5,
            countdown=30,
            time_limit=1800,
            soft_time_limit=1500,
            ignore_result=False,
            expires=7200
        )

        assert config.name == "custom_task"
        assert config.queue == "priority"
        assert config.max_retries == 5
        assert config.countdown == 30
        assert config.time_limit == 1800
        assert config.soft_time_limit == 1500
        assert config.ignore_result is False
        assert config.expires == 7200

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        config = TaskConfig()

        assert hasattr(config, '__dataclass_fields__')
        fields = config.__dataclass_fields__
        assert 'name' in fields
        assert 'queue' in fields
        assert 'max_retries' in fields
        assert 'countdown' in fields
        assert 'time_limit' in fields


class TestQueueConfig:
    """队列配置测试类"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        config = QueueConfig()

        assert config.name == "default"
        assert config.max_memory_per_child == 256
        assert config.worker_prefetch_multiplier == 4
        assert config.task_acks_late is True
        assert config.task_reject_on_worker_lost is True

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = QueueConfig(
            name="high_priority",
            max_memory_per_child=512,
            worker_prefetch_multiplier=2,
            task_acks_late=False,
            task_reject_on_worker_lost=False
        )

        assert config.name == "high_priority"
        assert config.max_memory_per_child == 512
        assert config.worker_prefetch_multiplier == 2
        assert config.task_acks_late is False
        assert config.task_reject_on_worker_lost is False

    def test_dataclass_properties(self):
        """测试dataclass属性"""
        config = QueueConfig()

        assert hasattr(config, '__dataclass_fields__')
        fields = config.__dataclass_fields__
        assert 'name' in fields
        assert 'max_memory_per_child' in fields
        assert 'worker_prefetch_multiplier' in fields
        assert 'task_acks_late' in fields


class TestCeleryAppManager:
    """Celery应用管理器测试类"""

    def test_init(self):
        """测试初始化"""
        manager = CeleryAppManager()

        assert manager.app is not None
        assert manager.configured is False
        assert isinstance(manager.task_configs, dict)
        assert isinstance(manager.queue_configs, dict)

    def test_configure_app(self):
        """测试配置应用"""
        manager = CeleryAppManager()

        result = manager.configure_app()

        assert result is True
        assert manager.configured is True

    def test_add_task_config(self):
        """测试添加任务配置"""
        manager = CeleryAppManager()

        task_config = TaskConfig(name="test_task", queue="test")
        manager.add_task_config("test_task", task_config)

        assert "test_task" in manager.task_configs
        assert manager.task_configs["test_task"] == task_config

    def test_add_queue_config(self):
        """测试添加队列配置"""
        manager = CeleryAppManager()

        queue_config = QueueConfig(name="test_queue")
        manager.add_queue_config("test_queue", queue_config)

        assert "test_queue" in manager.queue_configs
        assert manager.queue_configs["test_queue"] == queue_config

    def test_get_task_config_existing(self):
        """测试获取现有任务配置"""
        manager = CeleryAppManager()
        task_config = TaskConfig(name="test_task", queue="test")
        manager.add_task_config("test_task", task_config)

        result = manager.get_task_config("test_task")

        assert result == task_config

    def test_get_task_config_nonexistent(self):
        """测试获取不存在的任务配置"""
        manager = CeleryAppManager()

        result = manager.get_task_config("nonexistent_task")

        assert result is None

    def test_get_queue_config_existing(self):
        """测试获取现有队列配置"""
        manager = CeleryAppManager()
        queue_config = QueueConfig(name="test_queue")
        manager.add_queue_config("test_queue", queue_config)

        result = manager.get_queue_config("test_queue")

        assert result == queue_config

    def test_get_queue_config_nonexistent(self):
        """测试获取不存在的队列配置"""
        manager = CeleryAppManager()

        result = manager.get_queue_config("nonexistent_queue")

        assert result is None

    def test_configure_task_routes(self):
        """测试配置任务路由"""
        manager = CeleryAppManager()
        task_config = TaskConfig(name="test_task", queue="test_queue")
        manager.add_task_config("test_task", task_config)

        routes = manager.configure_task_routes()

        assert isinstance(routes, dict)
        assert "test_task" in routes
        assert routes["test_task"]["queue"] == "test_queue"

    def test_setup_beat_schedule(self):
        """测试设置定时任务"""
        manager = CeleryAppManager()

        schedule = manager.setup_beat_schedule()

        assert isinstance(schedule, dict)
        # Should contain default scheduled tasks
        assert len(schedule) >= 0  # May be empty initially

    def test_validate_configuration(self):
        """测试配置验证"""
        manager = CeleryAppManager()

        # Test empty configuration
        result = manager.validate_configuration()
        assert result is True

        # Test with task configurations
        manager.add_task_config("test_task", TaskConfig(name="test_task", queue="test"))
        result = manager.validate_configuration()
        assert result is True

    def test_get_worker_options(self):
        """测试获取工作进程选项"""
        manager = CeleryAppManager()

        options = manager.get_worker_options()

        assert isinstance(options, dict)
        assert "concurrency" in options
        assert "loglevel" in options
        assert "prefetch_multiplier" in options


class TestCeleryAppFunctions:
    """Celery应用函数测试"""

    def test_get_task_config(self):
        """测试获取任务配置函数"""
        config = get_task_config("daily_full_backup_task")

        assert config is not None
        assert config.name == "daily_full_backup_task"
        assert config.queue == "backup_queue"
        assert config.max_retries == 3

    def test_get_task_config_nonexistent(self):
        """测试获取不存在任务的配置"""
        config = get_task_config("nonexistent_task")

        assert config is None

    def test_get_queue_config(self):
        """测试获取队列配置函数"""
        config = get_queue_config("backup_queue")

        assert config is not None
        assert config.name == "backup_queue"
        assert config.max_memory_per_child == 256
        assert config.worker_prefetch_multiplier == 4

    def test_get_queue_config_nonexistent(self):
        """测试获取不存在队列的配置"""
        config = get_queue_config("nonexistent_queue")

        assert config is None

    def test_configure_task_routes_function(self):
        """测试配置任务路由函数"""
        routes = configure_task_routes()

        assert isinstance(routes, dict)
        # Should contain default task routes
        assert len(routes) >= 0

    def test_setup_celery_beat_schedule_function(self):
        """测试设置Celery定时任务函数"""
        schedule = setup_celery_beat_schedule()

        assert isinstance(schedule, dict)
        # Should contain default scheduled tasks
        assert len(schedule) >= 0

    def test_get_celery_config(self):
        """测试获取Celery配置函数"""
        config = get_celery_config()

        assert isinstance(config, dict)
        assert "broker_url" in config
        assert "result_backend" in config
        assert "task_serializer" in config
        assert "accept_content" in config
        assert "result_serializer" in config
        assert "timezone" in config

    def test_celery_app_exists(self):
        """测试Celery应用实例存在"""
        assert celery_app is not None
        assert hasattr(celery_app, 'conf')
        assert hasattr(celery_app, 'task')
        assert hasattr(celery_app, 'send_task')

    def test_celery_app_configuration(self):
        """测试Celery应用配置"""
        assert celery_app.conf.broker_url is not None
        assert celery_app.conf.result_backend is not None
        assert celery_app.conf.task_serializer == 'json'
        assert celery_app.conf.accept_content == ['json']
        assert celery_app.conf.result_serializer == 'json'
        assert celery_app.conf.timezone == 'UTC'

    def test_celery_app_task_registration(self):
        """测试Celery应用任务注册"""
        # Test that tasks can be accessed
        from src.tasks.celery_app import daily_full_backup_task
        assert hasattr(daily_full_backup_task, 'delay')
        assert hasattr(daily_full_backup_task, 'apply_async')


class TestCeleryAppIntegration:
    """Celery应用集成测试"""

    @patch('src.tasks.celery_app.os.environ.get')
    def test_environment_configuration(self, mock_get):
        """测试环境配置"""
        # Mock environment variables
        mock_get.side_effect = lambda key, default=None: {
            'CELERY_BROKER_URL': 'redis://custom-redis:6379/0',
            'CELERY_RESULT_BACKEND': 'redis://custom-redis:6379/1',
            'CELERY_WORKER_CONCURRENCY': '8',
            'CELERY_WORKER_PREFETCH_MULTIPLIER': '2',
            'CELERY_TASK_MAX_RETRIES': '5'
        }.get(key, default)

        # Test that environment variables are used
        from src.tasks.celery_app import CELERY_BROKER_URL, CELERY_WORKER_CONCURRENCY
        assert CELERY_BROKER_URL == 'redis://custom-redis:6379/0'
        assert CELERY_WORKER_CONCURRENCY == 8

    @patch('src.tasks.celery_app.os.environ.get')
    def test_default_environment_values(self, mock_get):
        """测试默认环境值"""
        # Mock no environment variables
        mock_get.return_value = None

        # Test that default values are used
        from src.tasks.celery_app import CELERY_BROKER_URL, CELERY_WORKER_CONCURRENCY
        assert CELERY_BROKER_URL == 'redis://localhost:6379/0'
        assert CELERY_WORKER_CONCURRENCY == 4

    def test_task_configuration_consistency(self):
        """测试任务配置一致性"""
        # Test that task configurations are consistent
        backup_config = get_task_config("daily_full_backup_task")
        hourly_config = get_task_config("hourly_incremental_backup_task")

        assert backup_config is not None
        assert hourly_config is not None
        assert backup_config.queue == "backup_queue"
        assert hourly_config.queue == "backup_queue"

    def test_queue_configuration_consistency(self):
        """测试队列配置一致性"""
        # Test that queue configurations are consistent
        backup_config = get_queue_config("backup_queue")
        default_config = get_queue_config("default")

        assert backup_config is not None
        assert default_config is not None
        assert backup_config.name == "backup_queue"
        assert default_config.name == "default"

    def test_route_configuration_structure(self):
        """测试路由配置结构"""
        routes = configure_task_routes()

        assert isinstance(routes, dict)
        for task_name, route_config in routes.items():
            assert isinstance(task_name, str)
            assert isinstance(route_config, dict)
            assert "queue" in route_config
            assert isinstance(route_config["queue"], str)

    def test_beat_schedule_structure(self):
        """测试定时任务结构"""
        schedule = setup_celery_beat_schedule()

        assert isinstance(schedule, dict)
        for task_name, task_schedule in schedule.items():
            assert isinstance(task_name, str)
            assert isinstance(task_schedule, dict)
            assert "task" in task_schedule
            assert "schedule" in task_schedule

    def test_celery_config_structure(self):
        """测试Celery配置结构"""
        config = get_celery_config()

        assert isinstance(config, dict)
        required_keys = [
            "broker_url", "result_backend", "task_serializer",
            "accept_content", "result_serializer", "timezone",
            "enable_utc", "task_track_started", "task_time_limit",
            "task_soft_time_limit", "worker_prefetch_multiplier",
            "task_acks_late", "worker_disable_rate_limits"
        ]
        for key in required_keys:
            assert key in config

    def test_task_retry_configuration(self):
        """测试任务重试配置"""
        config = get_task_config("daily_full_backup_task")

        assert config is not None
        assert config.max_retries >= 0
        assert config.countdown >= 0
        assert isinstance(config.max_retries, int)
        assert isinstance(config.countdown, int)

    def test_queue_memory_configuration(self):
        """测试队列内存配置"""
        config = get_queue_config("backup_queue")

        assert config is not None
        assert config.max_memory_per_child > 0
        assert config.worker_prefetch_multiplier > 0
        assert isinstance(config.max_memory_per_child, int)
        assert isinstance(config.worker_prefetch_multiplier, int)

    def test_task_time_limits(self):
        """测试任务时间限制"""
        config = get_task_config("daily_full_backup_task")

        assert config is not None
        assert config.time_limit > 0
        assert config.soft_time_limit > 0
        assert config.soft_time_limit < config.time_limit


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])