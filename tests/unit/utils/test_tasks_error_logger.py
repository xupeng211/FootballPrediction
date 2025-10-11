"""
任务错误日志记录器测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import logging

from src.tasks.error_logger import TaskErrorLogger


class TestTaskErrorLogger:
    """任务错误日志记录器测试"""

    @pytest.fixture
    def error_logger(self):
        """创建错误日志记录器实例"""
        return TaskErrorLogger()

    @pytest.mark.asyncio
    async def test_log_task_error(self, error_logger):
        """测试记录任务错误"""
        # 准备测试数据
        task_name = "test_task"
        task_id = "task_123"
        error = ValueError("Test error message")
        context = {"param1": "value1", "param2": 123}

        # 模拟数据库保存
        with patch.object(
            error_logger, "_save_error_to_db", new_callable=AsyncMock
        ) as mock_save:
            with patch("src.tasks.error_logger.logger") as mock_app_logger:
                await error_logger.log_task_error(
                    task_name=task_name,
                    task_id=task_id,
                    error=error,
                    context=context,
                    retry_count=2,
                )

                # 验证数据库保存被调用
                mock_save.assert_called_once()
                error_details = mock_save.call_args[0][0]
                assert error_details["task_name"] == task_name
                assert error_details["task_id"] == task_id
                assert error_details["error_type"] == "ValueError"
                assert error_details["error_message"] == "Test error message"
                assert error_details["retry_count"] == 2
                assert error_details["context"] == context

                # 验证应用日志记录被调用
                mock_app_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_task_error_without_context(self, error_logger):
        """测试记录任务错误（无上下文）"""
        error = RuntimeError("Runtime error")

        with patch.object(
            error_logger, "_save_error_to_db", new_callable=AsyncMock
        ) as mock_save:
            with patch("src.tasks.error_logger.logger"):
                await error_logger.log_task_error(
                    task_name="runtime_task", task_id="task_456", error=error
                )

                error_details = mock_save.call_args[0][0]
                assert error_details["context"] == {}
                assert error_details["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_log_task_error_logging_failure(self, error_logger):
        """测试记录错误日志时发生异常"""
        error = Exception("Test error")

        with patch.object(
            error_logger, "_save_error_to_db", new_callable=AsyncMock
        ) as mock_save:
            mock_save.side_effect = Exception("Database error")

            with patch("src.tasks.error_logger.logger") as mock_app_logger:
                await error_logger.log_task_error(
                    task_name="failing_task", task_id="task_789", error=error
                )

                # 验证错误被记录到应用日志
                assert (
                    mock_app_logger.error.call_count == 2
                )  # 一次原始错误，一次记录失败

    @pytest.mark.asyncio
    async def test_log_api_failure(self, error_logger):
        """测试记录API失败"""
        with patch.object(
            error_logger, "_save_api_failure_to_db", new_callable=AsyncMock
        ) as mock_save:
            with patch("src.tasks.error_logger.logger") as mock_app_logger:
                await error_logger.log_api_failure(
                    task_name="api_task",
                    api_endpoint="https://api.example.com/data",
                    http_status=500,
                    error_message="Internal Server Error",
                    retry_count=1,
                    response_data={"error": "detail"},
                )

                # 验证数据库保存被调用
                mock_save.assert_called_once()
                api_details = mock_save.call_args[0][0]
                assert api_details["task_name"] == "api_task"
                assert api_details["api_endpoint"] == "https://api.example.com/data"
                assert api_details["http_status"] == 500
                assert api_details["error_message"] == "Internal Server Error"
                assert api_details["retry_count"] == 1
                assert api_details["response_data"] == {"error": "detail"}

                # 验证应用日志记录被调用
                mock_app_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_system_error(self, error_logger):
        """测试记录系统错误"""
        system_error = MemoryError("Out of memory")
        context = {"memory_usage": "95%", "available_memory": "100MB"}

        with patch.object(
            error_logger, "_save_system_error_to_db", new_callable=AsyncMock
        ) as mock_save:
            with patch("src.tasks.error_logger.logger"):
                await error_logger.log_system_error(
                    task_name="memory_intensive_task",
                    system_error=system_error,
                    context=context,
                    severity="critical",
                )

                # 验证数据库保存被调用
                mock_save.assert_called_once()
                system_details = mock_save.call_args[0][0]
                assert system_details["task_name"] == "memory_intensive_task"
                assert system_details["error_type"] == "MemoryError"
                assert system_details["error_message"] == "Out of memory"
                assert system_details["severity"] == "critical"
                assert system_details["context"] == context

    @pytest.mark.asyncio
    async def test_get_error_statistics(self, error_logger):
        """测试获取错误统计"""
        with patch.object(
            error_logger, "_query_error_stats", new_callable=AsyncMock
        ) as mock_query:
            mock_stats = {
                "total_errors": 100,
                "errors_by_type": {
                    "ValueError": 30,
                    "ConnectionError": 25,
                    "TimeoutError": 20,
                    "MemoryError": 10,
                    "Other": 15,
                },
                "errors_by_task": {
                    "data_collection": 40,
                    "api_sync": 30,
                    "report_generation": 20,
                    "cleanup": 10,
                },
                "recent_errors": [
                    {
                        "timestamp": "2024-01-01T12:00:00",
                        "task_name": "data_collection",
                        "error_type": "ConnectionError",
                        "error_message": "Connection timeout",
                    }
                ],
            }
            mock_query.return_value = mock_stats

            stats = await error_logger.get_error_statistics(
                start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 31)
            )

            assert stats["total_errors"] == 100
            assert stats["errors_by_type"]["ValueError"] == 30
            assert stats["errors_by_task"]["data_collection"] == 40
            assert len(stats["recent_errors"]) == 1

    @pytest.mark.asyncio
    async def test_retry_attempt_logging(self, error_logger):
        """测试重试尝试日志记录"""
        retryable_error = ConnectionError("Connection refused")

        with patch.object(
            error_logger, "_save_retry_attempt", new_callable=AsyncMock
        ) as mock_save:
            with patch("src.tasks.error_logger.logger"):
                for retry_count in range(3):
                    await error_logger.log_retry_attempt(
                        task_name="retryable_task",
                        task_id="task_retry_123",
                        error=retryable_error,
                        retry_count=retry_count,
                        max_retries=3,
                        next_retry_delay=2**retry_count,
                    )

                # 验证每次重试都被记录
                assert mock_save.call_count == 3

                # 验证最后一次重试记录
                last_retry_details = mock_save.call_args[0][0]
                assert last_retry_details["retry_count"] == 2
                assert last_retry_details["max_retries"] == 3
                assert last_retry_details["next_retry_delay"] == 4

    def test_format_error_context(self, error_logger):
        """测试格式化错误上下文"""
        context = {
            "user_id": 12345,
            "request_data": {"key": "value"},
            "system_info": {"cpu": "80%", "memory": "60%"},
            "sensitive_data": "password123",
        }

        # 测试正常格式化
        formatted = error_logger._format_error_context(context, sanitize=True)
        assert "user_id" in formatted
        assert "request_data" in formatted
        assert "system_info" in formatted
        assert "password123" not in str(formatted)  # 敏感数据应被过滤

    def test_error_categorization(self, error_logger):
        """测试错误分类"""
        # 测试网络错误
        network_error = ConnectionError("Connection timeout")
        category = error_logger._categorize_error(network_error)
        assert category == "network"

        # 测试数据错误
        data_error = ValueError("Invalid data format")
        category = error_logger._categorize_error(data_error)
        assert category == "data"

        # 测试系统错误
        system_error = MemoryError("Out of memory")
        category = error_logger._categorize_error(system_error)
        assert category == "system"

        # 测试业务逻辑错误
        business_error = KeyError("Missing required field")
        category = error_logger._categorize_error(business_error)
        assert category == "business"
