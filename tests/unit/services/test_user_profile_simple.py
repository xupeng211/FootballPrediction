"""
Simple test file for user_profile.py service module
Provides comprehensive coverage for the actual UserProfileService implementation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# Import from src directory
from src.services.user_profile import UserProfileService
from src.models import User, UserProfile
from src.services.base import BaseService


class TestUserProfileService:
    """Test UserProfileService class methods and functionality"""

    @pytest.fixture
    def mock_user(self):
        """Create mock User object for testing"""
        user = Mock(spec=User)
        user.id = "test_user_123"
        user.username = "testuser"
        user.profile = Mock()
        user.profile.email = "test@example.com"
        return user

    @pytest.fixture
    def user_profile_service(self):
        """Create UserProfileService instance for testing"""
        with patch('src.services.base.BaseService.__init__') as mock_init:
            mock_init.return_value = None
            service = UserProfileService()
            service.name = "UserProfileService"
            service.logger = Mock()
            service._user_profiles = {}
            return service

    def test_user_profile_service_inheritance(self):
        """Test UserProfileService inherits from BaseService"""
        assert issubclass(UserProfileService, BaseService)

    def test_user_profile_service_init(self):
        """Test UserProfileService initialization"""
        with patch('src.services.base.BaseService.__init__') as mock_init:
            service = UserProfileService()

            assert service is not None
            assert isinstance(service._user_profiles, dict)
            assert len(service._user_profiles) == 0
            mock_init.assert_called_once_with("UserProfileService")

    @pytest.mark.asyncio
    async def test_initialize_success(self, user_profile_service):
        """Test successful service initialization"""
        result = await user_profile_service.initialize()

        assert result is True
        user_profile_service.logger.info.assert_called_with("正在初始化 UserProfileService")

    @pytest.mark.asyncio
    async def test_shutdown(self, user_profile_service):
        """Test service shutdown"""
        # Add some profiles to test clearing
        user_profile_service._user_profiles["test_user"] = Mock()

        await user_profile_service.shutdown()

        assert len(user_profile_service._user_profiles) == 0
        user_profile_service.logger.info.assert_called_with("正在关闭 UserProfileService")

    @pytest.mark.asyncio
    async def test_generate_profile_success(self, user_profile_service, mock_user):
        """Test successful profile generation"""
        profile = await user_profile_service.generate_profile(mock_user)

        assert profile is not None
        assert profile.user_id == mock_user.id
        assert profile.display_name == mock_user.username
        assert profile.email == mock_user.profile.email
        assert isinstance(profile.preferences, dict)
        assert "interests" in profile.preferences
        assert "content_type" in profile.preferences
        assert "language" in profile.preferences
        assert "behavior_patterns" in profile.preferences
        assert isinstance(profile.created_at, datetime)

        # Verify profile is stored
        assert mock_user.id in user_profile_service._user_profiles
        assert user_profile_service._user_profiles[mock_user.id] == profile

    @pytest.mark.asyncio
    async def test_generate_profile_logging(self, user_profile_service, mock_user):
        """Test profile generation logging"""
        await user_profile_service.generate_profile(mock_user)

        user_profile_service.logger.info.assert_called_with("正在生成用户画像: test_user_123")

    @pytest.mark.asyncio
    async def test_get_profile_exists(self, user_profile_service, mock_user):
        """Test getting existing profile"""
        # First generate a profile
        generated_profile = await user_profile_service.generate_profile(mock_user)

        # Then retrieve it
        retrieved_profile = await user_profile_service.get_profile(mock_user.id)

        assert retrieved_profile is not None
        assert retrieved_profile == generated_profile
        assert retrieved_profile.user_id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_profile_not_exists(self, user_profile_service):
        """Test getting non-existent profile"""
        profile = await user_profile_service.get_profile("nonexistent_user")

        assert profile is None

    @pytest.mark.asyncio
    async def test_update_profile_exists(self, user_profile_service, mock_user):
        """Test updating existing profile"""
        # First generate a profile
        await user_profile_service.generate_profile(mock_user)

        # Then update it
        updates = {
            "display_name": "Updated Name",
            "new_preference": "new_value"
        }
        updated_profile = await user_profile_service.update_profile(mock_user.id, updates)

        assert updated_profile is not None
        assert updated_profile.display_name == "Updated Name"
        assert updated_profile.preferences["new_preference"] == "new_value"

    @pytest.mark.asyncio
    async def test_update_profile_not_exists(self, user_profile_service):
        """Test updating non-existent profile"""
        updates = {"display_name": "Updated Name"}

        profile = await user_profile_service.update_profile("nonexistent_user", updates)

        assert profile is None

    @pytest.mark.asyncio
    async def test_update_profile_attribute_vs_preferences(self, user_profile_service, mock_user):
        """Test updating profile attributes vs preferences"""
        # First generate a profile
        await user_profile_service.generate_profile(mock_user)

        # Update both attributes and preferences
        updates = {
            "display_name": "Updated Name",  # This is an attribute
            "custom_setting": "custom_value"  # This should go to preferences
        }
        updated_profile = await user_profile_service.update_profile(mock_user.id, updates)

        assert updated_profile is not None
        assert updated_profile.display_name == "Updated Name"
        assert updated_profile.preferences["custom_setting"] == "custom_value"

    def test_create_profile_success(self, user_profile_service):
        """Test successful profile creation (sync version)"""
        user_data = {
            "user_id": "new_user_456",
            "name": "New User",
            "email": "newuser@example.com"
        }

        result = user_profile_service.create_profile(user_data)

        assert result is not None
        assert result["status"] == "created"
        assert "profile" in result
        assert result["profile"]["user_id"] == "new_user_456"
        assert result["profile"]["display_name"] == "New User"
        assert result["profile"]["email"] == "newuser@example.com"

        # Verify profile is stored
        assert "new_user_456" in user_profile_service._user_profiles

    def test_create_profile_empty_data(self, user_profile_service):
        """Test profile creation with empty data"""
        result = user_profile_service.create_profile({})

        assert result is not None
        assert result["status"] == "error"
        assert "message" in result
        assert "Empty or invalid user data" in result["message"]

    def test_create_profile_no_user_id(self, user_profile_service):
        """Test profile creation without user_id"""
        user_data = {"name": "Test User", "email": "test@example.com"}

        result = user_profile_service.create_profile(user_data)

        assert result["status"] == "error"
        assert "Empty or invalid user data" in result["message"]

    def test_create_profile_minimal_data(self, user_profile_service):
        """Test profile creation with minimal data"""
        user_data = {"user_id": "minimal_user"}

        result = user_profile_service.create_profile(user_data)

        assert result["status"] == "created"
        assert result["profile"]["user_id"] == "minimal_user"
        assert result["profile"]["display_name"] == "Anonymous"
        assert result["profile"]["email"] == ""

    def test_delete_profile_exists(self, user_profile_service):
        """Test deleting existing profile"""
        # First create a profile
        user_data = {"user_id": "delete_user", "name": "Delete Me"}
        user_profile_service.create_profile(user_data)

        # Then delete it
        result = user_profile_service.delete_profile("delete_user")

        assert result is not None
        assert result["status"] == "deleted"
        assert "delete_user" not in user_profile_service._user_profiles

    def test_delete_profile_not_exists(self, user_profile_service):
        """Test deleting non-existent profile"""
        result = user_profile_service.delete_profile("nonexistent_user")

        assert result is not None
        assert result["status"] == "not_found"

    def test_profiles_property(self, user_profile_service):
        """Test _profiles property for test compatibility"""
        # Create a mock profile that doesn't have to_dict method
        class MockProfile:
            def __init__(self, user_id):
                self.user_id = user_id
                self.data = {"test": "data"}

        # Add profiles with and without to_dict method
        profile1 = MockProfile("user1")
        profile2 = Mock()
        profile2.to_dict = Mock(return_value={"user_id": "user2", "converted": True})

        user_profile_service._user_profiles["user1"] = profile1
        user_profile_service._user_profiles["user2"] = profile2

        profiles_dict = user_profile_service._profiles

        assert isinstance(profiles_dict, dict)
        assert len(profiles_dict) == 2
        assert "user1" in profiles_dict
        assert "user2" in profiles_dict
        # user1 should return the profile object (no to_dict method)
        assert profiles_dict["user1"] == profile1
        # user2 should return the dict result
        assert profiles_dict["user2"]["converted"] is True


class TestUserProfileServiceEdgeCases:
    """Edge case tests for UserProfileService"""

    @pytest.mark.asyncio
    async def test_generate_profile_with_none_user(self, user_profile_service):
        """Test profile generation with None user"""
        with pytest.raises(AttributeError):
            await user_profile_service.generate_profile(None)

    @pytest.mark.asyncio
    async def test_generate_profile_with_invalid_user(self, user_profile_service):
        """Test profile generation with invalid user object"""
        invalid_user = "not a user object"

        with pytest.raises(AttributeError):
            await user_profile_service.generate_profile(invalid_user)

    @pytest.mark.asyncio
    async def test_update_profile_with_none_updates(self, user_profile_service, mock_user):
        """Test profile update with None updates"""
        # First generate a profile
        await user_profile_service.generate_profile(mock_user)

        # Try to update with None
        with pytest.raises(TypeError):
            await user_profile_service.update_profile(mock_user.id, None)

    @pytest.mark.asyncio
    async def test_update_profile_with_empty_updates(self, user_profile_service, mock_user):
        """Test profile update with empty updates dict"""
        # First generate a profile
        original_profile = await user_profile_service.generate_profile(mock_user)

        # Update with empty dict
        updated_profile = await user_profile_service.update_profile(mock_user.id, {})

        # Should return the same profile
        assert updated_profile == original_profile

    def test_create_profile_with_none_data(self, user_profile_service):
        """Test profile creation with None data"""
        with pytest.raises(TypeError):
            user_profile_service.create_profile(None)

    def test_create_profile_with_non_dict_data(self, user_profile_service):
        """Test profile creation with non-dict data"""
        with pytest.raises(TypeError):
            user_profile_service.create_profile("not a dict")

    def test_delete_profile_with_none_user_id(self, user_profile_service):
        """Test profile deletion with None user_id"""
        with pytest.raises(TypeError):
            user_profile_service.delete_profile(None)

    def test_delete_profile_with_empty_user_id(self, user_profile_service):
        """Test profile deletion with empty user_id"""
        result = user_profile_service.delete_profile("")

        assert result["status"] == "not_found"

    def test_profiles_property_empty(self, user_profile_service):
        """Test _profiles property with no profiles"""
        profiles_dict = user_profile_service._profiles

        assert isinstance(profiles_dict, dict)
        assert len(profiles_dict) == 0

    def test_profiles_property_with_complex_profiles(self, user_profile_service):
        """Test _profiles property with complex profile objects"""
        # Create a mock profile with nested data
        class ComplexProfile:
            def __init__(self):
                self.user_id = "complex_user"
                self.nested_data = {"level1": {"level2": "deep value"}}
                self.list_data = [1, 2, 3]

        complex_profile = ComplexProfile()
        user_profile_service._user_profiles["complex_user"] = complex_profile

        profiles_dict = user_profile_service._profiles

        assert isinstance(profiles_dict, dict)
        assert "complex_user" in profiles_dict
        # Should return the original object since it doesn't have to_dict
        assert profiles_dict["complex_user"] == complex_profile


class TestUserProfileServiceIntegration:
    """Integration tests for UserProfileService"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete profile lifecycle"""
        with patch('src.services.base.BaseService.__init__'):
            service = UserProfileService()
            service.logger = Mock()
            service._user_profiles = {}

            # Test initialization
            await service.initialize()

            # Create a mock user
            user = Mock(spec=User)
            user.id = "lifecycle_user"
            user.username = "lifecycleuser"
            user.profile = Mock()
            user.profile.email = "lifecycle@example.com"

            # Generate profile
            profile = await service.generate_profile(user)
            assert profile.user_id == "lifecycle_user"

            # Get profile
            retrieved_profile = await service.get_profile("lifecycle_user")
            assert retrieved_profile == profile

            # Update profile
            updated_profile = await service.update_profile("lifecycle_user", {"display_name": "Updated"})
            assert updated_profile.display_name == "Updated"

            # Test sync operations
            sync_result = service.create_profile({"user_id": "sync_user", "name": "Sync User"})
            assert sync_result["status"] == "created"

            delete_result = service.delete_profile("sync_user")
            assert delete_result["status"] == "deleted"

            # Test profiles property
            profiles_dict = service._profiles
            assert "lifecycle_user" in profiles_dict

            # Shutdown
            await service.shutdown()
            assert len(service._user_profiles) == 0

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent profile operations"""
        with patch('src.services.base.BaseService.__init__'):
            service = UserProfileService()
            service.logger = Mock()
            service._user_profiles = {}

            # Create multiple mock users
            users = []
            for i in range(5):
                user = Mock(spec=User)
                user.id = f"concurrent_user_{i}"
                user.username = f"concurrentuser{i}"
                user.profile = Mock()
                user.profile.email = f"user{i}@example.com"
                users.append(user)

            # Create concurrent profile generation tasks
            tasks = []
            for user in users:
                task = service.generate_profile(user)
                tasks.append(task)

            # Run all tasks concurrently
            profiles = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all profiles were created
            assert len(profiles) == 5
            for i, profile in enumerate(profiles):
                assert isinstance(profile, UserProfile)
                assert profile.user_id == f"concurrent_user_{i}"

            # Verify all profiles are stored
            assert len(service._user_profiles) == 5

    @pytest.mark.asyncio
    async def test_profile_preferences_structure(self):
        """Test that profile preferences have expected structure"""
        with patch('src.services.base.BaseService.__init__'):
            service = UserProfileService()
            service.logger = Mock()
            service._user_profiles = {}

            user = Mock(spec=User)
            user.id = "preferences_test"
            user.username = "prefuser"
            user.profile = Mock()
            user.profile.email = "pref@example.com"

            profile = await service.generate_profile(user)

            # Check preferences structure
            preferences = profile.preferences
            assert isinstance(preferences, dict)
            assert "interests" in preferences
            assert "content_type" in preferences
            assert "language" in preferences
            assert "behavior_patterns" in preferences

            # Check specific values
            assert isinstance(preferences["interests"], list)
            assert "足球" in preferences["interests"]
            assert isinstance(preferences["content_type"], str)
            assert preferences["language"] == "zh"
            assert isinstance(preferences["behavior_patterns"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])