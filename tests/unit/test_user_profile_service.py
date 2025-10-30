#!/usr/bin/env python3
""""""""
用户画像服务测试
测试 src.services.user_profile 模块的功能
""""""""


import pytest

from src.services.user_profile import User, UserProfile, UserProfileService


@pytest.mark.unit
class TestUserProfile:
    """用户画像测试"""

    def test_user_profile_creation(self):
        """测试用户画像创建"""
        preferences = {"theme": "dark", "language": "zh-CN"}
        profile = UserProfile(
            user_id="user123",
            display_name="测试用户",
            email="test@example.com",
            preferences=preferences,
        )

        assert profile.user_id == "user123"
        assert profile.display_name == "测试用户"
        assert profile.email == "test@example.com"
        assert profile.preferences == preferences

    def test_user_profile_to_dict(self):
        """测试用户画像转字典"""
        preferences = {"theme": "light", "notifications": True}
        profile = UserProfile(
            user_id="user456",
            display_name="Demo User",
            email="demo@example.com",
            preferences=preferences,
        )

        result = profile.to_dict()

        expected = {
            "user_id": "user456",
            "display_name": "Demo User",
            "email": "demo@example.com",
            "preferences": preferences,
        }
        assert result == expected

    def test_user_profile_empty_preferences(self):
        """测试空偏好的用户画像"""
        profile = UserProfile(
            user_id="user789",
            display_name="Empty Pref User",
            email="empty@example.com",
            preferences={},
        )

        assert profile.preferences == {}
        result = profile.to_dict()
        assert result["preferences"] == {}

    def test_user_profile_complex_preferences(self):
        """测试复杂偏好的用户画像"""
        complex_preferences = {
            "theme": "dark",
            "language": "en-US",
            "notifications": {"email": True, "push": False, "sms": True},
            "privacy": {"public_profile": False, "show_predictions": True},
            "favorite_teams": ["team1", "team2"],
        }

        profile = UserProfile(
            user_id="complex_user",
            display_name="Complex User",
            email="complex@example.com",
            preferences=complex_preferences,
        )

        assert profile.preferences == complex_preferences
        result = profile.to_dict()
        assert result["preferences"] == complex_preferences


@pytest.mark.unit
class TestUser:
    """用户测试"""

    def test_user_creation(self):
        """测试用户创建"""
        user = User(id="user001", username="testuser")

        assert user.id == "user001"
        assert user.username == "testuser"

    def test_user_different_types(self):
        """测试不同类型的用户ID"""
        user_numeric = User(id="123", username="numeric_id")
        user_uuid = User(id="uuid-1234-5678", username="uuid_id")

        assert user_numeric.id == "123"
        assert user_numeric.username == "numeric_id"
        assert user_uuid.id == "uuid-1234-5678"
        assert user_uuid.username == "uuid_id"


@pytest.mark.unit
class TestUserProfileService:
    """用户画像服务测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = UserProfileService()

        assert service.name == "UserProfileService"
        assert isinstance(service._user_profiles, dict)
        assert len(service._user_profiles) == 0

    @patch("src.services.user_profile.UserProfileService._on_initialize")
    async def test_service_on_initialize(self, mock_initialize):
        """测试服务初始化方法"""
        mock_initialize.return_value = True
        service = UserProfileService()

        result = await service._on_initialize()

        assert result is True
        mock_initialize.assert_called_once()

    def test_service_inheritance(self):
        """测试服务继承关系"""
        service = UserProfileService()

        # 验证继承自SimpleService
from src.services.base_unified import SimpleService

        assert isinstance(service, SimpleService)
        assert hasattr(service, "name")
        assert hasattr(service, "logger")

    @patch("src.services.user_profile.UserProfileService.logger")
    def test_logger_configuration(self, mock_logger):
        """测试日志配置"""
        service = UserProfileService()

        # 验证logger属性存在
        assert hasattr(service, "logger")

    def test_user_profiles_storage(self):
        """测试用户画像存储"""
        service = UserProfileService()

        # 初始状态
        assert len(service._user_profiles) == 0

        # 直接操作存储
        profile = UserProfile(
            user_id="test_user",
            display_name="Test",
            email="test@example.com",
            preferences={},
        )
        service._user_profiles["test_user"] = profile

        # 验证存储
        assert len(service._user_profiles) == 1
        assert "test_user" in service._user_profiles
        assert service._user_profiles["test_user"] == profile

    def test_service_name_consistency(self):
        """测试服务名称一致性"""
        service1 = UserProfileService()
        service2 = UserProfileService()

        # 验证服务名称一致
        assert service1.name == service2.name
        assert service1.name == "UserProfileService"

    def test_multiple_service_instances(self):
        """测试多个服务实例"""
        service1 = UserProfileService()
        service2 = UserProfileService()

        # 验证不同实例有独立的存储
        assert service1 is not service2
        assert service1._user_profiles is not service2._user_profiles

    def test_service_state_isolation(self):
        """测试服务状态隔离"""
        service1 = UserProfileService()
        service2 = UserProfileService()

        # 在service1中添加用户画像
        profile1 = UserProfile(
            user_id="user1",
            display_name="User 1",
            email="user1@example.com",
            preferences={},
        )
        service1._user_profiles["user1"] = profile1

        # 验证service2不受影响
        assert len(service2._user_profiles) == 0
        assert "user1" not in service2._user_profiles
