#!/usr/bin/env python3
"""
Unit tests for predictions API module.

Tests for src/api/predictions.py module functions and endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.api.predictions import (
    get_match_prediction,
    predict_match,
    batch_predict_matches,
    get_match_prediction_history,
    get_recent_predictions,
    verify_prediction
)


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_match():
    """Mock match data."""
    match = MagicMock()
    match.id = 1
    match.home_team_id = 1
    match.away_team_id = 2
    match.league_id = 1
    match.match_time = datetime.now()
    match.match_status = "scheduled"
    match.season = "2024-25"
    return match


@pytest.fixture
def mock_prediction():
    """Mock prediction data."""
    from types import SimpleNamespace

    prediction = SimpleNamespace()
    prediction.id = 1
    prediction.match_id = 1
    prediction.home_win_probability = 0.6
    prediction.draw_probability = 0.25
    prediction.away_win_probability = 0.15
    prediction.predicted_result = "home"
    prediction.confidence_score = 0.85
    prediction.model_version = "xgboost_v1.0"
    prediction.model_name = "XGBoost Classifier"
    prediction.created_at = datetime.now()
    prediction.is_correct = None
    prediction.actual_result = None

    return prediction


@pytest.fixture
def mock_prediction_service():
    """Mock prediction service."""
    service = MagicMock()

    # Mock async method with to_dict()
    class MockPredictionResult:
        def to_dict(self):
            return {
                "match_id": 1,
                "home_win_prob": 0.6,
                "draw_prob": 0.25,
                "away_win_prob": 0.15,
                "predicted_goals": {"home": 2.1, "away": 1.2},
                "confidence": 0.85
            }

    # Mock async methods
    service.predict_match = AsyncMock(return_value=MockPredictionResult())

    # Mock batch predict results with to_dict() method
    class MockBatchResult:
        def __init__(self, match_id, success=True):
            self.match_id = match_id
            self.success = success

        def to_dict(self):
            return {
                "match_id": self.match_id,
                "success": self.success,
                "prediction": {"home_win_prob": 0.6} if self.success else None
            }

    service.batch_predict_matches = AsyncMock(return_value=[
        MockBatchResult(1, True),
        MockBatchResult(2, True),
        MockBatchResult(3, True)
    ])

    return service


class TestGetMatchPrediction:
    """Test cases for get_match_prediction function."""

    @pytest.mark.asyncio
    async def test_get_match_prediction_success(self, mock_session, mock_prediction, mock_match):
        """Test successful match prediction retrieval."""
        # Setup mocks - need to mock both match and prediction queries
        call_count = 0

        def mock_execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            # First call should be for Match, second for Prediction
            if call_count == 1:
                # Match query
                result.scalar_one_or_none.return_value = mock_match
            else:
                # Prediction query
                result.scalar_one_or_none.return_value = mock_prediction

            return result

        mock_session.execute.side_effect = mock_execute_side_effect

        # Execute function
        result = await get_match_prediction(1, False, mock_session)

        # Verify result
        assert result["success"] is True
        assert result["data"]["match_id"] == 1
        assert result["data"]["prediction"]["home_win_probability"] == 0.6
        assert result["data"]["prediction"]["draw_probability"] == 0.25
        assert result["data"]["prediction"]["away_win_probability"] == 0.15
        assert result["data"]["source"] == "cached"

    @pytest.mark.asyncio
    async def test_get_match_prediction_not_found(self, mock_session):
        """Test match prediction retrieval when match not found."""
        # Setup mocks - match not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect HTTPException
        with pytest.raises(Exception) as exc_info:
            await get_match_prediction(999, False, mock_session)

        # Check that it's an HTTPException with 404 status
        assert "比赛 999 不存在" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_match_prediction_database_error(self, mock_session):
        """Test match prediction retrieval with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = Exception("Database connection error")

        # Execute function and expect HTTPException
        with pytest.raises(Exception) as exc_info:
            await get_match_prediction(1, False, mock_session)

        # Check that it's an HTTPException with 500 status
        assert "获取预测结果失败" in str(exc_info.value)


