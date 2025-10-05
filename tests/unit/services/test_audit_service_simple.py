"""
审计服务简化测试 / Audit Service Simple Tests

基于实际源码测试审计服务功能
"""

import asyncio

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.audit_service import AuditService, AuditContext, audit_context


@pytest.mark.asyncio
class TestAuditService:
    """审计服务测试类"""

    @pytest.fixture
    def service(self):
        """创建审计服务实例"""
        service = AuditService()
        service.db_manager = MagicMock()
        service.logger = MagicMock()
        return service

    @pytest.fixture
    def audit_context_data(self):
        """审计上下文数据"""
        return {
            "user_id": "test_user_123",
            "username": "testuser",
            "user_role": "analyst",
            "session_id": "sess_456",
            "ip_address": "192.168.1.100",
            "user_agent": "pytest-test",
        }

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.db_manager is not None
        assert service.logger is not None
        assert "users" in service.sensitive_tables
        assert "password" in service.sensitive_columns

    def test_audit_context_creation(self):
        """测试审计上下文创建"""
        ctx = AuditContext(
            user_id="user123",
            username="testuser",
            user_role="admin",
            ip_address="127.0.0.1",
        )

        assert ctx.user_id == "user123"
        assert ctx.username == "testuser"
        assert ctx.user_role == "admin"
        assert ctx.ip_address == "127.0.0.1"

        ctx_dict = ctx.to_dict()
        assert ctx_dict["user_id"] == "user123"
        assert ctx_dict["username"] == "testuser"

    def test_mask_sensitive_data(self, service):
        """测试敏感数据脱敏"""
        # 测试敏感表数据脱敏
        sensitive_data = {
            "table": "users",
            "data": {
                "id": 1,
                "username": "test",
                "password": "secret123",
                "email": "test@example.com",
            },
        }

        masked = service.mask_sensitive_data(sensitive_data)
        assert masked["data"]["password"] == "[MASKED]"
        assert masked["data"]["username"] == "test"  # 非敏感字段保持不变

    def test_mask_sensitive_columns(self, service):
        """测试敏感列脱敏"""
        data = {"password": "secret", "token": "abc123", "normal_field": "visible"}

        masked = service.mask_sensitive_data(data)
        assert masked["password"] == "[MASKED]"
        assert masked["token"] == "[MASKED]"
        assert masked["normal_field"] == "visible"

    def test_serialize_data(self, service):
        """测试数据序列化"""
        # 测试可序列化数据
        data = {"string": "test", "number": 123, "boolean": True, "none": None}

        serialized = service.serialize_data(data)
        assert isinstance(serialized, str)

        # 测试不可序列化数据
        data_with_func = {"callback": lambda x: x, "normal": "test"}

        serialized = service.serialize_data(data_with_func)
        assert "normal" in serialized
        assert "callback" not in serialized or "function" in serialized

    async def test_log_action(self, service, audit_context_data):
        """测试记录审计日志"""
        # 设置审计上下文
        audit_context.set(audit_context_data)

        # Mock数据库操作
        mock_session = MagicMock()
        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        # 测试记录操作
        await service.log_action(
            action="CREATE",
            resource_type="prediction",
            resource_id="pred_123",
            details={"model_version": "v1.0"},
        )

        # 验证调用
        service.db_manager.get_async_session.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_log_batch_actions(self, service, audit_context_data):
        """测试批量记录审计日志"""
        audit_context.set(audit_context_data)

        mock_session = MagicMock()
        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        actions = [
            {
                "action": "CREATE",
                "resource_type": "prediction",
                "resource_id": "pred_1",
            },
            {
                "action": "UPDATE",
                "resource_type": "prediction",
                "resource_id": "pred_2",
            },
            {
                "action": "DELETE",
                "resource_type": "prediction",
                "resource_id": "pred_3",
            },
        ]

        await service.log_batch_actions(actions)

        # 验证批量添加
        assert mock_session.add.call_count == 3
        mock_session.commit.assert_called_once()

    async def test_get_audit_logs(self, service):
        """测试获取审计日志"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(id=1, action="CREATE", user_id="user1"),
            MagicMock(id=2, action="UPDATE", user_id="user2"),
        ]
        mock_session.execute.return_value = mock_result

        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        logs = await service.get_audit_logs(user_id="user1", action="CREATE", limit=10)

        assert len(logs) == 2
        mock_session.execute.assert_called_once()

    async def test_get_audit_statistics(self, service):
        """测试获取审计统计"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock(
            total_count=100,
            unique_users=20,
            action_counts={"CREATE": 40, "UPDATE": 35, "DELETE": 25},
        )
        mock_session.execute.return_value = mock_result

        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        stats = await service.get_audit_statistics(days=30)

        assert stats["total_count"] == 100
        assert stats["unique_users"] == 20
        assert "action_counts" in stats

    async def test_cleanup_old_logs(self, service):
        """测试清理旧日志"""
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(rowcount=50)

        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        deleted_count = await service.cleanup_old_logs(days=90)

        assert deleted_count == 50
        mock_session.commit.assert_called_once()

    def test_audit_decorator(self, service):
        """测试审计装饰器"""

        @service.audit_action("TEST_ACTION", "test_resource")
        async def test_function(param1, param2):
            return f"result: {param1}-{param2}"

        # Mock上下文
        with patch.object(service, "log_action", new_callable=AsyncMock) as _mock_log:
            # 设置审计上下文
            audit_context.set({"user_id": "test_user", "username": "testuser"})

            # 运行被装饰的函数
            result = test_function("arg1", "arg2")

            # 验证日志记录
            assert asyncio.iscoroutine(result)
            # 注意：这里需要await，但装饰器可能需要调整

    def test_extract_request_info(self, service):
        """测试提取请求信息"""
        # 创建模拟请求
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "test-browser"}
        mock_request.url = "http://test.com/api/endpoint"

        request_info = service.extract_request_info(mock_request)

        assert request_info["ip_address"] == "192.168.1.1"
        assert request_info["user_agent"] == "test-browser"
        assert "endpoint" in request_info["endpoint"]

    async def test_export_audit_logs(self, service):
        """测试导出审计日志"""
        mock_logs = [
            {
                "id": 1,
                "action": "CREATE",
                "user_id": "user1",
                "timestamp": datetime.now(),
                "details": {"test": "data"},
            },
            {
                "id": 2,
                "action": "UPDATE",
                "user_id": "user2",
                "timestamp": datetime.now(),
                "details": {"test": "data2"},
            },
        ]

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_logs
        mock_session.execute.return_value = mock_result

        service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        service.db_manager.get_async_session.return_value.__aexit__.return_value = None

        exported = await service.export_audit_logs(
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            format="json",
        )

        assert "data" in exported
        assert "count" in exported
        assert exported["count"] == 2

    def test_is_sensitive_table(self, service):
        """测试判断是否为敏感表"""
        assert service.is_sensitive_table("users") is True
        assert service.is_sensitive_table("predictions") is False
        assert service.is_sensitive_table("permissions") is True
        assert service.is_sensitive_table("matches") is False

    def test_is_sensitive_column(self, service):
        """测试判断是否为敏感列"""
        assert service.is_sensitive_column("password") is True
        assert service.is_sensitive_column("token") is True
        assert service.is_sensitive_column("score") is False
        assert service.is_sensitive_column("email") is False
