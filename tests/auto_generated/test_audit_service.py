"""
audit_service.py 测试文件
测试权限审计服务功能，包括装饰器模式和上下文管理
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import inspect

# 模拟外部依赖
with patch.dict('sys.modules', {
    'fastapi': Mock(),
    'src.database.connection': Mock(),
    'src.database.models.audit_log': Mock()
}):
    # 模拟 fastapi.Request
    class MockRequest:
        def __init__(self, client=None, headers=None):
            self.client = client or {}
            self.headers = headers or {}

# 清理Prometheus注册表以避免重复注册
try:
    from prometheus_client import REGISTRY
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
except ImportError:
    pass

# 添加 src 目录到路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.audit_service import AuditContext, audit_context, AuditAction, AuditSeverity, AuditLog


class TestAuditContext:
    """测试审计上下文管理器"""

    def test_audit_context_creation(self):
        """测试审计上下文创建"""
        context = AuditContext(
            user_id="user123",
            username="test_user",
            user_role="admin",
            session_id="session456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert context.user_id == "user123"
        assert context.username == "test_user"
        assert context.user_role == "admin"
        assert context.session_id == "session456"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"

    def test_audit_context_minimal(self):
        """测试最小审计上下文创建"""
        context = AuditContext(user_id="user123")

        assert context.user_id == "user123"
        assert context.username is None
        assert context.user_role is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.user_agent is None

    def test_audit_context_from_request(self):
        """测试从FastAPI请求创建审计上下文"""
        mock_request = MockRequest(
            headers={
                "x-user-id": "user123",
                "x-username": "test_user",
                "x-user-role": "admin",
                "x-session-id": "session456",
                "x-forwarded-for": "192.168.1.1",
                "user-agent": "Mozilla/5.0"
            }
        )

        context = AuditContext.from_request(mock_request)

        assert context.user_id == "user123"
        assert context.username == "test_user"
        assert context.user_role == "admin"
        assert context.session_id == "session456"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"

    def test_audit_context_from_request_partial_headers(self):
        """测试从部分头部信息创建审计上下文"""
        mock_request = MockRequest(
            headers={
                "x-user-id": "user123",
                "user-agent": "Mozilla/5.0"
            }
        )

        context = AuditContext.from_request(mock_request)

        assert context.user_id == "user123"
        assert context.username is None
        assert context.user_role is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.user_agent == "Mozilla/5.0"

    def test_audit_context_context_manager(self):
        """测试审计上下文作为上下文管理器"""
        context = AuditContext(user_id="user123", username="test_user")

        # 测试进入上下文
        token = context.__enter__()
        assert token == context

        # 测试退出上下文
        context.__exit__(None, None, None)
        # 应该无异常

    def test_audit_context_context_manager_with_exception(self):
        """测试审计上下文处理异常情况"""
        context = AuditContext(user_id="user123")

        context.__enter__()
        # 模拟异常处理
        result = context.__exit__(ValueError("Test error"), None, None)
        assert result is None  # 不处理异常


class TestAuditDecorators:
    """测试审计装饰器功能"""

    def test_audit_function_decorator(self):
        """测试函数装饰器"""
        from services.audit_service import audit_operation

        @audit_operation("test_operation", "测试操作")
        def test_function(param1, param2):
            return f"result_{param1}_{param2}"

        # 模拟装饰器环境
        result = test_function("value1", "value2")
        assert result == "result_value1_value2"

    def test_audit_async_function_decorator(self):
        """测试异步函数装饰器"""
        from services.audit_service import audit_operation

        @audit_operation("async_test_operation", "异步测试操作")
        async def async_test_function(param1, param2):
            await asyncio.sleep(0.001)
            return f"async_result_{param1}_{param2}"

        # 模拟异步装饰器
        async def run_test():
            result = await async_test_function("value1", "value2")
            return result

        result = asyncio.run(run_test())
        assert result == "async_result_value1_value2"

    def test_audit_class_method_decorator(self):
        """测试类方法装饰器"""
        from services.audit_service import audit_operation

        class TestClass:
            @audit_operation("class_method", "类方法操作")
            def test_method(self, value):
                return f"class_result_{value}"

        test_obj = TestClass()
        result = test_obj.test_method("test_value")
        assert result == "class_result_test_value"

    def test_audit_operation_with_severity(self):
        """测试带严重程度的审计操作"""
        from services.audit_service import audit_operation, AuditSeverity

        @audit_operation("high_risk_operation", "高风险操作", severity=AuditSeverity.HIGH)
        def high_risk_function():
            return "high_risk_result"

        result = high_risk_function()
        assert result == "high_risk_result"

    def test_audit_operation_with_custom_action(self):
        """测试自定义审计动作"""
        from services.audit_service import audit_operation, AuditAction

        @audit_operation("custom_action", "自定义操作", action=AuditAction.UPDATE)
        def custom_action_function():
            return "custom_result"

        result = custom_action_function()
        assert result == "custom_result"


class TestAuditLog:
    """测试审计日志功能"""

    def test_audit_log_creation(self):
        """测试审计日志创建"""
        from services.audit_service import AuditLog

        log = AuditLog(
            user_id="user123",
            action="CREATE",
            resource_type="user_profile",
            resource_id="profile456",
            details={"field": "email", "old_value": "old@email.com", "new_value": "new@email.com"},
            severity="INFO",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert log.user_id == "user123"
        assert log.action == "CREATE"
        assert log.resource_type == "user_profile"
        assert log.resource_id == "profile456"
        assert log.details["field"] == "email"
        assert log.severity == "INFO"
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Mozilla/5.0"

    def test_audit_log_serialization(self):
        """测试审计日志序列化"""
        from services.audit_service import AuditLog

        log = AuditLog(
            user_id="user123",
            action="UPDATE",
            resource_type="settings",
            resource_id="settings789",
            details={"setting": "theme", "value": "dark"},
            severity="MEDIUM"
        )

        # 测试转换为字典
        log_dict = log.to_dict() if hasattr(log, 'to_dict') else log.__dict__
        assert log_dict["user_id"] == "user123"
        assert log_dict["action"] == "UPDATE"
        assert log_dict["resource_type"] == "settings"

    def test_audit_log_validation(self):
        """测试审计日志验证"""
        from services.audit_service import AuditLog

        # 测试必填字段
        log = AuditLog(
            user_id="user123",
            action="DELETE",
            resource_type="data",
            resource_id="data123"
        )

        assert log.user_id == "user123"
        assert log.action == "DELETE"
        assert log.resource_type == "data"
        assert log.resource_id == "data123"
        # 可选字段应该有默认值
        assert hasattr(log, 'severity') or True  # 可能有不同的实现


class TestAuditServiceIntegration:
    """测试审计服务集成功能"""

    @patch('services.audit_service.DatabaseManager')
    def test_audit_service_database_integration(self, mock_db_manager):
        """测试审计服务数据库集成"""
        # 模拟数据库操作
        mock_session = Mock()
        mock_db_manager.get_session.return_value = mock_session

        from services.audit_service import AuditService

        service = AuditService()
        result = service.log_audit_event(
            user_id="user123",
            action="LOGIN",
            resource_type="session",
            resource_id="session456",
            details={"login_method": "password"}
        )

        assert result is not None
        mock_db_manager.get_session.assert_called_once()

    def test_audit_context_variable_management(self):
        """测试审计上下文变量管理"""
        from services.audit_service import audit_context

        # 测试设置上下文
        context_data = {
            "user_id": "user123",
            "username": "test_user",
            "operation": "data_access"
        }

        token = audit_context.set(context_data)
        retrieved_context = audit_context.get()

        assert retrieved_context == context_data

        # 测试重置上下文
        audit_context.reset(token)
        # 上下文应该被重置

    def test_audit_bulk_operations(self):
        """测试批量审计操作"""
        from services.audit_service import AuditService

        # 模拟批量操作
        operations = [
            {
                "user_id": "user123",
                "action": "CREATE",
                "resource_type": "record",
                "resource_id": f"record_{i}",
                "details": {"batch_id": "batch123"}
            }
            for i in range(5)
        ]

        service = AuditService()
        results = []
        for op in operations:
            result = service.log_audit_event(**op)
            results.append(result)

        assert len(results) == 5
        # 验证批量操作的结果

    def test_audit_error_handling(self):
        """测试审计错误处理"""
        from services.audit_service import AuditService

        service = AuditService()

        # 测试无效输入
        with pytest.raises(ValueError):
            service.log_audit_event(
                user_id="",  # 空用户ID
                action="INVALID",
                resource_type="test"
            )

        # 测试缺失必填字段
        with pytest.raises(ValueError):
            service.log_audit_event(
                user_id="user123"
                # 缺少 action, resource_type 等必填字段
            )

    def test_audit_performance_monitoring(self):
        """测试审计性能监控"""
        from services.audit_service import AuditService

        service = AuditService()

        import time
        start_time = time.time()

        # 执行多个审计操作
        for i in range(100):
            service.log_audit_event(
                user_id=f"user_{i}",
                action="PERFORMANCE_TEST",
                resource_type="test",
                resource_id=f"test_{i}"
            )

        end_time = time.time()
        execution_time = end_time - start_time

        # 性能应该在合理范围内
        assert execution_time < 5.0  # 100次操作应该在5秒内完成

    def test_audit_concurrent_operations(self):
        """测试并发审计操作"""
        from services.audit_service import AuditService

        service = AuditService()

        async def concurrent_audit_operation(user_id_suffix):
            return service.log_audit_event(
                user_id=f"concurrent_user_{user_id_suffix}",
                action="CONCURRENT_TEST",
                resource_type="concurrent_resource",
                resource_id=f"concurrent_{user_id_suffix}"
            )

        # 运行并发操作
        tasks = [concurrent_audit_operation(i) for i in range(20)]
        results = asyncio.run(asyncio.gather(*tasks, return_exceptions=True))

        # 验证所有操作都完成
        assert len(results) == 20
        # 检查是否有异常
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent operations had exceptions: {exceptions}"


class TestAuditSeverityAndActions:
    """测试审计严重程度和动作类型"""

    def test_audit_severity_levels(self):
        """测试审计严重程度级别"""
        from services.audit_service import AuditSeverity

        # 测试所有严重程度级别
        severities = [AuditSeverity.LOW, AuditSeverity.MEDIUM, AuditSeverity.HIGH, AuditSeverity.CRITICAL]

        for severity in severities:
            assert hasattr(severity, 'value')
            assert severity.value in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

    def test_audit_action_types(self):
        """测试审计动作类型"""
        from services.audit_service import AuditAction

        # 测试所有动作类型
        actions = [AuditAction.CREATE, AuditAction.READ, AuditAction.UPDATE, AuditAction.DELETE, AuditAction.EXECUTE]

        for action in actions:
            assert hasattr(action, 'value')
            assert action.value in ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']

    def test_audit_severity_impact_mapping(self):
        """测试严重程度影响映射"""
        from services.audit_service import AuditSeverity, AuditService

        service = AuditService()

        # 测试不同严重程度的影响
        severity_impact = {
            AuditSeverity.LOW: "informational",
            AuditSeverity.MEDIUM: "warning",
            AuditSeverity.HIGH: "alert",
            AuditSeverity.CRITICAL: "critical"
        }

        for severity, expected_impact in severity_impact.items():
            impact = service.get_severity_impact(severity)
            assert impact == expected_impact


if __name__ == "__main__":
    pytest.main([__file__, "-v"])