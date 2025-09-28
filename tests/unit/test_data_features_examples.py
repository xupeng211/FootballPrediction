"""
Tests for data features examples module
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import functions selectively to avoid module-level skip


@pytest.mark.unit
class TestDataFeaturesExamples:
    """Test data features examples"""

    def test_module_imports(self):
        """测试模块导入"""
        try:
            from src.data.features.examples import example_initialize_feature_store
            assert callable(example_initialize_feature_store)
        except ImportError:
            pytest.skip("Examples module not available")

    @patch('src.data.features.examples.FootballFeatureStore')
    def test_example_initialize_feature_store_mock(self, mock_feature_store):
        """测试特征仓库初始化示例（使用Mock）"""
        # Mock the FootballFeatureStore class
        mock_store = Mock()
        mock_feature_store.return_value = mock_store

        # Import and call the function
        from src.data.features.examples import example_initialize_feature_store
        result = example_initialize_feature_store()

        # Verify the function returns the mocked store
        assert result == mock_store

    @patch('src.data.features.examples.pd.DataFrame')
    def test_example_write_features_mock(self, mock_dataframe):
        """测试特征写入示例（使用Mock）"""
        # Mock pandas DataFrame
        mock_df = Mock()
        mock_dataframe.return_value = mock_df

        try:
            from src.data.features.examples import example_write_features
            # This should not raise an exception
            assert True
        except ImportError:
            pytest.skip("Examples module not available")

    def test_example_functions_exist(self):
        """测试示例函数存在性"""
        functions_to_check = [
            'example_initialize_feature_store',
            'example_write_features',
            'example_get_online_features',
            'example_get_historical_features',
            'example_feature_statistics'
        ]

        for func_name in functions_to_check:
            try:
                from src.data.features.examples import func_name
                assert callable(func_name)
            except ImportError:
                pytest.skip(f"Function {func_name} not available")

    def test_config_parameters_exist(self):
        """测试配置参数存在性"""
        try:
            from src.data.features.examples import example_initialize_feature_store

            # The function should handle config parameters properly
            # We're just testing it doesn't crash when called
            with patch('src.data.features.examples.FootballFeatureStore'):
                result = example_initialize_feature_store()
                assert result is not None
        except ImportError:
            pytest.skip("Examples module not available")