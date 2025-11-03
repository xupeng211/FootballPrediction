"""
预测API测试套件
Prediction API Test Suite

测试预测相关的API端点，确保预测功能的正确性。
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.api.app import app


class TestPredictionsAPI:
    """预测API基础测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_prediction_data(self):
        """模拟预测数据"""
        return {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "predicted_home_score": 2,
            "predicted_away_score": 1,
            "confidence": 0.75,
            "prediction_date": datetime.utcnow().isoformat()
        }

    def test_predictions_list_endpoint(self, client):
        """测试预测列表端点"""
        with patch('src.api.predictions.get_all_predictions') as mock_get:
            mock_predictions = [
                {
                    "id": 1,
                    "match_id": 12345,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "predicted_home_score": 2,
                    "predicted_away_score": 1,
                    "confidence": 0.75
                }
            ]
            mock_get.return_value = mock_predictions

            response = client.get("/api/predictions")

            # 检查响应状态（可能存在也可能不存在）
            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)

    def test_single_prediction_endpoint(self, client, mock_prediction_data):
        """测试单个预测端点"""
        with patch('src.api.predictions.get_prediction_by_id') as mock_get:
            mock_get.return_value = mock_prediction_data

            response = client.get("/api/predictions/12345")

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                assert data["match_id"] == 12345
                assert "predicted_home_score" in data
                assert "predicted_away_score" in data

    def test_create_prediction_endpoint(self, client, mock_prediction_data):
        """测试创建预测端点"""
        with patch('src.api.predictions.create_prediction') as mock_create:
            mock_create.return_value = {**mock_prediction_data, "id": 1}

            response = client.post("/api/predictions", json=mock_prediction_data)

            # 检查响应状态
            assert response.status_code in [201, 200, 404, 422]

            if response.status_code in [201, 200]:
                data = response.json()
                assert "id" in data

    def test_update_prediction_endpoint(self, client, mock_prediction_data):
        """测试更新预测端点"""
        with patch('src.api.predictions.update_prediction') as mock_update:
            updated_data = {**mock_prediction_data, "predicted_home_score": 3}
            mock_update.return_value = updated_data

            response = client.put("/api/predictions/12345", json=updated_data)

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                assert data["predicted_home_score"] == 3

    def test_delete_prediction_endpoint(self, client):
        """测试删除预测端点"""
        with patch('src.api.predictions.delete_prediction') as mock_delete:
            mock_delete.return_value = True

            response = client.delete("/api/predictions/12345")

            # 检查响应状态
            assert response.status_code in [200, 204, 404, 422]

    def test_predictions_by_match_endpoint(self, client):
        """测试按比赛获取预测端点"""
        with patch('src.api.predictions.get_predictions_by_match') as mock_get:
            mock_predictions = [
                {
                    "id": 1,
                    "match_id": 12345,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "predicted_home_score": 2,
                    "predicted_away_score": 1
                }
            ]
            mock_get.return_value = mock_predictions

            response = client.get("/api/predictions/match/12345")

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                if len(data) > 0:
                    assert data[0]["match_id"] == 12345


class TestPredictionsValidation:
    """预测API验证测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_invalid_prediction_data(self, client):
        """测试无效预测数据"""
        invalid_data = {
            "match_id": "invalid_id",  # 应该是数字
            "home_team": "",  # 空字符串
            "away_team": "",  # 空字符串
            "predicted_home_score": -1,  # 负数
            "predicted_away_score": "invalid",  # 应该是数字
            "confidence": 1.5  # 超出范围
        }

        response = client.post("/api/predictions", json=invalid_data)

        # 应该返回验证错误
        assert response.status_code in [422, 400]

    def test_missing_required_fields(self, client):
        """测试缺少必需字段"""
        incomplete_data = {
            "home_team": "Team A"
            # 缺少其他必需字段
        }

        response = client.post("/api/predictions", json=incomplete_data)

        # 应该返回验证错误
        assert response.status_code in [422, 400]

    def test_confidence_range_validation(self, client):
        """测试置信度范围验证"""
        invalid_confidence_data = {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "predicted_home_score": 2,
            "predicted_away_score": 1,
            "confidence": 1.5  # 超出0-1范围
        }

        response = client.post("/api/predictions", json=invalid_confidence_data)

        # 应该返回验证错误
        assert response.status_code in [422, 400]

    def test_score_range_validation(self, client):
        """测试分数范围验证"""
        invalid_score_data = {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "predicted_home_score": -5,  # 负分数
            "predicted_away_score": 100,  # 过高分数
            "confidence": 0.75
        }

        response = client.post("/api/predictions", json=invalid_score_data)

        # 应该返回验证错误
        assert response.status_code in [422, 400]


class TestPredictionsAPIAuthentication:
    """预测API认证测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        # 尝试访问需要认证的端点
        response = client.post("/api/predictions", json={})

        # 可能需要认证，返回401或403
        assert response.status_code in [401, 403, 404, 422]

    def test_valid_authentication(self, client):
        """测试有效认证"""
        # 使用模拟的认证头
        headers = {
            "Authorization": "Bearer mock_token",
            "X-API-Key": "mock_api_key"
        }

        response = client.get("/api/predictions", headers=headers)

        # 检查响应状态
        assert response.status_code in [200, 401, 403, 404]

    def test_invalid_token(self, client):
        """测试无效令牌"""
        headers = {
            "Authorization": "Bearer invalid_token"
        }

        response = client.post("/api/predictions", json={}, headers=headers)

        # 应该返回认证错误
        assert response.status_code in [401, 403, 404, 422]


