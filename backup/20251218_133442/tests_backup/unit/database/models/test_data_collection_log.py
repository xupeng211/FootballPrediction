"""测试数据采集日志模型."""

import pytest
from datetime import datetime
from src.database.models.data_collection_log import DataCollectionLog


class TestDataCollectionLog:
    """测试数据采集日志模型."""

    def test_table_name(self):
        """测试表名."""
        assert DataCollectionLog.__tablename__ == "data_collection_logs"

    def test_model_fields(self):
        """测试模型字段."""
        # 检查所有必需的字段存在
        required_fields = [
            "id",
            "source",
            "status",
            "start_time",
            "end_time",
            "records_count",
            "error_message",
            "created_at",
        ]

        for field in required_fields:
            assert hasattr(DataCollectionLog, field), f"Missing field: {field}"

    def test_repr_method(self):
        """测试__repr__方法."""
        # 创建一个模拟的模型实例
        log = DataCollectionLog(
            source="test_api",
            status="success",
            start_time=datetime.now(),
            records_count=100,
        )

        # 检查repr包含关键信息
        repr_str = repr(log)
        assert "DataCollectionLog" in repr_str
        assert "test_api" in repr_str or "success" in repr_str

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.data_collection_log import DataCollectionLog

        assert DataCollectionLog is not None
