"""测试特征模型."""

import pytest
from datetime import datetime
from src.database.models.features import FeatureEntity


class TestFeatureEntity:
    """测试特征实体模型."""

    def test_table_name(self):
        """测试表名."""
        assert hasattr(FeatureEntity, "__tablename__")

    def test_model_fields(self):
        """测试模型字段."""
        required_fields = ["id", "match_id", "feature_data", "created_at", "updated_at"]

        for field in required_fields:
            assert hasattr(FeatureEntity, field), f"Missing field: {field}"

    def test_model_import(self):
        """测试模型导入."""
        from src.database.models.features import FeatureEntity

        assert FeatureEntity is not None
