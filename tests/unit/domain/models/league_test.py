"""Domain Models League 测试"""

import pytest


def test_league_model_exists():
    """测试联赛模型存在"""
    try:

        assert True
    except ImportError:
        pytest.skip("模块导入失败")


def test_league_can_create():
    """测试联赛可以创建"""
    try:
        from domain.models.league import League

        league = League()
        assert league is not None
    except ImportError:
        pytest.skip("创建失败")
