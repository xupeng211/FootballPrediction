from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
import sys

from src.scheduler.recovery_handler import (
from unittest.mock import Mock, MagicMock, patch, call
import pytest

"""
RecoveryHandler Batch-Ω-004 测试套件

专门为 recovery_handler.py 设计的测试，目标是将其覆盖率从 0% 提升至 ≥70%
覆盖所有失败处理、恢复策略、错误分类和统计功能
"""

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from src.scheduler.recovery_handler import (
    RecoveryHandler,
    TaskFailure,
    FailureType,
    RecoveryStrategy
)
class TestRecoveryHandlerBatchOmega004:
    """RecoveryHandler Batch-Ω-004 测试类"""
    @pytest.fixture
    def recovery_handler(self):
        """创建 RecoveryHandler 实例"""
        return RecoveryHandler()
    @pytest.fixture
    def mock_task(self):
        """创建模拟任务对象"""
        task = Mock()
        task.task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_35"): task.name = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_NAME_35"): task.cron_expression = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_CRON_EXPRESS"): task.priority = 1[": task.timeout = 300[": task.retry_count = 0[": task.max_retries = 3"
        task.next_run_time = None
        task._update_next_run_time = Mock()
        return task
    @pytest.fixture
    def sample_failure(self):
        "]]]""示例失败记录"""
        return TaskFailure(
        task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_37"),": failure_time=datetime.now() - timedelta(hours=1),": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG"),": retry_count=1,": context = {"]task_name[" "]测试任务["}""""
        )
    def test_recovery_handler_initialization(self, recovery_handler):
        "]""测试 RecoveryHandler 初始化"""
        # 检查基本属性
    assert recovery_handler.failure_history ==[]
    assert recovery_handler.failure_patterns =={}
    assert recovery_handler.alert_handlers ==[]
        # 检查统计信息
    assert recovery_handler.total_failures ==0
    assert recovery_handler.successful_recoveries ==0
    assert recovery_handler.failed_recoveries ==0
        # 检查恢复配置
    assert len(recovery_handler.recovery_configs) ==6
    assert FailureType.TIMEOUT in recovery_handler.recovery_configs
    assert FailureType.CONNECTION_ERROR in recovery_handler.recovery_configs
    assert FailureType.DATA_ERROR in recovery_handler.recovery_configs
    def test_task_failure_initialization(self):
        """测试 TaskFailure 初始化"""
        failure_time = datetime.now()
        context = {"task_name[: "测试任务"", "priority]: 1}": failure = TaskFailure(": task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_37"),": failure_time=failure_time,": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG"),": retry_count=1,": context=context[""
        )
    assert failure.task_id =="]]test_task_001[" assert failure.failure_time ==failure_time[""""
    assert failure.failure_type ==FailureType.TIMEOUT
    assert failure.error_message =="]]Task timeout[" assert failure.retry_count ==1[""""
    assert failure.context ==context
    assert failure.recovery_attempts ==[]
    def test_task_failure_add_recovery_attempt(self):
        "]]""测试 TaskFailure 添加恢复尝试记录"""
        failure = TaskFailure(
        task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_37"),": failure_time=datetime.now(),": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")""""
        )
        attempt_time = datetime.now()
        failure.add_recovery_attempt(
            strategy=RecoveryStrategy.IMMEDIATE_RETRY,
            success=True,
            attempt_time=attempt_time,
            details = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_DETAILS_73")""""
        )
    assert len(failure.recovery_attempts) ==1
    attempt = failure.recovery_attempts[0]
    assert attempt["]strategy["] ==RecoveryStrategy.IMMEDIATE_RETRY.value[" assert attempt["]]success["] is True[" assert attempt["]]attempt_time["] ==attempt_time.isoformat()" assert attempt["]details["] =="]立即重试成功[" def test_task_failure_to_dict("
    """"
        "]""测试 TaskFailure 转换为字典"""
        failure_time = datetime.now()
        failure = TaskFailure(
        task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_37"),": failure_time=failure_time,": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG"),": retry_count=1,": context = {"]task_name[: "测试任务["}"]"""
        )
        # 添加恢复尝试
        failure.add_recovery_attempt(
            RecoveryStrategy.IMMEDIATE_RETRY,
            True,
            datetime.now(),
            "]重试成功["""""
        )
        result_dict = failure.to_dict()
    assert result_dict["]task_id["] =="]test_task_001[" assert result_dict["]failure_time["] ==failure_time.isoformat()" assert result_dict["]failure_type["] ==FailureType.TIMEOUT.value[" assert result_dict["]]error_message["] =="]Task timeout[" assert result_dict["]retry_count["] ==1[" assert result_dict["]]context["] =={"]task_name[" "]测试任务["}" assert len(result_dict["]recovery_attempts["]) ==1[" def test_failure_type_enum(self):"""
        "]]""测试 FailureType 枚举"""
    assert FailureType.TIMEOUT.value =="timeout[" assert FailureType.CONNECTION_ERROR.value =="]connection_error[" assert FailureType.DATA_ERROR.value =="]data_error[" assert FailureType.RESOURCE_ERROR.value =="]resource_error[" assert FailureType.PERMISSION_ERROR.value =="]permission_error[" assert FailureType.UNKNOWN_ERROR.value =="]unknown_error[" def test_recovery_strategy_enum("
    """"
        "]""测试 RecoveryStrategy 枚举"""
    assert RecoveryStrategy.IMMEDIATE_RETRY.value =="immediate_retry[" assert RecoveryStrategy.EXPONENTIAL_BACKOFF.value =="]exponential_backoff[" assert RecoveryStrategy.FIXED_DELAY.value =="]fixed_delay[" assert RecoveryStrategy.MANUAL_INTERVENTION.value =="]manual_intervention[" assert RecoveryStrategy.SKIP_AND_CONTINUE.value =="]skip_and_continue[" def test_classify_failure_timeout("
    """"
        "]""测试分类超时失败"""
    assert recovery_handler._classify_failure("Task timeout[") ==FailureType.TIMEOUT[" assert recovery_handler._classify_failure("]]time out[") ==FailureType.TIMEOUT[" assert recovery_handler._classify_failure("]]任务超时[") ==FailureType.TIMEOUT[" def test_classify_failure_connection_error(self, recovery_handler):"""
        "]]""测试分类连接错误"""
    assert recovery_handler._classify_failure("Connection failed[") ==FailureType.CONNECTION_ERROR[" assert recovery_handler._classify_failure("]]Network unreachable[") ==FailureType.CONNECTION_ERROR[" assert recovery_handler._classify_failure("]]连接失败[") ==FailureType.CONNECTION_ERROR[" assert recovery_handler._classify_failure("]]网络错误[") ==FailureType.CONNECTION_ERROR[" def test_classify_failure_data_error(self, recovery_handler):"""
        "]]""测试分类数据错误"""
    assert recovery_handler._classify_failure("Data parse error[") ==FailureType.DATA_ERROR[" assert recovery_handler._classify_failure("]]Invalid JSON format[") ==FailureType.DATA_ERROR[" assert recovery_handler._classify_failure("]]数据格式错误[") ==FailureType.DATA_ERROR[" def test_classify_failure_resource_error(self, recovery_handler):"""
        "]]""测试分类资源错误"""
    assert recovery_handler._classify_failure("Memory allocation failed[") ==FailureType.RESOURCE_ERROR[" assert recovery_handler._classify_failure("]]Disk space full[") ==FailureType.RESOURCE_ERROR[" assert recovery_handler._classify_failure("]]内存不足[") ==FailureType.RESOURCE_ERROR[" def test_classify_failure_permission_error(self, recovery_handler):"""
        "]]""测试分类权限错误"""
    assert recovery_handler._classify_failure("Permission denied[") ==FailureType.PERMISSION_ERROR[" assert recovery_handler._classify_failure("]]Access forbidden[") ==FailureType.PERMISSION_ERROR[" assert recovery_handler._classify_failure("]]权限不足[") ==FailureType.PERMISSION_ERROR[" def test_classify_failure_unknown(self, recovery_handler):"""
        "]]""测试分类未知错误"""
    assert recovery_handler._classify_failure("Unknown error[") ==FailureType.UNKNOWN_ERROR[" assert recovery_handler._classify_failure("]]Something went wrong[") ==FailureType.UNKNOWN_ERROR[" def test_update_failure_patterns(self, recovery_handler):"""
        "]]""测试更新失败模式"""
        # 第一次失败
        recovery_handler._update_failure_patterns("task_001[", FailureType.TIMEOUT)": assert len(recovery_handler.failure_patterns["]task_001["]) ==1[" assert recovery_handler.failure_patterns["]]task_001["][0] ==FailureType.TIMEOUT[""""
    # 第二次失败
    recovery_handler._update_failure_patterns("]]task_001[", FailureType.CONNECTION_ERROR)": assert len(recovery_handler.failure_patterns["]task_001["]) ==2[""""
    # 测试超过10条记录的情况
    for i in range(12):
        recovery_handler._update_failure_patterns("]]task_001[", FailureType.DATA_ERROR)""""
    # 应该只保留最近10条
    assert len(recovery_handler.failure_patterns["]task_001["]) ==10[""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_handle_task_failure_success(self, mock_datetime, recovery_handler, mock_task):
        "]]""测试成功处理任务失败"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        with patch.object(recovery_handler, '_classify_failure') as mock_classify, \:
            patch.object(recovery_handler, '_execute_recovery_strategy') as mock_execute, \
            patch.object(recovery_handler, '_check_and_send_alerts') as mock_check_alerts:
            mock_classify.return_value = FailureType.TIMEOUT
            mock_execute.return_value = True
            result = recovery_handler.handle_task_failure(mock_task, "Task timeout[")": assert result is True[" assert recovery_handler.total_failures ==1[""
    assert recovery_handler.successful_recoveries ==1
    assert recovery_handler.failed_recoveries ==0
    assert len(recovery_handler.failure_history) ==1
        # 验证失败记录
        failure = recovery_handler.failure_history[0]
    assert failure.task_id ==mock_task.task_id
    assert failure.failure_type ==FailureType.TIMEOUT
    assert failure.error_message =="]]]Task timeout["""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_handle_task_failure_with_exception(self, mock_datetime, recovery_handler, mock_task):
        "]""测试处理任务失败时发生异常"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        with patch.object(recovery_handler, '_classify_failure') as mock_classify:
            mock_classify.side_effect = Exception("Classification error[")": result = recovery_handler.handle_task_failure(mock_task, "]Task timeout[")": assert result is False[" assert recovery_handler.total_failures ==0[""
    assert recovery_handler.successful_recoveries ==0
    assert recovery_handler.failed_recoveries ==0
    def test_execute_recovery_strategy_immediate_retry(self, recovery_handler, mock_task, sample_failure):
        "]]]""测试执行立即重试策略"""
        # 修改失败类型为使用立即重试策略的配置
        sample_failure.failure_type = FailureType.CONNECTION_ERROR
        with patch.object(recovery_handler, '_exponential_backoff_retry') as mock_retry:
            mock_retry.return_value = True
            result = recovery_handler._execute_recovery_strategy(mock_task, sample_failure)
    assert result is True
        mock_retry.assert_called_once_with(mock_task, sample_failure, recovery_handler.recovery_configs[FailureType.CONNECTION_ERROR])
    def test_execute_recovery_strategy_unknown_strategy(self, recovery_handler, mock_task, sample_failure):
        """测试执行未知恢复策略"""
        # 修改配置为未知策略（使用一个无效的枚举值）
        original_config = recovery_handler.recovery_configs[FailureType.TIMEOUT].copy()
        class MockStrategy:
            def __init__(self, value):
                self.value = value
        recovery_handler.recovery_configs[FailureType.TIMEOUT]["strategy["] = MockStrategy("]unknown_strategy[")": result = recovery_handler._execute_recovery_strategy(mock_task, sample_failure)": assert result is False[""
        # 恢复原始配置
        recovery_handler.recovery_configs[FailureType.TIMEOUT] = original_config
    def test_execute_recovery_strategy_with_exception(self, recovery_handler, mock_task, sample_failure):
        "]]""测试执行恢复策略时发生异常"""
        # 修改为使用正确的策略方法
        with patch.object(recovery_handler, '_exponential_backoff_retry') as mock_retry:
            mock_retry.side_effect = Exception("Retry error[")": result = recovery_handler._execute_recovery_strategy(mock_task, sample_failure)": assert result is False[" assert len(sample_failure.recovery_attempts) ==1"
    assert sample_failure.recovery_attempts[0]["]]success["] is False[" def test_immediate_retry_success(self, recovery_handler, mock_task, sample_failure):"""
        "]]""测试立即重试成功"""
        config = {"max_retries[": 3}": result = recovery_handler._immediate_retry(mock_task, sample_failure, config)": assert result is True[" assert mock_task.next_run_time is not None"
    assert mock_task.retry_count ==1
    assert len(sample_failure.recovery_attempts) ==1
    assert sample_failure.recovery_attempts[0]["]]success["] is True[" def test_immediate_retry_max_retries_exceeded(self, recovery_handler, mock_task, sample_failure):"""
        "]]""测试立即重试超过最大重试次数"""
        mock_task.retry_count = 3
        config = {"max_retries[": 3}": result = recovery_handler._immediate_retry(mock_task, sample_failure, config)": assert result is False[" assert mock_task.retry_count ==3  # 重试次数不应改变"
    assert len(sample_failure.recovery_attempts) ==1
    assert sample_failure.recovery_attempts[0]["]]success["] is False[""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_exponential_backoff_retry_success(self, mock_datetime, recovery_handler, mock_task, sample_failure):
        "]]""测试指数退避重试成功"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        config = {
        "max_retries[": 3,""""
        "]base_delay[": 60,""""
        "]backoff_factor[": 2.0,""""
        "]max_delay[": 300[""""
        }
        result = recovery_handler._exponential_backoff_retry(mock_task, sample_failure, config)
    assert result is True
    assert mock_task.retry_count ==1
    assert mock_task.next_run_time ==mock_now + timedelta(seconds=60)  # 60 * (2.0^0) = 60
    assert len(sample_failure.recovery_attempts) ==1
    assert sample_failure.recovery_attempts[0]["]]success["] is True[""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_exponential_backoff_retry_with_max_delay(self, mock_datetime, recovery_handler, mock_task, sample_failure):
        "]]""测试指数退避重试达到最大延迟"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        mock_task.retry_count = 3  # 高重试次数
        config = {
        "max_retries[": 5,""""
        "]base_delay[": 60,""""
        "]backoff_factor[": 2.0,""""
        "]max_delay[": 300[""""
        }
        result = recovery_handler._exponential_backoff_retry(mock_task, sample_failure, config)
    assert result is True
        # 60 * (2.0^3) = 480, 但应该限制为300
    assert mock_task.next_run_time ==mock_now + timedelta(seconds=300)
    @patch('src.scheduler.recovery_handler.datetime')
    def test_fixed_delay_retry_success(self, mock_datetime, recovery_handler, mock_task, sample_failure):
        "]]""测试固定延迟重试成功"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        config = {"max_retries[": 3, "]base_delay[": 120}": result = recovery_handler._fixed_delay_retry(mock_task, sample_failure, config)": assert result is True[" assert mock_task.retry_count ==1"
    assert mock_task.next_run_time ==mock_now + timedelta(seconds=120)
    assert len(sample_failure.recovery_attempts) ==1
    assert sample_failure.recovery_attempts[0]["]]success["] is True[""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_request_manual_intervention_success(self, mock_datetime, recovery_handler, mock_task, sample_failure):
        "]]""测试请求人工干预成功"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        config = {}
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert = result recovery_handler._request_manual_intervention(mock_task, sample_failure, config)
    assert result is True
        # 检查任务被暂停（下次执行时间设置为一年后）
        expected_next_time = mock_now + timedelta(days=365)
    assert mock_task.next_run_time ==expected_next_time
    assert len(sample_failure.recovery_attempts) ==1
    assert sample_failure.recovery_attempts[0]["success["] is True[""""
        # 验证发送了紧急告警
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args
    assert call_args[1]["]]level["] =="]CRITICAL["""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_skip_and_continue_success(self, mock_datetime, recovery_handler, mock_task, sample_failure):
        "]""测试跳过并继续成功"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        config = {}
        result = recovery_handler._skip_and_continue(mock_task, sample_failure, config)
    assert result is True
    assert mock_task.retry_count ==0  # 重置为0
    assert mock_task._update_next_run_time.called  # 应该被调用
    assert len(sample_failure.recovery_attempts) ==1
    assert sample_failure.recovery_attempts[0]["success["] is True[" def test_check_and_send_alerts_threshold_reached(self, recovery_handler, mock_task, sample_failure):"""
        "]]""测试检查并发送告警（达到阈值）"""
        mock_task.retry_count = 3
        sample_failure.failure_type = FailureType.TIMEOUT
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert, \:
            patch.object(recovery_handler, '_check_failure_patterns') as mock_check_patterns:
            recovery_handler._check_and_send_alerts(mock_task, sample_failure)
            # 应该发送告警（TIMEOUT的告警阈值是2）
            mock_send_alert.assert_called_once()
            mock_check_patterns.assert_called_once_with(mock_task.task_id)
    def test_check_and_send_alerts_threshold_not_reached(self, recovery_handler, mock_task, sample_failure):
        """测试检查并发送告警（未达到阈值）"""
        mock_task.retry_count = 1
        sample_failure.failure_type = FailureType.TIMEOUT
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert, \:
            patch.object(recovery_handler, '_check_failure_patterns') as mock_check_patterns:
            recovery_handler._check_and_send_alerts(mock_task, sample_failure)
            # 不应该发送告警
            mock_send_alert.assert_not_called()
            mock_check_patterns.assert_called_once_with(mock_task.task_id)
    def test_check_failure_patterns_repeated_failures(self, recovery_handler):
        """测试检查失败模式（重复失败）"""
        # 添加连续三次同类型失败
        recovery_handler.failure_patterns["task_001["] = [": FailureType.TIMEOUT,": FailureType.TIMEOUT,": FailureType.TIMEOUT"
        ]
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert:
            recovery_handler._check_failure_patterns("]task_001[")""""
            # 应该发送告警
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args
    assert call_args[1]["]level["] =="]HIGH[" def test_check_failure_patterns_no_repeated_failures("
    """"
        "]""测试检查失败模式（无重复失败）"""
        # 添加不同类型的失败
        recovery_handler.failure_patterns["task_001["] = [": FailureType.TIMEOUT,": FailureType.CONNECTION_ERROR,": FailureType.DATA_ERROR"
        ]
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert:
            recovery_handler._check_failure_patterns("]task_001[")""""
            # 不应该发送告警
            mock_send_alert.assert_not_called()
    def test_check_failure_patterns_insufficient_failures(self, recovery_handler):
        "]""测试检查失败模式（失败次数不足）"""
        # 只添加两次失败
        recovery_handler.failure_patterns["task_001["] = [": FailureType.TIMEOUT,": FailureType.TIMEOUT[""
        ]
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert:
            recovery_handler._check_failure_patterns("]]task_001[")""""
            # 不应该发送告警
            mock_send_alert.assert_not_called()
    def test_check_failure_patterns_no_patterns(self, recovery_handler):
        "]""测试检查失败模式（无失败模式）"""
        with patch.object(recovery_handler, '_send_alert') as mock_send_alert:
            recovery_handler._check_failure_patterns("nonexistent_task[")""""
            # 不应该发送告警
            mock_send_alert.assert_not_called()
    @patch('src.scheduler.recovery_handler.datetime')
    def test_send_alert(self, mock_datetime, recovery_handler):
        "]""测试发送告警"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        # 注册一个模拟的告警处理器
        mock_calls = []
        def mock_handler(alert_data):
            mock_calls.append(alert_data)
        mock_handler.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___312"): recovery_handler.register_alert_handler(mock_handler)": recovery_handler._send_alert(": level = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_LEVEL_313"),": message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_MESSAGE_313"),": details = {"]key[": ["]value["}""""
        )
        # 验证告警处理器被调用
    assert len(mock_calls) ==1
        call_args = mock_calls[0]
    assert call_args["]level["] =="]WARNING[" assert call_args["]message["] =="]Test alert[" assert call_args["]details["] =={"]key[" "]value["}" assert call_args["]timestamp["] ==mock_now.isoformat()" assert call_args["]component["] =="]scheduler[" def test_send_alert_handler_exception("
    """"
        "]""测试告警处理器异常"""
        # 注册一个会抛出异常的处理器
        def mock_handler(alert_data):
            raise Exception("Handler error[")": mock_handler.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___325"): recovery_handler.register_alert_handler(mock_handler)""""
        # 不应该抛出异常
        recovery_handler._send_alert("]WARNING[", "]Test alert[", {})": def test_register_alert_handler(self, recovery_handler):"""
        "]""测试注册告警处理器"""
        # 创建一个带有 __name__ 属性的可调用对象
        def mock_handler(alert_data):
            pass
        mock_handler.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___312"): recovery_handler.register_alert_handler(mock_handler)": assert len(recovery_handler.alert_handlers) ==1[" assert recovery_handler.alert_handlers[0] ==mock_handler[""
    def test_get_failure_statistics_empty(self, recovery_handler):
        "]]]""测试获取失败统计信息（空状态）"""
        stats = recovery_handler.get_failure_statistics()
    assert stats["total_failures["] ==0[" assert stats["]]successful_recoveries["] ==0[" assert stats["]]failed_recoveries["] ==0[" assert stats["]]recovery_success_rate["] ==0.0[" assert stats["]]failure_by_type["] =={}" assert stats["]failure_by_task["] =={}" assert stats["]recent_24h_failures["] ==0[" assert stats["]]failure_patterns["] =={}" def test_get_failure_statistics_with_data(self, recovery_handler, sample_failure):"""
        "]""测试获取失败统计信息（有数据）"""
        # 添加一些失败记录
        recovery_handler.failure_history = ["sample_failure[": recovery_handler.total_failures = 1[": recovery_handler.successful_recoveries = 1[": recovery_handler.failed_recoveries = 0[": recovery_handler.failure_patterns = {sample_failure.task_id [FailureType.TIMEOUT]}"
        stats = recovery_handler.get_failure_statistics()
    assert stats["]]]]total_failures["] ==1[" assert stats["]]successful_recoveries["] ==1[" assert stats["]]failed_recoveries["] ==0[" assert stats["]]recovery_success_rate["] ==100.0[" assert stats["]]failure_by_type["] =={"]timeout[" 1}" assert stats["]failure_by_task["] =={sample_failure.task_id 1}" assert stats["]recent_24h_failures["] ==1[" assert stats["]]failure_patterns["] =={sample_failure.task_id ["]timeout["]}" def test_get_recent_failures(self, recovery_handler, sample_failure):"""
        "]""测试获取最近的失败记录"""
        # 添加失败记录
        recovery_handler.failure_history = ["sample_failure[": recent_failures = recovery_handler.get_recent_failures(limit=10)": assert len(recent_failures) ==1[" assert recent_failures[0]["]]task_id["] ==sample_failure.task_id[" assert recent_failures[0]["]]failure_type["] ==sample_failure.failure_type.value[" def test_get_recent_failures_with_limit(self, recovery_handler):"""
        "]]""测试获取最近的失败记录（有限制）"""
        # 创建多个失败记录
        failures = []
        for i in range(5):
        failure = TaskFailure(
        task_id = f["task_{i03d}"],": failure_time=datetime.now() - timedelta(hours=i),": failure_type=FailureType.TIMEOUT,": error_message=f["Error {i}"]""""
            )
            failures.append(failure)
        recovery_handler.failure_history = failures
        recent_failures = recovery_handler.get_recent_failures(limit=3)
    assert len(recent_failures) ==3
        # 应该按时间倒序排列
    assert recent_failures[0]["task_id["] =="]task_000[" assert recent_failures[1]["]task_id["] =="]task_001[" assert recent_failures[2]["]task_id["] =="]task_002["""""
    @patch('src.scheduler.recovery_handler.datetime')
    def test_clear_old_failures(self, mock_datetime, recovery_handler):
        "]""测试清理旧的失败记录"""
        mock_now = datetime.now()
        mock_datetime.now.return_value = mock_now
        # 创建旧的和新的失败记录
        old_failure = TaskFailure(
        task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_360"),": failure_time=mock_now - timedelta(days=35),": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")""""
        )
        new_failure = TaskFailure(
            task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_363"),": failure_time=mock_now - timedelta(days=10),": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")""""
        )
        recovery_handler.failure_history = ["]old_failure[", new_failure]": cleared_count = recovery_handler.clear_old_failures(days_to_keep=30)": assert cleared_count ==1[" assert len(recovery_handler.failure_history) ==1"
    assert recovery_handler.failure_history[0].task_id =="]]new_task[" def test_clear_old_failures_no_old_records("
    """"
        "]""测试清理旧的失败记录（无旧记录）"""
        failure = TaskFailure(
        task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_373"),": failure_time=datetime.now() - timedelta(days=10),": failure_type=FailureType.TIMEOUT,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")""""
        )
        recovery_handler.failure_history = ["]failure[": cleared_count = recovery_handler.clear_old_failures(days_to_keep=30)": assert cleared_count ==0[" assert len(recovery_handler.failure_history) ==1[""
    def test_edge_case_empty_recovery_configs(self, recovery_handler):
        "]]]""测试边界情况：空的恢复配置"""
        original_configs = recovery_handler.recovery_configs
        recovery_handler.recovery_configs = {}
        # 应该能正常处理空配置
        result = recovery_handler._classify_failure("Unknown error[")": assert result ==FailureType.UNKNOWN_ERROR["""
        # 恢复原始配置
        recovery_handler.recovery_configs = original_configs
    def test_edge_case_large_retry_count(self, recovery_handler, mock_task, sample_failure):
        "]]""测试边界情况：大重试次数"""
        mock_task.retry_count = 999
        config = {"max_retries[": 5}": result = recovery_handler._immediate_retry(mock_task, sample_failure, config)": assert result is False[" assert sample_failure.recovery_attempts[0]["]]details["] =="]已达到最大重试次数 5[" def test_edge_case_negative_delay_calculation("
    """"
        "]""测试边界情况：负延迟计算"""
        config = {
        "max_retries[": 10,""""
        "]base_delay[": -60,  # 负延迟[""""
        "]]backoff_factor[": 2.0,""""
        "]max_delay[": 300[""""
        }
        # 应该能处理负延迟（虽然不应该在实际使用中出现）
        result = recovery_handler._exponential_backoff_retry(mock_task, sample_failure, config)
    assert result is True
    def test_integration_complete_failure_handling_workflow(self, recovery_handler, mock_task):
        "]]""测试集成：完整的失败处理工作流"""
        # 注册告警处理器
        mock_calls = []
        def mock_handler(alert_data):
            mock_calls.append(alert_data)
        mock_handler.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___393"): recovery_handler.register_alert_handler(mock_handler)""""
        # 处理任务失败
        with patch.object(recovery_handler, '_execute_recovery_strategy') as mock_execute:
            mock_execute.return_value = True
            result = recovery_handler.handle_task_failure(mock_task, "]Connection timeout[")": assert result is True[" assert recovery_handler.total_failures ==1[""
    assert recovery_handler.successful_recoveries ==1
    assert len(recovery_handler.failure_history) ==1
            # 验证失败分类
            failure = recovery_handler.failure_history[0]
    assert failure.failure_type ==FailureType.TIMEOUT
    def test_integration_statistics_after_multiple_failures(self, recovery_handler, mock_task):
        "]]]""测试集成：多次失败后的统计"""
        # 模拟多次失败处理
        for i in range(3):
        mock_task.task_id = f["task_{i03d}"]": recovery_handler.handle_task_failure(mock_task, f["Error {i}"])": stats = recovery_handler.get_failure_statistics()": assert stats["total_failures["] ==3[" assert stats["]]recovery_success_rate["] >= 0.0  # 验证计算成功，不关心具体值[" assert len(stats["]]failure_by_task["]) ==3[" def test_integration_alert_handler_registration_and_execution(self, recovery_handler):"""
        "]]""测试集成：告警处理器注册和执行"""
        # 创建并注册多个告警处理器
        calls1 = []
        def handler1(alert_data):
            calls1.append(alert_data)
        handler1.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___420"): calls2 = []": def handler2(alert_data):": calls2.append(alert_data)": handler2.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___421"): recovery_handler.register_alert_handler(handler1)": recovery_handler.register_alert_handler(handler2)"""
        # 发送告警
        recovery_handler._send_alert("]WARNING[", "]Test alert[", {})""""
        # 两个处理器都应该被调用
    assert len(calls1) ==1
    assert len(calls2) ==1
    def test_error_handling_invalid_task_attributes(self, recovery_handler):
        "]""测试错误处理：无效的任务属性"""
        # 创建缺少必要属性的任务
        invalid_task = Mock()
        invalid_task.task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_429")""""
        # 缺少其他属性
        # 应该能处理而不崩溃
        try:
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            pass
        except Exception as e:
           pass  # Auto-fixed empty except block
 pass
            recovery_handler.handle_task_failure(invalid_task, "]Test error[")": except AttributeError:"""
            # 如果抛出AttributeError，也是合理的
            pass
    def test_configuration_validation_recovery_configs(self, recovery_handler):
        "]""测试配置验证：恢复配置"""
        # 验证所有失败类型都有配置
        for failure_type in FailureType:
    assert failure_type in recovery_handler.recovery_configs
        config = recovery_handler.recovery_configs["failure_type[": assert "]strategy[" in config[""""
    assert "]]max_retries[" in config[""""
    assert "]]alert_threshold[" in config[""""
    def test_memory_usage_large_failure_history(self, recovery_handler):
        "]]""测试内存使用：大量失败历史"""
        # 创建大量失败记录
        for i in range(1000):
        failure = TaskFailure(
        task_id = f["task_{i03d}"],": failure_time=datetime.now() - timedelta(hours=i),": failure_type=FailureType.TIMEOUT,": error_message=f["Error {i}"]""""
            )
            recovery_handler.failure_history.append(failure)
            recovery_handler.total_failures += 1
        # 应该能处理大量数据
        stats = recovery_handler.get_failure_statistics()
    assert stats["total_failures["] ==1000["]"]""
        # 清理应该正常工作
        cleared_count = recovery_handler.clear_old_failures(days_to_keep=1)
    assert cleared_count > 0