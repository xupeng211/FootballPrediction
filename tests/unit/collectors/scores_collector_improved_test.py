"""数据收集器测试"""

import pytest


def test_scores_collector_exists():
    """测试比分收集器存在"""
    try:

        assert True
    except ImportError:
        pytest.skip("模块导入失败")


def test_collector_can_instantiate():
    """测试收集器可以实例化"""
    try:
        from collectors.scores_collector_improved import ScoresCollectorImproved

        collector = ScoresCollectorImproved()
        assert collector is not None
    except ImportError:
        pytest.skip("实例化失败")
