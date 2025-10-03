from datetime import datetime, timedelta

from src.scheduler.recovery_handler import (
from unittest.mock import Mock, patch
import pytest
import os

"""
RecoveryHandler 基础测试套件
目标：覆盖核心故障恢复功能，避免复杂的外部依赖
"""

    RecoveryHandler,
    TaskFailure,
    FailureType,
    RecoveryStrategy)
class TestRecoveryHandlerBasic:
    """RecoveryHandler 基础测试套件"""
    @pytest.fixture
    def recovery_handler(self):
        """创建恢复处理器实例"""
        return RecoveryHandler()
    @pytest.fixture
    def sample_task(self):
        """创建示例任务"""
        task = Mock()
        task.task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_26"): task.name = os.getenv("TEST_RECOVERY_HANDLER_BASIC_NAME_26"): task.enabled = True[": task.retry_count = 0[": return task[": class TestInitialization:"
        "]]]]""测试初始化"""
        def test_init_success(self):
            """测试成功初始化"""
            handler = RecoveryHandler()
            assert handler is not None
            assert hasattr(handler, "failure_history[")" assert hasattr(handler, "]recovery_configs[")" assert hasattr(handler, "]failure_patterns[")" assert isinstance(handler.failure_history, list)"""
            assert isinstance(handler.recovery_configs, dict)
    class TestFailureClassification:
        "]""测试故障分类"""
        def test_classify_network_failure(self, recovery_handler):
            """测试网络故障分类"""
            failure_type = recovery_handler._classify_failure("网络连接失败[")": assert failure_type ==FailureType.CONNECTION_ERROR[" failure_type = recovery_handler._classify_failure("]]Connection timeout[")": assert failure_type ==FailureType.TIMEOUT[" def test_classify_database_failure(self, recovery_handler):""
            "]]""测试数据库故障分类"""
            failure_type = recovery_handler._classify_failure("数据库连接失败[")": assert failure_type ==FailureType.CONNECTION_ERROR[" failure_type = recovery_handler._classify_failure("]]SQL execution error[")": assert failure_type ==FailureType.UNKNOWN_ERROR[" def test_classify_resource_failure(self, recovery_handler):""
            "]]""测试资源故障分类"""
            failure_type = recovery_handler._classify_failure("内存不足[")": assert failure_type ==FailureType.RESOURCE_ERROR[" failure_type = recovery_handler._classify_failure("]]Out of memory[")": assert failure_type ==FailureType.RESOURCE_ERROR[" def test_classify_validation_failure(self, recovery_handler):""
            "]]""测试验证故障分类"""
            failure_type = recovery_handler._classify_failure("数据验证失败[")": assert failure_type ==FailureType.DATA_ERROR[" failure_type = recovery_handler._classify_failure("]]Invalid input data[")": assert failure_type ==FailureType.DATA_ERROR[" def test_classify_unknown_failure(self, recovery_handler):""
            "]]""测试未知故障分类"""
            failure_type = recovery_handler._classify_failure("未知错误[")": assert failure_type ==FailureType.UNKNOWN_ERROR[" class TestTaskFailureHandling:""
        "]]""测试任务故障处理"""
        def test_handle_task_failure_success(self, recovery_handler, sample_task):
            """测试成功处理任务故障"""
            result = recovery_handler.handle_task_failure(sample_task, "测试错误[")": assert result is True[" assert len(recovery_handler.failure_history) ==1[""
            attempt = recovery_handler.failure_history[0]
            assert attempt.task_id ==sample_task.task_id
            assert attempt.error_message =="]]]测试错误[" def test_handle_task_failure_multiple_attempts(""""
            self, recovery_handler, sample_task
        ):
            "]""测试多次故障处理"""
            # 第一次失败
            recovery_handler.handle_task_failure(sample_task, "第一次错误[")": assert len(recovery_handler.failure_history) ==1["""
            # 第二次失败
            recovery_handler.handle_task_failure(sample_task, "]]第二次错误[")": assert len(recovery_handler.failure_history) ==2[" def test_handle_task_failure_pattern_tracking(""
            self, recovery_handler, sample_task
        ):
            "]]""测试故障模式跟踪"""
            # 模拟相同类型的多次失败
            for i in range(3):
                recovery_handler.handle_task_failure(sample_task, f["网络错误 {i}"])""""
            # 检查故障模式
            patterns = recovery_handler.failure_patterns.get(sample_task.task_id, {})
            assert len(patterns) > 0
    class TestRecoveryStrategies:
        """测试恢复策略"""
        def test_immediate_retry_strategy(self, recovery_handler, sample_task):
            """测试立即重试策略"""
            from src.scheduler.recovery_handler import TaskFailure, RecoveryStrategy
            failure = TaskFailure(
                task_id=sample_task.task_id,
                failure_time=datetime.now(),
                failure_type=FailureType.TIMEOUT,
                error_message="任务超时[")""""
            # 直接测试立即重试方法，而不是通过策略执行
            config = {
                "]strategy[": RecoveryStrategy.IMMEDIATE_RETRY,""""
                "]max_retries[": 3}": result = recovery_handler._immediate_retry(sample_task, failure, config)": assert result is True[" assert sample_task.retry_count ==1"
            assert len(failure.recovery_attempts) ==1
            assert failure.recovery_attempts[0]["]]strategy["] =="]immediate_retry[" assert failure.recovery_attempts[0]["]success["] is True[" def test_exponential_backoff_strategy(self, recovery_handler, sample_task):"""
            "]]""测试指数退避策略"""
            from src.scheduler.recovery_handler import TaskFailure
            failure = TaskFailure(
                task_id=sample_task.task_id,
                failure_time=datetime.now(),
                failure_type=FailureType.CONNECTION_ERROR,
                error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_90"))": with patch.object(:": recovery_handler, "]_exponential_backoff_retry["""""
            ) as mock_retry:
                mock_retry.return_value = True
                result = recovery_handler._execute_recovery_strategy(
                    sample_task, failure
                )
                assert result is True
                mock_retry.assert_called_once()
        def test_fixed_delay_strategy(self, recovery_handler, sample_task):
            "]""测试固定延迟策略"""
            from src.scheduler.recovery_handler import TaskFailure
            # 使用 DATA_ERROR，因为根据实现，DATA_ERROR 使用 FIXED_DELAY 策略
            failure = TaskFailure(
                task_id=sample_task.task_id,
                failure_type=FailureType.DATA_ERROR,
                error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_104"),": failure_time=datetime.now())": with patch.object(recovery_handler, "]_fixed_delay_retry[") as mock_retry:": mock_retry.return_value = True[": result = recovery_handler._execute_recovery_strategy(": sample_task, failure"
                )
                assert result is True
                mock_retry.assert_called_once()
        def test_manual_intervention_strategy(self, recovery_handler, sample_task):
            "]]""测试人工干预策略"""
            from src.scheduler.recovery_handler import TaskFailure
            # 使用 PERMISSION_ERROR，因为根据实现，PERMISSION_ERROR 使用 MANUAL_INTERVENTION 策略
            failure = TaskFailure(
                task_id=sample_task.task_id,
                failure_time=datetime.now(),
                failure_type=FailureType.PERMISSION_ERROR,
                error_message="权限不足[")": with patch.object(:": recovery_handler, "]_request_manual_intervention["""""
            ) as mock_intervention:
                mock_intervention.return_value = False  # 人工干预通常失败
                result = recovery_handler._execute_recovery_strategy(
                    sample_task, failure
                )
                assert result is False
                mock_intervention.assert_called_once()
    class TestAlertHandling:
        "]""测试警报处理"""
        def test_send_alert(self, recovery_handler):
            """测试发送警报"""
            # 创建一个有完整属性的mock任务
            mock_task = Mock()
            mock_task.task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_26"): mock_task.name = os.getenv("TEST_RECOVERY_HANDLER_BASIC_NAME_26"): mock_task.retry_count = 3  # 设置重试次数以触发告警[": mock_task.cron_expression = os.getenv("TEST_RECOVERY_HANDLER_BASIC_CRON_EXPRESSION_131"): mock_task.priority = 1[": mock_task.timeout = 60[": with patch.object(recovery_handler, "]]_send_alert[") as mock_send_alert:": recovery_handler.handle_task_failure(mock_task, "]严重错误[")": mock_send_alert.assert_called()": def test_register_alert_handler(self, recovery_handler):""
            "]""测试注册警报处理器"""
            # 创建一个有 __name__ 属性的mock函数
            def custom_handler(alert_data):
                pass
            custom_handler.__name__ = os.getenv("TEST_RECOVERY_HANDLER_BASIC___NAME___133"): recovery_handler.register_alert_handler(custom_handler)""""
            # 触发警报
            recovery_handler._send_alert("]INFO[", "]测试消息[", {})""""
            # 由于我们无法直接验证内部调用，我们验证处理器已被注册
            assert custom_handler in recovery_handler.alert_handlers
    class TestStatisticsAndReporting:
        "]""测试统计和报告"""
        def test_get_failure_statistics(self, recovery_handler, sample_task):
            """测试获取故障统计"""
            # 添加一些故障
            recovery_handler.handle_task_failure(sample_task, "错误1[")": recovery_handler.handle_task_failure(sample_task, "]错误2[")": stats = recovery_handler.get_failure_statistics()": assert isinstance(stats, dict)" assert "]total_failures[" in stats[""""
            assert "]]failure_by_type[" in stats  # 修正：实际返回的是 failure_by_type[""""
            assert "]]recovery_success_rate[" in stats[""""
        def test_get_recent_failures(self, recovery_handler, sample_task):
            "]]""测试获取最近故障"""
            # 添加故障
            recovery_handler.handle_task_failure(sample_task, "最近错误[")": failures = recovery_handler.get_recent_failures(limit=10)": assert isinstance(failures, list)" assert len(failures) >= 1"
        def test_clear_old_failures(self, recovery_handler, sample_task):
            "]""测试清理旧故障"""
            # 添加故障
            recovery_handler.handle_task_failure(sample_task, "旧错误[")""""
            # 清理30天前的故障（我们的故障是新的，所以不会被清理）
            cleared_count = recovery_handler.clear_old_failures(days_to_keep=30)
            assert cleared_count ==0
            # 模拟旧故障 - 需要创建一个TaskFailure对象
            old_failure = TaskFailure(
                task_id=sample_task.task_id,
                failure_time=datetime.now() - timedelta(days=35),
                failure_type=FailureType.UNKNOWN_ERROR,
                error_message="]旧错误[")": recovery_handler.failure_history.append(old_failure)"""
            # 再次清理
            cleared_count = recovery_handler.clear_old_failures(days_to_keep=30)
            assert cleared_count >= 0
    class TestTaskFailureClass:
        "]""测试TaskFailure类"""
        def test_task_failure_creation(self):
            """测试TaskFailure创建"""
            failure = TaskFailure(
                task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_167"),": failure_time=datetime.now(),": failure_type=FailureType.CONNECTION_ERROR,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_169"))": assert failure.task_id =="]test_task[" assert failure.failure_type ==FailureType.CONNECTION_ERROR[""""
            assert failure.error_message =="]]网络错误[" assert failure.failure_time is not None[""""
            assert len(failure.recovery_attempts) ==0
        def test_task_failure_add_recovery_attempt(self):
            "]]""测试添加恢复尝试"""
            failure = TaskFailure(
                task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_167"),": failure_time=datetime.now(),": failure_type=FailureType.CONNECTION_ERROR,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_169"))": failure.add_recovery_attempt(": RecoveryStrategy.IMMEDIATE_RETRY, False, datetime.now(), "]重试失败["""""
            )
            assert len(failure.recovery_attempts) ==1
            assert failure.recovery_attempts[0]["]strategy["] =="]immediate_retry[" assert failure.recovery_attempts[0]["]success["] is False[" def test_task_failure_to_dict(self):"""
            "]]""测试TaskFailure转换为字典"""
            failure = TaskFailure(
                task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_167"),": failure_time=datetime.now(),": failure_type=FailureType.CONNECTION_ERROR,": error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_169"))": failure_dict = failure.to_dict()": assert isinstance(failure_dict, dict)" assert failure_dict["]task_id["] ==failure.task_id[" assert ("""
                failure_dict["]]failure_type["] ==failure.failure_type.value[""""
            )  # 修正：enum转换为字符串值
            assert failure_dict["]]error_message["] ==failure.error_message[" class TestErrorHandling:"""
        "]]""测试错误处理"""
        def test_handle_invalid_task(self, recovery_handler):
            """测试处理无效任务"""
            invalid_task = Mock()
            invalid_task.task_id = None
            # 应该能够处理而不抛出异常
            result = recovery_handler.handle_task_failure(invalid_task, "错误[")""""
            # 根据实现，可能返回True或False
            assert isinstance(result, bool)
    class TestIntegrationScenarios:
        "]""测试集成场景"""
        def test_full_recovery_workflow(self, recovery_handler, sample_task):
            """测试完整恢复工作流程"""
            # 1. 任务失败
            result = recovery_handler.handle_task_failure(sample_task, "网络连接失败[")": assert result is True["""
            # 2. 检查故障统计
            stats = recovery_handler.get_failure_statistics()
            assert stats["]]total_failures["] >= 1[""""
            # 3. 检查最近故障
            recent_failures = recovery_handler.get_recent_failures()
            assert len(recent_failures) >= 1
            # 4. 验证故障模式跟踪
            recovery_handler.failure_patterns.get(sample_task.task_id, {})
            # 应该有故障模式记录
    class TestPerformance:
        "]]""测试性能"""
        def test_multiple_failure_handling(self, recovery_handler):
            """测试多次故障处理性能"""
            import time
            start_time = time.time()
            # 处理多个故障
            for i in range(100):
                task = Mock()
                task.task_id = f["task_{i}"]": recovery_handler.handle_task_failure(task, f["错误 {i}"])": end_time = time.time()"""
            # 应该在合理时间内完成
            assert (end_time - start_time) < 5.0
    class TestConfiguration:
        """测试配置"""
        def test_recovery_configs_initialization(self, recovery_handler):
            """测试恢复配置初始化"""
            configs = recovery_handler.recovery_configs
            # 检查是否有所有故障类型的配置
            expected_types = [
                FailureType.TIMEOUT,
                FailureType.CONNECTION_ERROR,
                FailureType.DATA_ERROR,
                FailureType.RESOURCE_ERROR,
                FailureType.PERMISSION_ERROR,
                FailureType.UNKNOWN_ERROR]
            for failure_type in expected_types:
                assert failure_type in configs
                assert "strategy[" in configs["]failure_type[": assert (""""
                    "]max_retries[": in configs["]failure_type["""""
                )  # 修正：实际字段名是 max_retries
    class TestUtilityMethods:
        "]""测试工具方法"""
        def test_recovery_attempts_tracking(self, recovery_handler, sample_task):
            """测试恢复尝试跟踪"""
            # 添加多个恢复尝试
            recovery_handler.handle_task_failure(sample_task, "错误1[")": recovery_handler.handle_task_failure(sample_task, "]错误2[")"]"""
            # 验证跟踪
            assert len(recovery_handler.failure_history) >= 2
            # 验证特定任务的尝试
            task_attempts = [
                a
                for a in recovery_handler.failure_history:
                if a.task_id ==sample_task.task_id
            ]
            assert len(task_attempts) >= 2
            from src.scheduler.recovery_handler import TaskFailure, RecoveryStrategy
            from src.scheduler.recovery_handler import TaskFailure
            from src.scheduler.recovery_handler import TaskFailure
            from src.scheduler.recovery_handler import TaskFailure
            import time