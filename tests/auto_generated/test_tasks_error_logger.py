"""
Auto-generated tests for src.tasks.error_logger module
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import Dict, Any, Optional

from src.tasks.error_logger import TaskErrorLogger
from src.database.models.data_collection_log import CollectionStatus


class TestTaskErrorLogger:
    """测试任务错误日志记录器"""

    def test_task_error_logger_initialization(self):
        """测试任务错误日志记录器初始化"""
        logger = TaskErrorLogger()

        assert logger.db_manager is not None
        assert logger._db_type is None
        assert logger._query_builder is None

    @pytest.mark.asyncio
    async def test_log_task_error_basic(self):
        """测试基本任务错误日志记录"""
        logger = TaskErrorLogger()
        error = ValueError("Test error message")

        with patch.object(logger, '_save_error_to_db') as mock_save:
            await logger.log_task_error(
                task_name="test_task",
                task_id="task_123",
                error=error,
                context={"key": "value"},
                retry_count=2
            )

            # 验证保存调用
            mock_save.assert_called_once()
            call_args = mock_save.call_args[0][0]

            assert call_args["task_name"] == "test_task"
            assert call_args["task_id"] == "task_123"
            assert call_args["error_type"] == "ValueError"
            assert call_args["error_message"] == "Test error message"
            assert call_args["retry_count"] == 2
            assert call_args["context"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_log_task_error_without_context(self):
        """测试无上下文的任务错误日志记录"""
        logger = TaskErrorLogger()
        error = RuntimeError("Runtime error")

        with patch.object(logger, '_save_error_to_db') as mock_save:
            await logger.log_task_error(
                task_name="runtime_task",
                task_id="task_456",
                error=error
            )

            call_args = mock_save.call_args[0][0]
            assert call_args["task_name"] == "runtime_task"
            assert call_args["context"] == {}

    @pytest.mark.asyncio
    async def test_log_task_error_with_save_exception(self):
        """测试保存异常时的处理"""
        logger = TaskErrorLogger()
        error = Exception("Test error")

        with patch.object(logger, '_save_error_to_db') as mock_save:
            mock_save.side_effect = Exception("Save failed")

            # 应该不抛出异常
            await logger.log_task_error(
                task_name="failing_task",
                task_id="task_789",
                error=error
            )

            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_api_failure_basic(self):
        """测试基本API失败日志记录"""
        logger = TaskErrorLogger()

        with patch.object(logger, '_save_error_to_db') as mock_save:
            await logger.log_api_failure(
                task_name="api_task",
                api_endpoint="https://api.example.com/data",
                http_status=500,
                error_message="Internal server error",
                retry_count=1,
                response_data={"error": "server maintenance"}
            )

            call_args = mock_save.call_args[0][0]
            assert call_args["task_name"] == "api_task"
            assert call_args["error_type"] == "API_FAILURE"
            assert call_args["api_endpoint"] == "https://api.example.com/data"
            assert call_args["http_status"] == 500
            assert call_args["error_message"] == "Internal server error"
            assert call_args["retry_count"] == 1
            assert call_args["response_data"]["error"] == "server maintenance"

    @pytest.mark.asyncio
    async def test_log_api_failure_without_optional_params(self):
        """测试无可选参数的API失败日志记录"""
        logger = TaskErrorLogger()

        with patch.object(logger, '_save_error_to_db') as mock_save:
            await logger.log_api_failure(
                task_name="simple_api_task",
                api_endpoint="https://api.example.com/simple",
                http_status=None,
                error_message="Connection timeout"
            )

            call_args = mock_save.call_args[0][0]
            assert call_args["http_status"] is None
            assert call_args["retry_count"] == 0
            assert call_args["response_data"] is None

    @pytest.mark.asyncio
    @patch('src.tasks.error_logger.DataCollectionLog')
    async def test_log_data_collection_error_basic(self, mock_log_class):
        """测试基本数据采集错误日志记录"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()
        mock_log_entry = MagicMock()
        mock_log_entry.id = 123

        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_log_class.return_value = mock_log_entry

        with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await logger.log_data_collection_error(
                data_source="football_api",
                collection_type="match_data",
                error_message="API rate limit exceeded",
                records_processed=100,
                success_count=80,
                error_count=20
            )

            assert result == 123

            # 验证日志记录创建
            mock_log_class.assert_called_once()
            call_args = mock_log_class.call_args[1]

            assert call_args["data_source"] == "football_api"
            assert call_args["collection_type"] == "match_data"
            assert call_args["records_collected"] == 100
            assert call_args["success_count"] == 80
            assert call_args["error_count"] == 20
            assert call_args["status"] == CollectionStatus.FAILED.value
            assert call_args["error_message"] == "API rate limit exceeded"

            mock_session.add.assert_called_once_with(mock_log_entry)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_log_entry)

    @pytest.mark.asyncio
    @patch('src.tasks.error_logger.DataCollectionLog')
    async def test_log_data_collection_error_with_exception(self, mock_log_class):
        """测试数据采集错误日志记录异常处理"""
        logger = TaskErrorLogger()

        with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            result = await logger.log_data_collection_error(
                data_source="test_source",
                collection_type="test_type",
                error_message="Test error"
            )

            assert result is None  # 异常时返回None

    @pytest.mark.asyncio
    @patch('src.tasks.error_logger.DataCollectionLog')
    async def test_log_data_collection_error_with_none_id(self, mock_log_class):
        """测试日志记录ID为None的情况"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()
        mock_log_entry = MagicMock()
        mock_log_entry.id = None  # 模拟ID为None

        mock_log_class.return_value = mock_log_entry

        with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await logger.log_data_collection_error(
                data_source="test_source",
                collection_type="test_type",
                error_message="Test error"
            )

            assert result is None  # ID为None时返回None

    @pytest.mark.asyncio
    async def test_save_error_to_db_basic(self):
        """测试保存错误到数据库"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()

        error_details = {
            "task_name": "test_task",
            "task_id": "task_123",
            "error_type": "ValueError",
            "error_message": "Test error",
            "traceback": "Traceback line 1\nLine 2",
            "retry_count": 1,
            "context": {"key": "value"}
        }

        with patch.object(logger, '_ensure_error_logs_table_exists') as mock_ensure_table:
            with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session

                await logger._save_error_to_db(error_details)

                mock_ensure_table.assert_called_once_with(mock_session)

                # 验证SQL执行
                mock_session.execute.assert_called_once()
                call_args = mock_session.execute.call_args

                assert call_args[1]["task_name"] == "test_task"
                assert call_args[1]["task_id"] == "task_123"
                assert call_args[1]["error_type"] == "ValueError"
                assert call_args[1]["error_message"] == "Test error"
                assert call_args[1]["traceback"] == "Traceback line 1\nLine 2"
                assert call_args[1]["retry_count"] == 1
                assert call_args[1]["context_data"] == "{'key': 'value'}"

                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_error_to_db_with_exception(self):
        """测试保存错误异常处理"""
        logger = TaskErrorLogger()
        error_details = {"task_name": "test_task"}

        with patch.object(logger, '_ensure_error_logs_table_exists') as mock_ensure_table:
            with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute.side_effect = Exception("Insert failed")
                mock_get_session.return_value.__aenter__.return_value = mock_session

                # 应该不抛出异常
                await logger._save_error_to_db(error_details)

                mock_ensure_table.assert_called_once_with(mock_session)
                mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_type_postgresql(self):
        """测试获取PostgreSQL数据库类型"""
        logger = TaskErrorLogger()
        mock_engine = MagicMock()

        with patch('src.tasks.error_logger.get_db_type_from_engine') as mock_get_type:
            mock_get_type.return_value = "postgresql"

            logger.db_manager._async_engine = mock_engine

            db_type = await logger._get_db_type()

            assert db_type == "postgresql"
            mock_get_type.assert_called_once_with(mock_engine)

    @pytest.mark.asyncio
    async def test_get_db_type_default(self):
        """测试获取默认数据库类型"""
        logger = TaskErrorLogger()

        with patch('src.tasks.error_logger.get_db_type_from_engine') as mock_get_type:
            mock_get_type.side_effect = Exception("Type detection failed")

            db_type = await logger._get_db_type()

            assert db_type == "postgresql"  # 默认值

    @pytest.mark.asyncio
    async def test_get_query_builder(self):
        """测试获取查询构建器"""
        logger = TaskErrorLogger()

        with patch.object(logger, '_get_db_type') as mock_get_type:
            mock_get_type.return_value = "sqlite"

            with patch('src.tasks.error_logger.CompatibleQueryBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder_class.return_value = mock_builder

                result = await logger._get_query_builder()

                assert result == mock_builder
                mock_get_type.assert_called_once()
                mock_builder_class.assert_called_once_with("sqlite")

    @pytest.mark.asyncio
    async def test_ensure_error_logs_table_exists(self):
        """测试确保错误日志表存在"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()

        with patch.object(logger, '_get_db_type') as mock_get_type:
            mock_get_type.return_value = "postgresql"

            with patch('src.tasks.error_logger.SQLCompatibilityHelper') as mock_helper:
                mock_helper.create_error_logs_table_sql.return_value = "CREATE TABLE..."

                await logger._ensure_error_logs_table_exists(mock_session)

                mock_get_type.assert_called_once()
                mock_helper.create_error_logs_table_sql.assert_called_once_with("postgresql")

                mock_session.execute.assert_called_once()
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_error_logs_table_exists_with_exception(self):
        """测试确保错误日志表存在异常处理"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()

        with patch.object(logger, '_get_db_type') as mock_get_type:
            mock_get_type.return_value = "sqlite"

            with patch('src.tasks.error_logger.SQLCompatibilityHelper') as mock_helper:
                mock_helper.create_error_logs_table_sql.return_value = "CREATE TABLE..."
                mock_session.execute.side_effect = Exception("Table creation failed")

                # 应该不抛出异常
                await logger._ensure_error_logs_table_exists(mock_session)

                mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_error_statistics_basic(self):
        """测试获取错误统计信息"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()
        mock_query_builder = MagicMock()

        # 模拟查询结果
        mock_session.execute.side_effect = [
            MagicMock(scalar=lambda: 5),  # 总错误数
            MagicMock(__iter__=lambda: iter([
                MagicMock(task_name="task1", error_count=3),
                MagicMock(task_name="task2", error_count=2)
            ])),  # 按任务统计
            MagicMock(__iter__=lambda: iter([
                MagicMock(error_type="ValueError", error_count=4),
                MagicMock(error_type="RuntimeError", error_count=1)
            ]))  # 按类型统计
        ]

        with patch.object(logger, '_get_query_builder') as mock_get_builder:
            mock_get_builder.return_value = mock_query_builder
            mock_query_builder.build_error_statistics_query.return_value = "SELECT COUNT(*)"
            mock_query_builder.build_task_errors_query.return_value = "SELECT task_name, COUNT(*)"
            mock_query_builder.build_type_errors_query.return_value = "SELECT error_type, COUNT(*)"

            with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session

                result = await logger.get_error_statistics(hours=24)

                assert result["total_errors"] == 5
                assert len(result["task_errors"]) == 2
                assert result["task_errors"][0]["task_name"] == "task1"
                assert result["task_errors"][0]["error_count"] == 3

                assert len(result["type_errors"]) == 2
                assert result["type_errors"][0]["error_type"] == "ValueError"
                assert result["type_errors"][0]["error_count"] == 4

                assert result["time_range_hours"] == 24

    @pytest.mark.asyncio
    async def test_get_error_statistics_with_exception(self):
        """测试获取错误统计异常处理"""
        logger = TaskErrorLogger()

        with patch.object(logger, '_get_query_builder') as mock_get_builder:
            mock_get_builder.side_effect = Exception("Builder creation failed")

            result = await logger.get_error_statistics()

            assert result["total_errors"] == 0
            assert result["task_errors"] == []
            assert result["type_errors"] == []
            assert "error" in result

    @pytest.mark.asyncio
    async def test_cleanup_old_errors_basic(self):
        """测试清理旧错误日志"""
        logger = TaskErrorLogger()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_session.execute.return_value = mock_result

        mock_query_builder = MagicMock()
        mock_query_builder.build_cleanup_old_logs_query.return_value = "DELETE FROM error_logs..."

        with patch.object(logger, '_get_query_builder') as mock_get_builder:
            mock_get_builder.return_value = mock_query_builder

            with patch.object(logger.db_manager, 'get_async_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session

                result = await logger.cleanup_old_errors(days_to_keep=7)

                assert result == 10
                mock_session.execute.assert_called_once()
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_alias(self):
        """测试清理旧日志别名方法"""
        logger = TaskErrorLogger()

        with patch.object(logger, 'cleanup_old_errors') as mock_cleanup:
            mock_cleanup.return_value = 5

            result = await logger.cleanup_old_logs(days_to_keep=3)

            assert result == 5
            mock_cleanup.assert_called_once_with(days_to_keep=3)


@pytest.fixture
def sample_error_details():
    """示例错误详情fixture"""
    return {
        "task_name": "test_task",
        "task_id": "task_123",
        "error_type": "ValueError",
        "error_message": "Test error message",
        "traceback": "Traceback:\n  File test.py, line 1\n    raise ValueError",
        "retry_count": 2,
        "context": {"api_endpoint": "https://api.example.com", "status_code": 500},
        "timestamp": "2025-09-28T15:30:00"
    }


@pytest.fixture
def sample_api_error_details():
    """示例API错误详情fixture"""
    return {
        "task_name": "api_task",
        "error_type": "API_FAILURE",
        "api_endpoint": "https://api.football-data.org/v4/matches",
        "http_status": 429,
        "error_message": "Rate limit exceeded",
        "retry_count": 1,
        "response_data": {"error": "Too many requests"},
        "timestamp": "2025-09-28T15:31:00"
    }


@pytest.fixture
def mock_task_error_logger():
    """模拟任务错误日志记录器fixture"""
    logger = TaskErrorLogger()
    logger.db_manager = MagicMock()
    logger._db_type = "postgresql"
    logger._query_builder = MagicMock()
    return logger