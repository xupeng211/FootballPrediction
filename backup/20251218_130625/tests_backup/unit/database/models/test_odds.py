"""测试赔率模型."""

import pytest
from datetime import datetime
from decimal import Decimal
from src.database.models.odds import Odds


class TestOdds:
    """测试赔率模型."""

    def test_table_name(self):
        """测试表名."""
        assert Odds.__tablename__ == "odds"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "match_id",
            "bookmaker",
            "home_win",
            "draw",
            "away_win",
            "over_under",
            "asian_handicap",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert hasattr(Odds, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        odds = Odds(
            match_id=1,
            bookmaker="Bet365",
            home_win=Decimal("2.50"),
            draw=Decimal("3.20"),
            away_win=Decimal("2.80"),
        )

        repr_str = repr(odds)
        assert "Odds" in repr_str
        assert "Bet365" in repr_str or "1" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.odds import Odds

        assert Odds is not None
