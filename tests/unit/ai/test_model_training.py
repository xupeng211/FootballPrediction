"""
Unit tests for model training functionality.

Tests the BaselineModelTrainer class methods including:
- Training data preparation
- Model training and validation
- Model registration and MLflow integration
- Error handling and edge cases
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.model_training import BaselineModelTrainer


class TestBaselineModelTrainer:
    """Test cases for BaselineModelTrainer class."""

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
        mock_store.get_historical_features = AsyncMock()
        return mock_store

    @pytest.fixture
    def trainer(self, mock_db_manager, mock_feature_store):
        """Create BaselineModelTrainer instance with mocked dependencies."""
        with patch('src.models.model_training.DatabaseManager', return_value=mock_db_manager), \
             patch('src.models.model_training.FootballFeatureStore', return_value=mock_feature_store):
            trainer = BaselineModelTrainer()
            trainer.db_manager = mock_db_manager
            trainer.feature_store = mock_feature_store
            return trainer

    @pytest.fixture
    def sample_matches_data(self):
        """Sample historical matches data for testing."""
        return pd.DataFrame([
            {
                "id": 1,
                "home_team_id": 101,
                "away_team_id": 102,
                "league_id": 1,
                "match_time": datetime(2024, 1, 1),
                "home_score": 2,
                "away_score": 1,
                "season": "2024"
            },
            {
                "id": 2,
                "home_team_id": 103,
                "away_team_id": 104,
                "league_id": 1,
                "match_time": datetime(2024, 1, 2),
                "home_score": 1,
                "away_score": 1,
                "season": "2024"
            },
            {
                "id": 3,
                "home_team_id": 105,
                "away_team_id": 106,
                "league_id": 1,
                "match_time": datetime(2024, 1, 3),
                "home_score": 0,
                "away_score": 1,
                "season": "2024"
            }
        ])

    @pytest.fixture
    def sample_features_data(self):
        """Sample features data for testing."""
        return pd.DataFrame([
            {
                "match_id": 1,
                "team_id": 101,
                "event_timestamp": datetime(2024, 1, 1),
                "team_recent_performance:recent_5_wins": 3,
                "team_recent_performance:recent_5_goals_for": 8,
                "odds_features:home_odds_avg": 2.1,
                "odds_features:draw_odds_avg": 3.2,
                "historical_matchup:h2h_total_matches": 5
            },
            {
                "match_id": 2,
                "team_id": 103,
                "event_timestamp": datetime(2024, 1, 2),
                "team_recent_performance:recent_5_wins": 1,
                "team_recent_performance:recent_5_goals_for": 4,
                "odds_features:home_odds_avg": 1.8,
                "odds_features:draw_odds_avg": 3.5,
                "historical_matchup:h2h_total_matches": 3
            },
            {
                "match_id": 3,
                "team_id": 105,
                "event_timestamp": datetime(2024, 1, 3),
                "team_recent_performance:recent_5_wins": 0,
                "team_recent_performance:recent_5_goals_for": 2,
                "odds_features:home_odds_avg": 2.5,
                "odds_features:draw_odds_avg": 3.1,
                "historical_matchup:h2h_total_matches": 2
            }
        ])

    @pytest.fixture
    def mock_mlflow_experiment(self):
        """Mock MLflow experiment."""
        mock_exp = MagicMock()
        mock_exp.experiment_id = "test_experiment_id"
        return mock_exp

    @pytest.fixture
    def mock_mlflow_run(self):
        """Mock MLflow run."""
        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_run.info.status = "FINISHED"
        mock_run.info.start_time = datetime.now().timestamp() * 1000
        mock_run.info.end_time = (datetime.now() + timedelta(hours=1)).timestamp() * 1000
        mock_run.data.metrics = {
            "test_accuracy": 0.75,
            "test_precision": 0.73,
            "test_recall": 0.75,
            "test_f1": 0.74
        }
        mock_run.data.params = {
            "n_estimators": "100",
            "max_depth": "6"
        }
        mock_run.data.tags = {
            "model_type": "XGBoost",
            "purpose": "football_match_prediction"
        }
        return mock_run

    class TestTrainingDataPreparation:
        """Test cases for training data preparation methods."""

        @pytest.mark.asyncio
        async def test_prepare_training_data_success(self, trainer, sample_matches_data, sample_features_data):
            """Test successful training data preparation."""
            # Mock database query to return sample matches
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                MagicMock(
                    id=1, home_team_id=101, away_team_id=102, league_id=1,
                    match_time=datetime(2024, 1, 1), home_score=2, away_score=1, season="2024"
                ),
                MagicMock(
                    id=2, home_team_id=103, away_team_id=104, league_id=1,
                    match_time=datetime(2024, 1, 2), home_score=1, away_score=1, season="2024"
                )
            ]
            mock_session.execute.return_value = mock_result
            trainer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            # Mock feature store to return sample features
            trainer.feature_store.get_historical_features.return_value = sample_features_data

            # Call the method
            X, y = await trainer.prepare_training_data(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                min_samples=2
            )

            # Verify results
            assert len(X) == 2  # Two matches after filtering
            assert len(y) == 2
            assert not X.isnull().any().any()  # No missing values
            assert all(result in ['home', 'draw', 'away'] for result in y)

        @pytest.mark.asyncio
        async def test_prepare_training_data_insufficient_samples(self, trainer):
            """Test training data preparation with insufficient samples."""
            # Mock database to return empty result
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_session.execute.return_value = mock_result
            trainer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            # Should raise ValueError for insufficient samples
            with pytest.raises(ValueError, match="训练数据不足"):
                await trainer.prepare_training_data(
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 1, 31),
                    min_samples=1000
                )

        @pytest.mark.asyncio
        async def test_prepare_training_data_feature_store_fallback(self, trainer, sample_matches_data):
            """Test fallback to simplified features when feature store fails."""
            # Mock database query
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                MagicMock(
                    id=1, home_team_id=101, away_team_id=102, league_id=1,
                    match_time=datetime(2024, 1, 1), home_score=2, away_score=1, season="2024"
                )
            ]
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result
            mock_session.scalars.return_value = mock_result.scalars
            trainer.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            # Mock feature store to raise exception
            trainer.feature_store.get_historical_features.side_effect = Exception("Feature store error")

            # Mock simplified features calculation
            with patch.object(trainer, '_get_simplified_features', return_value=pd.DataFrame([
                {
                    "match_id": 1,
                    "team_id": 101,
                    "event_timestamp": datetime(2024, 1, 1),
                    "home_recent_wins": 3,
                    "home_recent_goals_for": 8,
                    "home_recent_goals_against": 4,
                    "away_recent_wins": 2,
                    "away_recent_goals_for": 5,
                    "away_recent_goals_against": 5,
                    "h2h_home_advantage": 0.5
                }
            ])):
                X, y = await trainer.prepare_training_data(
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 1, 31),
                    min_samples=1
                )

            # Should use simplified features
            assert len(X) == 1
            assert len(y) == 1

        def test_calculate_match_result(self, trainer):
            """Test match result calculation."""
            # Test home win
            row = {"home_score": 2, "away_score": 1}
            assert trainer._calculate_match_result(row) == "home"

            # Test away win
            row = {"home_score": 1, "away_score": 2}
            assert trainer._calculate_match_result(row) == "away"

            # Test draw
            row = {"home_score": 1, "away_score": 1}
            assert trainer._calculate_match_result(row) == "draw"

    class TestModelTraining:
        """Test cases for model training methods."""

        @pytest.mark.asyncio
        @patch('src.models.model_training.mlflow')
        @patch('src.models.model_training.xgb')
        async def test_train_baseline_model_success(self, mock_xgb, mock_mlflow, trainer, mock_mlflow_run):
            """Test successful model training."""
            # Setup mocks
            mock_mlflow.get_experiment_by_name.return_value = None
            mock_mlflow.create_experiment.return_value = "test_exp_id"
            mock_mlflow.start_run.return_value.__enter__.return_value = mock_mlflow_run
            mock_mlflow.start_run.return_value.__exit__ = MagicMock()

            mock_model = MagicMock()
            mock_xgb.XGBClassifier.return_value = mock_model

            # Mock training data preparation
            with patch.object(trainer, 'prepare_training_data', return_value=(
                pd.DataFrame({'feature1': [1, 2], 'feature2': [3, 4]}),
                pd.Series(['home', 'away'])
            )):
                with patch('src.models.model_training.train_test_split', return_value=(
                    pd.DataFrame({'feature1': [1], 'feature2': [3]}),
                    pd.DataFrame({'feature1': [2], 'feature2': [4]}),
                    pd.Series(['home']),
                    pd.Series(['away'])
                )):
                    result = await trainer.train_baseline_model(
                        experiment_name="test_exp",
                        model_name="test_model"
                    )

            # Verify training was called
                    mock_model.fit.assert_called_once()
                    mock_model.predict.assert_called()

            # Verify result structure
            assert "run_id" in result
            assert "metrics" in result
            assert result["metrics"]["accuracy"] >= 0

        @pytest.mark.asyncio
        @patch('src.models.model_training.mlflow')
        async def test_train_baseline_model_xgboost_unavailable(self, mock_mlflow, trainer):
            """Test model training when XGBoost is not available."""
            # Mock XGBoost import failure
            with patch('src.models.model_training.HAS_XGB', False):
                with pytest.raises(ImportError, match="XGBoost not available"):
                    await trainer.train_baseline_model()

        @pytest.mark.asyncio
        @patch('src.models.model_training.mlflow')
        async def test_train_baseline_model_mlflow_experiment_error(self, mock_mlflow, trainer):
            """Test model training with MLflow experiment error."""
            # Mock MLflow to raise exception when creating experiment
            mock_mlflow.get_experiment_by_name.side_effect = Exception("MLflow error")
            mock_mlflow.create_experiment.side_effect = Exception("Create failed")

            # Should use default experiment and continue training
            with patch.object(trainer, 'prepare_training_data', return_value=(
                pd.DataFrame({'feature1': [1]}), pd.Series(['home'])
            )):
                with patch('src.models.model_training.xgb.XGBClassifier') as mock_model_class:
                    mock_model = MagicMock()
                    mock_model_class.return_value = mock_model
                    with patch('src.models.model_training.train_test_split'):
                        # Should not raise exception despite MLflow error
                        result = await trainer.train_baseline_model()
                        assert "run_id" in result

    class TestModelPromotion:
        """Test cases for model promotion methods."""

        @pytest.mark.asyncio
        @patch('src.models.model_training.MlflowClient')
        async def test_promote_model_to_production_success(self, mock_client_class, trainer):
            """Test successful model promotion to production."""
            # Setup mock client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_latest_versions.return_value = [
                MagicMock(version="1", stage="Staging")
            ]

            result = await trainer.promote_model_to_production(
                model_name="test_model",
                version="1"
            )

            # Verify promotion was called
            mock_client.transition_model_version_stage.assert_called_once_with(
                name="test_model",
                version="1",
                stage="Production",
                archive_existing_versions=True
            )
            assert result is True

        @pytest.mark.asyncio
        @patch('src.models.model_training.MlflowClient')
        async def test_promote_model_to_production_no_staging_version(self, mock_client_class, trainer):
            """Test model promotion when no staging version exists."""
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_latest_versions.return_value = []  # No staging versions

            result = await trainer.promote_model_to_production("test_model")

            # Should return False
            assert result is False

    class TestModelPerformance:
        """Test cases for model performance methods."""

        @pytest.mark.asyncio
        @patch('src.models.model_training.MlflowClient')
        async def test_get_model_performance_summary_success(self, mock_client_class, trainer, mock_mlflow_run):
            """Test successful model performance summary retrieval."""
            # Setup mock client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_run.return_value = mock_mlflow_run

            result = trainer.get_model_performance_summary("test_run_id")

            # Verify result structure
            assert result["run_id"] == "test_run_id"
            assert result["status"] == "FINISHED"
            assert "metrics" in result
            assert "parameters" in result
            assert "tags" in result

        @pytest.mark.asyncio
        @patch('src.models.model_training.MlflowClient')
        async def test_get_model_performance_summary_error(self, mock_client_class, trainer):
            """Test model performance summary retrieval with error."""
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_run.side_effect = Exception("MLflow error")

            result = trainer.get_model_performance_summary("test_run_id")

            # Should return empty dict on error
            assert result == {}

    class TestTeamFeatures:
        """Test cases for team feature calculation."""

        @pytest.mark.asyncio
        async def test_calculate_team_simple_features(self, trainer):
            """Test team feature calculation."""
            # Setup mock session and query results
            mock_session = AsyncMock()
            mock_result = MagicMock()

            # Mock recent matches
            mock_matches = [
                MagicMock(home_team_id=101, away_team_id=102, home_score=2, away_score=1),
                MagicMock(home_team_id=103, away_team_id=101, home_score=1, away_score=2),
                MagicMock(home_team_id=101, away_team_id=104, home_score=3, away_score=0),
            ]
            mock_result.scalars.return_value.all.return_value = mock_matches
            mock_session.execute.return_value = mock_result

            result = await trainer._calculate_team_simple_features(
                session=mock_session,
                team_id=101,
                match_time=datetime(2024, 1, 10)
            )

            # Verify calculated features
            assert isinstance(result, dict)
            assert "recent_wins" in result
            assert "recent_goals_for" in result
            assert "recent_goals_against" in result
            assert result["recent_wins"] == 2  # Won 2 out of 3 matches
            assert result["recent_goals_for"] == 7  # 2 + 2 + 3 goals
            assert result["recent_goals_against"] == 4  # 1 + 1 + 0 goals