"""预测API单元测试（简化版）"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession


class TestPredictionsAPI:
    """预测API测试"""

    @pytest.mark.asyncio
    async def test_get_match_prediction_success(self, api_client):
        """测试获取比赛预测成功 - 使用mock session"""

        # Mock the entire get_async_session dependency
        @patch("src.api.predictions.get_async_session")
        async def test_with_mock_session(mock_get_session):
            # Create a mock session
            mock_session = MagicMock(spec=AsyncSession)

            # Mock the match
            mock_match = MagicMock()
            mock_match.id = 12345
            mock_match.home_team_id = 10
            mock_match.away_team_id = 20
            mock_match.league_id = 1
            mock_match.match_time = "2025-09-15T15:00:00"
            mock_match.match_status = "scheduled"
            mock_match.season = "2024-25"

            # Mock the prediction
            mock_prediction = MagicMock()
            mock_prediction.id = 1
            mock_prediction.model_version = "1.0"
            mock_prediction.model_name = "test_model"
            mock_prediction.predicted_result = "home_win"
            mock_prediction.home_win_probability = 0.45
            mock_prediction.draw_probability = 0.30
            mock_prediction.away_win_probability = 0.25
            mock_prediction.confidence_score = 0.75
            mock_prediction.created_at = "2025-09-14T10:00:00"
            mock_prediction.is_correct = None
            mock_prediction.actual_result = None

            # Setup mock results
            mock_match_result = MagicMock()
            mock_match_result.scalar_one_or_none.return_value = mock_match

            mock_prediction_result = MagicMock()
            mock_prediction_result.scalar_one_or_none.return_value = mock_prediction

            # Mock session.execute to return different results
            mock_session.execute.side_effect = [
                mock_match_result,  # First query: match
                mock_prediction_result,  # Second query: prediction
            ]

            # Mock the async context manager
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_session_cm():
                yield mock_session

            mock_get_session.return_value = mock_session_cm()

            # Make request
            response = api_client.get("/api/v1/predictions/12345")

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["match_id"] == 12345
            assert data["data"]["source"] == "cached"

        # Run the test
        await test_with_mock_session()

    @pytest.mark.asyncio
    async def test_get_match_prediction_not_found(self, api_client):
        """测试获取不存在的比赛预测"""

        # Mock the entire get_async_session dependency
        @patch("src.api.predictions.get_async_session")
        async def test_with_mock_session(mock_get_session):
            # Create a mock session
            mock_session = MagicMock(spec=AsyncSession)

            # Mock no match found
            mock_match_result = MagicMock()
            mock_match_result.scalar_one_or_none.return_value = None

            mock_session.execute.return_value = mock_match_result

            # Mock the async context manager
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_session_cm():
                yield mock_session

            mock_get_session.return_value = mock_session_cm()

            # Make request
            response = api_client.get("/api/v1/predictions/99999")

            # Verify response
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "比赛 99999 不存在" in data["detail"]

        # Run the test
        await test_with_mock_session()

    @pytest.mark.asyncio
    async def test_predict_match_success(self, api_client):
        """测试实时预测比赛成功"""
        # Mock the dependencies
        with patch("src.api.predictions.prediction_service") as mock_service, patch(
            "src.api.predictions.get_async_session"
        ) as mock_get_session:

            # Create a mock session
            mock_session = MagicMock(spec=AsyncSession)

            # Mock the match
            mock_match = MagicMock()
            mock_match.id = 12345

            mock_match_result = MagicMock()
            mock_match_result.scalar_one_or_none.return_value = mock_match

            mock_session.execute.return_value = mock_match_result

            # Mock the async context manager
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_session_cm():
                yield mock_session

            mock_get_session.return_value = mock_session_cm()

            # Mock prediction service
            mock_prediction_data = MagicMock()
            mock_prediction_data.to_dict.return_value = {
                "model_version": "1.0",
                "predicted_result": "home_win",
                "confidence_score": 0.75,
            }

            mock_service.predict_match = AsyncMock(return_value=mock_prediction_data)

            # Make request
            response = api_client.post("/api/v1/predictions/12345/predict")

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "比赛 12345 预测完成" in data["message"]
            assert data["data"]["model_version"] == "1.0"

    def test_batch_predict_too_many_matches(self, api_client):
        """测试批量预测比赛数量超过限制"""
        # Create 51 match IDs (exceeding the 50 limit)
        match_ids = list(range(1, 52))

        # Make request
        response = api_client.post(
            "/api/v1/predictions/batch",
            json=match_ids,
        )

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "批量预测最多支持50场比赛" in data["detail"]

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, api_client):
        """测试验证预测成功"""
        # Mock the prediction service
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=True)

            # Make request
            response = api_client.post("/api/v1/predictions/12345/verify")

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["match_id"] == 12345
            assert data["data"]["verified"] is True
            assert "预测结果验证完成" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_failure(self, api_client):
        """测试验证预测失败"""
        # Mock the prediction service
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=False)

            # Make request
            response = api_client.post("/api/v1/predictions/12345/verify")

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert data["data"]["verified"] is False
            assert "验证失败" in data["message"]
