import os
import warnings
from datetime import datetime

import pytest

os.environ.setdefault("MINIMAL_API_MODE", "true")
warnings.filterwarnings("ignore", category=UserWarning)

from src.models.common_models import User, UserProfile, UserRole

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")
from src.services.user_profile import UserProfileService


@pytest.fixture
async def service():
    svc = UserProfileService()
    await svc.initialize()
    try:
        yield svc
    finally:
        await svc.shutdown()


@pytest.fixture
def sample_user() -> User:
    profile = UserProfile(
        user_id = os.getenv("TEST_USER_PROFILE_SERVICE_USER_ID_29"),
        display_name = os.getenv("TEST_USER_PROFILE_SERVICE_DISPLAY_NAME_29"),
        email = os.getenv("TEST_USER_PROFILE_SERVICE_EMAIL_29"),
        preferences={"favorite_teams": ["Team A"]},
        created_at=datetime.utcnow(),
    )
    return User(
        id = os.getenv("TEST_USER_PROFILE_SERVICE_ID_32"),
        username = os.getenv("TEST_USER_PROFILE_SERVICE_USERNAME_32"),
        role=UserRole.USER,
        profile=profile,
    )


@pytest.mark.asyncio
async def test_generate_profile_persists_result(service: UserProfileService, sample_user: User):
    profile = await service.generate_profile(sample_user)

    assert profile.user_id == sample_user.id
    cached = await service.get_profile(sample_user.id)
    assert cached is profile
    assert "interests" in profile.preferences
    assert profile.preferences["language"] == "zh"


@pytest.mark.asyncio
async def test_update_profile_allows_incremental_changes(
    service: UserProfileService, sample_user: User
):
    await service.generate_profile(sample_user)

    updated = await service.update_profile(
        sample_user.id,
        {"preferences": {"language": "en", "interests": ["足球", "英超"]}},
    )

    assert updated is not None
    assert updated.preferences["language"] == "en"
    assert "英超" in updated.preferences["interests"]


def test_create_and_delete_profile_sync_path():
    service = UserProfileService()

    creation = service.create_profile(
        {
            "user_id": "user-2",
            "name": "Visitor",
            "email": "visitor@example.com",
            "interests": ["预测"],
            "language": "en",
            "content_type": "video",
        }
    )

    assert creation["status"] == "created"
    profile_dict = creation["profile"]
    assert profile_dict["user_id"] == "user-2"
    assert profile_dict["preferences"]["language"] == "en"

    assert service.delete_profile("user-2") == {"status": "deleted"}
    assert service.delete_profile("user-2") == {"status": "not_found"}
