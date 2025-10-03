from datetime import datetime, timedelta

from src.models.model_training import BaselineModelTrainer
from unittest.mock import patch
import pandas
import pytest
import os

"""
BaselineModelTrainer 基础测试套件
目标：覆盖核心功能，避免复杂的外部依赖
"""

class TestModelTrainingBasic:
    """BaselineModelTrainer 基础测试套件"""
    @pytest.fixture
    def trainer(self):
        """创建训练器实例"""
        return BaselineModelTrainer()
    class TestInitialization:
        """测试初始化"""
        def test_init_default_uri(self):
            """测试默认URI初始化"""
            trainer = BaselineModelTrainer()
            assert trainer.mlflow_tracking_uri =="http//localhost5002[" assert trainer.db_manager is not None[""""
            assert trainer.feature_store is not None
            assert isinstance(trainer.model_params, dict)
            assert isinstance(trainer.feature_refs, list)
        def test_init_custom_uri(self):
            "]]""测试自定义URI初始化"""
            custom_uri = "http://custom5000[": trainer = BaselineModelTrainer(custom_uri)": assert trainer.mlflow_tracking_uri ==custom_uri[" class TestConfiguration:""
        "]]""测试配置"""
        def test_model_params_configuration(self, trainer):
            """测试模型参数配置"""
            expected_params = {
                "n_estimators[": 100,""""
                "]max_depth[": 6,""""
                "]learning_rate[": 0.1,""""
                "]subsample[": 0.8,""""
                "]colsample_bytree[": 0.8,""""
                "]random_state[": 42,""""
                "]eval_metric[": ["]mlogloss["}": for key, value in expected_params.items():": assert trainer.model_params["]key[" ==value[" def test_feature_refs_configuration(self, trainer):"""
            "]]""测试特征引用配置"""
            assert len(trainer.feature_refs) > 0
            assert "team_recent_performancerecent_5_wins[" in trainer.feature_refs[""""
            assert "]]historical_matchuph2h_total_matches[" in trainer.feature_refs[""""
            assert "]]odds_featureshome_odds_avg[" in trainer.feature_refs[""""
    class TestMethodAvailability:
        "]]""测试方法可用性"""
        def test_training_methods_exist(self, trainer):
            """测试训练方法存在"""
            training_methods = [
                "prepare_training_data[",""""
                "]train_baseline_model[",""""
                "]_get_historical_matches[",""""
                "]get_model_performance_summary["]": for method in training_methods:": assert hasattr(trainer, method)" assert callable(getattr(trainer, method))"
    class TestFeatureEngineering:
        "]""测试特征工程"""
        def test_feature_refs_structure(self, trainer):
            """测试特征引用结构"""
            # 验证特征引用包含不同类型的特征
            team_features = [
                f for f in trainer.feature_refs if "team_recent_performance[": in f:""""
            ]
            h2h_features = [
                f for f in trainer.feature_refs if "]historical_matchup[": in f:""""
            ]
            odds_features = [f for f in trainer.feature_refs if "]odds_features[": in f]": assert len(team_features) > 0[" assert len(h2h_features) > 0[""
            assert len(odds_features) > 0
    class TestErrorHandling:
        "]]]""测试错误处理"""
        @pytest.mark.asyncio
        async def test_prepare_training_data_insufficient_samples(self, trainer):
            """测试训练数据不足"""
            # 创建少量数据的DataFrame
            small_df = pd.DataFrame({"id[: "1[", "]]match_time[": [datetime.now())": with patch.object(trainer, "]_get_historical_matches[") as mock_get_matches:": mock_get_matches.return_value = small_df[": with pytest.raises(ValueError, match = os.getenv("TEST_MODEL_TRAINING_BASIC_MATCH_75"))": await trainer.prepare_training_data(": datetime.now() - timedelta(days=30),": datetime.now(),"
                        min_samples=100)
    class TestIntegrationPoints:
        "]""测试集成点"""
        def test_database_manager_integration(self, trainer):
            """测试数据库管理器集成"""
            assert trainer.db_manager is not None
            # 验证数据库管理器有基本方法
            assert hasattr(trainer.db_manager, "get_session[")" assert hasattr(trainer.db_manager, "]initialize[")" def test_feature_store_integration(self, trainer):"""
            "]""测试特征存储集成"""
            assert trainer.feature_store is not None
            # 验证特征存储有基本方法
            assert hasattr(trainer.feature_store, "get_historical_features[")" class TestPerformanceCharacteristics:"""
        "]""测试性能特征"""
        def test_model_params_performance_config(self, trainer):
            """测试模型参数性能配置"""
            # 验证性能相关配置
            assert trainer.model_params["n_jobs["] ==-1  # 使用所有CPU核心["]"]" assert trainer.model_params["n_estimators["] >= 100  # 足够的树数量["]"]" assert trainer.model_params["subsample["] <= 1.0  # 合理的采样率["]"]" class TestCompatibility:"
        """测试兼容性"""
        def test_service_without_optional_deps(self):
            """测试无可选依赖情况下的服务"""
            trainer = BaselineModelTrainer()
            assert trainer is not None
            # 验证核心属性存在
            assert hasattr(trainer, "db_manager[")" assert hasattr(trainer, "]feature_store[")" assert hasattr(trainer, "]model_params[")" assert hasattr(trainer, "]feature_refs[")" def test_mlflow_uri_handling(self, trainer):"""
            "]""测试MLflow URI处理"""
            # 测试URI格式
            assert trainer.mlflow_tracking_uri.startswith("http[")" assert "]localhost[" in trainer.mlflow_tracking_uri[""""
    class TestUtilityMethods:
        "]]""测试工具方法"""
        def test_trainer_attributes_initialization(self, trainer):
            """测试训练器属性初始化"""
            # 验证所有必要属性都已正确初始化
            assert hasattr(trainer, "mlflow_tracking_uri[")" assert hasattr(trainer, "]db_manager[")" assert hasattr(trainer, "]feature_store[")" assert hasattr(trainer, "]model_params[")" assert hasattr(trainer, "]feature_refs[")""""
            # 验证参数类型
            assert isinstance(trainer.model_params, dict)
            assert isinstance(trainer.feature_refs, list)
    class TestDataValidation:
        "]""测试数据验证"""
        def test_model_params_validation(self, trainer):
            """测试模型参数验证"""
            # 验证关键参数存在且在合理范围内
            assert trainer.model_params["n_estimators["] > 0["]"]" assert trainer.model_params["max_depth["] > 0["]"]" assert 0 < trainer.model_params["learning_rate["] <= 1["]"]" assert 0 < trainer.model_params["subsample["] <= 1["]"]" assert trainer.model_params["random_state["] is not None["]"]" def test_feature_refs_validation(self, trainer):"
            """测试特征引用验证"""
            # 验证特征引用不为空且格式正确
            assert len(trainer.feature_refs) > 0
            # 验证特征引用格式（应该包含冒号分隔的命名空间）
            for feature_ref in trainer.feature_refs:
                assert :  in feature_ref  # 格式应该是 "namespacefeature_name[": class TestEdgeCases:""""
        "]""测试边界情况"""
        def test_empty_feature_refs_handling(self):
            """测试空特征引用处理"""
            # 即使特征引用为空，训练器也应该能正常初始化
            trainer = BaselineModelTrainer()
            # 临时清空特征引用
            original_features = trainer.feature_refs
            trainer.feature_refs = []
            # 验证训练器仍然可以正常工作
            assert hasattr(trainer, "feature_refs[")" assert len(trainer.feature_refs) ==0["""
            # 恢复原始特征引用
            trainer.feature_refs = original_features
        def test_custom_model_params_handling(self):
            "]]""测试自定义模型参数处理"""
            trainer = BaselineModelTrainer()
            # 测试可以修改模型参数
            original_n_estimators = trainer.model_params["n_estimators["]"]": trainer.model_params["n_estimators["] = 200["]"]": assert trainer.model_params["n_estimators["] ==200["]"]" assert trainer.model_params["n_estimators"] != original_n_estimators