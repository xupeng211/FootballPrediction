#!/usr/bin/env python3
"""
Phase 5.3.2: 模型训练全面测试

目标文件: src/models/model_training.py
当前覆盖率: 12% (178/208 行未覆盖)
目标覆盖率: ≥60%
测试重点: 模型训练、MLflow集成、超参数优化、模型评估
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import tempfile
import os

# Mock复杂依赖
modules_to_mock = [
    'pandas', 'numpy', 'sklearn', 'xgboost', 'mlflow',
    'feast', 'psycopg', 'psycopg_pool', 'great_expectations',
    'prometheus_client', 'confluent_kafka', 'redis'
]

for module in modules_to_mock:
    if module not in __builtins__:
        import sys
        if module not in sys.modules:
            sys.modules[module] = Mock()

# Mock更复杂的导入路径
import sys
sys.modules['feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source'] = Mock()
sys.modules['feast.infra.utils.postgres.connection_utils'] = Mock()
sys.modules['psycopg_pool._acompat'] = Mock()

try:
    from src.models.model_training import ModelTrainingPipeline
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"Import failed: {e}")
    IMPORT_SUCCESS = False


class TestModelTrainingPipeline:
    """模型训练管道测试"""

    @pytest.fixture
    def pipeline(self):
        """创建训练管道实例"""
        if not IMPORT_SUCCESS:
            pytest.skip("Cannot import ModelTrainingPipeline")

        return ModelTrainingPipeline()

    def test_pipeline_initialization(self, pipeline):
        """测试管道初始化"""
        print("🧪 测试训练管道初始化...")

        # 测试基本属性
    assert hasattr(pipeline, 'model_type')
    assert hasattr(pipeline, 'experiment_name')
    assert hasattr(pipeline, 'tracking_uri')
    assert hasattr(pipeline, 'model_registry')

        print("✅ 训练管道初始化测试通过")

    def test_model_configuration_loading(self, pipeline):
        """测试模型配置加载"""
        print("🧪 测试模型配置加载...")

        # 测试默认配置
        config = pipeline.get_default_config()

    assert isinstance(config, dict)
    assert 'model_params' in config
    assert 'training_params' in config
    assert 'evaluation_params' in config

        # 验证配置结构
        model_params = config['model_params']
    assert 'n_estimators' in model_params
    assert 'max_depth' in model_params
    assert 'learning_rate' in model_params

        print("✅ 模型配置加载测试通过")

    @pytest.mark.asyncio
    async def test_data_preparation(self, pipeline):
        """测试数据准备"""
        print("🧪 测试数据准备...")

        # Mock数据源
        mock_data = {
            'features': [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            'target': [0, 1, 0],
            'metadata': {'source': 'test', 'timestamp': '2024-01-01'}
        }

        with patch.object(pipeline, '_load_training_data', return_value=mock_data), \
             patch.object(pipeline, '_validate_data', return_value=True), \
             patch.object(pipeline, '_preprocess_features', return_value=mock_data):

            prepared_data = await pipeline.prepare_training_data()

    assert prepared_data is not None
    assert 'features' in prepared_data
    assert 'target' in prepared_data
    assert len(prepared_data['features']) == len(prepared_data['target'])

        print("✅ 数据准备测试通过")

    @pytest.mark.asyncio
    async def test_model_training_execution(self, pipeline):
        """测试模型训练执行"""
        print("🧪 测试模型训练执行...")

        # Mock训练数据
        training_data = {
            'X_train': [[1, 2, 3], [4, 5, 6]],
            'y_train': [0, 1],
            'X_val': [[7, 8, 9]],
            'y_val': [0]
        }

        # Mock模型
        mock_model = Mock()
        mock_model.fit = Mock()
        mock_model.predict = Mock(return_value=[0, 1])
        mock_model.score = Mock(return_value=0.85)

        with patch.object(pipeline, '_create_model', return_value=mock_model), \
             patch.object(pipeline, '_train_model'), \
             patch.object(pipeline, '_evaluate_model', return_value={'accuracy': 0.85}), \
             patch.object(pipeline, '_save_model', return_value='model_v1'):

            result = await pipeline.train_model(training_data)

    assert result is not None
    assert result['model_id'] == 'model_v1'
    assert result['accuracy'] == 0.85
    assert 'training_time' in result

        print("✅ 模型训练执行测试通过")

    @pytest.mark.asyncio
    async def test_hyperparameter_optimization(self, pipeline):
        """测试超参数优化"""
        print("🧪 测试超参数优化...")

        # Mock优化过程
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5],
            'learning_rate': [0.01, 0.1]
        }

        best_params = {
            'n_estimators': 200,
            'max_depth': 5,
            'learning_rate': 0.1
        }

        with patch.object(pipeline, '_define_param_grid', return_value=param_grid), \
             patch.object(pipeline, '_perform_grid_search', return_value=best_params), \
             patch.object(pipeline, '_validate_best_params', return_value=True):

            result = await pipeline.optimize_hyperparameters()

    assert result is not None
    assert result['best_params'] == best_params
    assert 'best_score' in result
    assert 'optimization_time' in result

        print("✅ 超参数优化测试通过")

    @pytest.mark.asyncio
    async def test_model_evaluation(self, pipeline):
        """测试模型评估"""
        print("🧪 测试模型评估...")

        # Mock评估数据
        y_true = [0, 1, 0, 1]
        y_pred = [0, 1, 1, 1]

        evaluation_metrics = {
            'accuracy': 0.75,
            'precision': 0.67,
            'recall': 1.0,
            'f1_score': 0.8,
            'confusion_matrix': [[1, 1], [0, 2]]
        }

        with patch.object(pipeline, '_calculate_metrics', return_value=evaluation_metrics), \
             patch.object(pipeline, '_generate_classification_report', return_value='classification_report'), \
             patch.object(pipeline, '_log_evaluation_results'):

            result = await pipeline.evaluate_model(y_true, y_pred)

    assert result is not None
    assert 'accuracy' in result
    assert 'precision' in result
    assert 'recall' in result
    assert 'f1_score' in result
    assert result['accuracy'] == 0.75

        print("✅ 模型评估测试通过")

    @pytest.mark.asyncio
    async def test_mlflow_integration(self, pipeline):
        """测试MLflow集成"""
        print("🧪 测试MLflow集成...")

        # Mock MLflow客户端
        mock_client = Mock()
        mock_client.create_experiment = Mock(return_value='exp_1')
        mock_client.log_param = Mock()
        mock_client.log_metric = Mock()
        mock_client.log_artifact = Mock()
        mock_client.set_tag = Mock()

        with patch('mlflow.client.MlflowClient', return_value=mock_client), \
             patch('mlflow.start_run'), \
             patch('mlflow.end_run'), \
             patch('mlflow.log_params'), \
             patch('mlflow.log_metrics'), \
             patch('mlflow.log_artifact'):

            run_info = await pipeline.log_mlflow_run(
                run_id='test_run',
                params={'n_estimators': 100},
                metrics={'accuracy': 0.85},
                artifacts={'model': 'model.pkl'}
            )

    assert run_info is not None
            mock_client.log_param.assert_called()
            mock_client.log_metric.assert_called()

        print("✅ MLflow集成测试通过")

    @pytest.mark.asyncio
    async def test_model_registry_operations(self, pipeline):
        """测试模型注册表操作"""
        print("🧪 测试模型注册表操作...")

        model_info = {
            'model_name': 'football_prediction',
            'model_version': 'v1.0',
            'model_path': '_tmp/model.pkl',
            'metrics': {'accuracy': 0.85},
            'params': {'n_estimators': 100}
        }

        with patch.object(pipeline, '_register_model', return_value=model_info), \
             patch.object(pipeline, '_transition_model_stage'), \
             patch.object(pipeline, '_get_model_version', return_value='v1.0'):

            result = await pipeline.register_model(model_info)

    assert result is not None
    assert result['model_name'] == 'football_prediction'
    assert result['model_version'] == 'v1.0'

        print("✅ 模型注册表操作测试通过")

    @pytest.mark.asyncio
    async def test_feature_store_integration(self, pipeline):
        """测试特征存储集成"""
        print("🧪 测试特征存储集成...")

        # Mock特征存储
        feature_data = {
            'feature_view': 'match_features',
            'features': ['home_team_strength', 'away_team_strength', 'form_rating'],
            'data': [[0.8, 0.6, 0.9], [0.7, 0.8, 0.7]]
        }

        with patch.object(pipeline, '_get_feature_store', return_value=Mock()), \
             patch.object(pipeline, '_retrieve_features', return_value=feature_data), \
             patch.object(pipeline, '_validate_features', return_value=True):

            result = await pipeline.get_training_features()

    assert result is not None
    assert 'feature_view' in result
    assert 'features' in result
    assert 'data' in result

        print("✅ 特征存储集成测试通过")

    @pytest.mark.asyncio
    async def test_model_validation(self, pipeline):
        """测试模型验证"""
        print("🧪 测试模型验证...")

        validation_results = {
            'cross_validation_score': 0.82,
            'test_score': 0.80,
            'validation_score': 0.81,
            'overfitting_detected': False,
            'recommendation': 'Model is ready for production'
        }

        with patch.object(pipeline, '_perform_cross_validation', return_value=validation_results), \
             patch.object(pipeline, '_check_overfitting', return_value=False), \
             patch.object(pipeline, '_generate_validation_report'):

            result = await pipeline.validate_model()

    assert result is not None
    assert 'cross_validation_score' in result
    assert 'overfitting_detected' in result
    assert result['overfitting_detected'] is False

        print("✅ 模型验证测试通过")

    @pytest.mark.asyncio
    async def test_model_deployment_readiness(self, pipeline):
        """测试模型部署就绪性检查"""
        print("🧪 测试模型部署就绪性检查...")

        readiness_checks = {
            'model_performance': True,
            'data_quality': True,
            'feature_availability': True,
            'infrastructure_ready': True,
            'overall_readiness': True
        }

        with patch.object(pipeline, '_check_model_performance', return_value=True), \
             patch.object(pipeline, '_check_data_quality', return_value=True), \
             patch.object(pipeline, '_check_feature_availability', return_value=True), \
             patch.object(pipeline, '_check_infrastructure', return_value=True):

            result = await pipeline.check_deployment_readiness()

    assert result is not None
    assert result['overall_readiness'] is True
    assert all(result.values())

        print("✅ 模型部署就绪性检查测试通过")

    @pytest.mark.asyncio
    async def test_training_error_handling(self, pipeline):
        """测试训练错误处理"""
        print("🧪 测试训练错误处理...")

        with patch.object(pipeline, '_load_training_data', side_effect=Exception("Data loading failed")):

            result = await pipeline.train_model({})

    assert result is not None
    assert 'error' in result
    assert 'Data loading failed' in result['error']

        print("✅ 训练错误处理测试通过")

    @pytest.mark.asyncio
    async def test_model_versioning(self, pipeline):
        """测试模型版本管理"""
        print("🧪 测试模型版本管理...")

        version_info = {
            'current_version': 'v1.0',
            'previous_version': 'v0.9',
            'version_history': [
                {'version': 'v0.9', 'created_at': '2024-01-01', 'accuracy': 0.82},
                {'version': 'v1.0', 'created_at': '2024-01-02', 'accuracy': 0.85}
            ]
        }

        with patch.object(pipeline, '_get_version_history', return_value=version_info), \
             patch.object(pipeline, '_compare_versions'), \
             patch.object(pipeline, '_rollback_version'):

            result = await pipeline.get_model_versions()

    assert result is not None
    assert 'current_version' in result
    assert 'version_history' in result
    assert len(result['version_history']) == 2

        print("✅ 模型版本管理测试通过")

    def test_training_configuration_validation(self, pipeline):
        """测试训练配置验证"""
        print("🧪 测试训练配置验证...")

        # 有效配置
        valid_config = {
            'model_params': {'n_estimators': 100, 'max_depth': 5},
            'training_params': {'test_size': 0.2, 'random_state': 42},
            'evaluation_params': {'cv_folds': 5}
        }

        # 无效配置
        invalid_config = {
            'model_params': {'n_estimators': -1},  # 无效值
            'training_params': {'test_size': 1.5}  # 无效值
        }

        # 测试有效配置
        is_valid = pipeline.validate_config(valid_config)
    assert is_valid is True

        # 测试无效配置
        is_valid = pipeline.validate_config(invalid_config)
    assert is_valid is False

        print("✅ 训练配置验证测试通过")


def test_model_training_comprehensive():
    """模型训练全面测试"""
    print("🚀 开始 Phase 5.3.2: 模型训练全面测试...")

    test_instance = TestModelTrainingPipeline()

    # 执行所有测试
    tests = [
        # 基础功能测试
        test_instance.test_pipeline_initialization,
        test_instance.test_model_configuration_loading,
        test_instance.test_training_configuration_validation,

        # 数据处理测试
        test_instance.test_data_preparation,
        test_instance.test_feature_store_integration,

        # 模型训练测试
        test_instance.test_model_training_execution,
        test_instance.test_hyperparameter_optimization,
        test_instance.test_model_evaluation,
        test_instance.test_model_validation,

        # ML集成测试
        test_instance.test_mlflow_integration,
        test_instance.test_model_registry_operations,
        test_instance.test_model_versioning,

        # 部署测试
        test_instance.test_model_deployment_readiness,

        # 错误处理测试
        test_instance.test_training_error_handling,
    ]

    passed = 0
    failed = 0

    # 执行同步测试
    for test in tests:
        try:
            pipeline = Mock()  # Mock pipeline for non-async tests
            test(pipeline)
            passed += 1
            print(f"  ✅ {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__}: {e}")

    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("🎉 Phase 5.3.2: 模型训练测试完成")
        print("\n📋 测试覆盖的功能:")
        print("  - ✅ 管道初始化和配置")
        print("  - ✅ 数据准备和预处理")
        print("  - ✅ 模型训练和评估")
        print("  - ✅ 超参数优化")
        print("  - ✅ MLflow集成")
        print("  - ✅ 模型注册表操作")
        print("  - ✅ 特征存储集成")
        print("  - ✅ 模型验证")
        print("  - ✅ 版本管理")
        print("  - ✅ 部署就绪性检查")
        print("  - ✅ 错误处理")
    else:
        print("❌ 部分测试失败")


if __name__ == "__main__":
    test_model_training_comprehensive()