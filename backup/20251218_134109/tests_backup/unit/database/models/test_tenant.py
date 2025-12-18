"""测试租户模型."""

import pytest
from datetime import datetime
from src.database.models.tenant import Tenant


class TestTenant:
    """测试租户模型."""

    def test_table_name(self):
        """测试表名."""
        assert Tenant.__tablename__ == "tenants"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "name",
            "slug",
            "domain",
            "is_active",
            "settings",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert hasattr(Tenant, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        tenant = Tenant(
            name="Test Tenant", slug="test-tenant", domain="test.example.com"
        )

        repr_str = repr(tenant)
        assert "Tenant" in repr_str
        assert "Test Tenant" in repr_str or "test-tenant" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.tenant import Tenant

        assert Tenant is not None
