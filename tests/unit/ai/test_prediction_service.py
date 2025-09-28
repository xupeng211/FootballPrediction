"""
Unit tests for prediction service functionality.

Tests the PredictionService class methods including:
- Model loading and caching
- Match prediction logic
- Feature preparation and validation
- Result storage and verification
- Error handling and edge cases
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import numpy as np
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.prediction_service import PredictionService, PredictionResult


class TestPredictionResult:
    """Test cases for PredictionResult dataclass."""

    def test_prediction_result_creation(self):
        """Test PredictionResult creation with all fields."""
        result = PredictionResult(
            match_id=12345,
            model_version="1.0",
            model_name="test_model",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.5,
            features_used={"feature1": 1.0},
            prediction_metadata={"test": "metadata"},
            created_at=datetime.now(),
            actual_result="home",
            is_correct=True,
            verified_at=datetime.now()
        )

        assert result.match_id == 12345
        assert result.model_version == "1.0"
        assert result.predicted_result == "home"
        assert result.is_correct is True

    def test_prediction_result_to_dict(self):
        """Test PredictionResult to_dict conversion."""
        created_at = datetime.now()
        verified_at = datetime.now()

        result = PredictionResult(
            match_id=12345,
            model_version="1.0",
            created_at=created_at,
            verified_at=verified_at
        )

        result_dict = result.to_dict()

        assert result_dict["match_id"] == 12345
        assert result_dict["created_at"] == created_at.isoformat()
        assert result_dict["verified_at"] == verified_at.isoformat()

    def test_prediction_result_defaults(self):
        """Test PredictionResult default values."""
        result = PredictionResult(
            match_id=12345,
            model_version="1.0"
        )

        assert result.home_win_probability == 0.0
        assert result.draw_probability == 0.0
        assert result.away_win_probability == 0.0
        assert result.predicted_result == "draw"
        assert result.confidence_score == 0.0
        assert result.model_name == "football_baseline_model"

    @pytest.mark.asyncio
    async def test_probability_distribution_validation(self):
        """Test that probabilities sum to approximately 1.0."""
        # Test valid probability distribution
        result = PredictionResult(
            match_id=12345,
            model_version="1.0",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2
        )

        total_prob = result.home_win_probability + result.draw_probability + result.away_win_probability
        assert abs(total_prob - 1.0) < 0.001  # Allow small floating point errors

        # Test invalid probability distribution (should be caught by validation)
        with pytest.raises(AssertionError):
            # This would be caught in actual validation logic
            invalid_result = PredictionResult(
                match_id=12345,
                model_version="1.0",
                home_win_probability=0.8,
                draw_probability=0.8,
                away_win_probability=0.8
            )
            total_prob = invalid_result.home_win_probability + invalid_result.draw_probability + invalid_result.away_win_probability
            assert abs(total_prob - 1.0) < 0.001  # This should fail


class TestPredictionService:
    """Test cases for PredictionService class."""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock DatabaseManager."""
        mock_db = MagicMock()
        mock_db.get_async_session.return_value.__aenter__ = AsyncMock()
        mock_db.get_async_session.return_value.__aexit__ = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_feature_store(self):
        """Mock FootballFeatureStore."""
        mock_store = MagicMock()
        mock_store.get_match_features_for_prediction = AsyncMock()
        return mock_store

    @pytest.fixture
    def mock_metrics_exporter(self):
        """Mock ModelMetricsExporter."""
        mock_exporter = MagicMock()
        mock_exporter.model_load_duration = MagicMock()
        mock_exporter.prediction_duration = MagicMock()
        mock_exporter.export_prediction_metrics = MagicMock()
        return mock_exporter

    @pytest.fixture
    def mock_cache(self):
        """Mock TTLCache."""
        mock_cache = MagicMock()
        mock_cache.get = MagicMock()
        mock_cache.set = MagicMock()
        return mock_cache

    @pytest.fixture
    def service(self, mock_db_manager, mock_feature_store, mock_metrics_exporter):
        """Create PredictionService instance with mocked dependencies."""
        with patch('src.models.prediction_service.DatabaseManager', return_value=mock_db_manager), \
             patch('src.models.prediction_service.FootballFeatureStore', return_value=mock_feature_store), \
             patch('src.models.prediction_service.ModelMetricsExporter', return_value=mock_metrics_exporter), \
             patch('src.models.prediction_service.TTLCache') as mock_cache_class:

            # Setup cache mocks
            mock_cache1 = MagicMock()
            mock_cache2 = MagicMock()
            mock_cache_class.side_effect = [mock_cache1, mock_cache2]  # model_cache and prediction_cache

            service = PredictionService()
            service.db_manager = mock_db_manager
            service.feature_store = mock_feature_store
            service.metrics_exporter = mock_metrics_exporter
            service.model_cache = mock_cache1
            service.prediction_cache = mock_cache2

            return service

    @pytest.fixture
    def sample_match_info(self):
        """Sample match information for testing."""
        return {
            "id": 12345,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "match_time": datetime(2024, 1, 1),
            "match_status": "scheduled",
            "season": "2024"
        }

    @pytest.fixture
    def sample_features(self):
        """Sample features for prediction."""
        return {
            "home_recent_wins": 3,
            "home_recent_goals_for": 8,
            "home_recent_goals_against": 4,
            "away_recent_wins": 2,
            "away_recent_goals_for": 5,
            "away_recent_goals_against": 5,
            "h2h_home_advantage": 0.6,
            "home_implied_probability": 0.45,
            "draw_implied_probability": 0.30,
            "away_implied_probability": 0.25
        }

    @pytest.fixture
    def mock_model(self):
        """Mock trained model."""
        mock_model = MagicMock()
        # Mock predict_proba to return probability distribution
        mock_model.predict_proba.return_value = np.array([[0.2, 0.3, 0.5]])  # [away, draw, home]
        mock_model.predict.return_value = np.array(["home"])
        return mock_model

    class TestModelLoading:
        """Test cases for model loading functionality."""

        @pytest.mark.asyncio
        @patch('src.models.prediction_service.mlflow')
        async def test_get_production_model_success(self, mock_mlflow, service, mock_model):
            """Test successful production model loading."""
            # Setup mocks
            mock_client = MagicMock()
            mock_mlflow.MlflowClient.return_value = mock_client
            mock_mlflow.sklearn.load_model.return_value = mock_model

            # Mock production version
            mock_client.get_latest_versions.return_value = [
                MagicMock(version="1", stage="Production")
            ]

            # Test cache miss
            service.model_cache.get.return_value = None

            model, version = await service.get_production_model()

            # Verify model was loaded and cached
            assert model is mock_model
            assert version == "1"
            mock_mlflow.sklearn.load_model.assert_called_once_with("models:/football_baseline_model/1")
            service.model_cache.set.assert_called_once()

        @pytest.mark.asyncio
        @patch('src.models.prediction_service.mlflow')
        async def test_get_production_model_cache_hit(self, mock_mlflow, service, mock_model):
            """Test production model loading with cache hit."""
            # Setup cached result
            service.model_cache.get.return_value = (mock_model, "1")

            model, version = await service.get_production_model()

            # Should return cached result without loading
            assert model is mock_model
            assert version == "1"
            mock_mlflow.sklearn.load_model.assert_not_called()

        @pytest.mark.asyncio
        @patch('src.models.prediction_service.mlflow')
        async def test_get_production_model_fallback_to_staging(self, mock_mlflow, service, mock_model):
            """Test model loading fallback to staging when production unavailable."""
            mock_client = MagicMock()
            mock_mlflow.MlflowClient.return_value = mock_client
            mock_mlflow.sklearn.load_model.return_value = mock_model

            # No production version, but staging available
            mock_client.get_latest_versions.side_effect = [
                [],  # No production versions
                [MagicMock(version="2", stage="Staging")]  # Staging version available
            ]

            service.model_cache.get.return_value = None

            model, version = await service.get_production_model()

            # Should use staging version
            assert model is mock_model
            assert version == "2"

        @pytest.mark.asyncio
        @patch('src.models.prediction_service.mlflow')
        async def test_get_production_model_no_versions_available(self, mock_mlflow, service):
            """Test model loading when no versions are available."""
            mock_client = MagicMock()
            mock_mlflow.MlflowClient.return_value = mock_client

            # No versions available
            mock_client.get_latest_versions.return_value = []

            service.model_cache.get.return_value = None

            with pytest.raises(ValueError, match="模型 football_baseline_model 没有可用版本"):
                await service.get_production_model()

        @pytest.mark.asyncio
        @patch('src.models.prediction_service.mlflow')
        async def test_get_production_model_with_retry(self, mock_mlflow, service, mock_model):
            """Test model loading with retry mechanism."""
            mock_client = MagicMock()
            mock_mlflow.MlflowClient.return_value = mock_client
            mock_mlflow.sklearn.load_model.return_value = mock_model

            mock_client.get_latest_versions.return_value = [
                MagicMock(version="1", stage="Production")
            ]

            service.model_cache.get.return_value = None

            # Test retry mechanism
            model, version = await service.get_production_model_with_retry()

            assert model is mock_model
            assert version == "1"

    class TestMatchPrediction:
        """Test cases for match prediction functionality."""

        @pytest.mark.asyncio
        async def test_predict_match_success(self, service, sample_match_info, sample_features, mock_model):
            """Test successful match prediction."""
            # Setup mocks
            service.model_cache.get.return_value = None
            service.prediction_cache.get.return_value = None

            with patch.object(service, 'get_production_model', return_value=(mock_model, "1")), \
                 patch.object(service, '_get_match_info', return_value=sample_match_info), \
                 patch.object(service.feature_store, 'get_match_features_for_prediction', return_value=sample_features), \
                 patch.object(service, '_store_prediction') as mock_store:

                result = await service.predict_match(12345)

            # Verify prediction result
            assert isinstance(result, PredictionResult)
            assert result.match_id == 12345
            assert result.model_version == "1"
            assert result.predicted_result == "home"
            assert result.confidence_score == 0.5  # Max probability

            # Verify probability distribution
            assert abs(result.home_win_probability + result.draw_probability + result.away_win_probability - 1.0) < 0.001
            assert result.features_used == sample_features

            # Verify storage and caching
            mock_store.assert_called_once()
            service.prediction_cache.set.assert_called_once()

        @pytest.mark.asyncio
        async def test_predict_match_cache_hit(self, service, mock_model):
            """Test match prediction with cache hit."""
            # Setup cached result
            cached_result = PredictionResult(
                match_id=12345,
                model_version="1",
                predicted_result="home",
                confidence_score=0.8
            )
            service.prediction_cache.get.return_value = cached_result

            result = await service.predict_match(12345)

            # Should return cached result
            assert result is cached_result
            # Should not call prediction logic
            with patch.object(service, 'get_production_model') as mock_get_model:
                await service.predict_match(12345)
                mock_get_model.assert_not_called()

        @pytest.mark.asyncio
        async def test_predict_match_feature_service_fallback(self, service, sample_match_info, mock_model):
            """Test match prediction with feature service fallback."""
            service.model_cache.get.return_value = None
            service.prediction_cache.get.return_value = None

            with patch.object(service, 'get_production_model', return_value=(mock_model, "1")), \
                 patch.object(service, '_get_match_info', return_value=sample_match_info), \
                 patch.object(service, '_store_prediction'), \
                 patch.object(service.feature_store, 'get_match_features_for_prediction', side_effect=Exception("Feature error")):

                result = await service.predict_match(12345)

            # Should use default features
            assert result.features_used is not None
            assert "home_recent_wins" in result.features_used

        @pytest.mark.asyncio
        async def test_predict_match_nonexistent_match(self, service, mock_model):
            """Test match prediction for nonexistent match."""
            service.model_cache.get.return_value = None
            service.prediction_cache.get.return_value = None

            with patch.object(service, 'get_production_model', return_value=(mock_model, "1")), \
                 patch.object(service, '_get_match_info', return_value=None):

                with pytest.raises(ValueError, match="比赛 12345 不存在"):
                    await service.predict_match(12345)

    class TestFeaturePreparation:
        """Test cases for feature preparation functionality."""

        def test_prepare_features_for_prediction_success(self, service, sample_features):
            """Test successful feature preparation."""
            features_array = service._prepare_features_for_prediction(sample_features)

            # Verify array shape and type
            assert isinstance(features_array, np.ndarray)
            assert features_array.shape == (1, len(service.feature_order))

            # Verify feature order is preserved
            expected_order = [
                "home_recent_wins", "home_recent_goals_for", "home_recent_goals_against",
                "away_recent_wins", "away_recent_goals_for", "away_recent_goals_against",
                "h2h_home_advantage", "home_implied_probability", "draw_implied_probability", "away_implied_probability"
            ]

            # Check that all expected features are present
            for i, feature_name in enumerate(expected_order):
                assert features_array[0][i] == float(sample_features.get(feature_name, 0.0))

        def test_prepare_features_for_prediction_missing_features(self, service):
            """Test feature preparation with missing features."""
            incomplete_features = {
                "home_recent_wins": 3,
                "away_recent_wins": 2
                # Missing other features
            }

            features_array = service._prepare_features_for_prediction(incomplete_features)

            # Missing features should be filled with 0.0
            assert features_array[0][0] == 3.0  # home_recent_wins
            assert features_array[0][3] == 2.0  # away_recent_wins
            assert features_array[0][1] == 0.0  # missing home_recent_goals_for

        def test_get_default_features(self, service):
            """Test default features generation."""
            default_features = service._get_default_features()

            # Verify default features structure
            assert isinstance(default_features, dict)
            assert "home_recent_wins" in default_features
            assert "away_recent_wins" in default_features
            assert "h2h_home_advantage" in default_features

            # Verify probability distribution sums to 1.0
            prob_sum = (default_features.get("home_implied_probability", 0) +
                       default_features.get("draw_implied_probability", 0) +
                       default_features.get("away_implied_probability", 0))
            assert abs(prob_sum - 1.0) < 0.001

    class TestMatchInfoRetrieval:
        """Test cases for match information retrieval."""

        @pytest.mark.asyncio
        async def test_get_match_info_success(self, service, sample_match_info):
            """Test successful match info retrieval."""
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(**sample_match_info)
            mock_session.execute.return_value = mock_result
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await service._get_match_info(12345)

            # Verify match info structure
            assert result is not None
            assert result["id"] == 12345
            assert result["home_team_id"] == 101
            assert result["away_team_id"] == 102

        @pytest.mark.asyncio
        async def test_get_match_info_not_found(self, service):
            """Test match info retrieval for nonexistent match."""
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = None
            mock_session.execute.return_value = mock_result
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await service._get_match_info(99999)

            # Should return None for nonexistent match
            assert result is None

    class TestPredictionStorage:
        """Test cases for prediction storage functionality."""

        @pytest.mark.asyncio
        async def test_store_prediction_success(self, service):
            """Test successful prediction storage."""
            prediction_result = PredictionResult(
                match_id=12345,
                model_version="1",
                predicted_result="home",
                confidence_score=0.8,
                created_at=datetime.now()
            )

            mock_session = AsyncMock()
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            await service._store_prediction(prediction_result)

            # Verify database operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

        @pytest.mark.asyncio
        async def test_store_prediction_database_error(self, service):
            """Test prediction storage with database error."""
            prediction_result = PredictionResult(
                match_id=12345,
                model_version="1",
                predicted_result="home",
                confidence_score=0.8
            )

            mock_session = AsyncMock()
            mock_session.add.side_effect = Exception("Database error")
            mock_session.rollback = AsyncMock()
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            with pytest.raises(Exception, match="Database error"):
                await service._store_prediction(prediction_result)

            # Verify rollback was called
            mock_session.rollback.assert_called_once()

    class TestPredictionVerification:
        """Test cases for prediction verification functionality."""

        @pytest.mark.asyncio
        async def test_verify_prediction_success(self, service):
            """Test successful prediction verification."""
            mock_session = AsyncMock()

            # Mock match query result
            mock_match_result = MagicMock()
            mock_match_result.first.return_value = MagicMock(
                home_score=2, away_score=1, match_status="completed"
            )

            # Mock update query result
            mock_update_result = MagicMock()

            mock_session.execute.side_effect = [mock_match_result, mock_update_result]
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await service.verify_prediction(12345)

            # Verify verification was successful
            assert result is True
            mock_session.commit.assert_called_once()

        @pytest.mark.asyncio
        async def test_verify_prediction_match_not_completed(self, service):
            """Test prediction verification for incomplete match."""
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = None  # No completed match found
            mock_session.execute.return_value = mock_result
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await service.verify_prediction(12345)

            # Should return False for incomplete match
            assert result is False

        def test_calculate_actual_result(self, service):
            """Test actual result calculation."""
            # Test home win
            assert service._calculate_actual_result(2, 1) == "home"

            # Test away win
            assert service._calculate_actual_result(1, 2) == "away"

            # Test draw
            assert service._calculate_actual_result(1, 1) == "draw"

    class TestBatchPrediction:
        """Test cases for batch prediction functionality."""

        @pytest.mark.asyncio
        async def test_batch_predict_matches_success(self, service, mock_model):
            """Test successful batch prediction."""
            service.model_cache.get.return_value = None

            with patch.object(service, 'get_production_model', return_value=(mock_model, "1")), \
                 patch.object(service, 'predict_match') as mock_predict:

                # Mock individual predictions
                mock_predict.side_effect = [
                    PredictionResult(match_id=1, model_version="1", predicted_result="home"),
                    PredictionResult(match_id=2, model_version="1", predicted_result="away"),
                    PredictionResult(match_id=3, model_version="1", predicted_result="draw")
                ]

                results = await service.batch_predict_matches([1, 2, 3])

            # Verify results
            assert len(results) == 3
            assert results[0].match_id == 1
            assert results[1].match_id == 2
            assert results[2].match_id == 3

            # Verify model was loaded only once
            service.get_production_model.assert_called_once()

        @pytest.mark.asyncio
        async def test_batch_predict_mixed_success_failure(self, service, mock_model):
            """Test batch prediction with mixed success and failure."""
            service.model_cache.get.return_value = None

            with patch.object(service, 'get_production_model', return_value=(mock_model, "1")), \
                 patch.object(service, 'predict_match') as mock_predict:

                # Mock mixed results
                mock_predict.side_effect = [
                    PredictionResult(match_id=1, model_version="1", predicted_result="home"),
                    Exception("Prediction failed"),
                    PredictionResult(match_id=3, model_version="1", predicted_result="draw")
                ]

                results = await service.batch_predict_matches([1, 2, 3])

            # Should return successful predictions only
            assert len(results) == 2
            assert results[0].match_id == 1
            assert results[1].match_id == 3

    class TestModelAccuracy:
        """Test cases for model accuracy calculation."""

        @pytest.mark.asyncio
        async def test_get_model_accuracy_success(self, service):
            """Test successful model accuracy retrieval."""
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                total=100, correct=75
            )
            mock_session.execute.return_value = mock_result
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            accuracy = await service.get_model_accuracy("test_model", 7)

            # Verify accuracy calculation
            assert accuracy == 0.75

        @pytest.mark.asyncio
        async def test_get_model_accuracy_no_data(self, service):
            """Test model accuracy retrieval with no verification data."""
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = None
            mock_session.execute.return_value = mock_result
            service.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            accuracy = await service.get_model_accuracy("test_model", 7)

            # Should return None when no data available
            assert accuracy is None