class TestPredictMatch:
    """Test cases for predict_match function."""

    @pytest.mark.asyncio
    async def test_predict_match_success(self, mock_session, mock_match, mock_prediction_service):
        """Test successful match prediction."""
        # Setup mocks
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        with patch('src.api.predictions.prediction_service', mock_prediction_service):
            # Execute function
            result = await predict_match(1, session=mock_session)

            # Verify result
            assert result["success"] is True
            assert result["data"]["match_id"] == 1
            assert "home_win_prob" in result["data"]
            assert "draw_prob" in result["data"]
            assert "away_win_prob" in result["data"]

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self, mock_session):
        """Test match prediction when match not found."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await predict_match(999, session=mock_session)

    @pytest.mark.asyncio
    async def test_predict_match_already_completed(self, mock_session):
        """Test match prediction when match is already completed."""
        # Setup mocks
        completed_match = MagicMock()
        completed_match.status = "completed"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = completed_match
        mock_session.execute.return_value = mock_result

        # Execute function and expect exception
        with pytest.raises(Exception):
            await predict_match(1, session=mock_session)

    @pytest.mark.asyncio
    async def test_predict_match_service_error(self, mock_session, mock_match):
        """Test match prediction with service error."""
        # Setup mocks
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        with patch('src.api.predictions.prediction_service') as mock_service:
            mock_service.predict_match.side_effect = Exception("Prediction service error")

            # Execute function and expect exception
            with pytest.raises(Exception):
                await predict_match(1, mock_session)


class TestBatchPredictMatches:
    """Test cases for batch_predict_matches function."""

    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(self, mock_session, mock_prediction_service):
        """Test successful batch match prediction."""
        # Setup match IDs list
        match_ids = [1, 2, 3]

        # Mock database query to return valid match IDs
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [
            MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)
        ]
        mock_session.execute.return_value = mock_matches_result

        with patch('src.api.predictions.prediction_service', mock_prediction_service):
            # Execute function
            result = await batch_predict_matches(match_ids, mock_session)

            # Verify result
            assert result["success"] is True
            assert "predictions" in result["data"]
            assert len(result["data"]["predictions"]) == 3

    @pytest.mark.asyncio
    async def test_batch_predict_matches_empty_request(self, mock_session):
        """Test batch match prediction with empty request."""
        # Setup empty match IDs list
        match_ids = []

        # Execute function
        result = await batch_predict_matches(match_ids, mock_session)

        # Verify result
        assert result["success"] is True
        assert len(result["data"]["predictions"]) == 0

    @pytest.mark.asyncio
    async def test_batch_predict_matches_partial_failure(self, mock_session, mock_prediction_service):
        """Test batch match prediction with partial failures."""
        # Setup match IDs list
        match_ids = [1, 2, 3]

        # Mock database query to return valid match IDs
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [
            MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)
        ]
        mock_session.execute.return_value = mock_matches_result

        # Setup mock service to return mixed results
        mock_prediction_service.batch_predict_matches.return_value = [
            {"match_id": 1, "success": True, "prediction": {}},
            {"match_id": 2, "success": False, "error": "Match not found"},
            {"match_id": 3, "success": True, "prediction": {}}
        ]

        with patch('src.api.predictions.prediction_service', mock_prediction_service):
            # Execute function
            result = await batch_predict_matches(match_ids, mock_session)

            # Verify result
            assert result["success"] is True
            assert len(result["data"]["predictions"]) == 3
            # Should include both successful and failed predictions

    @pytest.mark.asyncio
    async def test_batch_predict_matches_service_error(self, mock_session):
        """Test batch match prediction with service error."""
        # Setup match IDs list
        match_ids = [1, 2, 3]

        # Mock database query to return valid match IDs
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [
            MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)
        ]
        mock_session.execute.return_value = mock_matches_result

        with patch('src.api.predictions.prediction_service') as mock_service:
            mock_service.batch_predict_matches.side_effect = Exception("Service unavailable")

            # Execute function and expect exception
            with pytest.raises(Exception):
                await batch_predict_matches(match_ids, mock_session)


class TestGetMatchPredictionHistory:
    """Test cases for get_match_prediction_history function."""

    @pytest.mark.asyncio
    async def test_get_prediction_history_success(self, mock_session, mock_prediction):
        """Test successful prediction history retrieval."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_prediction]
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_match_prediction_history(1, 10, mock_session)

        # Verify result
        assert result["success"] is True
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        assert result["data"][0]["match_id"] == 1

    @pytest.mark.asyncio
    async def test_get_prediction_history_empty(self, mock_session):
        """Test prediction history retrieval with no history."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_match_prediction_history(1, 10, mock_session)

        # Verify result
        assert result["success"] is True
        assert len(result["data"]) == 0

    @pytest.mark.asyncio
    async def test_get_prediction_history_with_limit(self, mock_session, mock_prediction):
        """Test prediction history retrieval with custom limit."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_prediction]
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_match_prediction_history(1, 5, mock_session)

        # Verify result
        assert result["success"] is True
        assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_prediction_history_database_error(self, mock_session):
        """Test prediction history retrieval with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = Exception("Database error")

        # Execute function and expect exception
        with pytest.raises(Exception):
            await get_match_prediction_history(1, 10, mock_session)


class TestGetRecentPredictions:
    """Test cases for get_recent_predictions function."""

    @pytest.mark.asyncio
    async def test_get_recent_predictions_success(self, mock_session, mock_prediction):
        """Test successful recent predictions retrieval."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_prediction]
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_recent_predictions(24, 10, mock_session)

        # Verify result
        assert result["success"] is True
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_recent_predictions_empty(self, mock_session):
        """Test recent predictions retrieval with no predictions."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_recent_predictions(24, 50, mock_session)

        # Verify result
        assert result["success"] is True
        assert len(result["data"]) == 0

    @pytest.mark.asyncio
    async def test_get_recent_predictions_default_limit(self, mock_session, mock_prediction):
        """Test recent predictions retrieval with default limit."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_prediction]
        mock_session.execute.return_value = mock_result

        # Execute function
        result = await get_recent_predictions(24, 50, mock_session)

        # Verify result
        assert result["success"] is True
        assert len(result["data"]) == 1


