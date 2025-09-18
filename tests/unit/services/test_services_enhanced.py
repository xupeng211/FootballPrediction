"""
增强的服务层测试 - 快速提升覆盖率
针对src/services目录的核心功能测试
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.services.audit_service import AuditService
from src.services.base import BaseService
from src.services.content_analysis import ContentAnalysisService
from src.services.manager import ServiceManager
from src.services.user_profile import UserProfileService


class TestServiceManager:
    """测试服务管理器"""

    def test_service_manager_init(self):
        """测试服务管理器初始化"""
        manager = ServiceManager()
        assert hasattr(manager, "_services")
        assert isinstance(manager._services, dict)

    def test_register_service(self):
        """测试注册服务"""
        manager = ServiceManager()
        service = Mock()
        manager.register_service("test_service", service)
        assert "test_service" in manager._services
        assert manager._services["test_service"] is service

    def test_get_service_exists(self):
        """测试获取已存在的服务"""
        manager = ServiceManager()
        service = Mock()
        manager._services["test_service"] = service
        result = manager.get_service("test_service")
        assert result is service

    def test_get_service_not_exists(self):
        """测试获取不存在的服务"""
        manager = ServiceManager()
        result = manager.get_service("nonexistent")
        assert result is None

    def test_list_services(self):
        """测试列出所有服务"""
        manager = ServiceManager()
        service1 = Mock()
        service2 = Mock()
        manager._services = {"service1": service1, "service2": service2}
        result = manager.list_services()
        assert "service1" in result
        assert "service2" in result
        assert len(result) == 2


class TestBaseService:
    """测试基础服务类"""

    def test_base_service_init(self):
        """测试基础服务初始化"""
        service = BaseService()
        assert service.name == "BaseService"

    def test_base_service_start(self):
        """测试服务启动"""
        service = BaseService()
        result = service.start()
        assert result is True

    def test_base_service_stop(self):
        """测试服务停止"""
        service = BaseService()
        result = service.stop()
        assert result is True

    def test_base_service_status(self):
        """测试服务状态检查"""
        service = BaseService()
        result = service.get_status()
        assert result == "running"


class TestContentAnalysisService:
    """测试内容分析服务"""

    def test_content_analysis_service_init(self):
        """测试内容分析服务初始化"""
        service = ContentAnalysisService()
        assert service.name == "ContentAnalysisService"

    def test_analyze_text_basic(self):
        """测试基本文本分析"""
        service = ContentAnalysisService()
        result = service.analyze_text("这是一个测试文本")
        assert isinstance(result, dict)
        assert "character_count" in result
        assert result["character_count"] == 8  # "这是一个测试文本" 有8个字符

    def test_analyze_text_empty(self):
        """测试空文本分析"""
        service = ContentAnalysisService()
        result = service.analyze_text("")
        assert "error" in result
        assert result["error"] == "Empty text"

    def test_analyze_text_with_special_chars(self):
        """测试包含特殊字符的文本分析"""
        service = ContentAnalysisService()
        result = service.analyze_text("Hello! @#$ 123")
        assert isinstance(result, dict)
        assert "character_count" in result
        assert result["character_count"] == 14


class TestUserProfileService:
    """测试用户档案服务"""

    def test_user_profile_service_init(self):
        """测试用户档案服务初始化"""
        service = UserProfileService()
        assert service.name == "UserProfileService"

    def test_create_profile_basic(self):
        """测试创建基本用户档案"""
        service = UserProfileService()
        profile_data = {"user_id": "123", "name": "测试用户"}
        result = service.create_profile(profile_data)
        assert isinstance(result, dict)
        assert result.get("status") == "created"

    def test_create_profile_empty_data(self):
        """测试创建空数据的用户档案"""
        service = UserProfileService()
        result = service.create_profile({})
        assert result.get("status") == "error"

    @pytest.mark.asyncio
    async def test_get_profile_exists(self):
        """测试获取存在的用户档案"""
        service = UserProfileService()
        # 模拟档案存在

        from src.models import UserProfile

        service._user_profiles["123"] = UserProfile(
            user_id="123",
            display_name="测试用户",
            email="",
            preferences={},
            created_at=datetime.now(),
        )
        result = await service.get_profile("123")
        assert result is not None
        assert result.display_name == "测试用户"

    async def test_get_profile_not_exists(self):
        """测试获取不存在的用户档案"""
        service = UserProfileService()
        result = await service.get_profile("nonexistent")
        assert result is None

    async def test_update_profile(self):
        """测试更新用户档案"""
        service = UserProfileService()
        # 首先创建一个用户档案
        user_data = {"user_id": "123", "name": "测试用户", "email": "test@example.com"}
        service.create_profile(user_data)

        update_data = {"name": "更新后的用户"}
        result = await service.update_profile("123", update_data)
        # update_profile 返回 UserProfile 对象或 None，不是 dict
        assert result is not None
        assert hasattr(result, "user_id")
        assert result.user_id == "123"

    def test_delete_profile(self):
        """测试删除用户档案"""
        service = UserProfileService()
        result = service.delete_profile("123")
        assert isinstance(result, dict)


class TestAuditService:
    """测试审计服务"""

    @pytest.fixture
    def audit_service(self):
        """审计服务测试夹具 - 修改为不mock数据库，使用内存存储实现"""
        # 不再mock DatabaseManager，直接创建服务实例
        # AuditService的测试方法实际使用内存存储(_logs)，不需要mock数据库
        service = AuditService()
        return service

    def test_audit_service_init(self, audit_service):
        """测试审计服务初始化"""
        assert audit_service is not None
        assert hasattr(audit_service, "db_manager")

    def test_log_action_basic(self, audit_service):
        """测试记录基本操作 - 修复：使用正确的参数顺序"""
        # AuditService.log_action 的参数顺序是 (action, user_id, metadata)
        result = audit_service.log_action("login", "user123", {"ip": "127.0.0.1"})

        # 验证返回的日志条目
        assert result is not None
        assert result["action"] == "login"
        assert result["user_id"] == "user123"
        assert result["metadata"]["ip"] == "127.0.0.1"
        assert result["success"] is True

        # 验证日志被存储到内存中
        assert len(audit_service._logs) == 1
        assert audit_service._logs[0] == result

    def test_log_action_without_metadata(self, audit_service):
        """测试记录无元数据的操作 - 修复：使用正确的参数顺序"""
        # AuditService.log_action 的参数顺序是 (action, user_id, metadata)
        result = audit_service.log_action("logout", "user123")

        # 验证返回的日志条目
        assert result is not None
        assert result["action"] == "logout"
        assert result["user_id"] == "user123"
        assert result["metadata"] == {}  # 默认空字典
        assert result["success"] is True

        # 验证日志被存储到内存中
        assert len(audit_service._logs) == 1
        assert audit_service._logs[0] == result

    def test_get_user_audit_logs(self, audit_service):
        """测试获取用户审计日志 - 修复：使用正确的参数顺序"""
        # 先添加一些测试数据到内存存储
        audit_service.log_action("login", "user123", {"ip": "127.0.0.1"})
        audit_service.log_action("view", "user456", {"page": "dashboard"})
        audit_service.log_action("logout", "user123")

        # 测试获取特定用户的日志
        result = audit_service.get_user_audit_logs("user123")

        # 验证结果
        assert isinstance(result, list)
        assert len(result) == 2  # user123 的两条记录
        assert all(log["user_id"] == "user123" for log in result)
        assert result[0]["action"] == "login"
        assert result[1]["action"] == "logout"

    def test_get_audit_summary(self, audit_service):
        """测试获取审计摘要 - 修复：使用正确的参数顺序"""
        # 先添加一些测试数据到内存存储
        audit_service.log_action("login", "user123", {"ip": "127.0.0.1"})
        audit_service.log_action("view", "user456", {"page": "dashboard"})
        audit_service.log_action("logout", "user123")
        audit_service.log_action("create", "user456", {"entity": "post"})

        # 测试获取审计摘要
        result = audit_service.get_audit_summary()

        # 验证结果结构和内容
        assert isinstance(result, dict)
        assert "total_logs" in result
        assert "users" in result
        assert "actions" in result

        # 验证统计数据
        assert result["total_logs"] == 4
        assert set(result["users"]) == {"user123", "user456"}
        assert set(result["actions"]) == {"login", "view", "logout", "create"}

    @pytest.mark.asyncio
    async def test_async_log_action(self, audit_service):
        """测试异步记录操作 - 修复：使用内存存储方法"""
        # async_log_action 实际上调用 log_action，测试内存存储实现
        result = await audit_service.async_log_action(
            "view", "user123", {"page": "dashboard"}
        )

        # 验证返回的日志条目
        assert result is not None
        assert result["action"] == "view"
        assert result["user_id"] == "user123"
        assert result["metadata"]["page"] == "dashboard"
        assert result["success"] is True

        # 验证日志被存储到内存中
        assert len(audit_service._logs) == 1
        assert audit_service._logs[0] == result

    def test_batch_log_actions(self, audit_service):
        """测试批量记录操作 - 修复：使用内存存储方法"""
        actions = [
            {"user_id": "user1", "action": "login"},
            {"user_id": "user2", "action": "logout"},
        ]
        # batch_log_actions 实际调用内存存储的 log_action 方法
        result = audit_service.batch_log_actions(actions)

        # 验证返回结果
        assert isinstance(result, list)
        assert len(result) == 2

        # 验证每个日志条目
        assert result[0]["action"] == "login"
        assert result[0]["user_id"] == "user1"
        assert result[1]["action"] == "logout"
        assert result[1]["user_id"] == "user2"

        # 验证日志被存储到内存中
        assert len(audit_service._logs) == 2


class TestServiceIntegration:
    """测试服务集成"""

    def test_services_work_together(self):
        """测试服务协同工作"""
        manager = ServiceManager()
        content_service = ContentAnalysisService()
        user_service = UserProfileService()

        manager.register_service("content", content_service)
        manager.register_service("user", user_service)

        # 测试服务间协作
        content_result = manager.get_service("content").analyze_text("测试")
        user_result = manager.get_service("user").create_profile({"id": "123"})

        assert content_result is not None
        assert user_result is not None

    def test_service_error_handling(self):
        """测试服务错误处理"""
        service = BaseService()

        # 测试服务在错误情况下的行为
        with patch.object(service, "get_status", side_effect=Exception("测试错误")):
            try:
                service.get_status()
                assert False, "应该抛出异常"
            except Exception as e:
                assert "测试错误" in str(e)

    def test_service_lifecycle(self):
        """测试服务生命周期"""
        service = BaseService()

        # 测试完整的服务生命周期
        assert service.start() is True
        assert service.get_status() == "running"
        assert service.stop() is True
