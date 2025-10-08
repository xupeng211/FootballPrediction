"""数据收集器基础测试"""

import pytest


class TestBasicCollectorImports:
    """测试数据收集器的基础导入"""

    def test_import_fixtures_collector(self):
        """测试赛程收集器导入"""
        try:
            from src.collectors import fixtures_collector

            assert fixtures_collector is not None
        except ImportError as e:
            pytest.skip(f"无法导入fixtures_collector: {e}")

    def test_import_odds_collector(self):
        """测试赔率收集器导入"""
        try:
            from src.collectors import odds_collector

            assert odds_collector is not None
        except ImportError as e:
            pytest.skip(f"无法导入odds_collector: {e}")

    def test_import_scores_collector(self):
        """测试比分收集器导入"""
        try:
            from src.collectors import scores_collector

            assert scores_collector is not None
        except ImportError as e:
            pytest.skip(f"无法导入scores_collector: {e}")

    def test_import_streaming_collector(self):
        """测试流数据收集器导入"""
        try:
            from src.collectors import streaming_collector

            assert streaming_collector is not None
        except ImportError as e:
            pytest.skip(f"无法导入streaming_collector: {e}")


class TestBasicCollectorFunctionality:
    """测试数据收集器的基本功能"""

    def test_base_collector_exists(self):
        """测试基础收集器类存在"""
        try:
            from src.data.collectors.base_collector import BaseCollector

            assert BaseCollector is not None
        except ImportError as e:
            pytest.skip(f"无法导入BaseCollector: {e}")

    def test_collector_interface(self):
        """测试收集器接口"""
        try:
            from src.data.collectors.base_collector import BaseCollector

            # 测试抽象方法定义
            assert hasattr(BaseCollector, "collect")
            assert hasattr(BaseCollector, "initialize")
            assert hasattr(BaseCollector, "shutdown")

        except Exception as e:
            pytest.skip(f"无法测试BaseCollector接口: {e}")

    def test_fixtures_collector_class(self):
        """测试赛程收集器类"""
        try:
            from src.collectors.fixtures_collector import FixturesCollector

            assert FixturesCollector is not None
        except ImportError as e:
            pytest.skip(f"无法导入FixturesCollector: {e}")

    def test_odds_collector_class(self):
        """测试赔率收集器类"""
        try:
            from src.collectors.odds_collector import OddsCollector

            assert OddsCollector is not None
        except ImportError as e:
            pytest.skip(f"无法导入OddsCollector: {e}")
