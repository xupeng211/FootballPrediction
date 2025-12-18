"""测试原始数据模型."""

import pytest
from datetime import datetime
from src.database.models.raw_data import RawData


class TestRawData:
    """测试原始数据模型."""

    def test_table_name(self):
        """测试表名."""
        assert RawData.__tablename__ == "raw_data"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "source",
            "data_type",
            "external_id",
            "raw_content",
            "processed",
            "created_at",
            "processed_at",
        ]

        for field in required_fields:
            assert hasattr(RawData, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        raw_data = RawData(
            source="football_api",
            data_type="match",
            external_id="12345",
            processed=False,
        )

        repr_str = repr(raw_data)
        assert "RawData" in repr_str
        assert "football_api" in repr_str or "match" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.raw_data import RawData

        assert RawData is not None
