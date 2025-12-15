"""
足球预测管道测试
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

# 测试目标
from src.ml.football_prediction_pipeline import (
    FootballPredictionPipeline,
    create_simple_prediction_pipeline,
    create_advanced_prediction_pipeline,
)


class TestFootballPredictionPipeline:
    """足球预测管道测试类"""

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        np.random.seed(42)
        n_samples = 100

        data = {
            "home_team": np.random.choice(["Team_A", "Team_B", "Team_C"], n_samples),
            "away_team": np.random.choice(["Team_X", "Team_Y", "Team_Z"], n_samples),
            "home_team_score": np.random.randint(0, 5, n_samples),
            "away_team_score": np.random.randint(0, 5, n_samples),
            "home_team_shots": np.random.randint(5, 25, n_samples),
            "away_team_shots": np.random.randint(5, 25, n_samples),
            "odds_home_win": np.random.uniform(1.5, 5.0, n_samples),
            "odds_draw": np.random.uniform(3.0, 4.5, n_samples),
            "odds_away_win": np.random.uniform(1.8, 6.0, n_samples),
        }

        # 创建目标变量（主队是否获胜）
        y = (data["home_team_score"] > data["away_team_score"]).astype(int)

        X = pd.DataFrame(data)
        y_series = pd.Series(y)

        return X, y_series

    @pytest.fixture
    def pipeline(self):
        """创建管道实例"""
        return FootballPredictionPipeline(
            model_name="test_pipeline", output_dir="test_models", use_mlflow=False
        )

    def test_pipeline_initialization(self, pipeline):
        """测试管道初始化"""
        assert pipeline.model_name == "test_pipeline"
        assert pipeline.use_mlflow is False
        assert pipeline.is_fitted is False
        assert pipeline.feature_pipeline is None
        assert pipeline.model_trainer is None

    def test_build_feature_pipeline(self, pipeline):
        """测试构建特征管道"""
        # 使用默认参数构建
        result = pipeline.build_feature_pipeline()

        # 验证链式调用返回自身
        assert result is pipeline
        assert pipeline.feature_pipeline is not None

    def test_build_feature_pipeline_with_custom_features(self, pipeline):
        """测试使用自定义特征构建管道"""
        numeric_features = ["home_team_score", "away_team_score"]
        categorical_features = ["home_team", "away_team"]

        result = pipeline.build_feature_pipeline(
            numeric_features=numeric_features, categorical_features=categorical_features
        )

        assert result is pipeline
        assert pipeline.feature_pipeline is not None

    def test_prepare_data(self, pipeline, sample_data):
        """测试数据准备"""
        X, y = sample_data

        # 先构建特征管道
        pipeline.build_feature_pipeline()

        # 准备数据
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)

        # 验证数据分割
        assert len(X_train) > len(X_test)
        assert len(y_train) == len(X_train)
        assert len(y_test) == len(X_test)
        assert len(X_train.columns) == len(X.columns)

    @patch("src.models.model_training.HAS_XGB", False)
    def test_train_model_without_xgboost(self, pipeline, sample_data):
        """测试在没有 XGBoost 时的模型训练"""
        X, y = sample_data

        # 构建管道和准备数据
        pipeline.build_feature_pipeline()
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)

        # 尝试训练 XGBoost 模型应该失败
        with pytest.raises(ImportError, match="XGBoost is not installed"):
            pipeline.train_model(X_train, y_train, X_test, y_test, model_type="xgboost")

    def test_train_model_random_forest(self, pipeline, sample_data):
        """测试训练随机森林模型"""
        X, y = sample_data

        # 构建管道和准备数据
        pipeline.build_feature_pipeline()
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)

        # 训练随机森林模型
        result = pipeline.train_model(
            X_train, y_train, X_test, y_test, model_type="random_forest"
        )

        # 验证训练结果
        assert result is not None
        assert pipeline.is_fitted is True
        assert "model" in result
        assert "metrics" in result

    def test_predict_before_fitting(self, pipeline, sample_data):
        """测试在未拟合时进行预测应该失败"""
        X, _ = sample_data

        with pytest.raises(ValueError, match="Pipeline must be fitted"):
            pipeline.predict(X)

    def test_predict_after_fitting(self, pipeline, sample_data):
        """测试拟合后进行预测"""
        X, y = sample_data

        # 训练模型
        pipeline.build_feature_pipeline()
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)
        pipeline.train_model(
            X_train, y_train, X_test, y_test, model_type="random_forest"
        )

        # 进行预测
        predictions = pipeline.predict(X_test)

        # 验证预测结果
        assert len(predictions) == len(X_test)
        assert all(pred in [0, 1] for pred in predictions)  # 二分类

    def test_predict_proba_after_fitting(self, pipeline, sample_data):
        """测试拟合后获取预测概率"""
        X, y = sample_data

        # 训练模型
        pipeline.build_feature_pipeline()
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)
        pipeline.train_model(
            X_train, y_train, X_test, y_test, model_type="random_forest"
        )

        # 获取预测概率
        probabilities = pipeline.predict_proba(X_test)

        # 验证概率结果
        assert len(probabilities) == len(X_test)
        # 二分类应该返回两个类别的概率
        assert all(len(probs) == 2 for probs in probabilities)
        # 概率和应该等于1
        assert all(abs(sum(probs) - 1.0) < 1e-10 for probs in probabilities)

    def test_evaluate_model(self, pipeline, sample_data):
        """测试模型评估"""
        X, y = sample_data

        # 训练模型
        pipeline.build_feature_pipeline()
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)
        pipeline.train_model(
            X_train, y_train, X_test, y_test, model_type="random_forest"
        )

        # 评估模型
        evaluation_result = pipeline.evaluate(X_test, y_test)

        # 验证评估结果
        assert evaluation_result is not None
        assert "accuracy" in evaluation_result
        assert "classification_report" in evaluation_result
        assert "confusion_matrix" in evaluation_result
        assert 0 <= evaluation_result["accuracy"] <= 1

    def test_save_and_load_pipeline(self, pipeline, sample_data, tmp_path):
        """测试管道保存和加载"""
        X, y = sample_data

        # 训练模型
        pipeline.build_feature_pipeline()
        X_train, X_test, y_train, y_test = pipeline.prepare_data(X, y)
        pipeline.train_model(
            X_train, y_train, X_test, y_test, model_type="random_forest"
        )

        # 保存管道
        save_path = tmp_path / "test_pipeline.pkl"
        saved_path = pipeline.save_pipeline(str(save_path))

        # 创建新管道并加载
        new_pipeline = FootballPredictionPipeline()
        new_pipeline.load_pipeline(str(saved_path))

        # 验证加载的管道
        assert new_pipeline.is_fitted is True
        assert new_pipeline.model_name == pipeline.model_name

        # 验证预测结果一致
        original_predictions = pipeline.predict(X_test)
        loaded_predictions = new_pipeline.predict(X_test)

        np.testing.assert_array_equal(original_predictions, loaded_predictions)


class TestConvenienceFunctions:
    """便捷函数测试类"""

    def test_create_simple_prediction_pipeline(self):
        """测试创建简单预测管道"""
        pipeline = create_simple_prediction_pipeline()

        assert isinstance(pipeline, FootballPredictionPipeline)
        assert pipeline.model_name == "simple_football_predictor"
        assert pipeline.use_mlflow is False

    def test_create_advanced_prediction_pipeline(self):
        """测试创建高级预测管道"""
        pipeline = create_advanced_prediction_pipeline()

        assert isinstance(pipeline, FootballPredictionPipeline)
        assert pipeline.model_name == "advanced_football_predictor"
        assert pipeline.use_mlflow is True


class TestFeatureEngineerIntegration:
    """特征工程集成测试"""

    def test_feature_pipeline_creation(self):
        """测试特征管道创建"""
        from src.features.feature_engineer import (
            FeaturePipelineBuilder,
            create_default_football_pipeline,
        )

        # 测试默认管道创建
        pipeline = create_default_football_pipeline()
        assert pipeline is not None

        # 测试自定义管道创建
        builder = FeaturePipelineBuilder()
        pipeline = builder.build_pipeline()
        assert pipeline is not None

        # 测试特征添加
        builder.add_numeric_feature("test_numeric")
        builder.add_categorical_feature("test_categorical")
        pipeline = builder.build_pipeline()
        assert pipeline is not None

    def test_feature_pipeline_summary(self):
        """测试特征管道摘要"""
        from src.features.feature_engineer import FeaturePipelineBuilder

        builder = FeaturePipelineBuilder()
        builder.add_numeric_feature("feature1")
        builder.add_categorical_feature("feature2")

        summary = builder.get_pipeline_summary()

        assert "numeric_features_count" in summary
        assert "categorical_features_count" in summary
        assert "total_features" in summary
        assert summary["numeric_features_count"] == 1
        assert summary["categorical_features_count"] == 1
        assert summary["total_features"] == 2