class TestVerifyPrediction:
    """Test cases for verify_prediction function."""

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, mock_session, mock_prediction):
        """Test successful prediction verification."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prediction
        mock_session.execute.return_value = mock_result

        # Setup verification data
        verification_data = {
            "actual_home_score": 2,
            "actual_away_score": 1,
            "actual_result": "home_win"
        }

        # Execute function
        result = await verify_prediction(1, mock_session, verification_data)

        # Verify result
        assert result["success"] is True
        assert result["data"]["match_id"] == 1
        assert "verification_result" in result["data"]

    @pytest.mark.asyncio
    async def test_verify_prediction_not_found(self, mock_session):
        """Test prediction verification when prediction not found."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Setup verification data
        verification_data = {
            "actual_home_score": 2,
            "actual_away_score": 1,
            "actual_result": "home_win"
        }

        # Execute function and expect exception
        with pytest.raises(Exception):
            await verify_prediction(999, mock_session, verification_data)

    @pytest.mark.asyncio
    async def test_verify_prediction_invalid_data(self, mock_session, mock_prediction):
        """Test prediction verification with invalid data."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prediction
        mock_session.execute.return_value = mock_result

        # Setup invalid verification data
        verification_data = {
            "actual_home_score": "invalid",  # Should be number
            "actual_away_score": 1,
            "actual_result": "home_win"
        }

        # Execute function and expect exception
        with pytest.raises(Exception):
            await verify_prediction(1, mock_session, verification_data)


class TestPredictionsAPIModule:
    """Test cases for predictions API module imports and configuration."""

    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        from src.api import predictions
        assert hasattr(predictions, 'get_match_prediction')
        assert hasattr(predictions, 'predict_match')
        assert hasattr(predictions, 'batch_predict_matches')
        assert hasattr(predictions, 'get_match_prediction_history')
        assert hasattr(predictions, 'get_recent_predictions')
        assert hasattr(predictions, 'verify_prediction')
        assert hasattr(predictions, 'router')

    def test_router_configuration(self):
        """Test that the router is properly configured."""
        from src.api import predictions
        assert predictions.router is not None
        assert predictions.router.prefix == "/predictions"
        assert "predictions" in predictions.router.tags

    def test_logger_exists(self):
        """Test that the logger is properly configured."""
        from src.api import predictions
        from src.api.predictions import logger
        assert logger is not None

    def test_prediction_service_import(self):
        """Test that prediction service can be imported."""
        from src.api import predictions
        # The service might be None if not properly initialized
        assert hasattr(predictions, 'prediction_service')

    @pytest.mark.asyncio
    async def test_force_predict_flag(self, mock_session, mock_match, mock_prediction_service):
        """Test force_predict parameter functionality."""
        # Setup mocks with both match and prediction
        call_count = 0

        def mock_execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_match
            else:
                result.scalar_one_or_none.return_value = mock_match  # Return match for both calls

            return result

        mock_session.execute.side_effect = mock_execute_side_effect

        with patch('src.api.predictions.prediction_service', mock_prediction_service):
            # Test with force_predict=True
            result = await get_match_prediction(1, True, mock_session)

            assert result["success"] is True
            assert result["data"]["source"] == "real_time"

            # Verify prediction service was called
            mock_prediction_service.predict_match.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_match_already_completed_error(self, mock_session, mock_prediction_service):
        """Test error when trying to predict completed match."""
        # Setup completed match
        completed_match = MagicMock()
        completed_match.id = 1
        completed_match.home_team_id = 1
        completed_match.away_team_id = 2
        completed_match.league_id = 1
        completed_match.match_time = datetime.now()
        completed_match.match_status = "finished"  # Completed status
        completed_match.season = "2024-25"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = completed_match
        mock_session.execute.return_value = mock_result

        with patch('src.api.predictions.prediction_service', mock_prediction_service):
            # Test with force_predict=True on completed match
            with pytest.raises(Exception) as exc_info:
                await get_match_prediction(1, True, mock_session)

            assert "已结束" in str(exc_info.value)
            assert "无法生成预测" in str(exc_info.value)

            # Verify prediction service was not called
            mock_prediction_service.predict_match.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_predict_matches_limit_validation(self, mock_session):
        """Test batch prediction limit validation."""
        # Test with too many match IDs (over 50 limit)
        too_many_ids = list(range(1, 52))  # 51 IDs

        with pytest.raises(Exception) as exc_info:
            await batch_predict_matches(too_many_ids, mock_session)

        assert "最多支持50场比赛" in str(exc_info.value)

        # Test with exactly 50 IDs (should work)
        valid_ids = list(range(1, 51))  # 50 IDs

        # Mock database query to return valid match IDs
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [
            MagicMock(id=i) for i in valid_ids
        ]
        mock_session.execute.return_value = mock_matches_result

        with patch('src.api.predictions.prediction_service') as mock_service:
            mock_service.batch_predict_matches.return_value = []

            # Should not raise exception
            result = await batch_predict_matches(valid_ids, mock_session)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_recent_predictions_time_range(self, mock_session, mock_prediction):
        """Test recent predictions with custom time range."""
        # Setup mock data
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_prediction]
        mock_session.execute.return_value = mock_result

        # Test with custom hours and limit
        result = await get_recent_predictions(48, 25, mock_session)

        assert result["success"] is True
        assert result["data"]["time_range_hours"] == 48
        assert isinstance(result["data"]["total_predictions"], int)
        assert "predictions" in result["data"]

    @pytest.mark.asyncio
    async def test_verify_prediction_success_case(self, mock_session, mock_prediction_service):
        """Test successful prediction verification."""
        # Setup prediction service to return success
        mock_prediction_service.verify_prediction.return_value = True

        result = await verify_prediction(1, mock_session)

        assert result["success"] is True
        assert result["data"]["match_id"] == 1
        assert result["data"]["verified"] is True
        assert "预测结果验证完成" in result["message"]

        # Verify service was called
        mock_prediction_service.verify_prediction.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_verify_prediction_failure_case(self, mock_session, mock_prediction_service):
        """Test failed prediction verification."""
        # Setup prediction service to return failure
        mock_prediction_service.verify_prediction.return_value = False

        result = await verify_prediction(1, mock_session)

        assert result["success"] is False
        assert result["data"]["match_id"] == 1
        assert result["data"]["verified"] is False
        assert "预测结果验证失败" in result["message"]