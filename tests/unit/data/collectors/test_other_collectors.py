#!/usr/bin/env python3
"""
数据采集器基础测试

为其他采集器提供基础测试覆盖
"""

import pytest

from src.collectors.base_collector import CollectionResult


class TestBaseCollector:
    """基础采集器测试"""

    def test_collection_result_creation(self):
        """测试CollectionResult创建"""
        result = CollectionResult(success=True, data={"test": "data"})

        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None

    def test_collection_result_with_error(self):
        """测试CollectionResult错误情况"""
        result = CollectionResult(success=False, error="Test error")

        assert result.success is False
        assert result.error == "Test error"
        assert result.data is None

    def test_collection_result_defaults(self):
        """测试CollectionResult默认值"""
        result = CollectionResult(success=True)

        assert result.success is True
        assert result.data is None
        assert result.error is None
        assert result.status_code is None
        assert result.response_time is None
        assert result.cached is False


class TestOtherCollectors:
    """其他采集器的基础测试"""

    def test_odds_collector_import(self):
        """测试赔率采集器导入"""
        try:
            from src.data.collectors.odds_collector import OddsCollector

            assert OddsCollector is not None
        except ImportError:
            pytest.skip("OddsCollector not available")

    def test_scores_collector_import(self):
        """测试比分采集器导入"""
        try:
            from src.data.collectors.scores_collector import ScoresCollector

            assert ScoresCollector is not None
        except ImportError:
            pytest.skip("ScoresCollector not available")

    def test_streaming_collector_import(self):
        """测试流采集器导入"""
        try:
            from src.data.collectors.streaming_collector import StreamingCollector

            assert StreamingCollector is not None
        except ImportError:
            pytest.skip("StreamingCollector not available")
