from typing import List
from typing import Dict
"""
测试工具函数
"""

from datetime import datetime


def create_mock_match(**kwargs):
    """创建模拟比赛数据"""
    default_data = {
        "id": 1,
        "home_team_id": 100,
        "away_team_id": 200,
        "match_time": datetime.now(),
        "home_score": 0,
        "away_score": 0,
        "match_status": "scheduled",
    }
    default_data.update(kwargs)
    return default_data


def create_mock_prediction(**kwargs):
    """创建模拟预测数据"""
    default_data = {
        "id": 1,
        "match_id": 1,
        "model_name": "test_model",
        "predicted_result": "home_win",
        "confidence": 0.75,
        "predicted_at": datetime.now(),
    }
    default_data.update(kwargs)
    return default_data


def create_mock_team(**kwargs):
    """创建模拟球队数据"""
    default_data = {
        "id": 100,
        "name": "Test Team",
        "league_id": 1,
        "founded_year": 1900,
    }
    default_data.update(kwargs)
    return default_data


def assert_datetime_close(actual: datetime, expected: datetime, seconds: int = 5):
    """验证两个时间接近"""
    diff = abs((actual - expected).total_seconds())
    assert diff <= seconds, f"时间差 {diff}秒超过允许的 {seconds}秒"


def assert_json_equal(actual: Dict, expected: Dict, exclude_keys: List[str] = None):
    """比较 JSON 字典，排除指定键"""
    if exclude_keys:
        actual = {k: v for k, v in actual.items() if k not in exclude_keys}
        expected = {k: v for k, v in expected.items() if k not in exclude_keys}
    assert actual == expected


class MockResponse:
    """模拟 HTTP 响应"""

    def __init__(self, json_data: Dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")
