#!/usr/bin/env python3
"""
M4模块: 训练流水线单元测试

严格遵循TDD原则，在实现训练流水线之前编写测试用例。
验证XGBoost训练流水线的完整功能和MLOps最佳实践。

测试覆盖:
1. 模型初始化和配置管理
2. 数据加载和预处理流程
3. 模型训练和验证流程
4. 评估指标计算准确性
5. 模型持久化和加载
6. 特征重要性分析
7. 错误处理和边界条件

设计原则:
- TDD驱动: 先写测试，后写实现
- Mock隔离: 使用Mock对象隔离外部依赖
- 边界测试: 覆盖各种边界条件和异常
- 性能验证: 确保关键性能指标达标
- MLOps规范: 验证机器学习运维最佳实践
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
import tempfile
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

# 导入待测试的模块（这些将在Step 3中实现）
from src.ml.models.xgboost_classifier import (
    XGBoostClassifier,
    XGBoostModelConfig,
    create_xgboost_classifier,
)
from src.ml.training.training_pipeline import ClassificationTrainingPipeline

# 导入依赖模块
from src.ml.dataset.target_labels import MatchOutcome


class TestXGBoostModelConfig:
    """测试XGBoost模型配置"""

    def test_default_config_creation(self):
        """测试默认配置创建"""
        config = XGBoostModelConfig.create_default()

        assert config.max_depth == 6
        assert config.learning_rate == 0.1
        assert config.n_estimators == 100
        assert config.objective == "multi:softprob"
        assert config.num_class == 3
        assert config.model_name == "football_1x2_classifier"
        assert config.model_version == "1.0.0"

    def test_fine_tuning_config(self):
        """测试微调配置"""
        config = XGBoostModelConfig.create_for_fine_tuning()

        assert config.max_depth == 4
        assert config.learning_rate == 0.05
        assert config.n_estimators == 200
        assert config.reg_alpha == 0.1
        assert config.reg_lambda == 2.0

    def test_fast_training_config(self):
        """测试快速训练配置"""
        config = XGBoostModelConfig.create_for_fast_training()

        assert config.max_depth == 3
        assert config.learning_rate == 0.2
        assert config.n_estimators == 50
        assert config.max_bin == 128

    def test_config_serialization(self):
        """测试配置序列化"""
        # 创建配置
        config = XGBoostModelConfig.create_default()
        config.model_name = "test_model"
        config.max_depth = 8

        # 测试字典转换
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["model_name"] == "test_model"
        assert config_dict["max_depth"] == 8

        # 测试从字典重建
        rebuilt_config = XGBoostModelConfig.from_dict(config_dict)
        assert rebuilt_config.model_name == config.model_name
        assert rebuilt_config.max_depth == config.max_depth

    def test_config_file_operations(self, tmp_path):
        """测试配置文件操作"""
        config = XGBoostModelConfig.create_default()
        config.model_name = "test_file_config"

        config_path = tmp_path / "test_config.json"

        # 保存配置
        config.save_to_file(config_path)
        assert config_path.exists()

        # 读取配置
        loaded_config = XGBoostModelConfig.load_from_file(config_path)
        assert loaded_config.model_name == config.model_name
        assert loaded_config.max_depth == config.max_depth


class TestXGBoostClassifier:
    """测试XGBoost分类器"""

    @pytest.fixture
    def sample_config(self):
        """创建测试配置"""
        return XGBoostModelConfig(
            max_depth=3,
            learning_rate=0.1,
            n_estimators=10,  # 小数量用于快速测试
            early_stopping_rounds=2,
            random_state=42,
        )

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        np.random.seed(42)
        n_samples = 100
        n_features = 13

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1, 2], n_samples, p=[0.28, 0.26, 0.46])

        # 创建DataFrame以模拟真实数据
        feature_names = [f"feature_{i+1:02d}_test_feature" for i in range(n_features)]
        X_df = pd.DataFrame(X, columns=feature_names)

        return X_df, y

    def test_classifier_initialization(self, sample_config):
        """测试分类器初始化"""
        classifier = XGBoostClassifier(sample_config)

        assert classifier.config == sample_config
        assert classifier.model is not None
        assert classifier.is_trained is False
        assert classifier.feature_names is None
        assert classifier.classes_ is None

    def test_classifier_default_initialization(self):
        """测试默认配置初始化"""
        classifier = XGBoostClassifier()

        assert isinstance(classifier.config, XGBoostModelConfig)
        assert classifier.config.model_name == "football_1x2_classifier"
        assert classifier.is_trained is False

    def test_model_training(self, sample_config, sample_data):
        """测试模型训练"""
        X, y = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 训练模型
        metrics = classifier.train(X, y)

        # 验证训练结果
        assert classifier.is_trained is True
        assert classifier.feature_names is not None
        assert len(classifier.feature_names) == X.shape[1]
        assert classifier.classes_ is not None
        assert len(classifier.classes_) == 3

        # 验证指标
        assert "train_accuracy" in metrics
        assert "training_time_seconds" in metrics
        assert "n_features" in metrics
        assert "n_samples" in metrics
        assert metrics["train_accuracy"] >= 0.0
        assert metrics["train_accuracy"] <= 1.0

    def test_model_training_with_validation(self, sample_config, sample_data):
        """测试带验证集的训练"""
        X, y = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 分割数据
        split_idx = len(X) // 2
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # 训练模型
        metrics = classifier.train(X_train, y_train, X_val, y_val)

        # 验证包含验证指标
        assert "val_accuracy" in metrics
        assert "train_accuracy" in metrics
        assert metrics["val_accuracy"] >= 0.0
        assert metrics["val_accuracy"] <= 1.0

    def test_model_prediction(self, sample_config, sample_data):
        """测试模型预测"""
        X, y = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 训练模型
        classifier.train(X, y)

        # 预测
        predictions = classifier.predict(X)
        probabilities = classifier.predict_proba(X)

        # 验证预测结果
        assert len(predictions) == len(X)
        assert all(pred in [0, 1, 2] for pred in predictions)
        assert probabilities.shape == (len(X), 3)  # 3个类别
        assert np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6)  # 概率和为1

    def test_model_evaluation(self, sample_config, sample_data):
        """测试模型评估"""
        X, y = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 训练模型
        classifier.train(X, y)

        # 评估
        metrics = classifier.evaluate(X, y)

        # 验证评估指标
        expected_metrics = [
            "test_accuracy",
            "test_precision_weighted",
            "test_recall_weighted",
            "test_f1_weighted",
            "test_precision_HOME_WIN",
            "test_precision_DRAW",
            "test_precision_AWAY_WIN",
        ]

        for metric in expected_metrics:
            assert metric in metrics
            assert 0.0 <= metrics[metric] <= 1.0

    def test_feature_importance(self, sample_config, sample_data):
        """测试特征重要性分析"""
        X, y = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 训练模型
        classifier.train(X, y)

        # 获取特征重要性
        importance_df = classifier.get_feature_importance()

        # 验证特征重要性
        assert isinstance(importance_df, pd.DataFrame)
        assert len(importance_df) == X.shape[1]
        assert "feature_name" in importance_df.columns
        assert "importance" in importance_df.columns
        assert "feature_display_name" in importance_df.columns
        assert all(importance_df["importance"] >= 0)

    def test_model_save_and_load(self, sample_config, sample_data, tmp_path):
        """测试模型保存和加载"""
        X, y = sample_data
        original_classifier = XGBoostClassifier(sample_config)

        # 训练原始模型
        original_classifier.train(X, y)
        original_predictions = original_classifier.predict(X)

        # 保存模型
        model_path = tmp_path / "test_model.pkl"
        original_classifier.save_model(model_path)

        # 验证文件存在
        assert model_path.exists()
        assert model_path.with_suffix(".json").exists()
        assert model_path.with_suffix(".config.json").exists()

        # 加载模型
        loaded_classifier = XGBoostClassifier.load_model(model_path)

        # 验证加载的模型
        assert loaded_classifier.is_trained is True
        assert loaded_classifier.feature_names == original_classifier.feature_names
        assert np.array_equal(loaded_classifier.classes_, original_classifier.classes_)

        # 验证预测一致性
        loaded_predictions = loaded_classifier.predict(X)
        np.testing.assert_array_equal(original_predictions, loaded_predictions)

    def test_prediction_without_training(self, sample_config, sample_data):
        """测试未训练模型的预测"""
        X, _ = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 尝试预测未训练的模型应该失败
        with pytest.raises(RuntimeError, match="模型尚未训练"):
            classifier.predict(X)

        with pytest.raises(RuntimeError, match="模型尚未训练"):
            classifier.predict_proba(X)

    def test_invalid_training_data(self, sample_config):
        """测试无效训练数据"""
        classifier = XGBoostClassifier(sample_config)

        # 形状不匹配的数据
        X_invalid = np.random.randn(100, 10)
        y_invalid = np.random.randint(0, 3, 90)  # 不同的样本数

        with pytest.raises(ValueError, match="样本数不匹配"):
            classifier.train(X_invalid, y_invalid)

    def test_convenience_function(self):
        """测试便捷创建函数"""
        # 测试默认配置
        classifier1 = create_xgboost_classifier("default")
        assert classifier1.config.max_depth == 6

        # 测试微调配置
        classifier2 = create_xgboost_classifier("fine_tuning")
        assert classifier2.config.max_depth == 4

        # 测试快速训练配置
        classifier3 = create_xgboost_classifier("fast_training")
        assert classifier3.config.max_depth == 3

        # 测试无效配置
        with pytest.raises(ValueError, match="未知的配置类型"):
            create_xgboost_classifier("invalid_type")

    def test_model_info(self, sample_config, sample_data):
        """测试模型信息获取"""
        X, y = sample_data
        classifier = XGBoostClassifier(sample_config)

        # 未训练时的信息
        info = classifier.get_model_info()
        assert info["is_trained"] is False
        assert info["model_name"] == sample_config.model_name
        assert "n_estimators" not in info  # 未训练时没有此信息

        # 训练后的信息
        classifier.train(X, y)
        info = classifier.get_model_info()
        assert info["is_trained"] is True
        assert "n_estimators" in info
        assert "model_params" in info


class TestClassificationTrainingPipeline:
    """测试训练流水线"""

    @pytest.fixture
    def mock_dataset_path(self, tmp_path):
        """创建模拟数据集文件"""
        # 创建模拟数据集
        np.random.seed(42)
        n_samples = 200

        data = {
            "match_id": [f"match_{i}" for i in range(n_samples)],
            "home_team_id": [f"team_{i % 10}" for i in range(n_samples)],
            "away_team_id": [f"team_{i % 10 + 10}" for i in range(n_samples)],
            "match_date": ["2024-01-01"] * n_samples,
            "final_home_score": np.random.poisson(1.5, n_samples),
            "final_away_score": np.random.poisson(1.2, n_samples),
            "target_label": np.random.choice(
                ["HOME_WIN", "DRAW", "AWAY_WIN"], n_samples
            ),
            "target_numeric": np.random.choice([2, 1, 0], n_samples),
            "feature_completeness_score": np.random.uniform(0.8, 1.0, n_samples),
            "data_quality_flag": ["HIGH"] * n_samples,
        }

        # 添加特征列
        for i in range(13):  # 13个特征
            data[f"feature_{i+1:03d}_test_feature"] = np.random.randn(n_samples)

        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test_dataset.parquet"
        df.to_parquet(dataset_path)

        return dataset_path

    @pytest.fixture
    def training_pipeline(self, tmp_path):
        """创建训练流水线实例"""
        model_output_dir = tmp_path / "models"
        return ClassificationTrainingPipeline(model_output_dir=str(model_output_dir))

    def test_pipeline_initialization(self, tmp_path):
        """测试流水线初始化"""
        model_output_dir = tmp_path / "models"
        pipeline = ClassificationTrainingPipeline(
            model_output_dir=str(model_output_dir)
        )

        assert pipeline.model_output_dir == Path(model_output_dir)
        assert isinstance(pipeline.classifier, XGBoostClassifier)

    def test_pipeline_run_success(self, training_pipeline, mock_dataset_path, tmp_path):
        """测试成功运行流水线"""
        # 运行流水线
        metrics = asyncio.run(
            training_pipeline.run_pipeline(
                dataset_path=str(mock_dataset_path),
                model_output_path=str(tmp_path / "trained_model.pkl"),
            )
        )

        # 验证输出指标
        expected_metrics = [
            "train_accuracy",
            "test_accuracy",
            "train_precision_weighted",
            "test_precision_weighted",
            "train_f1_weighted",
            "test_f1_weighted",
        ]

        for metric in expected_metrics:
            assert metric in metrics
            assert 0.0 <= metrics[metric] <= 1.0

        # 验证模型文件创建
        model_file = tmp_path / "trained_model.pkl"
        assert model_file.exists()

        # 验证元数据文件
        metadata_file = tmp_path / "training_metrics.json"
        assert metadata_file.exists()

    def test_pipeline_data_preprocessing(self, training_pipeline, mock_dataset_path):
        """测试数据预处理"""
        # 加载和预处理数据
        X, y, feature_names = training_pipeline._load_and_preprocess_data(
            str(mock_dataset_path)
        )

        # 验证数据形状和类型
        assert isinstance(X, np.ndarray)
        assert isinstance(y, np.ndarray)
        assert isinstance(feature_names, list)

        assert X.shape[0] == len(y)
        assert len(feature_names) == X.shape[1]

        # 验证标签范围
        unique_labels = np.unique(y)
        assert all(label in [0, 1, 2] for label in unique_labels)

    def test_pipeline_model_saving(
        self, training_pipeline, mock_dataset_path, tmp_path
    ):
        """测试模型保存功能"""
        # 运行流水线
        metrics = asyncio.run(
            training_pipeline.run_pipeline(
                dataset_path=str(mock_dataset_path),
                model_output_path=str(tmp_path / "pipeline_test_model.pkl"),
            )
        )

        # 验证模型文件存在
        model_file = tmp_path / "pipeline_test_model.pkl"
        assert model_file.exists()

        # 验证模型可以加载
        loaded_classifier = XGBoostClassifier.load_model(model_file)
        assert loaded_classifier.is_trained is True

        # 验证元数据文件存在
        metadata_file = tmp_path / "pipeline_test_model.json"
        assert metadata_file.exists()

        # 验证元数据内容
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert "training_metrics" in metadata
        assert "model_config" in metadata
        assert "feature_names" in metadata
        assert "trained_at" in metadata

    def test_pipeline_error_handling_invalid_dataset(self, training_pipeline):
        """测试无效数据集的错误处理"""
        with pytest.raises(FileNotFoundError):
            asyncio.run(
                training_pipeline.run_pipeline(
                    dataset_path="nonexistent_dataset.parquet",
                    model_output_path="model.pkl",
                )
            )

    def test_pipeline_feature_importance_analysis(
        self, training_pipeline, mock_dataset_path, tmp_path
    ):
        """测试特征重要性分析"""
        # 运行流水线
        asyncio.run(
            training_pipeline.run_pipeline(
                dataset_path=str(mock_dataset_path),
                model_output_path=str(tmp_path / "importance_test_model.pkl"),
            )
        )

        # 验证特征重要性文件
        importance_file = tmp_path / "feature_importance.csv"
        assert importance_file.exists()

        # 验证特征重要性内容
        importance_df = pd.read_csv(importance_file)
        assert "feature_name" in importance_df.columns
        assert "importance" in importance_df.columns
        assert len(importance_df) > 0
        assert all(importance_df["importance"] >= 0)


class TestIntegrationScenarios:
    """集成测试场景"""

    @pytest.mark.asyncio
    async def test_end_to_end_training_workflow(self, tmp_path):
        """端到端训练工作流测试"""
        # 创建完整的数据集
        np.random.seed(42)
        n_samples = 500

        # 更真实的特征数据
        data = {
            "match_id": [f"match_{i}" for i in range(n_samples)],
            "final_home_score": np.random.poisson(1.4, n_samples),
            "final_away_score": np.random.poisson(1.1, n_samples),
            "target_numeric": np.random.choice(
                [0, 1, 2], n_samples, p=[0.28, 0.26, 0.46]
            ),
        }

        # Phase 5特征 (13个)
        feature_data = {
            "feature_001_home_form_score_5": np.random.beta(2, 3, n_samples),
            "feature_002_away_form_score_5": np.random.beta(2, 3, n_samples),
            "feature_003_home_form_score_3": np.random.beta(2, 3, n_samples),
            "feature_004_away_form_score_3": np.random.beta(2, 3, n_samples),
            "feature_005_home_xg_efficiency_5": np.random.gamma(2, 0.5, n_samples),
            "feature_006_away_xg_efficiency_5": np.random.gamma(2, 0.5, n_samples),
            "feature_007_home_xg_efficiency_3": np.random.gamma(2, 0.5, n_samples),
            "feature_008_away_xg_efficiency_3": np.random.gamma(2, 0.5, n_samples),
            "feature_009_odds_home_normalized": np.random.beta(1.5, 3, n_samples),
            "feature_010_odds_draw_normalized": np.random.beta(1, 3, n_samples),
            "feature_011_odds_away_normalized": np.random.beta(1.5, 3, n_samples),
            "feature_012_h2h_home_win_rate": np.random.beta(3, 3, n_samples),
            "feature_013_h2h_match_count_normalized": np.random.uniform(
                0, 1, n_samples
            ),
        }

        data.update(feature_data)

        df = pd.DataFrame(data)
        dataset_path = tmp_path / "realistic_dataset.parquet"
        df.to_parquet(dataset_path)

        # 创建并运行训练流水线
        pipeline = ClassificationTrainingPipeline(
            model_output_dir=str(tmp_path / "models"), config_type="fine_tuning"
        )

        # 运行完整流水线
        metrics = await pipeline.run_pipeline(
            dataset_path=str(dataset_path),
            model_output_path=str(tmp_path / "end_to_end_model.pkl"),
        )

        # 验证结果
        assert metrics["train_accuracy"] >= 0.5  # 基线准确率
        assert metrics["test_accuracy"] >= 0.4  # 测试准确率
        assert "training_time_seconds" in metrics

        # 验证模型持久化
        model_file = tmp_path / "end_to_end_model.pkl"
        assert model_file.exists()

        # 验证模型可以重新加载并预测
        loaded_classifier = XGBoostClassifier.load_model(model_file)
        test_data = df[
            [col for col in df.columns if col.startswith("feature_")]
        ].values[:10]
        predictions = loaded_classifier.predict(test_data)

        assert len(predictions) == 10
        assert all(pred in [0, 1, 2] for pred in predictions)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
