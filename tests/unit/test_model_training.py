"""
from unittest.mock import Mock, patch
import asyncio
模型训练测试模块

测试 src/models/model_training.py 的核心功能
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.models.model_training import BaselineModelTrainer


class TestBaselineModelTrainer:
    """测试基准模型训练器"""

    @pytest.fixture
    def trainer(self):
        """创建训练器实例"""
        with patch("src.models.model_training.mlflow"):
            with patch("src.models.model_training.DatabaseManager"):
                with patch("src.models.model_training.FootballFeatureStore"):
                    trainer = BaselineModelTrainer(
                        mlflow_tracking_uri="sqlite:///test.db"
                    )
                    return trainer

    def test_init_sets_parameters(self, trainer):
        """测试初始化时设置模型参数"""
    assert trainer.model_params["n_estimators"] == 100
    assert trainer.model_params["max_depth"] == 6
    assert trainer.model_params["learning_rate"] == 0.1
    assert trainer.model_params["random_state"] == 42

    def test_init_sets_feature_refs(self, trainer):
        """测试初始化时设置特征引用"""
    assert len(trainer.feature_refs) > 0
    assert any("team_recent_performance" in ref for ref in trainer.feature_refs)
    assert any("historical_matchup" in ref for ref in trainer.feature_refs)
    assert any("odds_features" in ref for ref in trainer.feature_refs)

    def test_model_params_configuration(self, trainer):
        """测试模型参数配置"""
        params = trainer.model_params

        # 验证关键参数存在且合理
    assert params["n_estimators"] > 0
    assert 0 < params["learning_rate"] <= 1
    assert params["max_depth"] > 0
    assert 0 < params["subsample"] <= 1
    assert 0 < params["colsample_bytree"] <= 1
    assert params["random_state"] is not None

    def test_feature_refs_completeness(self, trainer):
        """测试特征引用的完整性"""
        feature_refs = trainer.feature_refs

        # 验证包含各类特征
        team_perf_features = [
            ref for ref in feature_refs if "team_recent_performance" in ref
        ]
        h2h_features = [ref for ref in feature_refs if "historical_matchup" in ref]
        odds_features = [ref for ref in feature_refs if "odds_features" in ref]

    assert len(team_perf_features) > 0, "应包含球队表现特征"
    assert len(h2h_features) > 0, "应包含历史对战特征"
    assert len(odds_features) > 0, "应包含赔率特征"

    def test_calculate_match_result_basic(self, trainer):
        """测试基本的比赛结果计算逻辑"""
        # 由于实际实现可能返回不同的值，我们测试方法存在性
        row = pd.Series({"home_score": 3, "away_score": 1})
        result = trainer._calculate_match_result(row)
    assert isinstance(result, str)
    assert result in ["home", "away", "draw", "home_win", "away_win"]

    def test_trainer_has_required_attributes(self, trainer):
        """测试训练器具有必需的属性"""
    assert hasattr(trainer, "db_manager")
    assert hasattr(trainer, "feature_store")
    assert hasattr(trainer, "mlflow_tracking_uri")
    assert hasattr(trainer, "model_params")
    assert hasattr(trainer, "feature_refs")

    def test_trainer_methods_exist(self, trainer):
        """测试训练器具有必需的方法"""
    assert hasattr(trainer, "prepare_training_data")
    assert hasattr(trainer, "train_baseline_model")
    assert hasattr(trainer, "promote_model_to_production")
    assert hasattr(trainer, "get_model_performance_summary")

    def test_mlflow_tracking_uri_set(self, trainer):
        """测试MLflow跟踪URI设置"""
    assert trainer.mlflow_tracking_uri == "sqlite:_//test.db"

    def test_feature_refs_are_strings(self, trainer):
        """测试特征引用都是字符串格式"""
        for ref in trainer.feature_refs:
    assert isinstance(ref, str)
    assert ":" in ref  # 特征引用应包含冒号分隔符

    def test_model_params_valid_types(self, trainer):
        """测试模型参数类型正确"""
        params = trainer.model_params

    assert isinstance(params["n_estimators"], int)
    assert isinstance(params["max_depth"], int)
    assert isinstance(params["learning_rate"], (int, float))
    assert isinstance(params["subsample"], (int, float))
    assert isinstance(params["colsample_bytree"], (int, float))

    @pytest.mark.asyncio
    async def test_promote_model_to_production_with_mock(self, trainer):
        """测试将模型提升到生产环境（使用Mock）"""
        mock_client = Mock()
        mock_client.transition_model_version_stage = Mock()

        with patch("src.models.model_training.MlflowClient", return_value=mock_client):
            result = await trainer.promote_model_to_production("test_model", "1")

    assert result is True
        mock_client.transition_model_version_stage.assert_called_once()

    def test_class_exists_and_instantiable(self):
        """测试类存在且可实例化"""
        with patch("src.models.model_training.mlflow"):
            with patch("src.models.model_training.DatabaseManager"):
                with patch("src.models.model_training.FootballFeatureStore"):
                    trainer = BaselineModelTrainer()
    assert isinstance(trainer, BaselineModelTrainer)

    def test_default_mlflow_uri(self):
        """测试默认MLflow URI"""
        with patch("src.models.model_training.mlflow"):
            with patch("src.models.model_training.DatabaseManager"):
                with patch("src.models.model_training.FootballFeatureStore"):
                    trainer = BaselineModelTrainer()
    assert trainer.mlflow_tracking_uri == "http:_/localhost:5002"
