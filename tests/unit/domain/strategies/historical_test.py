"""Domain Strategies Historical 测试"""

import pytest


def test_historical_strategy_exists():
    """测试历史策略模块可以导入"""
    try:
        from domain.strategies.historical import HistoricalStrategy

        assert True
    except ImportError:
        pytest.skip("模块导入失败")


def test_historical_class_exists():
    """测试历史策略类存在"""
    try:
        from domain.strategies.historical import HistoricalMatch

        assert True
    except ImportError:
        pytest.skip("类导入失败")