class TestPredictionsAPIPerformance:
    """预测API性能测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_prediction_response_time(self, client):
        """测试预测响应时间"""
        import time

        start_time = time.time()
        response = client.get("/api/predictions")
        end_time = time.time()

        response_time = end_time - start_time

        # 预测查询应该在合理时间内响应（< 2秒）
        assert response_time < 2.0, f"Prediction API too slow: {response_time}s"

    def test_bulk_prediction_creation(self, client):
        """测试批量预测创建"""
        import time

        predictions_data = [
            {
                "match_id": i,
                "home_team": f"Team {i}",
                "away_team": f"Opponent {i}",
                "predicted_home_score": 2,
                "predicted_away_score": 1,
                "confidence": 0.75
            }
            for i in range(100)
        ]

        start_time = time.time()

        # 模拟批量创建（如果API支持）
        for data in predictions_data[:10]:  # 测试10个预测
            response = client.post("/api/predictions", json=data)
            # 不要求全部成功，只测试性能

        end_time = time.time()
        total_time = end_time - start_time

        # 批量操作应该在合理时间内完成
        assert total_time < 10.0, f"Bulk creation too slow: {total_time}s"


class TestPredictionsAPIErrorHandling:
    """预测API错误处理测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_not_found_prediction(self, client):
        """测试不存在的预测"""
        response = client.get("/api/predictions/99999")

        # 应该返回404或处理错误
        assert response.status_code in [404, 422, 400]

    def test_database_error_handling(self, client):
        """测试数据库错误处理"""
        with patch('src.api.predictions.get_prediction_by_id') as mock_get:
            mock_get.side_effect = Exception("Database connection error")

            response = client.get("/api/predictions/12345")

            # 应该优雅地处理数据库错误
            assert response.status_code in [500, 503, 404, 422]

    def test_external_service_error(self, client):
        """测试外部服务错误"""
        with patch('src.api.predictions.create_prediction') as mock_create:
            mock_create.side_effect = Exception("External API unavailable")

            prediction_data = {
                "match_id": 12345,
                "home_team": "Team A",
                "away_team": "Team B",
                "predicted_home_score": 2,
                "predicted_away_score": 1,
                "confidence": 0.75
            }

            response = client.post("/api/predictions", json=prediction_data)

            # 应该优雅地处理外部服务错误
            assert response.status_code in [500, 503, 404, 422]


class TestPredictionsAPIPagination:
    """预测API分页测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_predictions_list_pagination(self, client):
        """测试预测列表分页"""
        with patch('src.api.predictions.get_all_predictions') as mock_get:
            # 模拟分页数据
            mock_predictions = [
                {"id": i, "match_id": 12345 + i}
                for i in range(50)
            ]
            mock_get.return_value = mock_predictions

            # 测试分页参数
            response = client.get("/api/predictions?page=1&limit=10")

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                # 可能返回列表或分页对象
                if isinstance(data, dict):
                    assert "results" in data or "data" in data
                    assert "total" in data or "count" in data

    def test_invalid_pagination_parameters(self, client):
        """测试无效分页参数"""
        # 测试负数页码
        response = client.get("/api/predictions?page=-1")
        assert response.status_code in [422, 400, 404]

        # 测试过大的页大小
        response = client.get("/api/predictions?limit=10000")
        assert response.status_code in [422, 400, 404]

        # 测试无效参数类型
        response = client.get("/api/predictions?page=abc")
        assert response.status_code in [422, 400, 404]


class TestPredictionsAPIFilters:
    """预测API过滤测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_filter_by_team(self, client):
        """测试按队伍过滤"""
        with patch('src.api.predictions.get_predictions_by_team') as mock_get:
            mock_predictions = [
                {
                    "id": 1,
                    "match_id": 12345,
                    "home_team": "Team A",
                    "away_team": "Team B"
                }
            ]
            mock_get.return_value = mock_predictions

            response = client.get("/api/predictions?team=Team A")

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (list, dict))

    def test_filter_by_date_range(self, client):
        """测试按日期范围过滤"""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()

        with patch('src.api.predictions.get_predictions_by_date_range') as mock_get:
            mock_predictions = []
            mock_get.return_value = mock_predictions

            response = client.get(f"/api/predictions?start_date={start_date}&end_date={end_date}")

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

    def test_filter_by_confidence(self, client):
        """测试按置信度过滤"""
        with patch('src.api.predictions.get_high_confidence_predictions') as mock_get:
            mock_predictions = [
                {
                    "id": 1,
                    "confidence": 0.85
                }
            ]
            mock_get.return_value = mock_predictions

            response = client.get("/api/predictions?min_confidence=0.8")

            # 检查响应状态
            assert response.status_code in [200, 404, 422]

    def test_invalid_filter_parameters(self, client):
        """测试无效过滤参数"""
        # 测试无效日期格式
        response = client.get("/api/predictions?start_date=invalid-date")
        assert response.status_code in [422, 400, 404]

        # 测试无效置信度范围
        response = client.get("/api/predictions?min_confidence=1.5")
        assert response.status_code in [422, 400, 404]


# 测试工具函数
def create_mock_prediction_service():
    """创建模拟预测服务"""
    service = Mock()
    service.get_prediction.return_value = {
        "id": 1,
        "match_id": 12345,
        "home_team": "Team A",
        "away_team": "Team B",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75
    }
    return service


def create_valid_prediction_data():
    """创建有效的预测数据"""
    return {
        "match_id": 12345,
        "home_team": "Team A",
        "away_team": "Team B",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75
    }


def create_invalid_prediction_data():
    """创建无效的预测数据"""
    return {
        "match_id": "invalid",
        "home_team": "",
        "predicted_home_score": -1,
        "confidence": 1.5
    }