"""测试球队模型."""

import pytest
from datetime import datetime
from src.database.models.team import Team


class TestTeam:
    """测试球队模型."""

    def test_table_name(self):
        """测试表名."""
        assert Team.__tablename__ == "teams"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "name",
            "short_name",
            "country",
            "league_id",
            "external_id",
            "founded_year",
            "stadium",
            "logo_url",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert hasattr(Team, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        team = Team(name="Manchester United", short_name="MUFC", country="England")

        repr_str = repr(team)
        assert "Team" in repr_str
        assert "Manchester United" in repr_str or "MUFC" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.team import Team

        assert Team is not None
