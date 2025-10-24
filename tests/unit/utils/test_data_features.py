"""数据特征测试"""

import pytest


@pytest.mark.unit

class TestDataFeatures:
    """测试数据特征模块"""

    def test_feature_store_import(self):
        """测试特征存储导入"""
        try:
            from src.data.features.feature_store import FeatureStore

            assert FeatureStore is not None
        except ImportError:
            pytest.skip("FeatureStore not available")

    def test_feature_definitions_import(self):
        """测试特征定义导入"""
        try:
            from src.data.features.feature_definitions import get_all_features

            assert callable(get_all_features)
        except ImportError:
            pytest.skip("feature_definitions not available")

    def test_feature_examples_import(self):
        """测试特征示例导入"""
        try:
            from src.data.features.examples import example_features

            assert example_features is not None
        except ImportError:
            pytest.skip("feature examples not available")
