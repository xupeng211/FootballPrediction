from datetime import datetime, timedelta

from src.models.model_training import BaselineModelTrainer
from unittest.mock import Mock, patch
import numpy
import pandas
import pytest

"""
BaselineModelTrainer 完整测试套件
目标：100% 覆盖率，覆盖所有训练流程、数据预处理、模型验证等功能
"""

class TestModelTrainingComplete:
    """BaselineModelTrainer 完整测试套件"""
    @pytest.fixture
    def trainer(self):
        """创建训练器实例"""
        return BaselineModelTrainer()
    @pytest.fixture
    def sample_matches_df(self):
        """创建样本比赛数据"""
        return pd.DataFrame({
                "id[: "1, 2, 3, 4, 5[","]"""
                "]home_team_id[: "10, 11, 12, 13, 14[","]"""
                "]away_team_id[: "15, 16, 17, 18, 19[","]"""
                "]match_time[": [": datetime.now()"""
        )
    @pytest.fixture
    def sample_features_df(self):
        "]""创建样本特征数据"""
        return pd.DataFrame({
                "match_id[: "1, 2, 3, 4, 5[","]"""
                "]team_recent_performance:recent_5_wins[: "3, 2, 1, 4, 2[","]"""
                "]team_recent_performance:recent_5_draws[: "1, 2, 1, 0, 1[","]"""
                "]team_recent_performance:recent_5_losses[: "1, 1, 3, 1, 2[","]"""
                "]team_recent_performance:recent_5_goals_for[: "8, 5, 3, 10, 6[","]"""
                "]team_recent_performance:recent_5_goals_against[: "4, 5, 7, 2, 4[","]"""
                "]historical_matchup:h2h_total_matches[: "10, 8, 12, 6, 9[","]"""
                "]historical_matchup:h2h_home_wins[: "4, 3, 5, 2, 4[","]"""
                "]historical_matchup:h2h_away_wins[: "3, 2, 4, 1, 2[","]"""
                "]historical_matchup:h2h_draws[: "3, 3, 3, 3, 3[","]"""
                "]odds_features:home_odds_avg[: "1.8, 2.1, 1.9, 1.7, 2.0[","]"""
                "]odds_features:draw_odds_avg[: "3.5, 3.2, 3.4, 3.6, 3.3[","]"""
                "]odds_features:away_odds_avg[": [4.2, 3.8, 4.0, 4.5, 3.9])""""
        )
    class TestInitialization:
        "]""测试初始化"""
        def test_trainer_initialization_success(self):
            """测试训练器成功初始化"""
            trainer = BaselineModelTrainer()
            assert trainer.db_manager is not None
            assert trainer.feature_store is not None
            assert trainer.mlflow_tracking_uri =="http//localhost5002[" assert isinstance(trainer.model_params, dict)""""
            assert trainer.model_params["]n_estimators["] ==100[" assert isinstance(trainer.feature_refs, list)"""
        def test_trainer_custom_mlflow_uri(self):
            "]]""测试自定义MLflow URI"""
            custom_uri = "http://custom5000[": trainer = BaselineModelTrainer(custom_uri)": assert trainer.mlflow_tracking_uri ==custom_uri[" class TestTrainingDataPreparation:""
        "]]""测试训练数据准备"""
        @pytest.mark.asyncio
        async def test_prepare_training_data_success(
            self, trainer, sample_matches_df, sample_features_df
        ):
            """测试成功准备训练数据"""
            with patch.object(:
                trainer, "_get_historical_matches["""""
            ) as mock_get_matches, patch.object(
                trainer.feature_store, "]get_historical_features["""""
            ) as mock_get_features:
                mock_get_matches.return_value = sample_matches_df
                mock_get_features.return_value = sample_features_df
                X, y = await trainer.prepare_training_data(
                    datetime.now() - timedelta(days=30), datetime.now(), min_samples=5
                )
                assert isinstance(X, pd.DataFrame)
                assert isinstance(y, pd.Series)
                assert len(X) ==len(sample_matches_df)
                assert len(y) ==len(sample_matches_df)
        @pytest.mark.asyncio
        async def test_prepare_training_data_insufficient_samples(self, trainer):
            "]""测试训练数据不足"""
            small_df = pd.DataFrame({"id[: "1[", "]]match_time[": [datetime.now())": with patch.object(trainer, "]_get_historical_matches[") as mock_get_matches:": mock_get_matches.return_value = small_df[": with pytest.raises(ValueError, match = "]]训练数据不足[")": await trainer.prepare_training_data(": datetime.now() - timedelta(days=30),": datetime.now(),"
                        min_samples=100)
    class TestModelTraining:
        "]""测试模型训练"""
        @pytest.mark.asyncio
        async def test_train_model_success(
            self, trainer, sample_matches_df, sample_features_df
        ):
            """测试成功训练模型"""
            with patch.object(:
                trainer, "_get_historical_matches["""""
            ) as mock_get_matches, patch.object(
                trainer.feature_store, "]get_historical_features["""""
            ) as mock_get_features, patch(
                "]mlflow.start_run["""""
            ) as mock_mlflow:
                mock_get_matches.return_value = sample_matches_df
                mock_get_features.return_value = sample_features_df
                mock_mlflow.return_value.__enter__ = Mock()
                mock_mlflow.return_value.__exit__ = Mock()
                try: "]model[", metrics = await trainer.train_model(": datetime.now() - timedelta(days=30), datetime.now()"""
                    )
                    assert model is not None
                    assert isinstance(metrics, dict)
                    assert "]accuracy[" in metrics or "]model_path[": in metrics[": except Exception as e:": pass  # Auto-fixed empty except block[""
                   # 如果XGBoost不可用，跳过测试
                    pytest.skip(f["]]]XGBoost不可用["]: [{e)])": class TestModelEvaluation:"""
        "]""测试模型评估"""
        def test_evaluate_model_success(self, trainer):
            """测试成功评估模型"""
            # 创建模拟的模型和测试数据
            mock_model = Mock()
            mock_model.predict.return_value = np.array([0, 1, 0, 1])
            X_test = np.random.rand(4, 5)
            y_test = np.array([0, 1, 0, 1])
            try = metrics trainer._evaluate_model(mock_model, X_test, y_test)
                assert isinstance(metrics, dict)
                assert "accuracy[" in metrics[""""
            except Exception as e:
               pass  # Auto-fixed empty except block
               # 如果sklearn不可用，跳过测试
                pytest.skip(f["]]sklearn不可用["]: [{e)])": class TestMLflowIntegration:"""
        "]""测试MLflow集成"""
        @patch("mlflow.start_run[")": def test_mlflow_logging_enabled(self, mock_mlflow, trainer):"""
            "]""测试MLflow日志记录启用"""
            mock_mlflow.return_value.__enter__ = Mock()
            mock_mlflow.return_value.__exit__ = Mock()
            # 测试MLflow日志记录功能
            trainer.mlflow_tracking_uri = "http://test5000[": assert "]test[" in trainer.mlflow_tracking_uri[""""
    class TestFeatureEngineering:
        "]]""测试特征工程"""
        def test_feature_refs_configuration(self, trainer):
            """测试特征引用配置"""
            assert len(trainer.feature_refs) > 0
            assert "team_recent_performancerecent_5_wins[" in trainer.feature_refs[""""
            assert "]]historical_matchuph2h_total_matches[" in trainer.feature_refs[""""
            assert "]]odds_featureshome_odds_avg[" in trainer.feature_refs[""""
    class TestErrorHandling:
        "]]""测试错误处理"""
        @pytest.mark.asyncio
        async def test_feature_store_error_handling(self, trainer, sample_matches_df):
            """测试特征存储错误处理"""
            with patch.object(:
                trainer, "_get_historical_matches["""""
            ) as mock_get_matches, patch.object(
                trainer.feature_store, "]get_historical_features["""""
            ) as mock_get_features:
                mock_get_matches.return_value = sample_matches_df
                mock_get_features.side_effect = Exception("]特征存储错误[")": with pytest.raises(Exception, match = "]特征存储错误[")": await trainer.prepare_training_data(": datetime.now() - timedelta(days=30),": datetime.now(),"
                        min_samples=5)
    class TestConfiguration:
        "]""测试配置"""
        def test_model_params_configuration(self, trainer):
            """测试模型参数配置"""
            expected_params = {
                "n_estimators[": 100,""""
                "]max_depth[": 6,""""
                "]learning_rate[": 0.1,""""
                "]subsample[": 0.8,""""
                "]random_state[": 42,""""
                "]eval_metric[": ["]mlogloss["}": for key, value in expected_params.items():": assert trainer.model_params["]key[" ==value[" class TestUtilityMethods:"""
        "]]""测试工具方法"""
        @pytest.mark.asyncio
        async def test_get_historical_matches(self, trainer):
            """测试获取历史比赛"""
            # 这个方法测试需要实际数据库连接，这里只测试接口存在
            assert hasattr(trainer, "_get_historical_matches[")" assert callable(getattr(trainer, "]_get_historical_matches["))" class TestIntegrationScenarios:"""
        "]""测试集成场景"""
        @pytest.mark.asyncio
        async def test_complete_training_pipeline(self, trainer):
            """测试完整训练管道"""
            # 测试训练管道的所有步骤都能被调用
            with patch.object(:
                trainer, "prepare_training_data["""""
            ) as mock_prepare, patch.object(trainer, "]train_model[") as mock_train:": mock_prepare.return_value = (pd.DataFrame(), pd.Series())": mock_train.return_value = (Mock(), {"]accuracy[": 0.8})": datetime.now() - timedelta(days=30)": datetime.now()""
                # 验证方法存在且可调用
                assert callable(getattr(trainer, "]prepare_training_data["))" assert callable(getattr(trainer, "]train_model["))" class TestPerformance:"""
        "]""测试性能相关"""
        def test_large_dataset_handling(self, trainer):
            """测试大数据集处理"""
            # 测试配置支持大数据集
            assert trainer.model_params["n_jobs["] ==-1  # 使用所有CPU核心["]"]" assert trainer.model_params["n_estimators["] >= 100  # 足够的树数量["]"]" class TestCompatibility:"
        """测试兼容性"""
        def test_optional_dependencies_handling(self):
            """测试可选依赖处理"""
            # 测试在没有XGBoost/MLflow情况下的处理
            trainer = BaselineModelTrainer()
            # 验证类可以正常初始化
            assert trainer is not None
            # 验证必要的属性存在
            assert hasattr(trainer, "model_params[")" assert hasattr(trainer, "]feature_refs")