"""
Test factories package
"""

from .user_factory import UserFactory

# Additional factories can be added as needed
def DataFactory(data_type: str, **kwargs):
    """Generic data factory for testing"""
    if data_type == "user":
        return UserFactory.create_test_user(**kwargs)
    else:
        raise ValueError(f"Unknown data type: {data_type}")

def MockFactory(mock_type: str, **kwargs):
    """Generic mock factory for testing"""
    from unittest.mock import Mock

    if mock_type == "user":
        mock_user = Mock()
        mock_user.id = kwargs.get("id", 1)
        mock_user.username = kwargs.get("username", "testuser")
        mock_user.email = kwargs.get("email", "test@example.com")
        return mock_user
    else:
        return Mock()

__all__ = ["UserFactory", "DataFactory", "MockFactory"]