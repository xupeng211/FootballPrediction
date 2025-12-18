"""测试数据质量日志模型."""

import pytest
from datetime import datetime
from src.database.models.data_quality_log import DataQualityLog


class TestDataQualityLog:
    """测试数据质量日志模型."""

    def test_table_name(self):
        """测试表名."""
        assert DataQualityLog.__tablename__ == "data_quality_logs"

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = [
            "id",
            "table_name",
            "record_id",
            "issue_type",
            "issue_description",
            "severity",
            "status",
            "created_at",
            "resolved_at",
        ]

        for field in required_fields:
            assert hasattr(DataQualityLog, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        log = DataQualityLog(
            table_name="matches", issue_type="missing_data", severity="high"
        )

        repr_str = repr(log)
        assert "DataQualityLog" in repr_str
        assert "matches" in repr_str or "missing_data" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.data_quality_log import DataQualityLog

        assert DataQualityLog is not None
