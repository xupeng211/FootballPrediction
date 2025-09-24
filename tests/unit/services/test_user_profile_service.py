from datetime import datetime

import pytest

from src.models import User, UserProfile, UserRole
from src.services.user_profile import UserProfileService

pytestmark = pytest.mark.unit


def _make_user(user_id: str = "user-1") -> User:
    base_profile = UserProfile(
        user_id=user_id,
        display_name="Example",
        email=f"{user_id}@example.com",
        preferences={"interests": ["football"]},
        created_at=datetime.utcnow(),
    )
    return User(
        id=user_id,
        username="example-user",
        role=UserRole.USER,
        profile=base_profile,
    )


@pytest.mark.asyncio
async def test_generate_and_get_profile() -> None:
    service = UserProfileService()
    await service.initialize()

    user = _make_user()
    generated = await service.generate_profile(user)

    assert generated.user_id == user.id
    assert await service.get_profile(user.id) is generated


@pytest.mark.asyncio
async def test_update_profile_overrides_known_fields_and_adds_preferences() -> None:
    service = UserProfileService()
    await service.initialize()

    user = _make_user("user-2")
    await service.generate_profile(user)

    updated = await service.update_profile(
        user.id,
        {
            "display_name": "Updated",
            "preferences": {"interests": ["basketball"]},
            "favorite_team": "Team A",
        },
    )

    assert updated is not None
    assert updated.display_name == "Updated"
    assert updated.preferences["interests"] == ["basketball"]
    assert updated.preferences["favorite_team"] == "Team A"


def test_create_and_delete_profile_sync_helpers() -> None:
    service = UserProfileService()

    created = service.create_profile({"user_id": "sync-user", "name": "Sync"})
    assert created["status"] == "created"
    assert created["profile"]["display_name"] == "Sync"

    profiles = service._profiles
    assert "sync-user" in profiles

    deleted = service.delete_profile("sync-user")
    assert deleted == {"status": "deleted"}
    assert service.delete_profile("sync-user") == {"status": "not_found"}


@pytest.mark.asyncio
async def test_shutdown_clears_cached_profiles() -> None:
    service = UserProfileService()
    await service.initialize()
    user = _make_user("user-3")
    await service.generate_profile(user)

    await service.shutdown()
    assert await service.get_profile("user-3") is None
