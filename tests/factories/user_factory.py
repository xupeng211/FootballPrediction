"""
User factory for testing
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class UserFactory:
    """Factory for creating test users"""

    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def create_test_user(cls, user_id: int = 1) -> "UserFactory":
        """Create a test user"""
        import hashlib
        import secrets

        password_hash = hashlib.sha256(
            "test_password".encode(), usedforsecurity=False
        ).hexdigest()

        return cls(
            id=user_id,
            username=f"testuser{user_id}",
            email=f"test{user_id}@example.com",
            password_hash=password_hash,
            is_active=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }
