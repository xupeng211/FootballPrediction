"""
Phase 3：机器学习模型训练模块综合测试
目标：全面提升model_training.py模块覆盖率到60%+
重点：测试模型训练流程、数据准备、MLflow集成、实验跟踪和模型注册功能
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest


class MockAsyncResult:
    """Mock for SQLAlchemy async result with proper scalars().all() support"""

    def __init__(self, scalars_result=None, scalar_one_or_none_result=None):
        self._scalars_result = scalars_result or []
        self._scalar_one_or_none_result = scalar_one_or_none_result

    def scalars(self):
        return MockScalarResult(self._scalars_result)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_result


class MockScalarResult:
    """Mock for SQLAlchemy scalars() result"""

    def __init__(self, result):
        self._result = result if isinstance(result, list) else [result]

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from xgboost import XGBClassifier

from src.models.model_training import BaselineModelTrainer


class TestModelTrainingBasic:
    """模型训练器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    def test_trainer_initialization(self):
        """测试训练器初始化"""
        assert self.trainer is not None
        assert hasattr(self.trainer, "feature_store")
        assert hasattr(self.trainer, "db_manager")
        assert hasattr(self.trainer, "mlflow_tracking_uri")
        assert hasattr(self.trainer, "model_params")
        assert hasattr(self.trainer, "feature_refs")
        assert self.trainer.mlflow_tracking_uri == "http://localhost:5002"
        assert isinstance(self.trainer.model_params, dict)
        assert isinstance(self.trainer.feature_refs, list)


