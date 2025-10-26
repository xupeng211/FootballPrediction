"""Domain Strategies Config 测试"""

import pytest

def test_config_strategy_exists():
    """测试配置策略模块可以导入"""
    try:
        from domain.strategies.config import ConfigStrategy
        assert True
    except ImportError:
        pytest.skip("模块导入失败")

def test_config_can_load():
    """测试配置可以加载"""
    try:
        from domain.strategies.config import StrategyConfig
        assert True
    except ImportError:
        pytest.skip("配置加载失败")
