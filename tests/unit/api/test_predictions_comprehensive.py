import os
"""
预测API端点测试 / Tests for Prediction API Endpoints

测试覆盖：
- 获取比赛预测结果
- 实时生成预测
- 批量预测接口
- 获取历史预测
- 验证预测结果
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.predictions import router
from src.database.models import Match, Prediction
from src.models.prediction_service import PredictionService


class TestPredictionAPI:
    """预测API测试类"""

    @pytest.fixture
    def mock_match(self):
        """模拟比赛数据"""
        match = MagicMock()
        match.id = 12345
        match.home_team_id = 10
        match.away_team_id = 20
        match.league_id = 1
        match.match_time = datetime.now() + timedelta(days=1)
        match.match_status = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MATCH_STATUS_33")
        match.season = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_SEASON_33")
        return match

    @pytest.fixture
    def mock_prediction(self):
        """模拟预测数据"""
        prediction = MagicMock()
        prediction.id = 1
        prediction.match_id = 12345
        prediction.model_version = "1.0"
        prediction.model_name = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_42")
        prediction.home_win_probability = 0.45
        prediction.draw_probability = 0.30
        prediction.away_win_probability = 0.25
        prediction.predicted_result = "home"
        prediction.confidence_score = 0.45
        prediction.created_at = datetime.now()
        prediction.is_correct = None
        prediction.actual_result = None
        prediction.verified_at = None
        return prediction

    @pytest.fixture
    def mock_prediction_result(self):
        """模拟预测服务结果"""
        result = MagicMock()
        result.to_dict.return_value = {
            "id": 2,
            "match_id": 12345,
            "model_version": "1.0",
            "model_name": "baseline",
            "home_win_probability": 0.45,
            "draw_probability": 0.30,
            "away_win_probability": 0.25,
            "predicted_result": "home",
            "confidence_score": 0.45,
            "created_at": datetime.now().isoformat(),
        }
        return result

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    @patch('src.api.predictions.prediction_service')
    async def test_get_match_prediction_cached(
        self, mock_service, mock_select, mock_match, mock_prediction
    ):
        """测试获取缓存的预测结果"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.side_effect = [mock_match, mock_prediction]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.predictions import get_match_prediction
        response = await get_match_prediction(12345, False, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["match_id"] == 12345
        assert response["data"]["source"] == "cached"
        assert "prediction" in response["data"]
        assert "match_info" in response["data"]

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    @patch('src.api.predictions.prediction_service')
    async def test_get_match_prediction_realtime(
        self, mock_service, mock_select, mock_match, mock_prediction_result
    ):
        """测试实时生成预测"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.side_effect = [mock_match, None]  # 没有缓存预测
        mock_session.execute.return_value = mock_result
        mock_service.predict_match.return_value = mock_prediction_result

        # 执行测试
        from src.api.predictions import get_match_prediction
        response = await get_match_prediction(12345, False, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["match_id"] == 12345
        assert response["data"]["source"] == "real_time"
        assert "prediction" in response["data"]
        mock_service.predict_match.assert_called_once_with(12345)

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    async def test_get_match_not_found(self, mock_select):
        """测试比赛不存在的情况"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None  # 比赛不存在
        mock_session.execute.return_value = mock_result

        # 执行测试并验证异常
        from src.api.predictions import get_match_prediction
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(99999, False, mock_session)

        assert exc_info.value.status_code == 404
        assert "99999 不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    @patch('src.api.predictions.prediction_service')
    async def test_predict_match(
        self, mock_service, mock_select, mock_match, mock_prediction_result
    ):
        """测试实时预测接口"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result
        mock_service.predict_match.return_value = mock_prediction_result

        # 执行测试
        from src.api.predictions import predict_match
        response = await predict_match(12345, mock_session)

        # 验证结果
        assert response["success"] is True
        assert "预测完成" in response["message"]
        assert "data" in response

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    @patch('src.api.predictions.prediction_service')
    async def test_batch_predict_matches(
        self, mock_service, mock_select, mock_match
    ):
        """测试批量预测接口"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        # 模拟查询返回有效的比赛ID
        mock_result.scalars.return_value.all.return_value = [12345, 12346]
        mock_session.execute.return_value = mock_result

        # 模拟批量预测结果
        mock_prediction = MagicMock()
        mock_prediction.to_dict.return_value = {"match_id": 12345}
        mock_service.batch_predict_matches.return_value = [mock_prediction]

        # 执行测试
        from src.api.predictions import batch_predict_matches
        response = await batch_predict_matches([12345, 12346], mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["total_requested"] == 2
        assert response["data"]["valid_matches"] == 2
        assert "predictions" in response["data"]

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    async def test_batch_predict_too_many_matches(self, mock_select):
        """测试批量预测超过限制"""
        from src.api.predictions import batch_predict_matches
        from fastapi import HTTPException

        # 创建超过50个比赛ID的列表
        too_many_matches = list(range(1, 60))

        # 执行测试并验证异常
        mock_session = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await batch_predict_matches(too_many_matches, mock_session)

        assert exc_info.value.status_code == 400
        assert "最多支持50场比赛" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    async def test_get_match_prediction_history(
        self, mock_select, mock_match
    ):
        """测试获取历史预测"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # 第一次查询返回比赛信息，第二次返回历史预测
        mock_prediction = MagicMock()
        mock_prediction.id = 1
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_42")
        mock_prediction.home_win_probability = 0.45
        mock_prediction.draw_probability = 0.30
        mock_prediction.away_win_probability = 0.25
        mock_prediction.predicted_result = "home"
        mock_prediction.confidence_score = 0.45
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = True
        mock_prediction.actual_result = "home"
        mock_prediction.verified_at = datetime.now()

        mock_result.scalar_one_or_none.return_value = mock_match
        mock_result.scalars.return_value.all.return_value = [mock_prediction]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.predictions import get_match_prediction_history
        response = await get_match_prediction_history(12345, 10, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["match_id"] == 12345
        assert response["data"]["total_predictions"] == 1
        assert len(response["data"]["predictions"]) == 1

    @pytest.mark.asyncio
    @patch('src.api.predictions.select')
    async def test_get_recent_predictions(self, mock_select):
        """测试获取最近预测"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # 模拟查询结果
        mock_pred = MagicMock()
        mock_pred.id = 1
        mock_pred.match_id = 12345
        mock_pred.model_version = "1.0"
        mock_pred.model_name = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_42")
        mock_pred.predicted_result = "home"
        mock_pred.confidence_score = 0.45
        mock_pred.created_at = datetime.now()
        mock_pred.is_correct = True
        mock_pred.home_team_id = 10
        mock_pred.away_team_id = 20
        mock_pred.match_time = datetime.now()
        mock_pred.match_status = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MATCH_STATUS_267")

        mock_result.fetchall.return_value = [mock_pred]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.predictions import get_recent_predictions
        response = await get_recent_predictions(24, 50, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["time_range_hours"] == 24
        assert response["data"]["total_predictions"] == 1
        assert len(response["data"]["predictions"]) == 1

    @pytest.mark.asyncio
    @patch('src.api.predictions.prediction_service')
    async def test_verify_prediction_success(self, mock_service):
        """测试验证预测结果成功"""
        # 设置模拟
        mock_service.verify_prediction.return_value = True
        mock_session = AsyncMock()

        # 执行测试
        from src.api.predictions import verify_prediction
        response = await verify_prediction(12345, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["verified"] is True
        assert "验证完成" in response["message"]

    @pytest.mark.asyncio
    @patch('src.api.predictions.prediction_service')
    async def test_verify_prediction_failure(self, mock_service):
        """测试验证预测结果失败"""
        # 设置模拟
        mock_service.verify_prediction.return_value = False
        mock_session = AsyncMock()

        # 执行测试
        from src.api.predictions import verify_prediction
        response = await verify_prediction(12345, mock_session)

        # 验证结果
        assert response["success"] is False
        assert response["data"]["verified"] is False
        assert "验证失败" in response["message"]