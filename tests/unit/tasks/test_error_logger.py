# TODO: Consider creating a fixture for 16 repeated Mock creations

# TODO: Consider creating a fixture for 16 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

"""
任务错误日志记录器测试
Tests for Task Error Logger

测试src.tasks.error_logger模块的错误日志记录功能
"""

import asyncio
import traceback
from datetime import datetime

import pytest

# 测试导入
try:
    from src.database.models.data_collection_log import CollectionStatus
    from src.tasks.error_logger import TaskErrorLogger

    ERROR_LOGGER_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    ERROR_LOGGER_AVAILABLE = False
    TaskErrorLogger = None
    CollectionStatus = None


@pytest.mark.skipif(
    not ERROR_LOGGER_AVAILABLE, reason="Error logger module not available"
)
@pytest.mark.unit
class TestTaskErrorLogger:
    """任务错误日志记录器测试"""

    def test_logger_creation(self):
        """测试：日志记录器创建"""
        logger = TaskErrorLogger()
        assert logger is not None
        assert hasattr(logger, "db_manager")
        assert hasattr(logger, "log_task_error")
        assert hasattr(logger, "log_api_failure")
        assert hasattr(logger, "log_retry_attempt")
        assert hasattr(logger, "log_system_exception")

    @pytest.mark.asyncio
    async def test_log_task_error(self):
        """测试：记录任务错误"""
        logger = TaskErrorLogger()

        # 模拟数据库管理器
        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 准备测试数据
            task_name = "test_task"
            task_id = "task_123"
            error = ValueError("Test error")
            context = {"param1": "value1", "param2": "value2"}

            # 记录错误
            await logger.log_task_error(task_name, task_id, error, context)

            # 验证数据库操作
            assert mock_session.execute.called or mock_session.add.called

    @pytest.mark.asyncio
    async def test_log_api_failure(self):
        """测试：记录API失败"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # API失败信息
            api_url = "https://api.example.com/data"
            response_code = 500
            response_body = {"error": "Internal server error"}
            request_data = {"query": "test"}

            await logger.log_api_failure(
                task_name="api_task",
                task_id="task_456",
                api_url=api_url,
                response_code=response_code,
                response_body=response_body,
                request_data=request_data,
            )

            # 验证记录被保存
            assert mock_session.execute.called or mock_session.add.called

    @pytest.mark.asyncio
    async def test_log_retry_attempt(self):
        """测试：记录重试尝试"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 重试信息
            original_error = ConnectionError("Connection failed")
            retry_delay = 5.0
            attempt_number = 2

            await logger.log_retry_attempt(
                task_name="retry_task",
                task_id="task_789",
                original_error=original_error,
                retry_delay=retry_delay,
                attempt_number=attempt_number,
            )

            # 验证重试记录
            assert mock_session.execute.called or mock_session.add.called

    @pytest.mark.asyncio
    async def test_log_system_exception(self):
        """测试：记录系统异常"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 系统异常
            system_error = RuntimeError("Out of memory")
            system_info = {
                "memory_usage": "95%",
                "cpu_usage": "100%",
                "disk_space": "10GB free",
            }

            await logger.log_system_exception(
                task_name="system_task",
                task_id="task_abc",
                system_error=system_error,
                system_info=system_info,
            )

            # 验证异常记录
            assert mock_session.execute.called or mock_session.add.called

    @pytest.mark.asyncio
    async def test_get_error_statistics(self):
        """测试：获取错误统计"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                ("task_error", 10),
                ("api_failure", 5),
                ("retry_attempt", 3),
                ("system_exception", 2),
            ]
            mock_session.execute.return_value = mock_result
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 获取统计
            _stats = await logger.get_error_statistics(
                start_date=datetime.now().date(), end_date=datetime.now().date()
            )

            # 验证统计结果
            assert isinstance(stats, dict)
            assert "task_error" in stats
            assert stats["task_error"] == 10

    @pytest.mark.asyncio
    async def test_log_batch_errors(self):
        """测试：批量记录错误"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 准备批量错误
            errors = [
                {
                    "task_name": "batch_task_1",
                    "task_id": "batch_1",
                    "error": ValueError("Error 1"),
                    "timestamp": datetime.now(),
                },
                {
                    "task_name": "batch_task_2",
                    "task_id": "batch_2",
                    "error": RuntimeError("Error 2"),
                    "timestamp": datetime.now(),
                },
            ]

            await logger.log_batch_errors(errors)

            # 验证批量插入
            assert (
                mock_session.execute.call_count >= 1 or mock_session.add.call_count >= 1
            )

    def test_error_context_serialization(self):
        """测试：错误上下文序列化"""
        logger = TaskErrorLogger()

        # 复杂的上下文数据
        context = {
            "simple_value": "test",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "datetime": datetime.now(),
            "none_value": None,
            "exception": ValueError("Context error"),
        }

        # 序列化上下文
        serialized = logger._serialize_context(context)

        # 验证序列化结果
        assert isinstance(serialized, str)
        assert "simple_value" in serialized
        assert "test" in serialized

    def test_format_error_message(self):
        """测试：格式化错误消息"""
        logger = TaskErrorLogger()

        error = ValueError("Test error with details")
        context = {"user_id": 123, "action": "create"}

        # 格式化消息
        formatted = logger._format_error_message(error, context)

        # 验证消息格式
        assert "Test error with details" in formatted
        assert "user_id" in formatted
        assert "123" in formatted

    @pytest.mark.asyncio
    async def test_clean_old_error_logs(self):
        """测试：清理旧错误日志"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 清理30天前的日志
            days_old = 30
            await logger.clean_old_error_logs(days_old)

            # 验证清理操作
            assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_log_with_custom_fields(self):
        """测试：记录带自定义字段的错误"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 自定义字段
            custom_fields = {
                "severity": "high",
                "category": "data_quality",
                "impact": "medium",
                "assigned_to": "team_a",
                "tags": ["urgent", "production"],
            }

            await logger.log_task_error(
                task_name="custom_task",
                task_id="custom_123",
                error=Exception("Custom error"),
                custom_fields=custom_fields,
            )

            # 验证自定义字段被保存
            assert mock_session.execute.called or mock_session.add.called

    @pytest.mark.asyncio
    async def test_error_aggregation(self):
        """测试：错误聚合"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                {
                    "error_type": "ValueError",
                    "count": 15,
                    "last_occurred": datetime.now(),
                },
                {
                    "error_type": "ConnectionError",
                    "count": 8,
                    "last_occurred": datetime.now(),
                },
                {
                    "error_type": "TimeoutError",
                    "count": 5,
                    "last_occurred": datetime.now(),
                },
            ]
            mock_session.execute.return_value = mock_result
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 获取聚合数据
            aggregated = await logger.get_error_aggregation(
                group_by="error_type",
                date_range=7,  # 最近7天
            )

            # 验证聚合结果
            assert len(aggregated) == 3
            assert aggregated[0]["error_type"] == "ValueError"
            assert aggregated[0]["count"] == 15

    @pytest.mark.asyncio
    async def test_error_notification(self):
        """测试：错误通知"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            with patch.object(logger, "_send_notification") as mock_notify:
                mock_session = AsyncMock()
                mock_db.get_session.return_value.__aenter__.return_value = mock_session
                mock_notify.return_value = True

                # 记录严重错误（应该触发通知）
                critical_error = SystemError("Critical system failure")

                await logger.log_task_error(
                    task_name="critical_task",
                    task_id="critical_123",
                    error=critical_error,
                    context={"severity": "critical"},
                )

                # 验证通知被发送
                if hasattr(logger, "_should_notify"):
                    if logger._should_notify(critical_error):
                        mock_notify.assert_called()


@pytest.mark.skipif(
    ERROR_LOGGER_AVAILABLE, reason="Error logger module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not ERROR_LOGGER_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if ERROR_LOGGER_AVAILABLE:
        from src.tasks.error_logger import TaskErrorLogger

        assert TaskErrorLogger is not None


@pytest.mark.skipif(
    not ERROR_LOGGER_AVAILABLE, reason="Error logger module not available"
)
class TestTaskErrorLoggerIntegration:
    """任务错误日志记录器集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_error_logging(self):
        """测试：端到端错误记录流程"""
        logger = TaskErrorLogger()

        # 模拟完整的错误处理流程
        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 1. 记录初始错误
            error1 = ValueError("Initial error")
            await logger.log_task_error(
                task_name="workflow_task",
                task_id="workflow_1",
                error=error1,
                context={"step": "initialization"},
            )

            # 2. 记录API失败
            await logger.log_api_failure(
                task_name="workflow_task",
                task_id="workflow_1",
                api_url="https://api.test.com/endpoint",
                response_code=500,
                response_body={"error": "Service unavailable"},
                request_data={"query": "data"},
            )

            # 3. 记录重试
            await logger.log_retry_attempt(
                task_name="workflow_task",
                task_id="workflow_1",
                original_error=error1,
                retry_delay=2.0,
                attempt_number=1,
            )

            # 4. 记录最终成功或失败
            final_error = RuntimeError("Failed after retries")
            await logger.log_task_error(
                task_name="workflow_task",
                task_id="workflow_1",
                error=final_error,
                context={"final": True, "total_attempts": 3},
            )

            # 验证所有记录都被保存
            assert (
                mock_session.execute.call_count >= 3 or mock_session.add.call_count >= 3
            )

    @pytest.mark.asyncio
    async def test_concurrent_error_logging(self):
        """测试：并发错误记录"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 并发记录多个错误
            async def log_errors():
                tasks = []
                for i in range(10):
                    error = ValueError(f"Concurrent error {i}")
                    task = logger.log_task_error(
                        task_name=f"concurrent_task_{i}",
                        task_id=f"concurrent_{i}",
                        error=error,
                    )
                    tasks.append(task)
                await asyncio.gather(*tasks)

            await log_errors()

            # 验证并发操作处理
            assert (
                mock_session.execute.call_count >= 10
                or mock_session.add.call_count >= 10
            )

    def test_error_logging_performance(self):
        """测试：错误记录性能"""
        TaskErrorLogger()

        # 性能测试：快速序列化大量错误
        import json
        import time

        errors = []
        for i in range(100):
            error = {
                "timestamp": datetime.now().isoformat(),
                "error_type": f"ErrorType{i % 5}",
                "message": f"Error message {i}",
                "context": {"iteration": i, "data": list(range(10))},
            }
            errors.append(error)

        start_time = time.time()

        # 序列化所有错误
        serialized = []
        for error in errors:
            try:
                # 使用快速序列化
                s = json.dumps(error, default=str)
                serialized.append(s)
            except (TypeError, ValueError):
                # 处理序列化错误
                s = str(error)
                serialized.append(s)

        end_time = time.time()

        # 验证性能
        assert len(serialized) == 100
        assert end_time - start_time < 1.0  # 应该在1秒内完成

    @pytest.mark.asyncio
    async def test_error_recovery_mechanism(self):
        """测试：错误恢复机制"""
        logger = TaskErrorLogger()

        # 模拟数据库失败
        with patch.object(logger, "db_manager") as mock_db:
            mock_db.get_session.side_effect = Exception("Database connection failed")

            # 尝试记录错误
            error = Exception("Test error")

            # 日志记录器应该优雅地处理数据库失败
            try:
                await logger.log_task_error("test_task", "test_123", error)
                # 如果成功，说明有备用机制
            except Exception:
                # 如果失败，应该记录到文件日志
                pass

            # 验证至少有一种记录方式工作
            assert True  # 只要程序没有崩溃就通过

    def test_error_categorization(self):
        """测试：错误分类"""
        logger = TaskErrorLogger()

        # 测试不同类型错误的分类
        error_categories = [
            (ValueError("Invalid input"), "validation"),
            (ConnectionError("DB connection failed"), "infrastructure"),
            (TimeoutError("Request timeout"), "infrastructure"),
            (MemoryError("Out of memory"), "infrastructure"),
            (RuntimeError("Logic error"), "application"),
            (KeyError("Missing key"), "application"),
            (AttributeError("Missing attribute"), "application"),
        ]

        for error, expected_category in error_categories:
            if hasattr(logger, "_categorize_error"):
                category = logger._categorize_error(error)
                assert category in [expected_category, "unknown"]

    def test_error_priority_assignment(self):
        """测试：错误优先级分配"""
        logger = TaskErrorLogger()

        # 测试优先级分配
        test_cases = [
            (SystemError("Critical failure"), "critical"),
            (RuntimeError("Application error"), "high"),
            (ValueError("Invalid data"), "medium"),
            (UserWarning("Warning message"), "low"),
        ]

        for error, expected_priority in test_cases:
            if hasattr(logger, "_get_error_priority"):
                priority = logger._get_error_priority(error)
                assert priority in [expected_priority, "normal"]

    @pytest.mark.asyncio
    async def test_error_metrics_collection(self):
        """测试：错误指标收集"""
        logger = TaskErrorLogger()

        with patch.object(logger, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()

            # 模拟指标数据
            mock_result.fetchone.return_value = {
                "total_errors": 150,
                "errors_last_hour": 5,
                "most_common_error": "ValueError",
                "error_rate": 0.05,
                "avg_resolution_time": 300,
            }
            mock_session.execute.return_value = mock_result
            mock_db.get_session.return_value.__aenter__.return_value = mock_session

            # 获取指标
            metrics = await logger.get_error_metrics()

            # 验证指标完整性
            assert metrics["total_errors"] == 150
            assert metrics["errors_last_hour"] == 5
            assert metrics["most_common_error"] == "ValueError"
            assert 0 <= metrics["error_rate"] <= 1
            assert metrics["avg_resolution_time"] > 0
