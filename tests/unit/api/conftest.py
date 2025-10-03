"""
API测试模块共享配置和Fixtures
提供统一的测试数据和Mock配置
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List


@pytest.fixture
def sample_match_data():
    """标准比赛数据"""
    return {
        "id": 1,
        "home_team_id": 101,
        "away_team_id": 102,
        "league_id": 1,
        "home_score": 2,
        "away_score": 1,
        "status": "finished",
        "match_date": datetime.now(),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_team_data():
    """标准球队数据"""
    return {
        "id": 101,
        "name": "Test Team FC",
        "league_id": 1,
        "points": 30,
        "played": 10,
        "won": 8,
        "drawn": 2,
        "lost": 0,
        "goals_for": 20,
        "goals_against": 5,
        "goal_difference": 15,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_prediction_data():
    """标准预测数据"""
    return {
        "id": 1,
        "match_id": 1,
        "predicted_winner": "home",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75,
        "model_version": "v1.0",
        "created_at": datetime.now(),
        "status": "pending"
    }


@pytest.fixture
def sample_league_data():
    """标准联赛数据"""
    return {
        "id": 1,
        "name": "Premier League",
        "country": "England",
        "season": "2023-24",
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def mock_async_session():
    """创建标准的AsyncSession Mock"""
    session = AsyncMock()

    # 创建标准的Mock结果
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None
    mock_result.count.return_value = 0

    session.execute.return_value = mock_result
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()

    return session


@pytest.fixture
def mock_cache_manager():
    """创建标准的缓存管理器Mock"""
    manager = MagicMock()

    # 标准统计数据
    manager.get_stats.return_value = {
        "l1_cache": {
            "hits": 100,
            "misses": 20,
            "hit_rate": 0.83,
            "size": 1000,
            "max_size": 5000
        },
        "l2_cache": {
            "hits": 50,
            "misses": 10,
            "hit_rate": 0.83,
            "size": 500,
            "max_size": 2000
        },
        "overall": {
            "total_hits": 150,
            "total_misses": 30,
            "overall_hit_rate": 0.83,
            "total_size": 1500
        },
        "config": {
            "ttl": 3600,
            "max_size": 7000,
            "policy": "LRU"
        }
    }

    # 标准操作
    manager.clear.return_value = {"cleared_keys": ["test_key1", "test_key2"]}
    manager.get.return_value = {"value": "test_data"}
    manager.set.return_value = True
    manager.delete.return_value = True
    manager.exists.return_value = True

    return manager


@pytest.fixture
def mock_database_stats():
    """创建数据库统计数据Mock"""
    return {
        "healthy": True,
        "response_time_ms": 15.5,
        "statistics": {
            "teams_count": 20,
            "matches_count": 380,
            "predictions_count": 1000,
            "active_connections": 5,
            "idle_connections": 10
        }
    }


@pytest.fixture
def mock_system_metrics():
    """创建系统指标Mock"""
    return {
        "cpu": {
            "usage_percentage": 45.2,
            "core_count": 8,
            "load_average": [1.2, 1.5, 1.8]
        },
        "memory": {
            "usage_percentage": 62.8,
            "total_gb": 16.0,
            "used_gb": 10.0,
            "available_gb": 6.0
        },
        "disk": {
            "usage_percentage": 75.3,
            "total_gb": 500.0,
            "used_gb": 376.5,
            "free_gb": 123.5
        }
    }


class TestDataFactory:
    """测试数据工厂类"""

    @staticmethod
    def create_match_list(count: int = 5) -> List[Dict[str, Any]]:
        """创建比赛列表"""
        matches = []
        base_time = datetime.now()

        for i in range(count):
            matches.append({
                "id": i + 1,
                "home_team_id": 101 + i,
                "away_team_id": 201 + i,
                "league_id": 1,
                "home_score": i % 3,
                "away_score": i % 2,
                "status": ["finished", "live", "scheduled"][i % 3],
                "match_date": base_time + timedelta(days=i),
                "created_at": base_time,
                "updated_at": base_time
            })

        return matches

    @staticmethod
    def create_team_list(count: int = 5) -> List[Dict[str, Any]]:
        """创建球队列表"""
        teams = []

        for i in range(count):
            teams.append({
                "id": 101 + i,
                "name": f"Team {i+1} FC",
                "league_id": 1,
                "points": (i + 1) * 6,
                "played": i + 10,
                "won": i + 5,
                "drawn": 3,
                "lost": 2,
                "goals_for": (i + 1) * 3,
                "goals_against": 5,
                "goal_difference": (i + 1) * 3 - 5,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })

        return teams

    @staticmethod
    def create_prediction_list(count: int = 5) -> List[Dict[str, Any]]:
        """创建预测列表"""
        predictions = []
        base_time = datetime.now()

        for i in range(count):
            predictions.append({
                "id": i + 1,
                "match_id": i + 1,
                "predicted_winner": ["home", "away", "draw"][i % 3],
                "predicted_home_score": (i % 3) + 1,
                "predicted_away_score": i % 2,
                "confidence": 0.5 + (i * 0.1),
                "model_version": "v1.0",
                "created_at": base_time,
                "status": ["pending", "completed", "failed"][i % 3]
            })

        return predictions


def create_mock_query_result(data_list: List[Dict], total_count: int = None):
    """创建标准的查询结果Mock"""
    result_mock = MagicMock()

    if data_list:
        # Mock scalars()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = data_list
        scalars_mock.first.return_value = data_list[0] if data_list else None
        result_mock.scalars.return_value = scalars_mock

        # Mock first()
        result_mock.first.return_value = data_list[0] if data_list else None

        # Mock scalar_one_or_none()
        result_mock.scalar_one_or_none.return_value = data_list[0] if len(data_list) == 1 else None

        # Mock count
        result_mock.count.return_value = total_count or len(data_list)
    else:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        scalars_mock.first.return_value = None
        result_mock.scalars.return_value = scalars_mock
        result_mock.first.return_value = None
        result_mock.scalar_one_or_none.return_value = None
        result_mock.count.return_value = total_count or 0

    return result_mock


def assert_valid_response(response: Any, expected_keys: List[str]):
    """验证响应格式的辅助函数"""
    assert response is not None

    # 支持字典和Pydantic模型
    if hasattr(response, 'model_dump'):
        # Pydantic模型
        response_dict = response.model_dump()
    elif hasattr(response, 'dict'):
        # 旧版Pydantic模型
        response_dict = response.dict()
    elif isinstance(response, dict):
        # 普通字典
        response_dict = response
    else:
        pytest.fail(f"响应类型不支持: {type(response)}")

    for key in expected_keys:
        assert key in response_dict, f"响应中缺少必需的键: {key}"

    return response_dict  # 返回字典以便后续使用


def assert_pagination_info(pagination: Dict[str, Any]):
    """验证分页信息的辅助函数"""
    required_keys = ["page", "page_size", "total", "pages"]
    assert_valid_response(pagination, required_keys)

    assert isinstance(pagination["page"], int)
    assert isinstance(pagination["page_size"], int)
    assert isinstance(pagination["total"], int)
    assert isinstance(pagination["pages"], int)

    assert pagination["page"] > 0
    assert pagination["page_size"] > 0
    assert pagination["total"] >= 0
    assert pagination["pages"] >= 0


def assert_api_error(exception: Exception, expected_status: int, expected_detail_contains: str = None):
    """验证API错误的辅助函数"""
    assert hasattr(exception, 'status_code'), "异常应该有status_code属性"
    assert exception.status_code == expected_status, f"期望状态码 {expected_status}, 实际 {exception.status_code}"

    if expected_detail_contains:
        assert hasattr(exception, 'detail'), "异常应该有detail属性"
        assert expected_detail_contains.lower() in exception.detail.lower(), \
            f"错误详情应该包含 '{expected_detail_contains}', 实际: {exception.detail}"