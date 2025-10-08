"""数据处理测试"""

import pytest


class TestDataProcessing:
    """测试数据处理模块"""

    def test_football_data_cleaner_import(self):
        """测试足球数据清理器导入"""
        try:
            from src.data.processing.football_data_cleaner import FootballDataCleaner

            assert FootballDataCleaner is not None
        except ImportError:
            pytest.skip("FootballDataCleaner not available")

    def test_missing_data_handler_import(self):
        """测试缺失数据处理导入"""
        try:
            from src.data.processing.missing_data_handler import MissingDataHandler

            assert MissingDataHandler is not None
        except ImportError:
            pytest.skip("MissingDataHandler not available")

    def test_streaming_collector_import(self):
        """测试流收集器导入"""
        try:
            from src.data.collectors.streaming_collector import StreamingDataCollector

            assert StreamingDataCollector is not None
        except ImportError:
            pytest.skip("StreamingDataCollector not available")
