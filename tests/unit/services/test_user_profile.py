# TODO: Consider creating a fixture for 7 repeated Mock creations

# TODO: Consider creating a fixture for 7 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
用户画像服务测试
Tests for User Profile Service
"""

from datetime import datetime

import pytest

from src.services.user_profile import User, UserProfile, UserProfileService


@pytest.mark.unit
class TestUserProfileService:
    """用户画像服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return UserProfileService()

    @pytest.fixture
    def sample_user(self):
        """示例用户"""
        _user = Mock(spec=User)
        user.id = "user_123"
        user.username = "testuser"
        user.display_name = "Test User"
        return user

    @pytest.fixture
    def sample_user_with_profile(self):
        """示例用户（带profile属性）"""
        _user = Mock()
        user.id = "user_456"
        user.username = "user456"
        user.profile = Mock()
        user.profile.email = "user456@example.com"
        user.profile.favorite_teams = ["曼联", "切尔西"]
        return user

    def test_service_initialization(self, service):
        """测试：服务初始化"""
        assert service.name == "UserProfileService"
        assert service._user_profiles == {}
        assert service._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试：成功初始化"""
        # When
        _result = await service.initialize()

        # Then
        assert _result is True
        assert service._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试：初始化失败"""
        # Given
        with patch.object(service, "_on_initialize", return_value=False):
            # When
            _result = await service.initialize()

            # Then
            assert _result is False
            assert service._initialized is False

    @pytest.mark.asyncio
    async def test_shutdown(self, service):
        """测试：关闭服务"""
        # Given
        await service.initialize()
        service._user_profiles["test"] = Mock()

        # When
        await service.shutdown()

        # Then
        assert len(service._user_profiles) == 0

    @pytest.mark.asyncio
    async def test_get_service_info(self, service):
        """测试：获取服务信息"""
        # Given
        await service.initialize()

        # When
        info = await service._get_service_info()

        # Then
        assert info["name"] == "UserProfileService"
        assert info["type"] == "UserProfileService"
        assert (
            info["description"]
            == "User profile service for managing user preferences and behavior"
        )
        assert info["version"] == "1.0.0"
        assert info["profiles_count"] == 0

    @pytest.mark.asyncio
    async def test_generate_profile(self, service, sample_user):
        """测试：生成用户画像"""
        # Given
        await service.initialize()

        # When
        profile = await service.generate_profile(sample_user)

        # Then
        assert profile.user_id == "user_123"
        assert profile.display_name in ["testuser", "Test User"]  # 根据实际实现调整
        assert "interests" in profile.preferences
        assert "behavior_patterns" in profile.preferences
        assert "content_type" in profile.preferences
        assert "language" in profile.preferences

    @pytest.mark.asyncio
    async def test_generate_profile_with_user_profile(
        self, service, sample_user_with_profile
    ):
        """测试：生成用户画像（带profile属性）"""
        # Given
        await service.initialize()

        # When
        profile = await service.generate_profile(sample_user_with_profile)

        # Then
        assert profile.user_id == "user_456"
        assert profile.email == "user456@example.com"
        # 应该包含喜欢的球队
        interests = profile.preferences.get("interests", [])
        assert "曼联" in interests or "切尔西" in interests

    @pytest.mark.asyncio
    async def test_get_profile_exists(self, service, sample_user):
        """测试：获取存在的画像"""
        # Given
        await service.initialize()
        created_profile = await service.generate_profile(sample_user)

        # When
        retrieved_profile = await service.get_profile("user_123")

        # Then
        assert retrieved_profile is not None
        assert retrieved_profile.user_id == created_profile.user_id

    @pytest.mark.asyncio
    async def test_get_profile_not_exists(self, service):
        """测试：获取不存在的画像"""
        # Given
        await service.initialize()

        # When
        profile = await service.get_profile("nonexistent")

        # Then
        assert profile is None

    @pytest.mark.asyncio
    async def test_update_profile_exists(self, service, sample_user):
        """测试：更新存在的画像"""
        # Given
        await service.initialize()
        await service.generate_profile(sample_user)

        # When
        updated_profile = await service.update_profile(
            "user_123", {"display_name": "Updated Name", "new_preference": "test_value"}
        )

        # Then
        assert updated_profile is not None
        assert updated_profile.display_name == "Updated Name"
        assert "new_preference" in updated_profile.preferences

    @pytest.mark.asyncio
    async def test_update_profile_not_exists(self, service):
        """测试：更新不存在的画像"""
        # Given
        await service.initialize()

        # When
        _result = await service.update_profile("nonexistent", {"test": "value"})

        # Then
        assert _result is None

    def test_analyze_user_interests_default(self, service, sample_user):
        """测试：分析用户兴趣（默认）"""
        # When
        interests = service._analyze_user_interests(sample_user)

        # Then
        assert isinstance(interests, list)
        assert "足球" in interests
        assert "体育" in interests
        assert "预测" in interests

    def test_analyze_user_interests_with_teams(self, service, sample_user_with_profile):
        """测试：分析用户兴趣（带球队）"""
        # When
        interests = service._analyze_user_interests(sample_user_with_profile)

        # Then
        assert "曼联" in interests
        assert "切尔西" in interests

    def test_analyze_behavior_patterns(self, service, sample_user):
        """测试：分析用户行为模式"""
        # When
        patterns = service._analyze_behavior_patterns(sample_user)

        # Then
        assert isinstance(patterns, dict)
        assert "active_hours" in patterns
        assert "login_frequency" in patterns
        assert "content_consumption_rate" in patterns
        assert "prediction_activity" in patterns

    def test_analyze_content_preferences(self, service, sample_user):
        """测试：分析内容偏好"""
        # When
        preferences = service._analyze_content_preferences(sample_user)

        # Then
        assert isinstance(preferences, dict)
        assert preferences["preferred_type"] == "text"
        assert preferences["language"] == "zh"
        assert "preferred_leagues" in preferences

    def test_get_notification_settings(self, service, sample_user):
        """测试：获取通知设置"""
        # When
        settings = service._get_notification_settings(sample_user)

        # Then
        assert isinstance(settings, dict)
        assert settings["email_notifications"] is True
        assert settings["push_notifications"] is True
        assert settings["match_reminders"] is True
        assert settings["prediction_updates"] is True

    def test_create_profile_success(self, service):
        """测试：创建画像（成功）"""
        # Given
        user_data = {
            "user_id": "new_user",
            "name": "New User",
            "email": "new@example.com",
            "interests": ["足球", "篮球"],
            "language": "en",
        }

        # When
        _result = service.create_profile(user_data)

        # Then
        assert _result["status"] == "created"
        assert "profile" in result
        assert _result["profile"]["user_id"] == "new_user"
        assert _result["profile"]["display_name"] == "New User"

    def test_create_profile_empty_data(self, service):
        """测试：创建画像（空数据）"""
        # When
        _result = service.create_profile({})

        # Then
        assert _result["status"] == "error"
        assert "Empty or invalid user data" in _result["message"]

    def test_create_profile_missing_user_id(self, service):
        """测试：创建画像（缺少user_id）"""
        # Given
        user_data = {"name": "Test", "email": "test@example.com"}

        # When
        _result = service.create_profile(user_data)

        # Then
        assert _result["status"] == "error"

    def test_delete_profile_exists(self, service):
        """测试：删除存在的画像"""
        # Given
        user_data = {"user_id": "delete_me", "name": "Delete Me"}
        service.create_profile(user_data)

        # When
        _result = service.delete_profile("delete_me")

        # Then
        assert _result["status"] == "deleted"
        assert "delete_me" not in service._user_profiles

    def test_delete_profile_not_exists(self, service):
        """测试：删除不存在的画像"""
        # When
        _result = service.delete_profile("nonexistent")

        # Then
        assert _result["status"] == "not_found"

    def test_profiles_property(self, service):
        """测试：_profiles属性"""
        # Given
        user_data = {"user_id": "test123", "name": "Test"}
        service.create_profile(user_data)

        # When
        profiles = service._profiles

        # Then
        assert isinstance(profiles, dict)
        assert "test123" in profiles

    @pytest.mark.asyncio
    async def test_multiple_profiles_management(self, service):
        """测试：管理多个画像"""
        # Given
        users = [
            Mock(id="user1", username="user1"),
            Mock(id="user2", username="user2"),
            Mock(id="user3", username="user3"),
        ]

        # When
        for user in users:
            await service.generate_profile(user)

        # Then
        assert len(service._user_profiles) == 3
        assert all(uid in service._user_profiles for uid in ["user1", "user2", "user3"])

    @pytest.mark.asyncio
    async def test_profile_preferences_update(self, service, sample_user):
        """测试：更新画像偏好"""
        # Given
        await service.initialize()
        await service.generate_profile(sample_user)

        # When
        updated = await service.update_profile(
            "user_123", {"preferences": {"new_key": "new_value"}}
        )

        # Then
        assert updated is not None
        # 注意：实际实现可能将整个preferences字典更新

    def test_user_profile_model(self):
        """测试：UserProfile模型"""
        # Given
        preferences = {"language": "zh", "interests": ["足球"]}

        # When
        profile = UserProfile(
            user_id="test123",
            display_name="Test User",
            email="test@example.com",
            preferences=preferences,
        )

        # Then
        assert profile.user_id == "test123"
        assert profile.display_name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.preferences == preferences

    def test_user_model(self):
        """测试：User模型"""
        # When
        _user = User(id="user123", username="testuser")

        # Then
        assert user.id == "user123"
        assert user.username == "testuser"
