import pytest

from src.database.models.user import User


@pytest.mark.unit
@pytest.mark.database
def test_user_model():
    _user = User(username="testuser", email="test@example.com")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