class TestModelTrainingDataPreparation:
    """模型训练数据准备测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    @pytest.mark.asyncio
    async def test_prepare_training_data_success(self):
        """测试成功准备训练数据"""
        # Mock feature store和数据库操作
        mock_features = pd.DataFrame(
            {
                "home_team_id": [1, 2, 3],
                "away_team_id": [4, 5, 6],
                "home_recent_form": [0.8, 0.6, 0.7],
                "away_recent_form": [0.5, 0.8, 0.6],
                "home_goals_scored": [2.0, 1.0, 3.0],
                "away_goals_conceded": [1.0, 2.0, 1.0],
            }
        )

        mock_matches = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "home_team_id": [1, 2, 3],
                "away_team_id": [4, 5, 6],
                "home_score": [2, 1, 3],
                "away_score": [1, 2, 1],
                "match_date": pd.to_datetime(
                    ["2023-01-01", "2023-01-02", "2023-01-03"]
                ),
            }
        )

        with patch.object(self.trainer, "feature_store") as mock_store, patch.object(
            self.trainer.db_manager, "get_async_session"
        ) as mock_get_session:

            # Mock feature store返回特征数据
            mock_store.get_features.return_value = mock_features
            mock_store.get_features_online.return_value = mock_features

            # Mock session和数据库查询
            mock_session = AsyncMock()
            mock_result = MagicMock()

            # 创建模拟的Match对象
            class MockMatch:
                def __init__(
                    self,
                    id,
                    home_team_id,
                    away_team_id,
                    league_id,
                    match_time,
                    home_score,
                    away_score,
                    season,
                ):
                    self.id = id
                    self.home_team_id = home_team_id
                    self.away_team_id = away_team_id
                    self.league_id = league_id
                    self.match_time = match_time
                    self.home_score = home_score
                    self.away_score = away_score
                    self.season = season

            # 生成足够的模拟数据以满足min_samples要求
            mock_matches = []
            for i in range(150):  # 生成150条记录
                mock_matches.append(
                    MockMatch(
                        i + 1,
                        (i % 20) + 1,  # home_team_id
                        (i % 20) + 21,  # away_team_id
                        1,  # league_id
                        datetime(2023, 1, 1) + timedelta(days=i),  # match_time
                        (i % 5),  # home_score
                        (i % 4),  # away_score
                        2023,  # season
                    )
                )

            mock_result.fetchall.return_value = mock_matches
            mock_session.execute.return_value = mock_result

            # Mock async session context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_get_session.return_value = mock_context_manager

            X, y = await self.trainer.prepare_training_data(
                datetime(2023, 1, 1), datetime(2023, 1, 31), min_samples=100
            )

            assert isinstance(X, pd.DataFrame)
            assert isinstance(y, pd.Series)
            assert len(X) == len(y)
            assert len(X) > 0

    @pytest.mark.asyncio
    async def test_prepare_training_data_insufficient_samples(self):
        """测试训练数据不足的情况"""
        # Mock feature store返回少量数据
        mock_features = pd.DataFrame(
            {
                "home_team_id": [1],
                "away_team_id": [4],
                "home_recent_form": [0.8],
                "away_recent_form": [0.5],
            }
        )

        with patch.object(self.trainer, "feature_store") as mock_store, patch.object(
            self.trainer.db_manager, "get_async_session"
        ) as mock_get_session:

            mock_store.get_features.return_value = mock_features
            mock_store.get_features_online.return_value = mock_features

            # Mock数据库返回少量数据
            mock_session = AsyncMock()
            mock_result = MagicMock()

            class MockMatch:
                def __init__(
                    self,
                    id,
                    home_team_id,
                    away_team_id,
                    league_id,
                    match_time,
                    home_score,
                    away_score,
                    season,
                ):
                    self.id = id
                    self.home_team_id = home_team_id
                    self.away_team_id = away_team_id
                    self.league_id = league_id
                    self.match_time = match_time
                    self.home_score = home_score
                    self.away_score = away_score
                    self.season = season

            # 只返回少量数据，不足min_samples要求
            mock_matches = [
                MockMatch(1, 1, 4, 1, datetime(2023, 1, 1), 2, 1, 2023),
                MockMatch(2, 2, 5, 1, datetime(2023, 1, 2), 1, 2, 2023),
                MockMatch(3, 3, 6, 1, datetime(2023, 1, 3), 3, 1, 2023),
            ]

            mock_result.fetchall.return_value = mock_matches
            mock_session.execute.return_value = mock_result

            # Mock async session context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_get_session.return_value = mock_context_manager

            with pytest.raises(
                ValueError, match="训练数据不足，需要至少 100 条记录，实际获取 3 条"
            ):
                await self.trainer.prepare_training_data(
                    datetime(2023, 1, 1), datetime(2023, 1, 31), min_samples=100
                )

    @pytest.mark.asyncio
    async def test_prepare_training_data_feature_store_error(self):
        """测试特征存储错误处理"""
        with patch.object(self.trainer, "feature_store") as mock_store:
            mock_store.get_features.side_effect = Exception("Feature store error")

            with pytest.raises(Exception):
                await self.trainer.prepare_training_data(
                    datetime(2023, 1, 1), datetime(2023, 1, 31)
                )

    @pytest.mark.asyncio
    async def test_prepare_training_data_database_error(self):
        """测试数据库错误处理"""
        mock_features = pd.DataFrame(
            {
                "home_team_id": [1, 2, 3],
                "away_team_id": [4, 5, 6],
                "home_recent_form": [0.8, 0.6, 0.7],
                "away_recent_form": [0.5, 0.8, 0.6],
            }
        )

        with patch.object(self.trainer, "feature_store") as mock_store, patch.object(
            self.trainer.db_manager, "get_async_session"
        ) as mock_get_session:

            mock_store.get_features.return_value = mock_features
            mock_store.get_features_online.return_value = mock_features
            mock_get_session.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await self.trainer.prepare_training_data(
                    datetime(2023, 1, 1), datetime(2023, 1, 31)
                )

    @pytest.mark.asyncio
    async def test_prepare_training_data_insufficient_data_handling(self):
        """测试数据不足时的处理"""
        # Mock feature store返回空数据
        mock_features = pd.DataFrame()

        with patch.object(self.trainer, "feature_store") as mock_store:
            mock_store.get_features.return_value = mock_features
            mock_store.get_features_online.return_value = mock_features

            with pytest.raises(ValueError, match="Insufficient training data"):
                await self.trainer.prepare_training_data(
                    datetime(2023, 1, 1), datetime(2023, 1, 31), min_samples=100
                )


class TestModelTrainingTraining:
    """模型训练核心功能测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    @pytest.mark.asyncio
    async def test_train_baseline_model_success(self):
        """测试成功训练基线模型"""
        # Mock数据准备
        mock_X = pd.DataFrame(
            {
                "home_recent_form": [0.8, 0.6, 0.7],
                "away_recent_form": [0.5, 0.8, 0.6],
                "home_goals_scored": [2.0, 1.0, 3.0],
                "away_goals_conceded": [1.0, 2.0, 1.0],
            }
        )
        mock_y = pd.Series([1, 0, 1])

        with patch.object(self.trainer, "prepare_training_data") as mock_prepare, patch(
            "src.models.model_training.mlflow"
        ) as mock_mlflow_module, patch("xgboost.XGBClassifier") as mock_xgb_class:

            mock_prepare.return_value = (mock_X, mock_y)
            mock_model = MagicMock()
            mock_xgb_class.return_value = mock_model

            # Mock MLflow
            mock_run = MagicMock()
            mock_run.info.run_id = "test_run_id"
            mock_mlflow.start_run.return_value = mock_run
            mock_mlflow.log_params.return_value = None
            mock_mlflow.log_metrics.return_value = None
            mock_mlflow.log_artifact.return_value = None
            mock_mlflow.log_model.return_value = None
            mock_mlflow.register_model.return_value = MagicMock()

            run_id = await self.trainer.train_baseline_model(
                experiment_name="test_experiment", model_name="test_model"
            )

            assert run_id == "test_run_id"
            mock_model.fit.assert_called_once()
            mock_mlflow.start_run.assert_called_once()
            mock_mlflow.log_params.assert_called()
            mock_mlflow.log_metrics.assert_called()

    @pytest.mark.asyncio
    async def test_train_baseline_model_custom_dates(self):
        """测试使用自定义日期训练模型"""
        mock_X = pd.DataFrame({"feature1": [1, 2, 3]})
        mock_y = pd.Series([1, 0, 1])

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)

        with patch.object(self.trainer, "prepare_training_data") as mock_prepare, patch(
            "src.models.model_training.MlflowClient"
        ) as mock_mlflow, patch("xgboost.XGBClassifier") as mock_xgb_class:

            mock_prepare.return_value = (mock_X, mock_y)
            mock_model = MagicMock()
            mock_xgb_class.return_value = mock_model

            mock_run = MagicMock()
            mock_run.info.run_id = "test_run_id"
            mock_mlflow.start_run.return_value = mock_run
            mock_mlflow.register_model.return_value = MagicMock()

            run_id = await self.trainer.train_baseline_model(
                experiment_name="test_experiment",
                model_name="test_model",
                start_date=start_date,
                end_date=end_date,
            )

            # 验证使用自定义日期
            mock_prepare.assert_called_once_with(start_date, end_date, 1000)
            assert run_id == "test_run_id"

    @pytest.mark.asyncio
    async def test_train_baseline_model_data_preparation_failure(self):
        """测试数据准备失败的情况"""
        with patch.object(self.trainer, "prepare_training_data") as mock_prepare:
            mock_prepare.side_effect = Exception("Data preparation failed")

            with pytest.raises(Exception, match="Data preparation failed"):
                await self.trainer.train_baseline_model(
                    experiment_name="test_experiment", model_name="test_model"
                )

    @pytest.mark.asyncio
    async def test_train_baseline_model_mlflow_error(self):
        """测试MLflow错误处理"""
        mock_X = pd.DataFrame({"feature1": [1, 2, 3]})
        mock_y = pd.Series([1, 0, 1])

        with patch.object(self.trainer, "prepare_training_data") as mock_prepare, patch(
            "src.models.model_training.MlflowClient"
        ) as mock_mlflow, patch("xgboost.XGBClassifier") as mock_xgb_class:

            mock_prepare.return_value = (mock_X, mock_y)
            mock_model = MagicMock()
            mock_xgb_class.return_value = mock_model
            mock_mlflow.start_run.side_effect = Exception("MLflow error")

            with pytest.raises(Exception, match="MLflow error"):
                await self.trainer.train_baseline_model(
                    experiment_name="test_experiment", model_name="test_model"
                )

    @pytest.mark.asyncio
    async def test_train_baseline_model_model_fit_error(self):
        """测试模型拟合错误处理"""
        mock_X = pd.DataFrame({"feature1": [1, 2, 3]})
        mock_y = pd.Series([1, 0, 1])

        with patch.object(self.trainer, "prepare_training_data") as mock_prepare, patch(
            "src.models.model_training.MlflowClient"
        ) as mock_mlflow, patch("xgboost.XGBClassifier") as mock_xgb_class:

            mock_prepare.return_value = (mock_X, mock_y)
            mock_model = MagicMock()
            mock_model.fit.side_effect = Exception("Model fit error")
            mock_xgb_class.return_value = mock_model

            mock_run = MagicMock()
            mock_run.info.run_id = "test_run_id"
            mock_mlflow.start_run.return_value = mock_run

            # 应该抛出异常
            with pytest.raises(Exception, match="Model fit error"):
                await self.trainer.train_baseline_model(
                    experiment_name="test_experiment", model_name="test_model"
                )


