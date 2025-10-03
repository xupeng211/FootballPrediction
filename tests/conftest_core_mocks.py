"""
核心模块测试的通用Mock Fixtures
用于解决外部依赖问题，提升核心模块覆盖率
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime, date


@pytest.fixture
def mock_async_session():
    """模拟AsyncSession，用于数据库操作"""
    session = AsyncMock(spec=AsyncSession)

    # 模拟session的基本操作
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()

    # 模拟查询结果
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_db_session():
    """模拟同步数据库Session"""
    session = MagicMock(spec=Session)
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.get.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_redis_manager():
    """模拟Redis管理器"""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.exists.return_value = False
    redis_mock.hgetall.return_value = {}
    redis_mock.hset.return_value = True
    redis_mock.expire.return_value = True
    redis_mock.ping.return_value = True
    return redis_mock


@pytest.fixture
def mock_mlflow_client():
    """模拟MLflow客户端"""
    mlflow_mock = MagicMock()
    mlflow_mock.get_experiment_by_name.return_value = None
    mlflow_mock.create_experiment.return_value = MagicMock(experiment_id="test_exp")
    mlflow_mock.log_metric.return_value = None
    mlflow_mock.log_param.return_value = None
    mlflow_tracker = MagicMock()
    mlflow_tracker.log_metric = MagicMock()
    mlflow_tracker.log_param = MagicMock()
    mlflow.start_run.return_value = MagicMock()
    mlflow.active_run.return_value = MagicMock(info={"run_id": "test_run"})
    return mlflow_mock


@pytest.fixture
def mock_database_manager():
    """模拟数据库管理器"""
    db_mock = MagicMock()
    db_mock.get_session.return_value = mock_async_session()
    db_mock.check_connection.return_value = True
    db_mock.execute_query.return_value = []
    return db_mock


@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "id": 1,
        "home_team_id": 101,
        "away_team_id": 102,
        "league_id": 1,
        "home_score": 2,
        "away_score": 1,
        "status": "finished",
        "match_date": datetime(2024, 1, 1),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_team_data():
    """示例球队数据"""
    return {
        "id": 101,
        "name": "Test Team",
        "league_id": 1,
        "points": 30,
        "played": 10,
        "won": 9,
        "drawn": 1,
        "lost": 0,
        "goals_for": 25,
        "goals_against": 5,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_league_data():
    """示例联赛数据"""
    return {
        "id": 1,
        "name": "Test League",
        "country": "Test Country",
        "season": "2024",
        "total_teams": 20,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def mock_prediction_model():
    """模拟预测模型"""
    model_mock = MagicMock()
    model_mock.predict.return_value = [0.7, 0.2, 0.1]  # win/draw/lose probabilities
    model_mock.predict_proba.return_value = [[0.7, 0.2, 0.1]]
    model_mock.classes_ = ["win", "draw", "lose"]
    return model_mock


@pytest.fixture
def mock_external_apis():
    """模拟外部API调用"""
    import requests_mock

    with requests_mock.Mocker() as m:
        # 模拟成功的API响应
        m.get("http://external-api.com/matches", json={
            "matches": [
                {"id": 1, "home_team": "Team A", "away_team": "Team B"}
            ]
        })
        m.get("http://external-api.com/teams", json={
            "teams": [
                {"id": 101, "name": "Team A"}
            ]
        })
        yield m


# 模拟数据库查询结果的辅助函数
def create_mock_query_result(data_list):
    """创建模拟查询结果"""
    result_mock = MagicMock()

    if data_list:
        # 模拟scalars()返回
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = data_list
        result_mock.scalars.return_value = scalars_mock

        # 模拟first()返回
        result_mock.first.return_value = data_list[0] if data_list else None

        # 模拟scalar_one_or_none()返回
        result_mock.scalar_one_or_none.return_value = data_list[0] if len(data_list) == 1 else None
    else:
        result_mock.scalars.return_value.all.return_value = []
        result_mock.first.return_value = None
        result_mock.scalar_one_or_none.return_value = None

    return result_mock


# 模拟分页结果的辅助函数
def create_mock_paginated_result(items, page=1, page_size=10, total=None):
    """创建模拟分页结果"""
    if total is None:
        total = len(items)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


# Pytest标记用于区分不同类型的测试
pytest.mark.unit_test = pytest.mark.unit_test
pytest.mark.integration_test = pytest.mark.integration_test
pytest.mark.api_test = pytest.mark.api_test
pytest.mark.mock_test = pytest.mark.mock_test