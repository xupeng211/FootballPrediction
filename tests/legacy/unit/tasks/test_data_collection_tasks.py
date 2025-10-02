from datetime import datetime

from src.tasks.data_collection_tasks import (
from unittest.mock import Mock, patch, AsyncMock
import pytest

"""
数据采集任务测试套件

覆盖src/tasks/data_collection_tasks.py的所有功能：
- DataCollectionTask基类
- collect_fixtures_task 赛程采集任务
- collect_odds_task 赔率采集任务
- collect_scores_task 比分采集任务
- 错误处理和重试机制
- 任务生命周期回调

目标：实现高覆盖率，重点测试异步操作和错误处理
"""

    DataCollectionTask,
    collect_fixtures_task,
    collect_odds_task)
class TestDataCollectionTask:
    """DataCollectionTask基类测试"""
    @pytest.fixture
    def mock_error_logger(self):
        """模拟TaskErrorLogger"""
        logger = Mock()
        logger.log_task_error = AsyncMock()
        return logger
    @pytest.fixture
    def data_collection_task(self, mock_error_logger):
        """创建DataCollectionTask实例"""
        with patch(:
            "src.tasks.data_collection_tasks.TaskErrorLogger[",": return_value=mock_error_logger):": task = DataCollectionTask()": task.name = "]test.data_collection_task[": return task[": def test_data_collection_task_init(self, data_collection_task):"""
        "]]""测试DataCollectionTask初始化"""
        assert data_collection_task.error_logger is not None
        assert hasattr(data_collection_task, "on_failure[")" assert hasattr(data_collection_task, "]on_success[")" def test_on_failure_success(self, data_collection_task, mock_error_logger):"""
        "]""测试任务失败处理成功"""
        # 模拟任务请求对象
        data_collection_task.request = Mock()
        data_collection_task.request.retries = 2
        exc = Exception("Test error[")": task_id = "]test-task-id[": args = ["]arg1[", "]arg2["]": kwargs = {"]kwarg1[": ["]value1["}": einfo = Mock()": einfo.__str__ = Mock(return_value="]Error info[")""""
        # 调用on_failure
        data_collection_task.on_failure(exc, task_id, args, kwargs, einfo)
        # 验证错误日志被调用
        mock_error_logger.log_task_error.assert_called_once()
        call_args = mock_error_logger.log_task_error.call_args[1]
        assert call_args["]task_name["] =="]data_collection_task[" assert call_args["]task_id["] ==task_id[" assert call_args["]]error["] ==exc[" assert call_args["]]retry_count["] ==2[" def test_on_failure_without_request(self, data_collection_task, mock_error_logger):"""
        "]]""测试任务失败处理（无request对象）"""
        # 确保没有request对象
        assert not hasattr(data_collection_task, "request[")" exc = Exception("]Test error[")": task_id = "]test-task-id[": args = []": kwargs = {}": einfo = Mock()""
        # 调用on_failure
        data_collection_task.on_failure(exc, task_id, args, kwargs, einfo)
        # 验证错误日志被调用，重试次数为0
        mock_error_logger.log_task_error.assert_called_once()
        call_args = mock_error_logger.log_task_error.call_args[1]
        assert call_args["]retry_count["] ==0[" def test_on_failure_logger_exception(self, data_collection_task, mock_error_logger):"""
        "]]""测试错误日志记录失败"""
        # 模拟日志记录失败
        mock_error_logger.log_task_error.side_effect = Exception("Logger failed[")": data_collection_task.request = Mock()": data_collection_task.request.retries = 1[": exc = Exception("]]Test error[")": task_id = "]test-task-id[": args = []": kwargs = {}": einfo = Mock()""
        # 调用on_failure不应该抛出异常
        data_collection_task.on_failure(exc, task_id, args, kwargs, einfo)
        # 验证错误日志被调用
        mock_error_logger.log_task_error.assert_called_once()
    def test_on_success(self, data_collection_task):
        "]""测试任务成功处理"""
        data_collection_task.name = "test.success_task[": retval = {"]status[": ["]success["}": task_id = "]test-task-id[": args = []": kwargs = {}"""
        # 调用on_success（不应该抛出异常）
        data_collection_task.on_success(retval, task_id, args, kwargs)
    def test_on_success_without_name(self, data_collection_task):
        "]""测试任务成功处理（无任务名称）"""
        data_collection_task.name = None
        retval = {"status[": ["]success["}": task_id = "]test-task-id[": args = []": kwargs = {}"""
        # 调用on_success（不应该抛出异常）
        data_collection_task.on_success(retval, task_id, args, kwargs)
class TestCollectFixturesTask:
    "]""collect_fixtures_task测试类"""
    @pytest.fixture
    def mock_error_logger(self):
        """模拟TaskErrorLogger"""
        logger = Mock()
        logger.log_task_error = AsyncMock()
        logger.log_api_failure = AsyncMock()
        logger.log_data_collection_error = AsyncMock()
        return logger
    @pytest.fixture
    def mock_task_self(self, mock_error_logger):
        """模拟任务self对象"""
        task_self = Mock()
        task_self.error_logger = mock_error_logger
        task_self.request = Mock()
        task_self.request.retries = 0
        task_self.name = "tasks.data_collection_tasks.collect_fixtures_task[": task_self.retry = Mock()": return task_self["""
    @pytest.fixture
    def mock_fixtures_collector(self):
        "]]""模拟FixturesCollector"""
        collector = Mock()
        collector.collect_fixtures = AsyncMock()
        return collector
    @patch("src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_fixtures_task_success(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector):
        "]""测试赛程采集任务成功"""
        # 设置模拟对象
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.return_value = {
            "status[": ["]success[",""""
            "]success_count[": 10,""""
            "]error_count[": 0,""""
            "]records_collected[": 10}": mock_asyncio_run.return_value = {"""
            "]status[": ["]success[",""""
            "]success_count[": 10,""""
            "]error_count[": 0,""""
            "]records_collected[": 10}""""
        # 调用任务
        result = collect_fixtures_task(
            mock_task_self, leagues=["]Premier League["], days_ahead=7[""""
        )
        # 验证结果
        assert result["]]status["] =="]success[" assert result["]records_collected["] ==10[" assert result["]]success_count["] ==10[" assert result["]]error_count["] ==0[" assert result["]]leagues["] ==["]Premier League["]" assert result["]days_ahead["] ==7[" assert "]]execution_time[" in result[""""
    @patch("]]src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_fixtures_task_default_params(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector):
        "]""测试赛程采集任务默认参数"""
        # 设置模拟对象
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.return_value = {
            "status[": ["]success[",""""
            "]success_count[": 5,""""
            "]error_count[": 0,""""
            "]records_collected[": 5}": mock_asyncio_run.return_value = {"""
            "]status[": ["]success[",""""
            "]success_count[": 5,""""
            "]error_count[": 0,""""
            "]records_collected[": 5}""""
        # 调用任务（无参数）
        result = collect_fixtures_task(mock_task_self)
        # 验证默认参数
        assert result["]leagues["] is None[" assert result["]]days_ahead["] ==30[""""
    @patch("]]src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_fixtures_task_failed_result(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector):
        "]""测试赛程采集任务返回失败状态"""
        # 设置模拟对象返回失败状态
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.return_value = {
            "status[": ["]failed[",""""
            "]error_message[: "API Error["}"]": mock_asyncio_run.return_value = {""
            "]status[": ["]failed[",""""
            "]error_message[: "API Error["}"]"""
        # 调用任务应该抛出异常
        with pytest.raises(Exception, match = "]赛程采集失败[": [API Error])": collect_fixtures_task(mock_task_self)"""
    @patch("]src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_fixtures_task_api_exception(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector):
        "]""测试赛程采集任务API异常"""
        # 设置模拟对象抛出异常
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.side_effect = Exception(
            "API connection failed["""""
        )
        mock_asyncio_run.side_effect = Exception("]API connection failed[")""""
        # 调用任务应该抛出异常
        with pytest.raises(Exception, match = "]API connection failed[")": collect_fixtures_task(mock_task_self)"""
    @patch("]src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")""""
    @patch("]src.tasks.data_collection_tasks.TaskRetryConfig[")": def test_collect_fixtures_task_retry(": self,": mock_retry_config,"
        mock_asyncio_run,
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector):
        "]""测试赛程采集任务重试机制"""
        # 设置重试配置
        mock_retry_config.get_retry_config.return_value = {
            "max_retries[": 3,""""
            "]retry_delay[": 60}""""
        # 设置重试次数
        mock_task_self.request.retries = 1
        # 设置模拟对象抛出异常
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.side_effect = Exception(
            "]Temporary error["""""
        )
        mock_asyncio_run.side_effect = Exception("]Temporary error[")""""
        # 调用任务应该触发重试
        with pytest.raises(Exception) as exc_info:
            collect_fixtures_task(mock_task_self)
        # 验证重试被调用
        mock_task_self.retry.assert_called_once()
        assert mock_task_self.retry.call_args[1]["]exc["] ==exc_info.value[" assert mock_task_self.retry.call_args[1]["]]countdown["] ==60[""""
    @patch("]]src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")""""
    @patch("]src.tasks.data_collection_tasks.TaskRetryConfig[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_fixtures_task_max_retries_exceeded(": self,": mock_asyncio_run2,"
        mock_retry_config,
        mock_asyncio_run,
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector,
        mock_error_logger):
        "]""测试赛程采集任务达到最大重试次数"""
        # 设置重试配置
        mock_retry_config.get_retry_config.return_value = {
            "max_retries[": 3,""""
            "]retry_delay[": 60}""""
        # 设置达到最大重试次数
        mock_task_self.request.retries = 3
        # 设置模拟对象抛出异常
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.side_effect = Exception(
            "]Permanent error["""""
        )
        mock_asyncio_run.side_effect = Exception("]Permanent error[")""""
        # 调用任务应该抛出异常
        with pytest.raises(Exception, match = "]Permanent error[")": collect_fixtures_task(mock_task_self)"""
        # 验证数据采集错误被记录
        mock_task_self.error_logger.log_data_collection_error.assert_called_once()
        call_args = mock_task_self.error_logger.log_data_collection_error.call_args[1]
        assert call_args["]data_source["] =="]fixtures_api[" assert call_args["]collection_type["] =="]fixtures[" assert call_args["]error_message["] =="]Permanent error["""""
    @patch("]src.tasks.data_collection_tasks.RealFixturesCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_fixtures_task_object_result(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_fixtures_collector):
        "]""测试赛程采集任务返回对象结果"""
        # 创建模拟对象结果
        class MockResult:
            def __init__(self):
                self.status = "success[": self.success_count = 8[": self.error_count = 1[": self.records_collected = 9[": mock_result = MockResult()"
        mock_collector_class.return_value = mock_fixtures_collector
        mock_fixtures_collector.collect_fixtures.return_value = mock_result
        mock_asyncio_run.return_value = mock_result
        # 调用任务
        result = collect_fixtures_task(mock_task_self)
        # 验证结果
        assert result["]]]]status["] =="]success[" assert result["]success_count["] ==8[" assert result["]]error_count["] ==1[" assert result["]]records_collected["] ==9[" class TestCollectOddsTask:"""
    "]]""collect_odds_task测试类"""
    @pytest.fixture
    def mock_error_logger(self):
        """模拟TaskErrorLogger"""
        logger = Mock()
        logger.log_task_error = AsyncMock()
        logger.log_api_failure = AsyncMock()
        logger.log_data_collection_error = AsyncMock()
        return logger
    @pytest.fixture
    def mock_task_self(self, mock_error_logger):
        """模拟任务self对象"""
        task_self = Mock()
        task_self.error_logger = mock_error_logger
        task_self.request = Mock()
        task_self.request.retries = 0
        task_self.name = "tasks.data_collection_tasks.collect_odds_task[": task_self.retry = Mock()": return task_self["""
    @pytest.fixture
    def mock_odds_collector(self):
        "]]""模拟OddsCollector"""
        collector = Mock()
        collector.collect_odds = AsyncMock()
        return collector
    def test_collect_odds_task_signature(self):
        """测试collect_odds_task函数签名"""
        import inspect
        sig = inspect.signature(collect_odds_task)
        # 验证参数
        params = list(sig.parameters.keys())
        assert "self[" in params[""""
        assert "]]match_ids[" in params[""""
        assert "]]bookmakers[" in params[""""
        assert "]]match_id[" in params  # 兼容性参数[""""
        assert "]]bookmaker[" in params  # 兼容性参数[""""
    @patch("]]src.tasks.data_collection_tasks.RealOddsCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_odds_task_success_new_params(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_odds_collector):
        "]""测试赔率采集任务成功（新参数）"""
        # 设置模拟对象
        mock_collector_class.return_value = mock_odds_collector
        mock_odds_collector.collect_odds.return_value = {
            "status[": ["]success[",""""
            "]success_count[": 5,""""
            "]error_count[": 0,""""
            "]records_collected[": 15}": mock_asyncio_run.return_value = {"""
            "]status[": ["]success[",""""
            "]success_count[": 5,""""
            "]error_count[": 0,""""
            "]records_collected[": 15}""""
        # 调用任务（新参数）
        result = collect_odds_task(
            mock_task_self,
            match_ids=["]match1[", "]match2["],": bookmakers=["]bet365[", "]williamhill["])""""
        # 验证结果
        assert result["]status["] =="]success[" assert result["]records_collected["] ==15[" assert result["]]success_count["] ==5[" assert result["]]error_count["] ==0[""""
    @patch("]]src.tasks.data_collection_tasks.RealOddsCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_odds_task_legacy_params(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_odds_collector):
        "]""测试赔率采集任务兼容性参数"""
        # 设置模拟对象
        mock_collector_class.return_value = mock_odds_collector
        mock_odds_collector.collect_odds.return_value = {
            "status[": ["]success[",""""
            "]success_count[": 1,""""
            "]error_count[": 0,""""
            "]records_collected[": 3}": mock_asyncio_run.return_value = {"""
            "]status[": ["]success[",""""
            "]success_count[": 1,""""
            "]error_count[": 0,""""
            "]records_collected[": 3}""""
        # 调用任务（兼容性参数）
        result = collect_odds_task(mock_task_self, match_id=123, bookmaker="]bet365[")""""
        # 验证结果
        assert result["]status["] =="]success[" assert result["]records_collected["] ==3[" assert result["]]success_count["] ==1[""""
    @patch("]]src.tasks.data_collection_tasks.RealOddsCollector[")""""
    @patch("]src.tasks.data_collection_tasks.asyncio.run[")": def test_collect_odds_task_default_params(": self,": mock_asyncio_run,"
        mock_collector_class,
        mock_task_self,
        mock_odds_collector):
        "]""测试赔率采集任务默认参数"""
        # 设置模拟对象
        mock_collector_class.return_value = mock_odds_collector
        mock_odds_collector.collect_odds.return_value = {
            "status[": ["]success[",""""
            "]success_count[": 10,""""
            "]error_count[": 0,""""
            "]records_collected[": 20}": mock_asyncio_run.return_value = {"""
            "]status[": ["]success[",""""
            "]success_count[": 10,""""
            "]error_count[": 0,""""
            "]records_collected[": 20}""""
        # 调用任务（无参数）
        result = collect_odds_task(mock_task_self)
        # 验证默认参数结果
        assert result["]status["] =="]success[" assert result["]records_collected["] ==20[" class TestDataCollectionTaskIntegration:"""
    "]]""数据采集任务集成测试"""
    def test_task_retry_configuration(self):
        """测试任务重试配置集成"""
        from src.tasks.data_collection_tasks import TaskRetryConfig
        # 验证collect_fixtures_task的重试配置
        config = TaskRetryConfig.get_retry_config("collect_fixtures_task[")": assert config["]max_retries["] ==3[" assert config["]]retry_delay["] ==300[" assert config["]]retry_backoff["] is True[" assert config["]]retry_jitter["] is True[" def test_task_error_logging_integration(self):"""
        "]]""测试任务错误日志记录集成"""
        # 验证DataCollectionTask正确集成了错误日志记录
        with patch(:
            "src.tasks.data_collection_tasks.TaskErrorLogger["""""
        ) as mock_logger_class = mock_logger Mock()
            mock_logger_class.return_value = mock_logger
            task = DataCollectionTask()
            # 验证错误日志记录器被正确初始化
            assert task.error_logger ==mock_logger
            mock_logger_class.assert_called_once()
    @patch("]src.tasks.data_collection_tasks.datetime[")": def test_task_execution_time_format(self, mock_datetime):"""
        "]""测试任务执行时间格式"""
        # 模拟当前时间
        now = datetime(2025, 9, 29, 12, 0, 0)
        mock_datetime.now.return_value = now
        mock_datetime.isoformat = Mock(return_value="2025-09-29T12:0000[")""""
        # 验证时间格式
        with patch("]src.tasks.data_collection_tasks.RealFixturesCollector["), patch(:""""
            "]src.tasks.data_collection_tasks.asyncio.run["""""
        ) as mock_run:
            mock_run.return_value = {
                "]status[": ["]success[",""""
                "]success_count[": 1,""""
                "]error_count[": 0,""""
                "]records_collected[": 1}": mock_self = Mock()": mock_self.error_logger = Mock()": mock_self.request = Mock()"
            mock_self.request.retries = 0
            result = collect_fixtures_task(mock_self)
            # 验证执行时间格式
            assert "]execution_time[" in result[""""
            assert result["]]execution_time["] =="]2025-09-29T120000[" if __name__ =="]__main__[": pytest.main(""""
        ["]__file__[",""""
            "]-v[",""""
            "]--cov=src.tasks.data_collection_tasks[",""""
            "]--cov-report=term-missing["]"]"""
    )
        import inspect
        from src.tasks.data_collection_tasks import TaskRetryConfig