class TestModelTrainingMLflowIntegration:
    """MLflow集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    @pytest.mark.asyncio
    async def test_promote_model_to_production_success(self):
        """测试成功将模型提升到生产环境"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            # Mock MLflow返回模型版本
            mock_version = MagicMock()
            mock_version.version = "2"
            mock_mlflow.get_latest_versions.return_value = [mock_version]

            # Mock模型详情
            mock_model_details = MagicMock()
            mock_model_details.status = "READY"
            mock_mlflow.get_model_version_download_uri.return_value = "test_uri"

            # Mock模型更新
            mock_mlflow.transition_model_version_stage.return_value = None
            mock_mlflow.update_model_version.return_value = None

            result = await self.trainer.promote_model_to_production(
                model_name="test_model", version="2"
            )

            assert result is True
            mock_mlflow.transition_model_version_stage.assert_called_once()
            mock_mlflow.update_model_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_promote_model_to_production_latest_version(self):
        """测试使用最新版本提升模型"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            # Mock获取最新版本
            mock_version = MagicMock()
            mock_version.version = "3"
            mock_mlflow.get_latest_versions.return_value = [mock_version]

            mock_model_details = MagicMock()
            mock_model_details.status = "READY"
            mock_mlflow.get_model_version_download_uri.return_value = "test_uri"
            mock_mlflow.transition_model_version_stage.return_value = None
            mock_mlflow.update_model_version.return_value = None

            result = await self.trainer.promote_model_to_production(
                model_name="test_model"
            )

            assert result is True
            # 应该使用最新版本
            mock_mlflow.get_model_version_download_uri.assert_called_with(
                "test_model", "3"
            )

    @pytest.mark.asyncio
    async def test_promote_model_to_production_no_versions(self):
        """测试没有可用版本的情况"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            mock_mlflow.get_latest_versions.return_value = []

            result = await self.trainer.promote_model_to_production(
                model_name="test_model"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_promote_model_to_production_model_not_ready(self):
        """测试模型未准备好的情况"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            mock_version = MagicMock()
            mock_version.version = "1"
            mock_mlflow.get_latest_versions.return_value = [mock_version]

            mock_model_details = MagicMock()
            mock_model_details.status = "PENDING"
            mock_mlflow.get_model_version_download_uri.return_value = "test_uri"

            result = await self.trainer.promote_model_to_production(
                model_name="test_model"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_promote_model_to_production_mlflow_error(self):
        """测试MLflow错误处理"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            mock_version = MagicMock()
            mock_version.version = "1"
            mock_mlflow.get_latest_versions.return_value = [mock_version]
            mock_mlflow.get_model_version_download_uri.side_effect = Exception(
                "MLflow error"
            )

            result = await self.trainer.promote_model_to_production(
                model_name="test_model"
            )

            assert result is False

    def test_get_model_performance_summary_success(self):
        """测试获取模型性能摘要"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            # Mock运行详情
            mock_run = MagicMock()
            mock_run.data.metrics = {
                "accuracy": 0.85,
                "precision": 0.82,
                "recall": 0.78,
                "f1_score": 0.80,
            }
            mock_run.data.params = {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
            }
            mock_mlflow.get_run.return_value = mock_run

            summary = self.trainer.get_model_performance_summary("test_run_id")

            assert isinstance(summary, dict)
            assert "metrics" in summary
            assert "parameters" in summary
            assert summary["metrics"]["accuracy"] == 0.85
            assert summary["parameters"]["n_estimators"] == 100
            mock_mlflow.get_run.assert_called_once_with("test_run_id")

    def test_get_model_performance_summary_run_not_found(self):
        """测试运行不存在的情况"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            mock_mlflow.get_run.return_value = None

            summary = self.trainer.get_model_performance_summary("nonexistent_run")

            assert isinstance(summary, dict)
            assert "error" in summary
            assert "not found" in summary["error"].lower()

    def test_get_model_performance_summary_mlflow_error(self):
        """测试MLflow错误处理"""
        with patch("src.models.model_training.MlflowClient") as mock_mlflow:
            mock_mlflow.get_run.side_effect = Exception("MLflow error")

            summary = self.trainer.get_model_performance_summary("test_run_id")

            assert isinstance(summary, dict)
            assert "error" in summary
            assert "mlflow error" in summary["error"].lower()


class TestModelTrainingCrossValidation:
    """交叉验证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    def test_cross_validate_model_success(self):
        """测试成功执行交叉验证"""
        X = pd.DataFrame(
            {"feature1": [1, 2, 3, 4, 5], "feature2": [0.1, 0.2, 0.3, 0.4, 0.5]}
        )
        y = pd.Series([1, 0, 1, 0, 1])

        with patch("sklearn.model_selection.cross_validate") as mock_cv:
            mock_cv.return_value = {
                "test_accuracy": [0.8, 0.9, 0.85],
                "test_precision": [0.75, 0.85, 0.80],
                "test_recall": [0.80, 0.90, 0.85],
            }

            result = self.trainer._cross_validate_model(X, y)

            assert isinstance(result, dict)
            assert "mean_accuracy" in result
            assert "std_accuracy" in result
            assert result["mean_accuracy"] == 0.85  # (0.8 + 0.9 + 0.85) / 3
            mock_cv.assert_called_once()

    def test_cross_validate_model_insufficient_data(self):
        """测试数据不足的情况"""
        X = pd.DataFrame({"feature1": [1, 2]})
        y = pd.Series([1, 0])

        result = self.trainer._cross_validate_model(X, y)

        assert "error" in result
        assert "insufficient" in result["error"].lower()

    def test_cross_validate_model_cv_error(self):
        """测试交叉验证错误处理"""
        X = pd.DataFrame(
            {"feature1": [1, 2, 3, 4, 5], "feature2": [0.1, 0.2, 0.3, 0.4, 0.5]}
        )
        y = pd.Series([1, 0, 1, 0, 1])

        with patch("sklearn.model_selection.cross_validate") as mock_cv:
            mock_cv.side_effect = Exception("CV error")

            result = self.trainer._cross_validate_model(X, y)

            assert "error" in result
            assert "cv error" in result["error"].lower()


class TestModelTrainingFeatureEngineering:
    """特征工程测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    def test_engineer_features_success(self):
        """测试成功进行特征工程"""
        raw_data = pd.DataFrame(
            {
                "home_team_id": [1, 2],
                "away_team_id": [3, 4],
                "home_goals_scored": [2, 1],
                "away_goals_scored": [1, 2],
                "home_goals_conceded": [1, 2],
                "away_goals_conceded": [2, 1],
                "home_possession": [60.0, 55.0],
                "away_possession": [40.0, 45.0],
            }
        )

        result = self.trainer._engineer_features(raw_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(raw_data)
        # 检查是否包含了计算的特征
        assert "home_goal_diff" in result.columns
        assert "away_goal_diff" in result.columns
        assert "home_form_trend" in result.columns
        assert "away_form_trend" in result.columns

    def test_engineer_features_empty_data(self):
        """测试空数据的特征工程"""
        raw_data = pd.DataFrame()

        result = self.trainer._engineer_features(raw_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_engineer_features_missing_columns(self):
        """测试缺少必要列的特征工程"""
        raw_data = pd.DataFrame(
            {
                "home_team_id": [1, 2],
                "away_team_id": [3, 4],
                # 缺少其他必要列
            }
        )

        result = self.trainer._engineer_features(raw_data)

        assert isinstance(result, pd.DataFrame)
        # 应该有默认值处理

    def test_engineer_features_calculation_error(self):
        """测试特征计算错误处理"""
        raw_data = pd.DataFrame(
            {
                "home_goals_scored": [2, 1],
                "home_goals_conceded": [0, 0],  # 会导致除零错误
            }
        )

        # 应该能够处理异常情况
        result = self.trainer._engineer_features(raw_data)
        assert isinstance(result, pd.DataFrame)


class TestModelTrainingIntegration:
    """模型训练集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.trainer = BaselineModelTrainer()

    @pytest.mark.asyncio
    async def test_complete_training_workflow(self):
        """测试完整的训练工作流"""
        # Mock数据准备
        mock_X = pd.DataFrame(
            {
                "home_recent_form": [0.8, 0.6, 0.7],
                "away_recent_form": [0.5, 0.8, 0.6],
                "home_goals_scored": [2.0, 1.0, 3.0],
                "away_goals_conceded": [1.0, 2.0, 1.0],
            }
        )
        mock_y = pd.Series([1, 0, 1])

        with patch.object(self.trainer, "prepare_training_data") as mock_prepare, patch(
            "src.models.model_training.MlflowClient"
        ) as mock_mlflow, patch("xgboost.XGBClassifier") as mock_xgb_class:

            mock_prepare.return_value = (mock_X, mock_y)
            mock_model = MagicMock()
            mock_xgb_class.return_value = mock_model

            # Mock MLflow
            mock_run = MagicMock()
            mock_run.info.run_id = "integration_test_run"
            mock_mlflow.start_run.return_value = mock_run
            mock_mlflow.log_params.return_value = None
            mock_mlflow.log_metrics.return_value = None
            mock_mlflow.log_artifact.return_value = None
            mock_mlflow.log_model.return_value = None
            mock_mlflow.register_model.return_value = MagicMock()

            # Mock模型提升
            mock_version = MagicMock()
            mock_version.version = "1"
            mock_mlflow.get_latest_versions.return_value = [mock_version]
            mock_mlflow.get_model_version_download_uri.return_value = "test_uri"
            mock_mlflow.transition_model_version_stage.return_value = None
            mock_mlflow.update_model_version.return_value = None

            # 执行训练
            run_id = await self.trainer.train_baseline_model(
                experiment_name="integration_test", model_name="integration_model"
            )

            assert run_id == "integration_test_run"

            # 获取性能摘要
            performance = self.trainer.get_model_performance_summary(run_id)
            assert isinstance(performance, dict)

            # 提升到生产环境
            promotion_result = await self.trainer.promote_model_to_production(
                model_name="integration_model"
            )
            assert promotion_result is True

    @pytest.mark.asyncio
    async def test_training_with_retry_mechanism(self):
        """测试带重试机制的训练"""
        mock_X = pd.DataFrame({"feature1": [1, 2, 3]})
        mock_y = pd.Series([1, 0, 1])

        call_count = 0

        def mock_prepare_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # 前两次失败
                raise Exception("Temporary failure")
            return (mock_X, mock_y)

        with patch.object(
            self.trainer, "prepare_training_data", side_effect=mock_prepare_with_failure
        ), patch("src.models.model_training.MlflowClient") as mock_mlflow, patch(
            "xgboost.XGBClassifier"
        ) as mock_xgb_class, patch(
            "asyncio.sleep", new_callable=AsyncMock
        ):  # Mock sleep

            mock_model = MagicMock()
            mock_xgb_class.return_value = mock_model

            mock_run = MagicMock()
            mock_run.info.run_id = "retry_test_run"
            mock_mlflow.start_run.return_value = mock_run
            mock_mlflow.register_model.return_value = MagicMock()

            # 应该最终成功
            run_id = await self.trainer.train_baseline_model(
                experiment_name="retry_test", model_name="retry_model"
            )

            assert run_id == "retry_test_run"
            assert call_count == 3  # 应该重试了3次

    def test_model_training_consistency(self):
        """测试模型训练的一致性"""
        # 验证训练器的配置一致性
        assert hasattr(self.trainer, "timeout")
        assert hasattr(self.trainer, "retries")
        assert isinstance(self.trainer.timeout, (int, float))
        assert isinstance(self.trainer.retries, int)
        assert self.trainer.timeout > 0
        assert self.trainer.retries >= 0
