"""
Celery应用配置简单测试

测试Celery应用的基本配置和任务路由功能
"""

import pytest
from unittest.mock import Mock, patch

from src.tasks.celery_app import app


@pytest.mark.unit
class TestCeleryAppBasic:
    """Celery应用基础测试类"""

    def test_app_configuration(self):
        """测试应用基本配置"""
        # 验证应用名称
        assert app.main == 'football_prediction_tasks'

        # 验证broker配置
        assert 'broker_url' in app.conf
        assert 'result_backend' in app.conf

        # 验证时区配置
        assert app.conf.timezone == 'UTC'

    def test_task_routes_configuration(self):
        """测试任务路由配置"""
        # 验证任务路由配置存在
        assert 'task_routes' in app.conf
        assert isinstance(app.conf.task_routes, dict)

        # 验证任务路由映射
        routes = app.conf.task_routes
        for task_pattern, route_config in routes.items():
            assert 'queue' in route_config
            assert isinstance(route_config['queue'], str)

    def test_beat_schedule_configuration(self):
        """测试Beat调度配置"""
        # 验证调度配置存在
        assert 'beat_schedule' in app.conf
        assert isinstance(app.conf.beat_schedule, dict)

    def test_task_serializer_configuration(self):
        """测试任务序列化配置"""
        # 验证序列化配置
        assert app.conf.task_serializer == 'json'
        assert app.conf.result_serializer == 'json'

    def test_timezone_configuration(self):
        """测试时区配置"""
        # 验证时区设置
        assert app.conf.timezone == 'UTC'
        assert app.conf.enable_utc is True

    def test_worker_configuration(self):
        """测试工作进程配置"""
        # 验证工作进程配置
        assert 'worker_prefetch_multiplier' in app.conf
        assert 'task_acks_late' in app.conf

    def test_imports_configuration(self):
        """测试导入配置"""
        # 验证导入配置存在
        assert 'imports' in app.conf
        # imports might be a tuple, not a list
        assert isinstance(app.conf.imports, (list, tuple))

    def test_app_inspection(self):
        """测试应用自省功能"""
        # 验证应用可以自省
        if hasattr(app, 'inspect'):
            inspect = app.inspect()
            assert inspect is not None
        else:
            # Some Celery configurations may not have inspect
            pytest.skip("Celery inspect not available")

    def test_task_registration(self):
        """测试任务注册"""
        # 验证任务可以注册
        from src.tasks.celery_app import app

        # 检查已注册的任务
        registered_tasks = app.tasks
        assert len(registered_tasks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.tasks.celery_app", "--cov-report=term-missing"])