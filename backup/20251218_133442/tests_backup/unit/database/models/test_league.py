"""测试联赛模型."""

import pytest
from datetime import datetime
from src.database.models.league import League


class TestLeague:
    """测试联赛模型."""

    def test_table_name(self):
        """测试表名."""
        assert League.__tablename__ == "leagues"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "name",
            "country",
            "season",
            "external_id",
            "is_active",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert hasattr(League, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        league = League(name="Premier League", country="England", season="2023-24")

        repr_str = repr(league)
        assert "League" in repr_str
        assert "Premier League" in repr_str or "England" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.league import League

        assert League is not None
