"""测试用户模型."""

import pytest
from datetime import datetime
from src.database.models.user import User


class TestUser:
    """测试用户模型."""

    def test_table_name(self):
        """测试表名."""
        assert User.__tablename__ == "users"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "username",
            "email",
            "password_hash",
            "first_name",
            "last_name",
            "is_active",
            "is_verified",
            "last_login",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert hasattr(User, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        user = User(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        repr_str = repr(user)
        assert "User" in repr_str
        assert "testuser" in repr_str or "test@example.com" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.user import User

        assert User is not None
