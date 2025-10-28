# TODO: Consider creating a fixture for 15 repeated Mock creations

# TODO: Consider creating a fixture for 15 repeated Mock creations

from unittest.mock import MagicMock, Mock, patch

"""
数据收集核心测试（语法修复版）
Tests for Data Collection Core (Syntax Fixed Version)

测试src.tasks.data_collection_core模块的数据收集功能
"""

from datetime import datetime

import pytest

# 尝试导入数据收集核心模块
DATA_COLLECTION_CORE_AVAILABLE = False
DataCollectionTask = None
celery_app = None
logger = None

try:
    from src.tasks.data_collection_core import DataCollectionTask, celery_app, logger

    DATA_COLLECTION_CORE_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    # 尝试模拟导入
    DataCollectionTask = None
    celery_app = None
    logger = None


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
@pytest.mark.unit
class TestDataCollectionTask:
    """数据收集任务测试"""

    def test_task_creation(self):
        """测试：任务创建"""
        task = DataCollectionTask()
        assert task is not None
        assert hasattr(task, "db_manager")
        assert hasattr(task, "orchestrator")

    def test_task_initialization(self):
        """测试：任务初始化"""
        task = DataCollectionTask()
        assert task.db_manager is None
        assert task.orchestrator is not None

    @patch("src.tasks.data_collection_core.DatabaseManager")
    def test_set_database_manager(self, mock_db_manager):
        """测试：设置数据库管理器"""
        mock_db_instance = Mock()
        mock_db_manager.return_value = mock_db_instance

        task = DataCollectionTask()
        task.set_database_manager(mock_db_instance)

        assert task.db_manager is mock_db_instance

    @patch("src.tasks.data_collection_core.DatabaseManager")
    def test_set_database_manager_propagates_to_collectors(self, mock_db_manager):
        """测试：数据库管理器传播到收集器"""
        mock_db_instance = Mock()
        mock_db_manager.return_value = mock_db_instance

        # 模拟收集器
        mock_collector = Mock()
        mock_collector.set_database_manager = Mock()

        task = DataCollectionTask()
        task.orchestrator.collectors = {"test_collector": mock_collector}
        task.set_database_manager(mock_db_instance)

        # 验证数据库管理器被传递给收集器
        mock_collector.set_database_manager.assert_called_once_with(mock_db_instance)

    def test_on_failure(self):
        """测试：任务失败回调"""
        task = DataCollectionTask()

        # 模拟失败参数
        exc = Exception("Test error")
        task_id = "test_task_123"
        args = []
        kwargs = {}
        einfo = Mock()

        # 应该不抛出异常
        task.on_failure(exc, task_id, args, kwargs, einfo)

    def test_on_success(self):
        """测试：任务成功回调"""
        task = DataCollectionTask()

        # 模拟成功参数
        retval = {"status": "success"}
        task_id = "test_task_123"
        args = []
        kwargs = {}

        # 应该不抛出异常
        task.on_success(retval, task_id, args, kwargs)


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
class TestCeleryApp:
    """Celery应用测试"""

    def test_celery_app_exists(self):
        """测试：Celery应用存在"""
        assert celery_app is not None
        assert hasattr(celery_app, "main")
        assert celery_app.main == "data_collection"

    def test_celery_app_name(self):
        """测试：Celery应用名称"""
        assert celery_app.main == "data_collection"

    def test_celery_app_configuration(self):
        """测试：Celery应用配置"""
        # 应该有conf属性
        assert hasattr(celery_app, "conf")
        assert celery_app.conf is not None


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
class TestDataCollectionTaskAdvanced:
    """数据收集任务高级测试"""

    @patch("src.tasks.data_collection_core.DataCollectionOrchestrator")
    def test_orchestrator_initialization(self, mock_orchestrator):
        """测试：编排器初始化"""
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        task = DataCollectionTask()

        # 验证编排器被创建
        mock_orchestrator.assert_called_once()
        assert task.orchestrator is mock_orch_instance

    @patch("src.tasks.data_collection_core.DatabaseManager")
    def test_database_manager_none_initially(self, mock_db_manager):
        """测试：初始时数据库管理器为None"""
        task = DataCollectionTask()
        assert task.db_manager is None

    @patch("src.tasks.data_collection_core.DatabaseManager")
    def test_multiple_set_database_manager_calls(self, mock_db_manager):
        """测试：多次设置数据库管理器"""
        mock_db_instance = Mock()
        mock_db_manager.return_value = mock_db_instance

        task = DataCollectionTask()
        task.set_database_manager(mock_db_instance)
        task.set_database_manager(mock_db_instance)

        # 应该都成功
        assert task.db_manager is mock_db_instance

    def test_on_failure_with_none_exception(self):
        """测试：失败回调处理None异常"""
        task = DataCollectionTask()

        # 尝试传入None
        try:
            task.on_failure(None, "task_id", [], {}, None)
        except (TypeError, AttributeError):
            # 可能抛出异常，这是预期的
            pass

    def test_on_success_with_none_return(self):
        """测试：成功回调处理None返回"""
        task = DataCollectionTask()

        # 应该能处理None返回值
        task.on_success(None, "task_id", [], {})

    def test_on_failure_logging(self):
        """测试：失败回调日志记录"""
        task = DataCollectionTask()

        with patch.object(task, "logger") as mock_logger:
            exc = Exception("Test error")
            task_id = "test_task_123"
            einfo = Mock()

            task.on_failure(exc, task_id, [], {}, einfo)

            # 验证日志被调用
            assert mock_logger.error.called

    def test_on_success_logging(self):
        """测试：成功回调日志记录"""
        task = DataCollectionTask()

        with patch.object(task, "logger") as mock_logger:
            retval = {"status": "success"}
            task_id = "test_task_123"

            task.on_success(retval, task_id, [], {})

            # 验证日志被调用
            assert mock_logger.info.called

    def test_on_failure_with_complex_exception(self):
        """测试：复杂异常的失败回调"""
        task = DataCollectionTask()

        # 创建异常链（不使用from语法以避免语法问题）
        try:
            raise ValueError("Inner error")
        except ValueError as inner_exc:
            exc = RuntimeError("Outer error")
            exc.__cause__ = inner_exc

        task_id = "test_task_123"
        einfo = Mock()
        einfo.exc_info = (type(exc), exc, exc.__traceback__)

        # 应该能处理异常链
        task.on_failure(exc, task_id, [], {}, einfo)

    def test_on_success_with_complex_return(self):
        """测试：复杂返回值的成功回调"""
        task = DataCollectionTask()

        # 复杂的返回值
        complex_retval = {
            "data": [1, 2, 3],
            "metadata": {"timestamp": datetime.now(), "source": "test"},
            "status": "success",
        }

        task_id = "test_task_123"

        # 应该能处理复杂返回值
        task.on_success(complex_retval, task_id, [], {})

    def test_concurrent_callback_calls(self):
        """测试：并发回调调用"""
        import threading

        task = DataCollectionTask()
        results = []

        def success_callback():
            task.on_success({"status": "ok"}, "task_id", [], {})
            results.append("success")

        def failure_callback():
            task.on_failure(Exception("error"), "task_id", [], {}, None)
            results.append("failure")

        # 创建多个线程同时调用回调
        threads = []
        for _ in range(10):
            t1 = threading.Thread(target=success_callback)
            t2 = threading.Thread(target=failure_callback)
            threads.extend([t1, t2])

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 应该有20个结果（10个成功，10个失败）
        assert len(results) == 20


