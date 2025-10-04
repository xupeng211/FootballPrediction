"""Unit测试全局配置和fixtures"""

import pytest


@pytest.fixture
def auth_headers():
    """提供认证头部"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def sample_prediction_data():
    """提供示例预测数据"""
    return {
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": "2024-01-01",
        "league": "Premier League",
    }
