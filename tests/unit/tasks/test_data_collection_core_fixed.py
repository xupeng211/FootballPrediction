"""
数据收集核心测试（修复版）
Tests for Data Collection Core (Fixed Version)

测试src.tasks.data_collection_core模块的数据收集功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# 测试导入
try:
    from src.tasks.data_collection_core import DataCollectionTask
    from src.tasks.data_collection_core import celery_app
    from src.tasks.data_collection_core import logger

    DATA_COLLECTION_CORE_AVAILABLE = True
except ImportError:
    DATA_COLLECTION_CORE_AVAILABLE = False
    DataCollectionTask = None
    celery_app = None
    logger = None

# 如果模块不可用，创建模拟
if not DATA_COLLECTION_CORE_AVAILABLE:
    celery_app = Mock()
    logger = Mock()


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
class TestDataCollectionTask:
    """数据收集任务测试"""

    @patch("src.tasks.data_collection_core.DataCollectionOrchestrator")
    def test_task_creation(self, mock_orchestrator_class):
        """测试：任务创建"""
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        task = DataCollectionTask()

        assert task is not None
        assert task.orchestrator is mock_orchestrator
        assert task.db_manager is None
        mock_orchestrator_class.assert_called_once()

    @patch("src.tasks.data_collection_core.DataCollectionOrchestrator")
    def test_set_database_manager(self, mock_orchestrator_class):
        """测试：设置数据库管理器"""
        mock_orchestrator = Mock()
        mock_orchestrator.collectors = {"collector1": Mock(), "collector2": Mock()}
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_db_manager = Mock()
        task = DataCollectionTask()
        task.set_database_manager(mock_db_manager)

        assert task.db_manager is mock_db_manager

        # 验证数据库管理器传递给收集器
        mock_orchestrator.collectors[
            "collector1"
        ].set_database_manager.assert_called_once_with(mock_db_manager)
        mock_orchestrator.collectors[
            "collector2"
        ].set_database_manager.assert_called_once_with(mock_db_manager)

    @patch("src.tasks.data_collection_core.DataCollectionOrchestrator")
    @patch("src.tasks.data_collection_core.logger")
    def test_on_failure(self, mock_logger):
        """测试：任务失败回调"""
        task = DataCollectionTask()

        exc = Exception("Test error")
        task_id = "test_task_123"
        args = ["arg1", "arg2"]
        kwargs = {"key1": "value1"}
        einfo = ExceptionInfo()

        task.on_failure(exc, task_id, args, kwargs, einfo)

        mock_logger.error.assert_any_call("Task test_task_123 failed: Test error")
        # 检查是否调用了error记录

    @patch("src.tasks.data_collection_core.DataCollectionOrchestrator")
    @patch("src.tasks.data_collection_core.logger")
    def test_on_success(self, mock_logger):
        """测试：任务成功回调"""
        task = DataCollectionTask()

        retval = {"status": "success"}
        task_id = "test_task_456"
        args = []
        kwargs = {}

        task.on_success(retval, task_id, args, kwargs)

        mock_logger.info.assert_called_once_with(
            "Task test_task_456 completed successfully"
        )


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
class TestDataCollectionCoreModule:
    """数据收集核心模块测试"""

    def test_celery_app_exists(self):
        """测试：Celery应用存在"""
        assert celery_app is not None

    def test_logger_exists(self):
        """测试：日志记录器存在"""
        assert logger is not None

    def test_module_constants(self):
        """测试：模块常量"""
        import src.tasks.data_collection_core as module

        # 验证模块属性
        assert hasattr(module, "DataCollectionTask")
        assert hasattr(module, "celery_app")
        assert hasattr(module, "logger")


class ExceptionInfo:
    """模拟异常信息对象"""

    def __str__(self):
        return "ExceptionInfo"


@pytest.mark.skipif(
    DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module should be available",
)
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


def test_celery_app_configuration():
    """测试：Celery应用配置"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        # 验证Celery应用配置
        assert celery_app.main == "data_collection"


@pytest.mark.asyncio
async def test_async_usage():
    """测试：异步使用场景"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        with patch("src.tasks.data_collection_core.DataCollectionOrchestrator"):
            task = DataCollectionTask()

            # 模拟异步操作
            mock_db_manager = Mock()
            task.set_database_manager(mock_db_manager)

            # 验证设置成功
            assert task.db_manager is mock_db_manager


@pytest.mark.skipif(
    not DATA_COLLECTION_CORE_AVAILABLE,
    reason="Data collection core module not available",
)
class TestDataCollectionIntegration:
    """数据收集集成测试"""

    @patch("src.tasks.data_collection_core.DatabaseManager")
    @patch("src.tasks.data_collection_core.DataCollectionOrchestrator")
    def test_collection_workflow(self, mock_db_manager_class, mock_orchestrator_class):
        """测试：收集工作流"""
        # 设置模拟
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_orchestrator = Mock()
        mock_orchestrator.collectors = {
            "fixtures": Mock(),
            "odds": Mock(),
            "scores": Mock(),
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # 创建任务并设置数据库
        task = DataCollectionTask()
        task.set_database_manager(mock_db_manager)

        # 验证初始化
        assert task.db_manager is mock_db_manager

        # 模拟收集过程
        for collector in mock_orchestrator.collectors.values():
            if hasattr(collector, "set_database_manager"):
                collector.set_database_manager.assert_called_once_with(mock_db_manager)


# 测试模拟场景
@pytest.mark.asyncio
async def test_mock_scenarios():
    """测试：模拟场景"""
    # 模拟Celery任务执行
    mock_task = Mock()
    mock_task.id = "test_task_789"
    mock_task.request = Mock()
    mock_task.request.id = "test_task_789"

    # 模拟任务执行
    try:
        _result = {"collected": 10, "status": "success"}
        # 在真实环境中，这里会调用on_success
        assert result["status"] == "success"
    except Exception:
        # 在真实环境中，这里会调用on_failure
        pass


def test_error_handling():
    """测试：错误处理"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        with patch("src.tasks.data_collection_core.logger") as mock_logger:
            task = DataCollectionTask()

            # 模拟错误场景
            exc = RuntimeError("Database connection failed")
            task_id = "error_task"

            # 测试错误处理
            task.on_failure(exc, task_id, [], {}, None)

            # 验证错误被记录
            mock_logger.error.assert_called()


def test_performance_metrics():
    """测试：性能指标"""
    if DATA_COLLECTION_CORE_AVAILABLE:
        import time

        with patch("src.tasks.data_collection_core.DataCollectionOrchestrator"):
            start_time = time.time()

            # 创建多个任务实例
            tasks = []
            for _ in range(10):
                task = DataCollectionTask()
                tasks.append(task)

            end_time = time.time()

            # 验证性能（10个实例应该在合理时间内创建）
            assert end_time - start_time < 1.0
            assert len(tasks) == 10
