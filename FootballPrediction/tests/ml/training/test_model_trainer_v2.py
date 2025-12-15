"""
TDD Model Trainer Tests - 模型训练器测试驱动开发
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock


class TestModelTrainer:
    """ModelTrainer的TDD测试用例"""

    @pytest.fixture
    def mock_data_loader(self):
        """创建模拟的数据加载器。"""
        mock_loader = AsyncMock()
        sample_data = pd.DataFrame({
            "match_date": pd.date_range("2024-01-01", periods=100, freq="D"),
            "home_team_id": [f"team_{i % 10}" for i in range(100)],
            "away_team_id": [f"team_{(i + 1) % 10}" for i in range(100)],
            "home_goals": np.random.poisson(1.5, 100),
            "away_goals": np.random.poisson(1.2, 100),
            "result": np.random.choice(["win", "draw", "loss"], 100),
        })
        mock_loader.load_data.return_value = sample_data
        return mock_loader

    @pytest.fixture
    def mock_feature_transformer(self):
        """创建模拟的特征工程转换器。"""
        mock_transformer = Mock()

        def mock_fit_transform(df):
            df_copy = df.copy()
            df_copy["rolling_home_goals_3"] = np.random.normal(1.5, 0.5, len(df))
            return df_copy

        mock_transformer.fit_transform = mock_fit_transform
        mock_transformer.transform = mock_fit_transform
        return mock_transformer

    @pytest.fixture
    def sample_model_params(self):
        """样本模型参数。"""
        return {
            "n_estimators": 100,
            "max_depth": 6,
            "random_state": 42,
        }

    def test_model_trainer_interface_definition(
        self, mock_data_loader, mock_feature_transformer, sample_model_params
    ):
        """测试ModelTrainer类的接口定义。"""
        try:
            from src.ml.training.trainer import ModelTrainer
        except ImportError:
            from FootballPrediction.src.ml.training.trainer import ModelTrainer

        assert ModelTrainer is not None
        
        trainer = ModelTrainer(
            data_loader=mock_data_loader,
            feature_transformers=[mock_feature_transformer],
            model_params=sample_model_params,
        )

        assert hasattr(trainer, "run")
        assert hasattr(trainer, "_split_data")
        assert hasattr(trainer, "get_feature_importance")

    @pytest.mark.asyncio
    async def test_run_pipeline_flow(
        self, mock_data_loader, mock_feature_transformer, sample_model_params
    ):
        """测试训练管道的完整流程调用。"""
        try:
            from src.ml.training.trainer import ModelTrainer
        except ImportError:
            from FootballPrediction.src.ml.training.trainer import ModelTrainer

        trainer = ModelTrainer(
            data_loader=mock_data_loader,
            feature_transformers=[mock_feature_transformer],
            model_params=sample_model_params,
        )

        metrics = await trainer.run(test_size=0.2)

        assert "accuracy" in metrics
        assert "train_samples" in metrics
        assert "test_samples" in metrics

    @pytest.mark.asyncio
    async def test_feature_importance_interface(
        self, mock_data_loader, mock_feature_transformer, sample_model_params
    ):
        """测试特征重要性接口。"""
        try:
            from src.ml.training.trainer import ModelTrainer
        except ImportError:
            from FootballPrediction.src.ml.training.trainer import ModelTrainer

        trainer = ModelTrainer(
            data_loader=mock_data_loader,
            feature_transformers=[mock_feature_transformer],
            model_params=sample_model_params,
        )

        assert hasattr(trainer, "get_feature_importance")

        importance = trainer.get_feature_importance()
        assert importance is None

        await trainer.run(test_size=0.2)
        importance = trainer.get_feature_importance()
        assert importance is not None
        assert isinstance(importance, pd.DataFrame)
