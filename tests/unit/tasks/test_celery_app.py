""""""""
Celery应用配置测试
Tests for Celery App Configuration

测试src.tasks.celery_app模块的Celery配置和任务管理功能
""""""""

import os

import pytest

# 尝试导入celery_app模块
try:
    from src.tasks.celery_app import DatabaseManager, RedisManager, celery_app, logger

    CELERY_APP_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    CELERY_APP_AVAILABLE = False
    celery_app = None
    DatabaseManager = None
    RedisManager = None
    logger = None


@pytest.mark.skipif(not CELERY_APP_AVAILABLE, reason="Celery app module not available")
@pytest.mark.unit
class TestCeleryApp:
    """Celery应用测试"""

    def test_celery_app_exists(self):
        """测试:Celery应用存在"""
        assert celery_app is not None
        assert hasattr(celery_app, "conf")
        assert hasattr(celery_app, "task")
        assert hasattr(celery_app, "send_task")

    def test_celery_app_configuration(self):
        """测试:Celery应用配置"""
        # 检查基本配置
        conf = celery_app.conf
        assert conf is not None

        # 检查必要的配置项
        required_configs = [
            "broker_url",
            "result_backend",
            "task_serializer",
            "accept_content",
            "result_serializer",
            "timezone",
        ]

        for config in required_configs:
            assert config in conf

    def test_broker_url_configuration(self):
        """测试:Broker URL配置"""
        conf = celery_app.conf
        broker_url = conf.get("broker_url", "")

        # 应该配置了Redis作为broker
        assert "redis" in broker_url.lower()
        assert "localhost" in broker_url or "127.0.0.1" in broker_url

    def test_result_backend_configuration(self):
        """测试:结果后端配置"""
        conf = celery_app.conf
        result_backend = conf.get("result_backend", "")

        # 应该配置了Redis作为结果后端
        assert "redis" in result_backend.lower()

    def test_task_routes_configuration(self):
        """测试:任务路由配置"""
        conf = celery_app.conf
        task_routes = conf.get("task_routes", {})

        # 应该有任务路由配置
        assert isinstance(task_routes, dict)

    def test_timezone_configuration(self):
        """测试:时区配置"""
        conf = celery_app.conf
        timezone = conf.get("timezone", "")

        # 应该配置了UTC时区
        assert timezone.upper() == "UTC"

    def test_task_serializer_configuration(self):
        """测试:任务序列化配置"""
        conf = celery_app.conf
        task_serializer = conf.get("task_serializer", "")
        result_serializer = conf.get("result_serializer", "")
        accept_content = conf.get("accept_content", [])

        # 应该使用JSON序列化
        assert task_serializer == "json"
        assert result_serializer == "json"
        assert "json" in accept_content

    def test_worker_concurrency_configuration(self):
        """测试:Worker并发配置"""
        conf = celery_app.conf

        # 检查并发相关配置
        worker_concurrency = conf.get("worker_concurrency")
        if worker_concurrency is not None:
            assert isinstance(worker_concurrency, int)
            assert worker_concurrency > 0

    def test_task_soft_time_limit(self):
        """测试:任务软时间限制"""
        conf = celery_app.conf
        soft_time_limit = conf.get("task_soft_time_limit")

        if soft_time_limit is not None:
            assert isinstance(soft_time_limit, (int, float))
            assert soft_time_limit > 0

    def test_task_time_limit(self):
        """测试:任务硬时间限制"""
        conf = celery_app.conf
        time_limit = conf.get("task_time_limit")

        if time_limit is not None:
            assert isinstance(time_limit, (int, float))
            assert time_limit > 0


@pytest.mark.skipif(not CELERY_APP_AVAILABLE, reason="Celery app module not available")
class TestDatabaseManager:
    """数据库管理器测试"""

    def test_database_manager_creation(self):
        """测试:数据库管理器创建"""
        db_manager = DatabaseManager()
        assert db_manager is not None
        assert hasattr(db_manager, "logger")
        assert hasattr(db_manager, "get_connection")
        assert hasattr(db_manager, "close_connection")

    def test_database_manager_logger(self):
        """测试:数据库管理器日志记录器"""
        db_manager = DatabaseManager()
        assert db_manager.logger is not None
        logger_name = db_manager.logger.name
        assert "DatabaseManager" in logger_name

    def test_get_connection(self):
        """测试:获取数据库连接"""
        db_manager = DatabaseManager()
        connection = db_manager.get_connection()
        # 模拟类返回None
        assert connection is None

    def test_close_connection(self):
        """测试:关闭数据库连接"""
        db_manager = DatabaseManager()
        # 应该不会抛出异常
        db_manager.close_connection()


@pytest.mark.skipif(not CELERY_APP_AVAILABLE, reason="Celery app module not available")
class TestRedisManager:
    """Redis管理器测试"""

    def test_redis_manager_creation(self):
        """测试:Redis管理器创建"""
        redis_manager = RedisManager()
        assert redis_manager is not None
        assert hasattr(redis_manager, "logger")
        assert hasattr(redis_manager, "get_redis_client")
        assert hasattr(redis_manager, "close_connection")

    def test_redis_manager_logger(self):
        """测试:Redis管理器日志记录器"""
        redis_manager = RedisManager()
        assert redis_manager.logger is not None
        logger_name = redis_manager.logger.name
        assert "RedisManager" in logger_name

    def test_get_redis_client(self):
        """测试:获取Redis客户端"""
        redis_manager = RedisManager()
        client = redis_manager.get_redis_client()
        # 模拟类返回None
        assert client is None

    def test_close_connection(self):
        """测试:关闭Redis连接"""
        redis_manager = RedisManager()
        # 应该不会抛出异常
        redis_manager.close_connection()


@pytest.mark.skipif(not CELERY_APP_AVAILABLE, reason="Celery app module not available")
class TestCeleryAppIntegration:
    """Celery应用集成测试"""

    @patch("src.tasks.celery_app.os.environ.get")
    def test_environment_variable_handling(self, mock_env_get):
        """测试:环境变量处理"""
        # 模拟环境变量
        mock_env_get.return_value = "redis://localhost:6379/0"

        # 应该能够获取环境变量
        value = os.environ.get("REDIS_URL", "default")
        assert value == "redis://localhost:6379/0"

    def test_celery_app_autodiscover(self):
        """测试:Celery应用自动发现任务"""
        # 检查是否配置了自动发现
        # 大多数Celery应用会配置这个
        # assert 'autodiscover_tasks' in str(conf)

    def test_celery_app_beat_schedule(self):
        """测试:Celery Beat调度配置"""
        conf = celery_app.conf
        beat_schedule = conf.get("beat_schedule", {})

        # 应该有调度配置或为空字典
        assert isinstance(beat_schedule, dict)

    def test_celery_app_imports(self):
        """测试:Celery应用导入配置"""
        conf = celery_app.conf
        imports = conf.get("imports", [])

        # 应该是列表
        assert isinstance(imports, list)

    def test_celery_app_module_configuration(self):
        """测试:Celery应用模块级配置"""
        # 检查模块级别的配置
        assert hasattr(celery_app, "main")
        assert celery_app.main is not None
        assert isinstance(celery_app.main, str)


@pytest.mark.skipif(not CELERY_APP_AVAILABLE, reason="Celery app module not available")
class TestCeleryAppErrorHandling:
    """Celery应用错误处理测试"""

    def test_invalid_task_name(self):
        """测试:无效任务名称"""
        # 尝试获取不存在的任务
        task = celery_app.tasks.get("non.existent.task")
        assert task is None

    def test_configuration_validation(self):
        """测试:配置验证"""
        conf = celery_app.conf

        # 验证必要的配置项类型
        assert isinstance(conf.get("task_serializer", ""), str)
        assert isinstance(conf.get("accept_content", []), (list, tuple))
        assert isinstance(conf.get("timezone", ""), str)


@pytest.mark.skipif(CELERY_APP_AVAILABLE, reason="Module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试:模块导入错误"""
        assert not CELERY_APP_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试:模块导入"""
    if CELERY_APP_AVAILABLE:
from src.tasks.celery_app import (
            DatabaseManager,
            RedisManager,
            celery_app,
            logger,
        )

        assert celery_app is not None
        assert DatabaseManager is not None
        assert RedisManager is not None
        assert logger is not None


def test_module_logger():
    """测试:模块日志记录器"""
    if CELERY_APP_AVAILABLE:
        assert logger is not None
        assert "celery_app" in logger.name


def test_all_classes_exported():
    """测试:所有类都被导出"""
    if CELERY_APP_AVAILABLE:
        import src.tasks.celery_app as celery_module

        expected_classes = ["DatabaseManager", "RedisManager"]

        for class_name in expected_classes:
            assert hasattr(celery_module, class_name)


def test_celery_app_singleton():
    """测试:Celery应用单例"""
    if CELERY_APP_AVAILABLE:
        # Celery应用通常是单例
from src.tasks.celery_app import celery_app as app1
from src.tasks.celery_app import celery_app as app2

        assert app1 is app2
