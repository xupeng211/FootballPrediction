"""
Prediction API单元测试 / Unit Tests for Prediction API

测试预测相关的API端点功能，包括：
- 获取比赛预测结果（缓存和实时生成）
- 实时预测比赛结果
- 批量预测
- 获取历史预测
- 获取最近预测
- 验证预测结果

Tests prediction-related API endpoints, including:
- Get match prediction (cached and real-time)
- Real-time match prediction
- Batch prediction
- Get prediction history
- Get recent predictions
- Verify prediction results
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 禁用 slowapi 限流
os.environ["RATE_LIMIT_AVAILABLE"] = "False"

# 重新导入模块以确保限流被禁用
if "src.api.predictions" in sys.modules:
    del sys.modules["src.api.predictions"]

from src.database.models import Match, MatchStatus, PredictedResult
from src.database.models import Predictions as Prediction


class TestPredictionAPI:
    """Prediction API测试类"""

    @pytest.mark.asyncio
    async def test_get_match_prediction_cached_success(self, api_client_full):
        """测试获取比赛预测结果 - 缓存命中成功"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_match.match_status = MatchStatus.SCHEDULED
        mock_match.season = "2024-25"

        # 创建mock预测
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = 1
        mock_prediction.match_id = 12345
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = "linear_regression"
        mock_prediction.predicted_result = PredictedResult.HOME_WIN
        mock_prediction.home_win_probability = 0.45
        mock_prediction.draw_probability = 0.30
        mock_prediction.away_win_probability = 0.25
        mock_prediction.confidence_score = 0.75
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = None
        mock_prediction.actual_result = None

        # 配置数据库查询结果
        # 第一次查询：获取比赛
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match

        # 第二次查询：获取预测
        prediction_result = MagicMock()
        prediction_result.scalar_one_or_none.return_value = mock_prediction

        mock_session.execute.side_effect = [match_result, prediction_result]

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/12345")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["match_id"] == 12345
        assert data["data"]["source"] == "cached"
        assert "match_info" in data["data"]
        assert "prediction" in data["data"]
        assert data["data"]["prediction"]["model_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_match_prediction_force_predict(self, api_client_full):
        """测试获取比赛预测结果 - 强制重新预测"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_match.match_status = MatchStatus.SCHEDULED
        mock_match.season = "2024-25"

        # 创建mock预测结果
        mock_prediction_result = MagicMock()
        mock_prediction_result.to_dict.return_value = {
            "id": 2,
            "model_version": "2.0",
            "model_name": "xgboost",
            "predicted_result": "home",
            "home_win_probability": 0.55,
            "draw_probability": 0.25,
            "away_win_probability": 0.20,
            "confidence_score": 0.80,
            "created_at": datetime.now().isoformat(),
        }

        # 配置数据库查询结果 - 只有比赛查询
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = match_result

        # Mock预测服务
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.predict_match = AsyncMock(return_value=mock_prediction_result)

            # 发送请求 - 强制重新预测
            response = api_client_full.get("/api/v1/predictions/12345?force_predict=true")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["source"] == "real_time"
            assert data["data"]["prediction"]["model_version"] == "2.0"

    @pytest.mark.asyncio
    async def test_get_match_prediction_match_not_found(self, api_client_full):
        """测试获取比赛预测结果 - 比赛不存在"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询结果 - 比赛不存在
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = match_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/99999")

        # 验证响应 - 使用项目自定义的错误响应格式
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 404
        assert "比赛 99999 不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_prediction_match_finished(self, api_client_full):
        """测试获取比赛预测结果 - 比赛已结束"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛 - 已结束
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime(2025, 9, 10, 15, 0, 0)
        mock_match.match_status = MatchStatus.FINISHED
        mock_match.season = "2024-25"

        # 配置数据库查询结果
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = match_result

        # 发送请求 - 强制预测已结束的比赛
        response = api_client_full.get("/api/v1/predictions/12345?force_predict=true")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 400
        assert "已结束，无法生成预测" in data["message"]

    @pytest.mark.asyncio
    async def test_predict_match_success(self, api_client_full):
        """测试实时预测比赛结果 - 成功"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20

        # 创建mock预测结果
        mock_prediction_result = MagicMock()
        mock_prediction_result.to_dict.return_value = {
            "id": 3,
            "model_version": "3.0",
            "model_name": "neural_network",
            "predicted_result": "draw",
            "home_win_probability": 0.35,
            "draw_probability": 0.40,
            "away_win_probability": 0.25,
            "confidence_score": 0.70,
            "created_at": datetime.now().isoformat(),
        }

        # 配置数据库查询结果
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = match_result

        # Mock预测服务
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.predict_match = AsyncMock(return_value=mock_prediction_result)

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/predict")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "比赛 12345 预测完成" in data["message"]
            assert data["data"]["model_version"] == "3.0"

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self, api_client_full):
        """测试实时预测比赛结果 - 比赛不存在"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询结果 - 比赛不存在
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = match_result

        # 发送请求
        response = api_client_full.post("/api/v1/predictions/99999/predict")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 404
        assert "比赛 99999 不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(self, api_client_full):
        """测试批量预测比赛 - 成功"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛ID列表
        match_ids = [12345, 12346, 12347]

        # 配置数据库查询结果 - 所有比赛都存在
        # 直接返回模拟的Row对象列表
        mock_row_1 = MagicMock()
        mock_row_1.id = 12345
        mock_row_2 = MagicMock()
        mock_row_2.id = 12346
        mock_row_3 = MagicMock()
        mock_row_3.id = 12347

        valid_matches_result = MagicMock()
        valid_matches_result.__iter__ = MagicMock(
            return_value=iter([mock_row_1, mock_row_2, mock_row_3])
        )
        mock_session.execute.return_value = valid_matches_result

        # 创建mock预测结果
        mock_prediction_1 = MagicMock()
        mock_prediction_1.to_dict.return_value = {
            "id": 1,
            "match_id": 12345,
            "model_version": "1.0",
        }

        mock_prediction_2 = MagicMock()
        mock_prediction_2.to_dict.return_value = {
            "id": 2,
            "match_id": 12346,
            "model_version": "1.0",
        }

        mock_prediction_3 = MagicMock()
        mock_prediction_3.to_dict.return_value = {
            "id": 3,
            "match_id": 12347,
            "model_version": "1.0",
        }

        # Mock预测服务
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.batch_predict_matches = AsyncMock(
                return_value=[mock_prediction_1, mock_prediction_2, mock_prediction_3]
            )

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/batch", json=match_ids)

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_requested"] == 3
            assert data["data"]["valid_matches"] == 3
            assert data["data"]["successful_predictions"] == 3
            assert len(data["data"]["predictions"]) == 3

    @pytest.mark.asyncio
    async def test_batch_predict_matches_partial_invalid(self, api_client_full):
        """测试批量预测比赛 - 部分无效比赛ID"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛ID列表 - 包含无效ID
        match_ids = [12345, 99999, 12346]

        # 配置数据库查询结果 - 只有部分比赛存在
        # 直接返回模拟的Row对象列表
        mock_row_1 = MagicMock()
        mock_row_1.id = 12345
        mock_row_2 = MagicMock()
        mock_row_2.id = 12346

        valid_matches_result = MagicMock()
        valid_matches_result.__iter__ = MagicMock(return_value=iter([mock_row_1, mock_row_2]))
        mock_session.execute.return_value = valid_matches_result

        # 创建mock预测结果
        mock_prediction_1 = MagicMock()
        mock_prediction_1.to_dict.return_value = {
            "id": 1,
            "match_id": 12345,
            "model_version": "1.0",
        }

        mock_prediction_2 = MagicMock()
        mock_prediction_2.to_dict.return_value = {
            "id": 2,
            "match_id": 12346,
            "model_version": "1.0",
        }

        # Mock预测服务
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.batch_predict_matches = AsyncMock(
                return_value=[mock_prediction_1, mock_prediction_2]
            )

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/batch", json=match_ids)

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_requested"] == 3
            assert data["data"]["valid_matches"] == 2
            assert data["data"]["successful_predictions"] == 2
            assert 99999 in data["data"]["invalid_match_ids"]
            assert len(data["data"]["predictions"]) == 2

    @pytest.mark.asyncio
    async def test_batch_predict_matches_too_many(self, api_client_full):
        """测试批量预测比赛 - 超过限制"""
        # 创建超过限制的比赛ID列表
        match_ids = list(range(1, 52))  # 51个ID，超过50个限制

        # 发送请求
        response = api_client_full.post("/api/v1/predictions/batch", json=match_ids)

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 400
        assert "批量预测最多支持50场比赛" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_success(self, api_client_full):
        """测试获取比赛历史预测 - 成功"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345

        # 创建mock历史预测
        mock_prediction_1 = MagicMock(spec=Prediction)
        mock_prediction_1.id = 1
        mock_prediction_1.model_version = "1.0"
        mock_prediction_1.model_name = "linear_regression"
        mock_prediction_1.predicted_result = PredictedResult.HOME_WIN
        mock_prediction_1.home_win_probability = 0.45
        mock_prediction_1.draw_probability = 0.30
        mock_prediction_1.away_win_probability = 0.25
        mock_prediction_1.confidence_score = 0.75
        mock_prediction_1.created_at = datetime.now()
        mock_prediction_1.is_correct = True
        mock_prediction_1.actual_result = PredictedResult.HOME_WIN
        mock_prediction_1.verified_at = datetime.now()

        mock_prediction_2 = MagicMock(spec=Prediction)
        mock_prediction_2.id = 2
        mock_prediction_2.model_version = "2.0"
        mock_prediction_2.model_name = "xgboost"
        mock_prediction_2.predicted_result = PredictedResult.HOME_WIN
        mock_prediction_2.home_win_probability = 0.50
        mock_prediction_2.draw_probability = 0.30
        mock_prediction_2.away_win_probability = 0.20
        mock_prediction_2.confidence_score = 0.80
        mock_prediction_2.created_at = datetime.now() - timedelta(hours=1)
        mock_prediction_2.is_correct = None
        mock_prediction_2.actual_result = None
        mock_prediction_2.verified_at = None

        # 配置数据库查询结果
        # 第一次查询：获取比赛
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match

        # 第二次查询：获取历史预测
        history_result = MagicMock()
        history_result.scalars.return_value.all.return_value = [
            mock_prediction_1,
            mock_prediction_2,
        ]

        mock_session.execute.side_effect = [match_result, history_result]

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/history/12345?limit=5")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["match_id"] == 12345
        assert data["data"]["total_predictions"] == 2
        assert len(data["data"]["predictions"]) == 2
        assert data["data"]["predictions"][0]["model_version"] == "1.0"
        assert data["data"]["predictions"][1]["model_version"] == "2.0"

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_match_not_found(self, api_client_full):
        """测试获取比赛历史预测 - 比赛不存在"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询结果 - 比赛不存在
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = match_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/history/99999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 404
        assert "比赛 99999 不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_recent_predictions_success(self, api_client_full):
        """测试获取最近预测 - 成功"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock最近预测记录
        mock_pred_1 = MagicMock()
        mock_pred_1.id = 1
        mock_pred_1.match_id = 12345
        mock_pred_1.model_version = "1.0"
        mock_pred_1.model_name = "linear_regression"
        mock_pred_1.predicted_result = PredictedResult.HOME_WIN
        mock_pred_1.confidence_score = 0.75
        mock_pred_1.created_at = datetime.now()
        mock_pred_1.is_correct = None
        mock_pred_1.home_team_id = 10
        mock_pred_1.away_team_id = 20
        mock_pred_1.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_pred_1.match_status = MatchStatus.SCHEDULED

        mock_pred_2 = MagicMock()
        mock_pred_2.id = 2
        mock_pred_2.match_id = 12346
        mock_pred_2.model_version = "2.0"
        mock_pred_2.model_name = "xgboost"
        mock_pred_2.predicted_result = PredictedResult.DRAW
        mock_pred_2.confidence_score = 0.80
        mock_pred_2.created_at = datetime.now() - timedelta(hours=2)
        mock_pred_2.is_correct = True
        mock_pred_2.home_team_id = 11
        mock_pred_2.away_team_id = 21
        mock_pred_2.match_time = datetime(2025, 9, 14, 15, 0, 0)
        mock_pred_2.match_status = MatchStatus.FINISHED

        # 配置数据库查询结果
        recent_result = MagicMock()
        recent_result.fetchall.return_value = [mock_pred_1, mock_pred_2]
        mock_session.execute.return_value = recent_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/recent?hours=24&limit=10")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["time_range_hours"] == 24
        assert data["data"]["total_predictions"] == 2
        assert len(data["data"]["predictions"]) == 2
        assert data["data"]["predictions"][0]["match_id"] == 12345
        assert data["data"]["predictions"][1]["match_id"] == 12346

    @pytest.mark.asyncio
    async def test_get_recent_predictions_empty(self, api_client_full):
        """测试获取最近预测 - 无预测记录"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询结果 - 无预测记录
        recent_result = MagicMock()
        recent_result.fetchall.return_value = []
        mock_session.execute.return_value = recent_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/recent?hours=1")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_predictions"] == 0
        assert len(data["data"]["predictions"]) == 0

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, api_client_full):
        """测试验证预测结果 - 成功"""
        # Mock预测服务
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=True)

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["match_id"] == 12345
            assert data["data"]["verified"] is True
            assert "预测结果验证完成" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_failure(self, api_client_full):
        """测试验证预测结果 - 失败"""
        # Mock预测服务
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=False)

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # 验证响应
            assert response.status_code == 200  # API返回成功，但验证失败
            data = response.json()
            assert data["success"] is False  # 业务逻辑失败
            assert data["data"]["match_id"] == 12345
            assert data["data"]["verified"] is False
            assert "预测结果验证失败" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_prediction_server_error(self, api_client_full):
        """测试获取比赛预测结果 - 服务器错误"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询抛出异常
        mock_session.execute.side_effect = Exception("数据库连接错误")

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/12345")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 500
        assert "获取预测结果失败" in data["message"]

    @pytest.mark.asyncio
    async def test_predict_match_server_error(self, api_client_full):
        """测试实时预测比赛结果 - 服务器错误"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询抛出异常
        mock_session.execute.side_effect = Exception("预测服务错误")

        # 发送请求
        response = api_client_full.post("/api/v1/predictions/12345/predict")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 500
        assert "预测失败" in data["message"]

    @pytest.mark.asyncio
    async def test_batch_predict_server_error(self, api_client_full):
        """测试批量预测比赛 - 服务器错误"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询抛出异常
        mock_session.execute.side_effect = Exception("批量预测服务错误")

        # 发送请求
        response = api_client_full.post("/api/v1/predictions/batch", json=[12345, 12346])

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 500
        assert "批量预测失败" in data["message"]

    @pytest.mark.asyncio
    async def test_get_prediction_history_server_error(self, api_client_full):
        """测试获取比赛历史预测 - 服务器错误"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询抛出异常
        mock_session.execute.side_effect = Exception("历史查询错误")

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/history/12345")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 500
        assert "获取历史预测失败" in data["message"]

    @pytest.mark.asyncio
    async def test_get_recent_predictions_server_error(self, api_client_full):
        """测试获取最近预测 - 服务器错误"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询抛出异常
        mock_session.execute.side_effect = Exception("最近预测查询错误")

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/recent")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 500
        assert "获取最近预测失败" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_server_error(self, api_client_full):
        """测试验证预测结果 - 服务器错误"""
        # Mock预测服务抛出异常
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(side_effect=Exception("验证服务错误"))

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # 验证响应
            assert response.status_code == 500
            data = response.json()
            assert data["error"] is True
            assert data["status_code"] == 500
            assert "验证预测结果失败" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_prediction_invalid_match_id(self, api_client_full):
        """测试获取比赛预测结果 - 不存在的比赛ID"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 配置数据库查询结果 - 比赛不存在
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = match_result

        # 发送请求 - 使用一个不存在的正数ID
        response = api_client_full.get("/api/v1/predictions/99998")

        # 验证响应 - 应该返回404，因为比赛不存在
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 404
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_prediction_with_probability_none(self, api_client_full):
        """测试获取比赛预测结果 - 概率为None值"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_match.match_status = MatchStatus.SCHEDULED
        mock_match.season = "2024-25"

        # 创建mock预测 - 概率为None
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = 1
        mock_prediction.match_id = 12345
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = "linear_regression"
        mock_prediction.predicted_result = PredictedResult.HOME_WIN
        mock_prediction.home_win_probability = None  # None值
        mock_prediction.draw_probability = None  # None值
        mock_prediction.away_win_probability = None  # None值
        mock_prediction.confidence_score = None  # None值
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = None
        mock_prediction.actual_result = None

        # 配置数据库查询结果
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match

        prediction_result = MagicMock()
        prediction_result.scalar_one_or_none.return_value = mock_prediction

        mock_session.execute.side_effect = [match_result, prediction_result]

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/12345")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["prediction"]["home_win_probability"] == 0.0  # 默认值
        assert data["data"]["prediction"]["draw_probability"] == 0.0  # 默认值
        assert data["data"]["prediction"]["away_win_probability"] == 0.0  # 默认值
        assert data["data"]["prediction"]["confidence_score"] == 0.0  # 默认值

    @pytest.mark.asyncio
    async def test_get_prediction_history_limit_validation(self, api_client_full):
        """测试获取比赛历史预测 - 限制参数验证"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock比赛
        mock_match = MagicMock(spec=Match)
        mock_match.id = 12345

        # 创建mock历史预测
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = 1
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = "linear_regression"
        mock_prediction.predicted_result = PredictedResult.HOME_WIN
        mock_prediction.home_win_probability = 0.45
        mock_prediction.draw_probability = 0.30
        mock_prediction.away_win_probability = 0.25
        mock_prediction.confidence_score = 0.75
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = True
        mock_prediction.actual_result = PredictedResult.HOME_WIN
        mock_prediction.verified_at = datetime.now()

        # 配置数据库查询结果
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = mock_match

        history_result = MagicMock()
        history_result.scalars.return_value.all.return_value = [mock_prediction]

        mock_session.execute.side_effect = [match_result, history_result]

        # 发送请求 - 使用最小限制
        response = api_client_full.get("/api/v1/predictions/history/12345?limit=1")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_predictions"] == 1

    @pytest.mark.asyncio
    async def test_get_recent_predictions_parameter_validation(self, api_client_full):
        """测试获取最近预测 - 参数验证"""
        # 配置mock数据库会话
        mock_session = api_client_full.mock_session

        # 创建mock最近预测记录
        mock_pred = MagicMock()
        mock_pred.id = 1
        mock_pred.match_id = 12345
        mock_pred.model_version = "1.0"
        mock_pred.model_name = "linear_regression"
        mock_pred.predicted_result = PredictedResult.HOME_WIN
        mock_pred.confidence_score = 0.75
        mock_pred.created_at = datetime.now()
        mock_pred.is_correct = None
        mock_pred.home_team_id = 10
        mock_pred.away_team_id = 20
        mock_pred.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_pred.match_status = MatchStatus.SCHEDULED

        # 配置数据库查询结果
        recent_result = MagicMock()
        recent_result.fetchall.return_value = [mock_pred]
        mock_session.execute.return_value = recent_result

        # 发送请求 - 使用最大参数值
        response = api_client_full.get("/api/v1/predictions/recent?hours=168&limit=200")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["time_range_hours"] == 168
        assert data["data"]["total_predictions"] == 1
