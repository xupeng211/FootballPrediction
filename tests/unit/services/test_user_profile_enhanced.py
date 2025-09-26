"""
Enhanced test file for user_profile.py service module
Provides comprehensive coverage for user profile management and functionality
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Import from src directory
from src.services.user_profile import (
    UserProfileService,
    UserProfile,
    UserProfileError,
    ProfilePreference,
    ProfileActivity,
    ProfileStats,
    ProfileConfig
)
from src.services.base import BaseService


class TestProfilePreference:
    """Test ProfilePreference dataclass and methods"""

    def test_profile_preference_creation(self):
        """Test ProfilePreference creation with default values"""
        preference = ProfilePreference()

        assert preference.favorite_teams == []
        assert preference.favorite_leagues == []
        assert preference.notification_enabled is True
        assert preference.language == "en"
        assert preference.timezone == "UTC"
        assert preference.theme == "light"

    def test_profile_preference_custom_values(self):
        """Test ProfilePreference creation with custom values"""
        preference = ProfilePreference(
            favorite_teams=["Manchester United", "Liverpool"],
            favorite_leagues=["Premier League", "Champions League"],
            notification_enabled=False,
            language="es",
            timezone="Europe/Madrid",
            theme="dark"
        )

        assert preference.favorite_teams == ["Manchester United", "Liverpool"]
        assert preference.favorite_leagues == ["Premier League", "Champions League"]
        assert preference.notification_enabled is False
        assert preference.language == "es"
        assert preference.timezone == "Europe/Madrid"
        assert preference.theme == "dark"

    def test_profile_preference_to_dict(self):
        """Test ProfilePreference to_dict method"""
        preference = ProfilePreference(
            favorite_teams=["Man Utd"],
            favorite_leagues=["Premier League"],
            notification_enabled=True,
            language="fr"
        )

        pref_dict = preference.to_dict()

        assert pref_dict["favorite_teams"] == ["Man Utd"]
        assert pref_dict["favorite_leagues"] == ["Premier League"]
        assert pref_dict["notification_enabled"] is True
        assert pref_dict["language"] == "fr"
        assert pref_dict["timezone"] == "UTC"  # Default value
        assert pref_dict["theme"] == "light"  # Default value

    def test_profile_preference_from_dict(self):
        """Test ProfilePreference from_dict class method"""
        pref_dict = {
            "favorite_teams": ["Barcelona", "Real Madrid"],
            "favorite_leagues": ["La Liga"],
            "notification_enabled": False,
            "language": "es",
            "timezone": "Europe/Madrid",
            "theme": "dark"
        }

        preference = ProfilePreference.from_dict(pref_dict)

        assert preference.favorite_teams == ["Barcelona", "Real Madrid"]
        assert preference.favorite_leagues == ["La Liga"]
        assert preference.notification_enabled is False
        assert preference.language == "es"
        assert preference.timezone == "Europe/Madrid"
        assert preference.theme == "dark"

    def test_profile_preference_validation(self):
        """Test ProfilePreference parameter validation"""
        # Test valid values
        preference = ProfilePreference(
            favorite_teams=["Team 1", "Team 2"],
            favorite_leagues=["League 1"],
            language="en",
            timezone="UTC"
        )
        assert preference is not None

        # Test invalid language
        with pytest.raises(ValueError):
            ProfilePreference(language="invalid_lang")

        # Test invalid timezone
        with pytest.raises(ValueError):
            ProfilePreference(timezone="Invalid/Timezone")

        # Test invalid theme
        with pytest.raises(ValueError):
            ProfilePreference(theme="invalid_theme")


class TestProfileActivity:
    """Test ProfileActivity dataclass and methods"""

    def test_profile_activity_creation(self):
        """Test ProfileActivity creation with required fields"""
        activity = ProfileActivity(
            activity_type="login",
            description="User logged in",
            timestamp=datetime.now()
        )

        assert activity.activity_type == "login"
        assert activity.description == "User logged in"
        assert isinstance(activity.timestamp, datetime)
        assert activity.metadata is None

    def test_profile_activity_full_creation(self):
        """Test ProfileActivity creation with all fields"""
        metadata = {"ip": "192.168.1.1", "device": "mobile"}
        activity = ProfileActivity(
            activity_type="prediction",
            description="User made prediction",
            timestamp=datetime.now(),
            metadata=metadata
        )

        assert activity.activity_type == "prediction"
        assert activity.description == "User made prediction"
        assert isinstance(activity.timestamp, datetime)
        assert activity.metadata == metadata

    def test_profile_activity_to_dict(self):
        """Test ProfileActivity to_dict method"""
        timestamp = datetime.now()
        activity = ProfileActivity(
            activity_type="login",
            description="User login",
            timestamp=timestamp,
            metadata={"device": "web"}
        )

        activity_dict = activity.to_dict()

        assert activity_dict["activity_type"] == "login"
        assert activity_dict["description"] == "User login"
        assert activity_dict["timestamp"] == timestamp.isoformat()
        assert activity_dict["metadata"] == {"device": "web"}

    def test_profile_activity_from_dict(self):
        """Test ProfileActivity from_dict class method"""
        timestamp_str = datetime.now().isoformat()
        activity_dict = {
            "activity_type": "logout",
            "description": "User logged out",
            "timestamp": timestamp_str,
            "metadata": {"duration": 3600}
        }

        activity = ProfileActivity.from_dict(activity_dict)

        assert activity.activity_type == "logout"
        assert activity.description == "User logged out"
        assert isinstance(activity.timestamp, datetime)
        assert activity.metadata == {"duration": 3600}

    def test_profile_activity_validation(self):
        """Test ProfileActivity parameter validation"""
        # Test invalid activity type
        with pytest.raises(ValueError):
            ProfileActivity(
                activity_type="invalid_activity",
                description="Test",
                timestamp=datetime.now()
            )

        # Test empty description
        with pytest.raises(ValueError):
            ProfileActivity(
                activity_type="login",
                description="",
                timestamp=datetime.now()
            )

        # Test future timestamp
        with pytest.raises(ValueError):
            ProfileActivity(
                activity_type="login",
                description="Test",
                timestamp=datetime.now() + timedelta(days=1)
            )


class TestProfileStats:
    """Test ProfileStats dataclass and methods"""

    def test_profile_stats_creation(self):
        """Test ProfileStats creation with default values"""
        stats = ProfileStats()

        assert stats.total_predictions == 0
        assert stats.successful_predictions == 0
        assert stats.total_logins == 0
        assert stats.last_login is None
        assert stats.account_created is not None
        assert stats.preferences_updated == 0

    def test_profile_stats_custom_values(self):
        """Test ProfileStats creation with custom values"""
        last_login = datetime.now() - timedelta(days=1)
        account_created = datetime.now() - timedelta(days=30)

        stats = ProfileStats(
            total_predictions=150,
            successful_predictions=95,
            total_logins=45,
            last_login=last_login,
            account_created=account_created,
            preferences_updated=5
        )

        assert stats.total_predictions == 150
        assert stats.successful_predictions == 95
        assert stats.total_logins == 45
        assert stats.last_login == last_login
        assert stats.account_created == account_created
        assert stats.preferences_updated == 5

    def test_profile_stats_success_rate(self):
        """Test ProfileStats success_rate property"""
        stats = ProfileStats(
            total_predictions=100,
            successful_predictions=75
        )

        assert stats.success_rate == 0.75

    def test_profile_stats_success_rate_no_predictions(self):
        """Test ProfileStats success_rate with no predictions"""
        stats = ProfileStats(
            total_predictions=0,
            successful_predictions=0
        )

        assert stats.success_rate == 0.0

    def test_profile_stats_days_active(self):
        """Test ProfileStats days_active property"""
        account_created = datetime.now() - timedelta(days=30)
        last_login = datetime.now() - timedelta(days=1)

        stats = ProfileStats(
            account_created=account_created,
            last_login=last_login
        )

        assert stats.days_active >= 29  # Should be approximately 30 days

    def test_profile_stats_to_dict(self):
        """Test ProfileStats to_dict method"""
        last_login = datetime.now() - timedelta(days=1)
        account_created = datetime.now() - timedelta(days=30)

        stats = ProfileStats(
            total_predictions=50,
            successful_predictions=30,
            total_logins=20,
            last_login=last_login,
            account_created=account_created,
            preferences_updated=3
        )

        stats_dict = stats.to_dict()

        assert stats_dict["total_predictions"] == 50
        assert stats_dict["successful_predictions"] == 30
        assert stats_dict["success_rate"] == 0.6
        assert stats_dict["last_login"] == last_login.isoformat()
        assert stats_dict["account_created"] == account_created.isoformat()
        assert stats_dict["days_active"] >= 29
        assert stats_dict["preferences_updated"] == 3

    def test_profile_stats_from_dict(self):
        """Test ProfileStats from_dict class method"""
        last_login_str = (datetime.now() - timedelta(days=1)).isoformat()
        account_created_str = (datetime.now() - timedelta(days=30)).isoformat()

        stats_dict = {
            "total_predictions": 200,
            "successful_predictions": 140,
            "total_logins": 75,
            "last_login": last_login_str,
            "account_created": account_created_str,
            "preferences_updated": 8
        }

        stats = ProfileStats.from_dict(stats_dict)

        assert stats.total_predictions == 200
        assert stats.successful_predictions == 140
        assert stats.success_rate == 0.7
        assert isinstance(stats.last_login, datetime)
        assert isinstance(stats.account_created, datetime)
        assert stats.total_logins == 75
        assert stats.preferences_updated == 8


class TestProfileConfig:
    """Test ProfileConfig dataclass and methods"""

    def test_profile_config_creation(self):
        """Test ProfileConfig creation with default values"""
        config = ProfileConfig()

        assert config.max_favorite_teams == 10
        assert config.max_favorite_leagues == 5
        assert config.activity_retention_days == 90
        assert config.enable_activity_tracking is True
        assert config.enable_profile_analytics is True

    def test_profile_config_custom_values(self):
        """Test ProfileConfig creation with custom values"""
        config = ProfileConfig(
            max_favorite_teams=20,
            max_favorite_leagues=10,
            activity_retention_days=180,
            enable_activity_tracking=False,
            enable_profile_analytics=True
        )

        assert config.max_favorite_teams == 20
        assert config.max_favorite_leagues == 10
        assert config.activity_retention_days == 180
        assert config.enable_activity_tracking is False
        assert config.enable_profile_analytics is True

    def test_profile_config_validation(self):
        """Test ProfileConfig parameter validation"""
        # Test invalid max_favorite_teams
        with pytest.raises(ValueError):
            ProfileConfig(max_favorite_teams=0)

        with pytest.raises(ValueError):
            ProfileConfig(max_favorite_teams=-5)

        # Test invalid max_favorite_leagues
        with pytest.raises(ValueError):
            ProfileConfig(max_favorite_leagues=0)

        # Test invalid activity_retention_days
        with pytest.raises(ValueError):
            ProfileConfig(activity_retention_days=0)

        with pytest.raises(ValueError):
            ProfileConfig(activity_retention_days=-30)


class TestUserProfile:
    """Test UserProfile dataclass and methods"""

    def test_user_profile_creation(self):
        """Test UserProfile creation with required fields"""
        preferences = ProfilePreference()
        stats = ProfileStats()

        profile = UserProfile(
            user_id="test_user_123",
            email="user@example.com",
            username="testuser",
            preferences=preferences,
            stats=stats
        )

        assert profile.user_id == "test_user_123"
        assert profile.email == "user@example.com"
        assert profile.username == "testuser"
        assert profile.preferences == preferences
        assert profile.stats == stats
        assert profile.is_active is True
        assert profile.activities == []
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_user_profile_full_creation(self):
        """Test UserProfile creation with all fields"""
        preferences = ProfilePreference(
            favorite_teams=["Man Utd"],
            notification_enabled=False
        )
        stats = ProfileStats(
            total_predictions=100,
            successful_predictions=60
        )
        activity = ProfileActivity(
            activity_type="login",
            description="User logged in",
            timestamp=datetime.now()
        )

        profile = UserProfile(
            user_id="test_user_456",
            email="test@example.com",
            username="testuser456",
            preferences=preferences,
            stats=stats,
            is_active=False,
            activities=[activity],
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now()
        )

        assert profile.user_id == "test_user_456"
        assert profile.email == "test@example.com"
        assert profile.username == "testuser456"
        assert profile.preferences.favorite_teams == ["Man Utd"]
        assert profile.preferences.notification_enabled is False
        assert profile.stats.success_rate == 0.6
        assert profile.is_active is False
        assert len(profile.activities) == 1
        assert profile.activities[0].activity_type == "login"

    def test_user_profile_add_activity(self):
        """Test UserProfile add_activity method"""
        profile = UserProfile(
            user_id="test_user",
            email="test@example.com",
            username="testuser",
            preferences=ProfilePreference(),
            stats=ProfileStats()
        )

        activity = ProfileActivity(
            activity_type="prediction",
            description="Made prediction",
            timestamp=datetime.now()
        )

        profile.add_activity(activity)

        assert len(profile.activities) == 1
        assert profile.activities[0] == activity
        assert profile.updated_at > profile.created_at

    def test_user_profile_remove_activity(self):
        """Test UserProfile remove_activity method"""
        activity = ProfileActivity(
            activity_type="login",
            description="User login",
            timestamp=datetime.now()
        )

        profile = UserProfile(
            user_id="test_user",
            email="test@example.com",
            username="testuser",
            preferences=ProfilePreference(),
            stats=ProfileStats(),
            activities=[activity]
        )

        profile.remove_activity(activity)

        assert len(profile.activities) == 0
        assert profile.updated_at > profile.created_at

    def test_user_profile_update_preferences(self):
        """Test UserProfile update_preferences method"""
        profile = UserProfile(
            user_id="test_user",
            email="test@example.com",
            username="testuser",
            preferences=ProfilePreference(),
            stats=ProfileStats()
        )

        new_preferences = ProfilePreference(
            favorite_teams=["Barcelona"],
            language="es"
        )

        profile.update_preferences(new_preferences)

        assert profile.preferences.favorite_teams == ["Barcelona"]
        assert profile.preferences.language == "es"
        assert profile.updated_at > profile.created_at

    def test_user_profile_to_dict(self):
        """Test UserProfile to_dict method"""
        profile = UserProfile(
            user_id="test_user_789",
            email="user@test.com",
            username="testuser789",
            preferences=ProfilePreference(
                favorite_teams=["Liverpool"]
            ),
            stats=ProfileStats(
                total_predictions=50,
                successful_predictions=30
            )
        )

        profile_dict = profile.to_dict()

        assert profile_dict["user_id"] == "test_user_789"
        assert profile_dict["email"] == "user@test.com"
        assert profile_dict["username"] == "testuser789"
        assert profile_dict["preferences"]["favorite_teams"] == ["Liverpool"]
        assert profile_dict["stats"]["total_predictions"] == 50
        assert profile_dict["stats"]["success_rate"] == 0.6
        assert profile_dict["is_active"] is True
        assert profile_dict["activities"] == []

    def test_user_profile_from_dict(self):
        """Test UserProfile from_dict class method"""
        profile_dict = {
            "user_id": "user_from_dict",
            "email": "from@dict.com",
            "username": "fromdict",
            "preferences": {
                "favorite_teams": ["Real Madrid"],
                "language": "es"
            },
            "stats": {
                "total_predictions": 200,
                "successful_predictions": 120,
                "total_logins": 50
            },
            "is_active": True,
            "activities": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        profile = UserProfile.from_dict(profile_dict)

        assert profile.user_id == "user_from_dict"
        assert profile.email == "from@dict.com"
        assert profile.username == "fromdict"
        assert profile.preferences.favorite_teams == ["Real Madrid"]
        assert profile.preferences.language == "es"
        assert profile.stats.success_rate == 0.6
        assert profile.is_active is True
        assert len(profile.activities) == 0

    def test_user_profile_validation(self):
        """Test UserProfile parameter validation"""
        preferences = ProfilePreference()
        stats = ProfileStats()

        # Test invalid user_id
        with pytest.raises(ValueError):
            UserProfile(
                user_id="",
                email="test@example.com",
                username="testuser",
                preferences=preferences,
                stats=stats
            )

        # Test invalid email
        with pytest.raises(ValueError):
            UserProfile(
                user_id="test_user",
                email="invalid_email",
                username="testuser",
                preferences=preferences,
                stats=stats
            )

        # Test invalid username
        with pytest.raises(ValueError):
            UserProfile(
                user_id="test_user",
                email="test@example.com",
                username="",
                preferences=preferences,
                stats=stats
            )


class TestUserProfileError:
    """Test UserProfileError exception class"""

    def test_user_profile_error_creation(self):
        """Test UserProfileError creation"""
        error = UserProfileError("Test profile error")

        assert str(error) == "Test profile error"
        assert isinstance(error, Exception)

    def test_user_profile_error_with_code(self):
        """Test UserProfileError with error code"""
        error = UserProfileError("Profile not found", code="PROFILE_NOT_FOUND")

        assert str(error) == "Profile not found"
        assert error.code == "PROFILE_NOT_FOUND"

    def test_user_profile_error_inheritance(self):
        """Test UserProfileError inherits from Exception"""
        error = UserProfileError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, UserProfileError)


class TestUserProfileService:
    """Test UserProfileService class methods and functionality"""

    @pytest.fixture
    def mock_database_manager(self):
        """Mock database manager for testing"""
        manager = Mock()
        manager.get_connection = AsyncMock()
        manager.close_connection = AsyncMock()
        return manager

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.user_profile = Mock()
        config.user_profile.max_favorite_teams = 10
        config.user_profile.max_favorite_leagues = 5
        config.user_profile.activity_retention_days = 90
        return config

    @pytest.fixture
    def user_profile_service(self, mock_database_manager, mock_config):
        """Create UserProfileService instance for testing"""
        with patch('src.services.base.DatabaseManager', return_value=mock_database_manager), \
             patch('src.services.base.load_config', return_value=mock_config):
            service = UserProfileService()
            return service

    def test_user_profile_service_inheritance(self):
        """Test UserProfileService inherits from BaseService"""
        assert issubclass(UserProfileService, BaseService)

    def test_user_profile_service_init(self, user_profile_service):
        """Test UserProfileService initialization"""
        assert user_profile_service is not None
        assert hasattr(user_profile_service, 'database_manager')
        assert hasattr(user_profile_service, 'config')
        assert hasattr(user_profile_service, 'logger')

    @pytest.mark.asyncio
    async def test_create_profile(self, user_profile_service):
        """Test create_profile method"""
        user_id = "new_user_123"
        email = "newuser@example.com"
        username = "newuser"

        # Mock database insertion
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "preferences": "{}",
            "stats": "{}",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.create_profile(user_id, email, username)

        assert profile.user_id == user_id
        assert profile.email == email
        assert profile.username == username
        assert profile.is_active is True
        assert isinstance(profile.preferences, ProfilePreference)
        assert isinstance(profile.stats, ProfileStats)

    @pytest.mark.asyncio
    async def test_create_profile_duplicate(self, user_profile_service):
        """Test create_profile method with duplicate user"""
        user_id = "existing_user"
        email = "existing@example.com"
        username = "existinguser"

        # Mock database to indicate duplicate
        mock_connection = AsyncMock()
        mock_connection.fetchrow.side_effect = Exception("Duplicate key violation")
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        with pytest.raises(UserProfileError) as exc_info:
            await user_profile_service.create_profile(user_id, email, username)

        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_profile(self, user_profile_service):
        """Test get_profile method"""
        user_id = "test_user_123"

        # Mock database query
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "username": "testuser",
            "preferences": '{"favorite_teams": ["Man Utd"], "language": "en"}',
            "stats": '{"total_predictions": 100, "successful_predictions": 60}',
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.get_profile(user_id)

        assert profile.user_id == user_id
        assert profile.email == "test@example.com"
        assert profile.username == "testuser"
        assert profile.preferences.favorite_teams == ["Man Utd"]
        assert profile.stats.success_rate == 0.6

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, user_profile_service):
        """Test get_profile method when profile not found"""
        user_id = "nonexistent_user"

        # Mock database query to return None
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        with pytest.raises(UserProfileError) as exc_info:
            await user_profile_service.get_profile(user_id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_profile(self, user_profile_service):
        """Test update_profile method"""
        user_id = "test_user_123"
        updated_data = {
            "email": "newemail@example.com",
            "username": "newusername"
        }

        # Mock database query and update
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": "newemail@example.com",
            "username": "newusername",
            "preferences": "{}",
            "stats": "{}",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.update_profile(user_id, updated_data)

        assert profile.email == "newemail@example.com"
        assert profile.username == "newusername"

    @pytest.mark.asyncio
    async def test_update_profile_preferences(self, user_profile_service):
        """Test update_profile_preferences method"""
        user_id = "test_user_123"
        new_preferences = ProfilePreference(
            favorite_teams=["Barcelona", "Real Madrid"],
            favorite_leagues=["La Liga"],
            language="es",
            theme="dark"
        )

        # Mock database update
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "username": "testuser",
            "preferences": json.dumps(new_preferences.to_dict()),
            "stats": "{}",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.update_profile_preferences(user_id, new_preferences)

        assert profile.preferences.favorite_teams == ["Barcelona", "Real Madrid"]
        assert profile.preferences.favorite_leagues == ["La Liga"]
        assert profile.preferences.language == "es"
        assert profile.preferences.theme == "dark"

    @pytest.mark.asyncio
    async def test_update_profile_preferences_validation(self, user_profile_service):
        """Test update_profile_preferences method with validation errors"""
        user_id = "test_user_123"
        invalid_preferences = ProfilePreference(
            favorite_teams=["Team 1", "Team 2", "Team 3", "Team 4", "Team 5", "Team 6", "Team 7", "Team 8", "Team 9", "Team 10", "Team 11"],  # Too many
            language="invalid_lang"
        )

        with pytest.raises(UserProfileError) as exc_info:
            await user_profile_service.update_profile_preferences(user_id, invalid_preferences)

        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_activity(self, user_profile_service):
        """Test add_activity method"""
        user_id = "test_user_123"
        activity = ProfileActivity(
            activity_type="prediction",
            description="Made match prediction",
            timestamp=datetime.now()
        )

        # Mock database update
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "username": "testuser",
            "preferences": "{}",
            "stats": "{}",
            "is_active": True,
            "activities": json.dumps([activity.to_dict()]),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.add_activity(user_id, activity)

        assert len(profile.activities) == 1
        assert profile.activities[0].activity_type == "prediction"

    @pytest.mark.asyncio
    async def test_get_profile_activities(self, user_profile_service):
        """Test get_profile_activities method"""
        user_id = "test_user_123"
        limit = 10

        # Mock database query
        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = [
            {
                "activity_type": "login",
                "description": "User logged in",
                "timestamp": datetime.now().isoformat(),
                "metadata": '{"ip": "192.168.1.1"}'
            },
            {
                "activity_type": "prediction",
                "description": "Made prediction",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "metadata": '{"match_id": "123"}'
            }
        ]
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        activities = await user_profile_service.get_profile_activities(user_id, limit)

        assert len(activities) == 2
        assert activities[0].activity_type == "login"
        assert activities[1].activity_type == "prediction"

    @pytest.mark.asyncio
    async def test_get_profile_stats(self, user_profile_service):
        """Test get_profile_stats method"""
        user_id = "test_user_123"

        # Mock database query
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "total_predictions": 150,
            "successful_predictions": 90,
            "total_logins": 25,
            "last_login": (datetime.now() - timedelta(days=1)).isoformat(),
            "account_created": (datetime.now() - timedelta(days=30)).isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        stats = await user_profile_service.get_profile_stats(user_id)

        assert stats.total_predictions == 150
        assert stats.successful_predictions == 90
        assert stats.success_rate == 0.6
        assert stats.total_logins == 25

    @pytest.mark.asyncio
    async def test_deactivate_profile(self, user_profile_service):
        """Test deactivate_profile method"""
        user_id = "test_user_123"

        # Mock database update
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "username": "testuser",
            "preferences": "{}",
            "stats": "{}",
            "is_active": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.deactivate_profile(user_id)

        assert profile.is_active is False

    @pytest.mark.asyncio
    async def test_activate_profile(self, user_profile_service):
        """Test activate_profile method"""
        user_id = "test_user_123"

        # Mock database update
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "username": "testuser",
            "preferences": "{}",
            "stats": "{}",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profile = await user_profile_service.activate_profile(user_id)

        assert profile.is_active is True

    @pytest.mark.asyncio
    async def test_delete_profile(self, user_profile_service):
        """Test delete_profile method"""
        user_id = "test_user_123"

        # Mock database deletion
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "DELETE 1"
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        result = await user_profile_service.delete_profile(user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(self, user_profile_service):
        """Test delete_profile method when profile not found"""
        user_id = "nonexistent_user"

        # Mock database deletion to indicate no rows affected
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "DELETE 0"
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        with pytest.raises(UserProfileError) as exc_info:
            await user_profile_service.delete_profile(user_id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_profiles(self, user_profile_service):
        """Test search_profiles method"""
        search_query = "test"
        limit = 5

        # Mock database search
        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = [
            {
                "user_id": "user1",
                "email": "test1@example.com",
                "username": "testuser1",
                "preferences": "{}",
                "stats": "{}",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "user_id": "user2",
                "email": "test2@example.com",
                "username": "testuser2",
                "preferences": "{}",
                "stats": "{}",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profiles = await user_profile_service.search_profiles(search_query, limit)

        assert len(profiles) == 2
        assert "test" in profiles[0].username.lower()

    @pytest.mark.asyncio
    async def test_get_profiles_by_team(self, user_profile_service):
        """Test get_profiles_by_team method"""
        team_name = "Manchester United"
        limit = 10

        # Mock database query
        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = [
            {
                "user_id": "fan1",
                "email": "fan1@example.com",
                "username": "mufan1",
                "preferences": '{"favorite_teams": ["Manchester United"]}',
                "stats": "{}",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        profiles = await user_profile_service.get_profiles_by_team(team_name, limit)

        assert len(profiles) == 1
        assert "Manchester United" in profiles[0].preferences.favorite_teams

    @pytest.mark.asyncio
    async def test_clean_old_activities(self, user_profile_service):
        """Test clean_old_activities method"""
        days_to_keep = 30

        # Mock database cleanup
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "DELETE 50"
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        result = await user_profile_service.clean_old_activities(days_to_keep)

        assert result == 50  # Number of deleted activities

    @pytest.mark.asyncio
    async def test_get_profile_analytics(self, user_profile_service):
        """Test get_profile_analytics method"""
        # Mock database analytics query
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {
            "total_profiles": 1000,
            "active_profiles": 850,
            "inactive_profiles": 150,
            "avg_predictions_per_user": 75.5,
            "most_popular_team": "Manchester United",
            "most_popular_league": "Premier League"
        }
        user_profile_service.database_manager.get_connection.return_value = mock_connection

        analytics = await user_profile_service.get_profile_analytics()

        assert analytics["total_profiles"] == 1000
        assert analytics["active_profiles"] == 850
        assert analytics["inactive_profiles"] == 150
        assert analytics["avg_predictions_per_user"] == 75.5
        assert analytics["most_popular_team"] == "Manchester United"

    @pytest.mark.asyncio
    async def test_health_check(self, user_profile_service):
        """Test health_check method"""
        # Mock database health check
        user_profile_service.database_manager.health_check = AsyncMock(return_value=True)

        health = await user_profile_service.health_check()

        assert health["status"] == "healthy"
        assert health["database"] is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, user_profile_service):
        """Test health_check method when unhealthy"""
        # Mock database health check to fail
        user_profile_service.database_manager.health_check = AsyncMock(return_value=False)

        health = await user_profile_service.health_check()

        assert health["status"] == "unhealthy"
        assert health["database"] is False


class TestUserProfileIntegration:
    """Integration tests for user profile service"""

    @pytest.mark.asyncio
    async def test_full_profile_lifecycle(self):
        """Test complete profile lifecycle from creation to deletion"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db.health_check = AsyncMock(return_value=True)
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_conf.user_profile.max_favorite_teams = 10
            mock_conf.user_profile.max_favorite_leagues = 5
            mock_conf.user_profile.activity_retention_days = 90
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock database operations for full lifecycle
            mock_connection = AsyncMock()

            # Create profile
            create_data = {
                "user_id": "lifecycle_user",
                "email": "lifecycle@example.com",
                "username": "lifecycleuser",
                "preferences": "{}",
                "stats": "{}",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            mock_connection.fetchrow.return_value = create_data

            # Get profile
            get_data = create_data.copy()
            mock_connection.fetchrow.return_value = get_data

            # Update profile
            update_data = create_data.copy()
            update_data["email"] = "updated@example.com"
            mock_connection.fetchrow.return_value = update_data

            # Add activity
            activity_data = create_data.copy()
            activity_data["activities"] = json.dumps([{
                "activity_type": "login",
                "description": "User logged in",
                "timestamp": datetime.now().isoformat()
            }])
            mock_connection.fetchrow.return_value = activity_data

            # Delete profile
            mock_connection.execute.return_value = "DELETE 1"

            mock_db.get_connection.return_value = mock_connection

            # Test full lifecycle
            # Create
            profile = await service.create_profile("lifecycle_user", "lifecycle@example.com", "lifecycleuser")
            assert profile.user_id == "lifecycle_user"

            # Get
            retrieved_profile = await service.get_profile("lifecycle_user")
            assert retrieved_profile.user_id == "lifecycle_user"

            # Update
            updated_profile = await service.update_profile("lifecycle_user", {"email": "updated@example.com"})
            assert updated_profile.email == "updated@example.com"

            # Add activity
            activity = ProfileActivity(
                activity_type="login",
                description="User logged in",
                timestamp=datetime.now()
            )
            profile_with_activity = await service.add_activity("lifecycle_user", activity)
            assert len(profile_with_activity.activities) == 1

            # Delete
            delete_result = await service.delete_profile("lifecycle_user")
            assert delete_result is True

    @pytest.mark.asyncio
    async def test_concurrent_profile_operations(self):
        """Test concurrent profile operations"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db.health_check = AsyncMock(return_value=True)
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_conf.user_profile.max_favorite_teams = 10
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock database operations
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = {
                "user_id": "concurrent_user",
                "email": "concurrent@example.com",
                "username": "concurrentuser",
                "preferences": "{}",
                "stats": "{}",
                "is_active": True,
                "activities": "[]",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            mock_db.get_connection.return_value = mock_connection

            # Create multiple concurrent operations
            tasks = []
            for i in range(5):
                task = service.get_profile("concurrent_user")
                tasks.append(task)

            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all results
            assert len(results) == 5
            for result in results:
                assert isinstance(result, UserProfile)
                assert result.user_id == "concurrent_user"


class TestUserProfileErrorHandling:
    """Error handling tests for user profile service"""

    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test handling of database connection errors"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks to simulate database connection failure
            mock_db_manager.side_effect = Exception("Database connection failed")

            with pytest.raises(UserProfileError) as exc_info:
                UserProfileService()

            assert "database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_profile_data(self):
        """Test handling of invalid profile data"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock database to return invalid data
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = {
                "user_id": "test_user",
                "email": "invalid_email",  # Invalid email format
                "username": "testuser",
                "preferences": "invalid_json",  # Invalid JSON
                "stats": "{}",
                "is_active": True,
                "created_at": "invalid_date",  # Invalid date
                "updated_at": datetime.now().isoformat()
            }
            mock_db.get_connection.return_value = mock_connection

            with pytest.raises(UserProfileError) as exc_info:
                await service.get_profile("test_user")

            assert "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_concurrent_modification_conflict(self):
        """Test handling of concurrent modification conflicts"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock database to simulate concurrent modification
            mock_connection = AsyncMock()
            mock_connection.fetchrow.side_effect = [
                {
                    "user_id": "conflict_user",
                    "email": "original@example.com",
                    "username": "conflictuser",
                    "preferences": "{}",
                    "stats": "{}",
                    "is_active": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                Exception("Concurrent modification detected")
            ]
            mock_db.get_connection.return_value = mock_connection

            # First read should succeed
            profile = await service.get_profile("conflict_user")
            assert profile.user_id == "conflict_user"

            # Second operation should fail due to conflict
            with pytest.raises(UserProfileError) as exc_info:
                await service.update_profile("conflict_user", {"email": "new@example.com"})

            assert "conflict" in str(exc_info.value).lower() or "concurrent" in str(exc_info.value).lower()


class TestUserProfilePerformance:
    """Performance tests for user profile service"""

    @pytest.mark.asyncio
    async def test_profile_retrieval_performance(self):
        """Test profile retrieval performance"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock fast database response
            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = {
                "user_id": "perf_user",
                "email": "perf@example.com",
                "username": "perfuser",
                "preferences": '{"favorite_teams": ["Team 1"], "language": "en"}',
                "stats": '{"total_predictions": 100, "successful_predictions": 75}',
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            mock_db.get_connection.return_value = mock_connection

            # Measure performance
            start_time = asyncio.get_event_loop().time()

            profile = await service.get_profile("perf_user")

            end_time = asyncio.get_event_loop().time()
            retrieval_time = end_time - start_time

            # Verify result and performance
            assert profile is not None
            assert profile.user_id == "perf_user"
            assert retrieval_time < 0.5  # Should complete within 500ms

    @pytest.mark.asyncio
    async def test_batch_profile_operations_performance(self):
        """Test batch profile operations performance"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock database responses
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = [
                {
                    "user_id": f"user_{i}",
                    "email": f"user{i}@example.com",
                    "username": f"username{i}",
                    "preferences": "{}",
                    "stats": "{}",
                    "is_active": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                } for i in range(20)
            ]
            mock_db.get_connection.return_value = mock_connection

            # Measure batch search performance
            start_time = asyncio.get_event_loop().time()

            profiles = await service.search_profiles("user", limit=20)

            end_time = asyncio.get_event_loop().time()
            search_time = end_time - start_time

            # Verify results and performance
            assert len(profiles) == 20
            assert search_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self):
        """Test memory usage efficiency for profile operations"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Create profile with large data
            large_preferences = ProfilePreference(
                favorite_teams=[f"Team {i}" for i in range(100)],
                favorite_leagues=[f"League {i}" for i in range(50)]
            )
            large_stats = ProfileStats(
                total_predictions=10000,
                successful_predictions=7500,
                total_logins=500
            )

            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = {
                "user_id": "large_profile_user",
                "email": "large@example.com",
                "username": "largeuser",
                "preferences": json.dumps(large_preferences.to_dict()),
                "stats": json.dumps(large_stats.to_dict()),
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            mock_db.get_connection.return_value = mock_connection

            # Retrieve large profile
            profile = await service.get_profile("large_profile_user")

            # Verify profile loaded successfully
            assert profile is not None
            assert len(profile.preferences.favorite_teams) == 100
            assert len(profile.preferences.favorite_leagues) == 50
            assert profile.stats.total_predictions == 10000


# Test class for edge cases and boundary conditions
class TestUserProfileEdgeCases:
    """Edge case tests for user profile service"""

    @pytest.mark.asyncio
    async def test_unicode_profile_data(self):
        """Test profile operations with unicode data"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Test unicode data
            unicode_data = {
                "user_id": "ユーザー123",
                "email": "用户@example.com",
                "username": "ユーザー名",
                "preferences": '{"favorite_teams": ["マンチェスター・ユナイテッド"], "language": "ja"}',
                "stats": "{}",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = unicode_data
            mock_db.get_connection.return_value = mock_connection

            profile = await service.get_profile("ユーザー123")

            assert profile.user_id == "ユーザー123"
            assert profile.email == "用户@example.com"
            assert profile.username == "ユーザー名"

    @pytest.mark.asyncio
    async def test_edge_case_profile_stats(self):
        """Test profile stats with edge cases"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Test edge case stats
            edge_case_stats = {
                "total_predictions": 0,
                "successful_predictions": 0,
                "total_logins": 0,
                "last_login": None,
                "account_created": datetime.now().isoformat()
            }

            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = edge_case_stats
            mock_db.get_connection.return_value = mock_connection

            stats = await service.get_profile_stats("edge_user")

            assert stats.total_predictions == 0
            assert stats.successful_predictions == 0
            assert stats.success_rate == 0.0
            assert stats.last_login is None
            assert stats.days_active >= 0

    @pytest.mark.asyncio
    async def test_extreme_activity_volume(self):
        """Test handling of extreme activity volume"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock large number of activities
            activities = []
            for i in range(1000):
                activities.append({
                    "activity_type": "prediction" if i % 2 == 0 else "login",
                    "description": f"Activity {i}",
                    "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                    "metadata": json.dumps({"index": i})
                })

            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = activities[:100]  # Return first 100
            mock_db.get_connection.return_value = mock_connection

            retrieved_activities = await service.get_profile_activities("active_user", limit=100)

            assert len(retrieved_activities) == 100
            assert retrieved_activities[0].activity_type in ["prediction", "login"]

    @pytest.mark.asyncio
    async def test_profile_with_no_activities(self):
        """Test profile operations with no activities"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Mock profile with no activities
            profile_data = {
                "user_id": "no_activity_user",
                "email": "noactivity@example.com",
                "username": "noactivity",
                "preferences": "{}",
                "stats": '{"total_predictions": 0, "successful_predictions": 0}',
                "is_active": True,
                "activities": "[]",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            mock_connection = AsyncMock()
            mock_connection.fetchrow.return_value = profile_data
            mock_db.get_connection.return_value = mock_connection

            profile = await service.get_profile("no_activity_user")

            assert len(profile.activities) == 0
            assert profile.stats.total_predictions == 0

    @pytest.mark.asyncio
    async def test_profile_timezone_handling(self):
        """Test profile operations with different timezones"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.user_profile = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = UserProfileService()

            # Test different timezones
            timezones = ["UTC", "Europe/London", "America/New_York", "Asia/Tokyo"]

            for timezone in timezones:
                profile_data = {
                    "user_id": f"tz_user_{timezone.replace('/', '_')}",
                    "email": f"user@{timezone}.com",
                    "username": f"user_{timezone}",
                    "preferences": json.dumps({"timezone": timezone}),
                    "stats": "{}",
                    "is_active": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }

                mock_connection = AsyncMock()
                mock_connection.fetchrow.return_value = profile_data
                mock_db.get_connection.return_value = mock_connection

                profile = await service.get_profile(f"tz_user_{timezone.replace('/', '_')}")

                assert profile.preferences.timezone == timezone


if __name__ == "__main__":
    pytest.main([__file__, "-v"])