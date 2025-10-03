from datetime import datetime

from src.tasks.error_logger import TaskErrorLogger
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import pytest
import os

"""
任务错误日志记录器测试套件

覆盖src/tasks/error_logger.py的所有功能：
- TaskErrorLogger类初始化
- log_task_error 任务错误日志记录
- log_api_failure API失败日志记录
- log_data_collection_error 数据采集错误记录
- _save_error_to_db 数据库保存功能
- 数据库兼容性处理
- 错误处理和回退机制

目标：实现高覆盖率，重点测试异步数据库操作和错误处理
"""

class TestTaskErrorLogger:
    """TaskErrorLogger类测试"""
    @pytest.fixture
    def mock_db_manager(self):
        """模拟DatabaseManager"""
        db_manager = Mock()
        db_manager.get_async_session = AsyncMock()
        return db_manager
    @pytest.fixture
    def error_logger(self, mock_db_manager):
        """创建TaskErrorLogger实例"""
        with patch(:
            "src.tasks.error_logger.DatabaseManager[", return_value=mock_db_manager[""""
        ):
            return TaskErrorLogger()
    def test_task_error_logger_init(self, error_logger):
        "]]""测试TaskErrorLogger初始化"""
        assert error_logger.db_manager is not None
        assert error_logger._db_type is None
        assert error_logger._query_builder is None
    def test_task_error_logger_init_with_dependencies(self):
        """测试TaskErrorLogger依赖注入"""
        with patch("src.tasks.error_logger.DatabaseManager[") as mock_db_class:": mock_db_manager = Mock()": mock_db_class.return_value = mock_db_manager[": logger = TaskErrorLogger()"
            # 验证DatabaseManager被调用
            mock_db_class.assert_called_once()
            assert logger.db_manager ==mock_db_manager
class TestLogTaskError:
    "]]""log_task_error方法测试"""
    @pytest.fixture
    def mock_db_manager(self):
        """模拟DatabaseManager"""
        db_manager = Mock()
        db_manager.get_async_session = AsyncMock()
        return db_manager
    @pytest.fixture
    def error_logger(self, mock_db_manager):
        """创建TaskErrorLogger实例"""
        with patch(:
            "src.tasks.error_logger.DatabaseManager[", return_value=mock_db_manager[""""
        ):
            logger = TaskErrorLogger()
            logger._save_error_to_db = AsyncMock()
            return logger
    @pytest.mark.asyncio
    async def test_log_task_error_success(self, error_logger):
        "]]""测试成功记录任务错误"""
        task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_69"): task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_69"): error = Exception("]Test error message[")": context = {"]param1[: "value1"", "param2]}": retry_count = 2[": await error_logger.log_task_error(": task_name=task_name,"
            task_id=task_id,
            error=error,
            context=context,
            retry_count=retry_count)
        # 验证数据库保存被调用
        error_logger._save_error_to_db.assert_called_once()
        call_args = error_logger._save_error_to_db.call_args[0][0]
        # 验证错误详情结构
        assert call_args["]task_name["] ==task_name[" assert call_args["]]task_id["] ==task_id[" assert call_args["]]error_type["] =="]Exception[" assert call_args["]error_message["] =="]Test error message[" assert call_args["]retry_count["] ==retry_count[" assert call_args["]]context["] ==context[" assert "]]traceback[" in call_args[""""
        assert "]]timestamp[" in call_args[""""
    @pytest.mark.asyncio
    async def test_log_task_error_without_context(self, error_logger):
        "]]""测试记录任务错误（无上下文）"""
        task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_69"): task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_69"): error = Exception("]Test error[")": await error_logger.log_task_error(": task_name=task_name, task_id=task_id, error=error[""
        )
        # 验证数据库保存被调用
        error_logger._save_error_to_db.assert_called_once()
        call_args = error_logger._save_error_to_db.call_args[0][0]
        # 验证上下文为空字典
        assert call_args["]]context["] =={}""""
    @pytest.mark.asyncio
    async def test_log_task_error_default_retry_count(self, error_logger):
        "]""测试记录任务错误（默认重试次数）"""
        task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_69"): task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_69"): error = Exception("]Test error[")": await error_logger.log_task_error(": task_name=task_name, task_id=task_id, error=error[""
        )
        # 验证默认重试次数为0
        call_args = error_logger._save_error_to_db.call_args[0][0]
        assert call_args["]]retry_count["] ==0[""""
    @pytest.mark.asyncio
    async def test_log_task_error_db_save_failure(self, error_logger):
        "]]""测试数据库保存失败时的处理"""
        error_logger._save_error_to_db.side_effect = Exception("DB save failed[")": task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_99"): task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_69"): error = Exception("]Test error[")""""
        # 调用不应该抛出异常
        await error_logger.log_task_error(
            task_name=task_name, task_id=task_id, error=error
        )
        # 验证数据库保存被调用（即使失败了）
        error_logger._save_error_to_db.assert_called_once()
    @pytest.mark.asyncio
    async def test_log_task_error_with_complex_exception(self, error_logger):
        "]""测试记录复杂异常信息"""
        class CustomError(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code
        error = CustomError("Custom error message[", 500)": task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_99"): task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_69"): await error_logger.log_task_error(": task_name=task_name, task_id=task_id, error=error["""
        )
        # 验证异常类型正确
        call_args = error_logger._save_error_to_db.call_args[0][0]
        assert call_args["]]error_type["] =="]CustomError[" assert call_args["]error_message["] =="]Custom error message[" class TestLogApiFailure:""""
    "]""log_api_failure方法测试"""
    @pytest.fixture
    def mock_db_manager(self):
        """模拟DatabaseManager"""
        db_manager = Mock()
        db_manager.get_async_session = AsyncMock()
        return db_manager
    @pytest.fixture
    def error_logger(self, mock_db_manager):
        """创建TaskErrorLogger实例"""
        with patch(:
            "src.tasks.error_logger.DatabaseManager[", return_value=mock_db_manager[""""
        ):
            logger = TaskErrorLogger()
            logger._save_error_to_db = AsyncMock()
            return logger
    @pytest.mark.asyncio
    async def test_log_api_failure_success(self, error_logger):
        "]]""测试成功记录API失败"""
        task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_69"): api_endpoint = os.getenv("TEST_ERROR_LOGGER_API_ENDPOINT_131"): http_status = 404[": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_133"): retry_count = 1[": response_data = {"]]error[: "Resource not found["}"]": await error_logger.log_api_failure(": task_name=task_name,"
            api_endpoint=api_endpoint,
            http_status=http_status,
            error_message=error_message,
            retry_count=retry_count,
            response_data=response_data)
        # 验证数据库保存被调用
        error_logger._save_error_to_db.assert_called_once()
        call_args = error_logger._save_error_to_db.call_args[0][0]
        # 验证API失败详情结构
        assert call_args["]task_name["] ==task_name[" assert call_args["]]error_type["] =="]API_FAILURE[" assert call_args["]api_endpoint["] ==api_endpoint[" assert call_args["]]http_status["] ==http_status[" assert call_args["]]error_message["] ==error_message[" assert call_args["]]retry_count["] ==retry_count[" assert call_args["]]response_data["] ==response_data[" assert "]]timestamp[" in call_args[""""
    @pytest.mark.asyncio
    async def test_log_api_failure_minimal_params(self, error_logger):
        "]]""测试记录API失败（最小参数）"""
        await error_logger.log_api_failure(
            task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_149"),": api_endpoint = os.getenv("TEST_ERROR_LOGGER_API_ENDPOINT_149"),": http_status=None,": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_149"))""""
        # 验证数据库保存被调用
        error_logger._save_error_to_db.assert_called_once()
        call_args = error_logger._save_error_to_db.call_args[0][0]
        # 验证默认值
        assert call_args["]retry_count["] ==0[" assert call_args["]]response_data["] is None[""""
    @pytest.mark.asyncio
    async def test_log_api_failure_db_save_failure(self, error_logger):
        "]]""测试数据库保存失败"""
        error_logger._save_error_to_db.side_effect = Exception("DB error[")": await error_logger.log_api_failure(": task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_155"),": api_endpoint = os.getenv("TEST_ERROR_LOGGER_API_ENDPOINT_149"),": http_status=500,": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_156"))""""
        # 验证即使失败也尝试了保存
        error_logger._save_error_to_db.assert_called_once()
class TestLogDataCollectionError:
    "]""log_data_collection_error方法测试"""
    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session
    @pytest.fixture
    def mock_db_manager(self, mock_session):
        """模拟DatabaseManager"""
        db_manager = Mock()
        db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        db_manager.get_async_session.return_value.__aexit__.return_value = None
        return db_manager
    @pytest.fixture
    def error_logger(self, mock_db_manager):
        """创建TaskErrorLogger实例"""
        with patch(:
            "src.tasks.error_logger.DatabaseManager[", return_value=mock_db_manager[""""
        ):
            return TaskErrorLogger()
    @pytest.mark.asyncio
    async def test_log_data_collection_error_success(self, error_logger, mock_session):
        "]]""测试成功记录数据采集错误"""
        # 模拟日志条目
        mock_log_entry = Mock()
        mock_log_entry.id = 123
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        with patch("src.tasks.error_logger.DataCollectionLog[") as mock_log_class, patch(:""""
            "]src.tasks.error_logger.CollectionStatus["""""
        ) as mock_status:
            mock_log_class.return_value = mock_log_entry
            mock_status.FAILED.value = os.getenv("TEST_ERROR_LOGGER_VALUE_190"): result = await error_logger.log_data_collection_error(": data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_191"),": collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_192"),": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_193"),": records_processed=100,": success_count=80,": error_count=20)"
            # 验证返回日志ID
            assert result ==123
            # 验证DataCollectionLog被正确创建
            mock_log_class.assert_called_once()
            call_args = mock_log_class.call_args[1]
            assert call_args["]data_source["] =="]api.test.com[" assert call_args["]collection_type["] =="]fixtures[" assert call_args["]records_collected["] ==100[" assert call_args["]]success_count["] ==80[" assert call_args["]]error_count["] ==20[" assert call_args["]]status["] =="]failed[" assert call_args["]error_message["] =="]API timeout["""""
            # 验证数据库操作
            mock_session.add.assert_called_once_with(mock_log_entry)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_log_entry)
    @pytest.mark.asyncio
    async def test_log_data_collection_error_minimal_params(
        self, error_logger, mock_session
    ):
        "]""测试记录数据采集错误（最小参数）"""
        mock_log_entry = Mock()
        mock_log_entry.id = None
        with patch("src.tasks.error_logger.DataCollectionLog[") as mock_log_class, patch(:""""
            "]src.tasks.error_logger.CollectionStatus["""""
        ) as mock_status:
            mock_log_class.return_value = mock_log_entry
            mock_status.FAILED.value = os.getenv("TEST_ERROR_LOGGER_VALUE_190"): result = await error_logger.log_data_collection_error(": data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_191"),": collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_192"),": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_149"))""""
            # 验证默认值和返回值
            assert result is None
            call_args = mock_log_class.call_args[1]
            assert call_args["]records_collected["] ==0[" assert call_args["]]success_count["] ==0[" assert call_args["]]error_count["] ==0[""""
    @pytest.mark.asyncio
    async def test_log_data_collection_error_db_exception(
        self, error_logger, mock_session
    ):
        "]]""测试数据库异常处理"""
        mock_session.commit.side_effect = Exception("Database error[")": with patch("]src.tasks.error_logger.DataCollectionLog["), patch(:""""
            "]src.tasks.error_logger.CollectionStatus["""""
        ):
            result = await error_logger.log_data_collection_error(
                data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_191"),": collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_192"),": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_149"))""""
            # 验证异常时返回None
            assert result is None
    @pytest.mark.asyncio
    async def test_log_data_collection_error_session_exception(self, error_logger):
        "]""测试会话获取异常"""
        error_logger.db_manager.get_async_session.side_effect = Exception(
            "Session error["""""
        )
        result = await error_logger.log_data_collection_error(
            data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_191"),": collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_192"),": error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_149"))""""
        # 验证异常时返回None
        assert result is None
class TestSaveErrorToDb:
    "]""_save_error_to_db方法测试"""
    @pytest.fixture
    def mock_db_manager(self):
        """模拟DatabaseManager"""
        db_manager = Mock()
        db_manager.get_async_session = AsyncMock()
        return db_manager
    @pytest.fixture
    def error_logger(self, mock_db_manager):
        """创建TaskErrorLogger实例"""
        with patch(:
            "src.tasks.error_logger.DatabaseManager[", return_value=mock_db_manager[""""
        ):
            return TaskErrorLogger()
    @pytest.mark.asyncio
    async def test_save_error_to_db_success(self, error_logger):
        "]]""测试成功保存错误到数据库"""
        error_details = {
            "task_name[": ["]test_task[",""""
            "]error_type[": ["]Exception[",""""
            "]error_message[: "Test error[","]"""
            "]timestamp[: "2025-09-29T12:00:00["}"]"""
        # 模拟数据库会话和查询构建器
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        error_logger.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        with patch(:
            "]src.tasks.error_logger.CompatibleQueryBuilder["""""
        ) as mock_builder_class = mock_builder Mock()
            mock_builder_class.return_value = mock_builder
            await error_logger._save_error_to_db(error_details)
            # 验证数据库操作被调用
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()
    @pytest.mark.asyncio
    async def test_save_error_to_db_session_exception(self, error_logger):
        "]""测试会话异常处理"""
        error_logger.db_manager.get_async_session.side_effect = Exception(
            "Session error["""""
        )
        error_details = {
            "]task_name[": ["]test_task[",""""
            "]error_type[": ["]Exception[",""""
            "]error_message[: "Test error["}"]"""
        # 调用不应该抛出异常
        await error_logger._save_error_to_db(error_details)
    @pytest.mark.asyncio
    async def test_save_error_to_db_execute_exception(self, error_logger):
        "]""测试执行异常处理"""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Execute error[")": error_logger.db_manager.get_async_session.return_value.__aenter__.return_value = (": mock_session[""
        )
        error_details = {
            "]]task_name[": ["]test_task[",""""
            "]error_type[": ["]Exception[",""""
            "]error_message[: "Test error["}"]"""
        # 调用不应该抛出异常
        await error_logger._save_error_to_db(error_details)
class TestTaskErrorLoggerIntegration:
    "]""TaskErrorLogger集成测试"""
    def test_database_type_detection(self):
        """测试数据库类型检测"""
        with patch("src.tasks.error_logger.DatabaseManager[") as mock_db_class:": mock_db_manager = Mock()": mock_db_class.return_value = mock_db_manager[": logger = TaskErrorLogger()"
            # 验证初始状态
            assert logger._db_type is None
            assert logger._query_builder is None
    @pytest.mark.asyncio
    async def test_full_error_logging_flow(self):
        "]]""测试完整的错误记录流程"""
        with patch("src.tasks.error_logger.DatabaseManager[") as mock_db_class:": mock_db_manager = Mock()": mock_db_class.return_value = mock_db_manager[": logger = TaskErrorLogger()"
            logger._save_error_to_db = AsyncMock()
            # 测试完整的错误记录流程
            error = Exception("]]Integration test error[")": await logger.log_task_error(": task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_308"),": task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_309"),": error=error,": context = {"]test[": ["]integration["},": retry_count=1)"""
            # 验证保存被调用
            logger._save_error_to_db.assert_called_once()
            call_args = logger._save_error_to_db.call_args[0][0]
            # 验证所有必要字段
            expected_fields = [
                "]task_name[",""""
                "]task_id[",""""
                "]error_type[",""""
                "]error_message[",""""
                "]traceback[",""""
                "]retry_count[",""""
                "]timestamp[",""""
                "]context["]": for field in expected_fields:": assert field in call_args[" def test_error_details_structure(self):"
        "]]""测试错误详情结构"""
        error_details = {
            "task_name[": ["]test_task[",""""
            "]error_type[": ["]Exception[",""""
            "]error_message[: "Test error[","]"""
            "]timestamp[": datetime.now().isoformat(),""""
            "]retry_count[": 0,""""
            "]context[": {}}""""
        # 验证必需字段
        required_fields = ["]task_name[", "]error_type[", "]error_message[", "]timestamp["]": for field in required_fields:": assert field in error_details[""
    @pytest.mark.asyncio
    async def test_concurrent_error_logging(self):
        "]]""测试并发错误记录"""
        with patch("src.tasks.error_logger.DatabaseManager[") as mock_db_class:": mock_db_manager = Mock()": mock_db_class.return_value = mock_db_manager[": logger = TaskErrorLogger()"
            logger._save_error_to_db = AsyncMock()
            # 模拟并发错误记录
            tasks = []
            for i in range(5):
                task = logger.log_task_error(
                    task_name=f["]]concurrent_task_{i}"],": task_id=f["task-{i}"],": error=Exception(f["Concurrent error {i}"]))": tasks.append(task)"""
            # 等待所有任务完成
            await asyncio.gather(*tasks)
            # 验证所有错误都被记录
            assert logger._save_error_to_db.call_count ==5
if __name__ =="__main__[": pytest.main(""""
        ["]__file__[", "]-v[", "]--cov=src.tasks.error_logger[", "]--cov-report=term-missing["]"]"""
    )