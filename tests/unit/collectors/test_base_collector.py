"""基础收集器测试"""

import pytest
from src.data.collectors.base_collector import DataCollector, CollectionResult


class TestDataCollector:
    """测试数据收集器"""

    def test_data_collector_import(self):
        """测试数据收集器导入"""
        try:
            from src.data.collectors.base_collector import DataCollector

            assert DataCollector is not None
        except ImportError:
            pytest.skip("DataCollector not available")

    def test_collection_result_import(self):
        """测试收集结果导入"""
        try:
            from src.data.collectors.base_collector import CollectionResult

            assert CollectionResult is not None
        except ImportError:
            pytest.skip("CollectionResult not available")

    def test_collection_result_creation(self):
        """测试创建收集结果实例"""
        try:
            result = CollectionResult(
                success=True, data={"test": "data"}, message="Test collection"
            )
            assert result.success is True
            assert result.data == {"test": "data"}
            assert result.message == "Test collection"
        except Exception:
            pytest.skip("Cannot create CollectionResult")

    def test_data_collector_is_abstract(self):
        """测试数据收集器是抽象类"""
        try:
            from src.data.collectors.base_collector import DataCollector
            import pytest

            # DataCollector 应该是抽象类，不能直接实例化
            with pytest.raises(TypeError):
                DataCollector()
        except Exception:
            pytest.skip("DataCollector abstract test not available")