@pytest.mark.skipif(DATA_COLLECTION_CORE_AVAILABLE, reason="Module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not DATA_COLLECTION_CORE_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        from src.tasks.data_collection_core import (
            DataCollectionTask,
            celery_app,
            logger,
        )

        assert DataCollectionTask is not None
        assert celery_app is not None
        assert logger is not None


def test_module_logger():
    """测试：模块日志记录器"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        assert logger is not None
        assert "data_collection_core" in logger.name


def test_class_exported():
    """测试：类被导出"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        import src.tasks.data_collection_core as core_module

        assert hasattr(core_module, "DataCollectionTask")
        assert hasattr(core_module, "celery_app")


def test_celery_app_isolation():
    """测试：Celery应用隔离"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        from src.tasks.data_collection_core import celery_app as app1
        from src.tasks.data_collection_core import celery_app as app2

        # 应该是同一个实例
        assert app1 is app2


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
class TestDataCollectionTaskEdgeCases:
    """数据收集任务边界情况测试"""

    def test_task_with_no_collectors(self):
        """测试：没有收集器的任务"""
        task = DataCollectionTask()
        task.orchestrator.collectors = {}

        # 应该能处理空的收集器字典
        mock_db_manager = Mock()
        task.set_database_manager(mock_db_manager)

        assert task.db_manager is mock_db_manager

    def test_task_with_multiple_collectors(self):
        """测试：有多个收集器的任务"""
        task = DataCollectionTask()

        # 创建多个模拟收集器
        collectors = {}
        for i in range(5):
            collector = Mock()
            collector.set_database_manager = Mock()
            collectors[f"collector_{i}"] = collector

        task.orchestrator.collectors = collectors

        # 设置数据库管理器
        mock_db_manager = Mock()
        task.set_database_manager(mock_db_manager)

        # 验证所有收集器都收到了数据库管理器
        for collector in collectors.values():
            if hasattr(collector, "set_database_manager"):
                collector.set_database_manager.assert_called_with(mock_db_manager)

    def test_collector_without_set_database_manager(self):
        """测试：没有set_database_manager方法的收集器"""
        task = DataCollectionTask()

        # 创建没有set_database_manager方法的收集器
        collector = Mock()
        del collector.set_database_manager

        task.orchestrator.collectors = {"test_collector": collector}

        # 应该不抛出异常
        mock_db_manager = Mock()
        task.set_database_manager(mock_db_manager)
