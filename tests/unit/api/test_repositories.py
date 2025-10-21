"""
仓储模式API端点测试
Tests for Repository Pattern API Endpoints

测试仓储模式的所有API端点，包括：
- 预测仓储（读和写）
- 用户仓储（读和写）
- 比赛仓储（读和写）
- 查询规范
- 统计功能
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.repositories import router


class MockPrediction:
    """模拟预测模型"""

    def __init__(
        self,
        id=1,
        user_id=1,
        match_id=123,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
        strategy_used="neural_network",
    ):
        self.id = id
        self.user_id = user_id
        self.match_id = match_id
        self.predicted_home = predicted_home
        self.predicted_away = predicted_away
        self.confidence = confidence
        self.strategy_used = strategy_used
        self.notes = "测试预测"
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MockUser:
    """模拟用户模型"""

    def __init__(self, id=1, username="testuser", email="test@example.com"):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = datetime.utcnow()
        self.is_active = True


class MockMatch:
    """模拟比赛模型"""

    def __init__(self, id=123, home_team="Team A", away_team="Team B"):
        self.id = id
        self.home_team = home_team
        self.away_team = away_team
        self.match_date = datetime.utcnow() + timedelta(days=1)
        self.status = "SCHEDULED"


class MockRepository:
    """模拟仓储"""

    def __init__(self):
        self._data = {}
        self.next_id = 1

    async def get_by_id(self, id):
        """根据ID获取"""
        return self.data.get(str(id))

    async def find_many(self, query_spec):
        """查询多个"""
        # 简化的查询实现
        filters = query_spec.filters or {}
        results = list(self.data.values())

        # 应用过滤器
        if filters:
            for key, value in filters.items():
                results = [r for r in results if getattr(r, key, None) == value]

        # 应用排序
        if query_spec.order_by:
            reverse = query_spec.order_by[0].startswith("-")
            sort_key = query_spec.order_by[0].lstrip("-")
            results.sort(key=lambda x: getattr(x, sort_key), reverse=reverse)

        # 应用限制和偏移
        if query_spec.offset:
            results = results[query_spec.offset :]
        if query_spec.limit:
            results = results[: query_spec.limit]

        return results

    async def get_user_statistics(self, user_id, period_days=None):
        """获取用户统计"""
        user_predictions = [p for p in self.data.values() if p.user_id == user_id]
        return {
            "user_id": user_id,
            "total_predictions": len(user_predictions),
            "average_confidence": sum(p.confidence for p in user_predictions)
            / len(user_predictions)
            if user_predictions
            else 0,
            "period_days": period_days or 30,
        }

    async def create(self, entity):
        """创建实体"""
        entity.id = self.next_id
        self.next_id += 1
        entity.created_at = datetime.utcnow()
        self._data[str(entity.id)] = entity
        return entity

    async def update(self, entity):
        """更新实体"""
        entity.updated_at = datetime.utcnow()
        self._data[str(entity.id)] = entity
        return entity

    async def delete(self, id):
        """删除实体"""
        if str(id) in self.data:
            del self._data[str(id)]
            return True
        return False


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestPredictionRepository:
    """预测仓储测试"""

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_predictions(self, mock_repo_dep, client):
        """测试：获取预测列表"""
        # Given
        mock_repo = MockRepository()
        # 添加一些测试数据
        mock_repo._data = {
            "1": MockPrediction(id=1, user_id=1, match_id=123),
            "2": MockPrediction(id=2, user_id=2, match_id=124),
            "3": MockPrediction(id=3, user_id=1, match_id=125),
        }
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert "total" in _data

        assert "predictions" in _data

        assert _data["total"] == 3
        assert len(_data["predictions"]) == 3

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_predictions_with_filters(self, mock_repo_dep, client):
        """测试：带过滤器的预测列表"""
        # Given
        mock_repo = MockRepository()
        mock_repo._data = {
            "1": MockPrediction(id=1, user_id=1, match_id=123),
            "2": MockPrediction(id=2, user_id=2, match_id=124),
            "3": MockPrediction(id=3, user_id=1, match_id=125),
        }
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions?user_id=1&limit=10&offset=0")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total"] == 2  # 只有user_id=1的预测

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_predictions_with_match_filter(self, mock_repo_dep, client):
        """测试：按比赛ID过滤预测"""
        # Given
        mock_repo = MockRepository()
        mock_repo._data = {
            "1": MockPrediction(id=1, user_id=1, match_id=123),
            "2": MockPrediction(id=2, user_id=2, match_id=124),
            "3": MockPrediction(id=3, user_id=1, match_id=125),
        }
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions?match_id=124")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total"] == 1  # 只有match_id=124的预测
        assert _data["predictions"][0]["match_id"] == 124

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_predictions_pagination(self, mock_repo_dep, client):
        """测试：预测列表分页"""
        # Given
        mock_repo = MockRepository()
        # 添加5个预测
        for i in range(1, 6):
            mock_repo._data[str(i)] = MockPrediction(id=i, user_id=i, match_id=100 + i)
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions?limit=2&offset=1")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total"] == 2  # 只返回2条
        assert len(_data["predictions"]) == 2

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_prediction_success(self, mock_repo_dep, client):
        """测试：成功获取单个预测"""
        # Given
        mock_repo = MockRepository()
        _prediction = MockPrediction(id=1, user_id=1, match_id=123)
        mock_repo._data["1"] = prediction
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions/1")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["id"] == 1
        assert _data["user_id"] == 1
        assert _data["match_id"] == 123
        assert "confidence" in _data

        assert "strategy_used" in _data

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_prediction_not_found(self, mock_repo_dep, client):
        """测试：获取不存在的预测"""
        # Given
        mock_repo = MockRepository()
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions/999")

        # Then
        assert response.status_code == 404
        assert "预测不存在" in response.json()["detail"]

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_user_prediction_statistics(self, mock_repo_dep, client):
        """测试：获取用户预测统计"""
        # Given
        mock_repo = MockRepository()
        # 添加用户1的3个预测
        for i in range(3):
            pred = MockPrediction(
                id=i + 1, user_id=1, match_id=100 + i, confidence=0.8 + i * 0.05
            )
            mock_repo._data[str(i + 1)] = pred
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions/user/1/statistics")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["user_id"] == 1
        assert _data["total_predictions"] == 3
        assert "average_confidence" in _data

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_get_user_prediction_statistics_with_period(self, mock_repo_dep, client):
        """测试：获取用户预测统计（指定时间范围）"""
        # Given
        mock_repo = MockRepository()
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions/user/1/statistics?days=7")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["period_days"] == 7

    def test_get_predictions_invalid_limit(self, client):
        """测试：无效的限制参数"""
        # When
        response = client.get("/repositories/predictions?limit=0")

        # Then - FastAPI会自动验证
        assert response.status_code == 422

    def test_get_predictions_invalid_offset(self, client):
        """测试：无效的偏移量参数"""
        # When
        response = client.get("/repositories/predictions?offset=-1")

        # Then - FastAPI会自动验证
        assert response.status_code == 422

    def test_get_predictions_invalid_period_days(self, client):
        """测试：无效的统计天数"""
        # When
        response = client.get("/repositories/predictions/user/1/statistics?days=0")

        # Then - FastAPI会自动验证
        assert response.status_code == 422


class TestRepositoryEdgeCases:
    """仓储边界条件测试"""

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_empty_predictions_list(self, mock_repo_dep, client):
        """测试：空的预测列表"""
        # Given
        mock_repo = MockRepository()
        mock_repo._data = {}  # 空数据
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total"] == 0
        assert _data["predictions"] == []

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_predictions_with_no_filters(self, mock_repo_dep, client):
        """测试：没有过滤器的预测列表"""
        # Given
        mock_repo = MockRepository()
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert "total" in _data

        assert "predictions" in _data

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_predictions_beyond_limit(self, mock_repo_dep, client):
        """测试：超出数据量的查询"""
        # Given
        mock_repo = MockRepository()
        # 只添加2个预测
        for i in range(2):
            mock_repo._data[str(i + 1)] = MockPrediction(id=i + 1)
        mock_repo_dep.return_value = mock_repo

        # When - 请求10个
        response = client.get("/repositories/predictions?limit=10")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total"] == 2  # 只返回实际存在的数量

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_predictions_offset_beyond_data(self, mock_repo_dep, client):
        """测试：偏移量超出数据范围"""
        # Given
        mock_repo = MockRepository()
        # 只添加2个预测
        for i in range(2):
            mock_repo._data[str(i + 1)] = MockPrediction(id=i + 1)
        mock_repo_dep.return_value = mock_repo

        # When - 偏移10个
        response = client.get("/repositories/predictions?offset=10")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total"] == 0  # 空列表

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_repository_exception_handling(self, mock_repo_dep, client):
        """测试：仓储异常处理"""
        # Given
        mock_repo = MockRepository()
        mock_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions/1")

        # Then
        assert response.status_code == 500

    @patch("src.api.repositories.ReadOnlyPredictionRepoDep")
    def test_statistics_for_user_with_no_predictions(self, mock_repo_dep, client):
        """测试：没有预测的用户统计"""
        # Given
        mock_repo = MockRepository()
        mock_repo_dep.return_value = mock_repo

        # When
        response = client.get("/repositories/predictions/user/999/statistics")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["total_predictions"] == 0
        assert _data["average_confidence"] == 0
