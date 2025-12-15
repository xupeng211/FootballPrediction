"""
Unit tests for Football Prediction Metrics module.

测试足球预测评估指标模块的各项功能。
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from src.evaluation.metrics import (
    Metrics, MetricsResult, evaluate_model,
)


class TestMetrics:
    """Metrics类测试"""

    @pytest.fixture
    def metrics_calculator(self):
        """创建Metrics实例"""
        return Metrics()

    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        np.random.seed(42)
        n_samples = 100

        # 生成三分类数据 (0=H, 1=D, 2=A)
        y_true = np.random.randint(0, 3, n_samples)

        # 生成预测（模拟不同质量）
        y_pred = y_true.copy()
        # 添加一些错误预测
        error_indices = np.random.choice(n_samples, size=int(n_samples * 0.3), replace=False)
        y_pred[error_indices] = np.random.randint(0, 3, len(error_indices))

        # 生成概率矩阵
        y_proba = np.random.dirichlet([1, 1, 1], n_samples)
        # 让预测类别的概率稍高一些
        for i, pred in enumerate(y_pred):
            y_proba[i, pred] = max(y_proba[i, pred], 0.5)
            # 重新归一化
            y_proba[i] = y_proba[i] / y_proba[i].sum()

        return y_true, y_pred, y_proba

    @pytest.fixture
    def sample_odds(self):
        """创建样本赔率数据"""
        np.random.seed(42)
        n_samples = 100

        # 生成合理赔率 (1.5 - 10.0)
        odds = np.random.uniform(1.5, 10.0, (n_samples, 3))

        return odds

    def test_initialization(self, metrics_calculator):
        """测试Metrics初始化"""
        assert metrics_calculator.supported_classes == ["H", "D", "A"]
        assert metrics_calculator.class_mapping == {0: "H", 1: "D", 2: "A"}

    def test_classification_metrics_basic(self, metrics_calculator, sample_data):
        """测试基本分类指标计算"""
        y_true, y_pred, y_proba = sample_data

        metrics = metrics_calculator.classification_metrics(y_true, y_pred, y_proba)

        # 验证必要指标存在
        assert "accuracy" in metrics
        assert "precision_weighted" in metrics
        assert "recall_weighted" in metrics
        assert "f1_weighted" in metrics
        assert "precision_macro" in metrics
        assert "recall_macro" in metrics
        assert "f1_macro" in metrics

        # 验证指标值范围
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision_weighted"] <= 1
        assert 0 <= metrics["recall_weighted"] <= 1
        assert 0 <= metrics["f1_weighted"] <= 1

        # 验证LogLoss存在（如果提供概率）
        if y_proba is not None:
            assert "logloss" in metrics
            assert metrics["logloss"] >= 0

    def test_classification_metrics_without_probabilities(self, metrics_calculator, sample_data):
        """测试无概率预测的分类指标"""
        y_true, y_pred, _ = sample_data

        metrics = metrics_calculator.classification_metrics(y_true, y_pred)

        # 应该仍能计算基本指标
        assert "accuracy" in metrics
        assert "precision_weighted" in metrics
        assert "logloss" not in metrics  # 无概率，不应有logloss

    def test_calibration_metrics(self, metrics_calculator, sample_data):
        """测试校准指标计算"""
        y_true, _, y_proba = sample_data

        metrics = metrics_calculator.calibration_metrics(y_true, y_proba)

        # 验证校准指标存在
        assert "brier_score_H" in metrics
        assert "brier_score_D" in metrics
        assert "brier_score_A" in metrics
        assert "brier_score_avg" in metrics

        # 验证ECE指标
        assert "ece_H" in metrics
        assert "ece_D" in metrics
        assert "ece_A" in metrics
        assert "ece_avg" in metrics

        # 验证MCE指标
        assert "mce_H" in metrics
        assert "mce_D" in metrics
        assert "mce_A" in metrics
        assert "mce_avg" in metrics

        # 验证Brier分数范围 (0, 1)
        for class_name in ["H", "D", "A"]:
            assert 0 <= metrics[f"brier_score_{class_name}"] <= 1

    def test_odds_metrics(self, metrics_calculator, sample_data, sample_odds):
        """测试博彩相关指标"""
        y_true, y_pred, y_proba = sample_data
        odds = sample_odds[:len(y_true)]  # 确保长度匹配

        metrics = metrics_calculator.odds_metrics(y_true, y_proba, odds)

        # 验证关键指标存在
        assert "total_bets" in metrics
        assert "win_rate" in metrics
        assert "total_stake" in metrics
        assert "total_winnings" in metrics
        assert "net_profit" in metrics
        assert "roi" in metrics

        # 验证指标值合理性
        if metrics["total_bets"] > 0:
            assert 0 <= metrics["win_rate"] <= 100
            assert metrics["total_stake"] >= 0

    def test_odds_metrics_no_threshold(self, metrics_calculator, sample_data, sample_odds):
        """测试高阈值下的博彩指标（可能无投注）"""
        y_true, y_pred, y_proba = sample_data
        odds = sample_odds[:len(y_true)]

        # 使用很高阈值，可能没有投注
        metrics = metrics_calculator.odds_metrics(y_true, y_proba, odds, threshold=1.0)

        # 可能没有投注
        if metrics["total_bets"] == 0:
            assert metrics["roi"] == 0
            assert metrics["win_rate"] == 0

    def test_evaluate_all(self, metrics_calculator, sample_data, sample_odds):
        """测试完整评估功能"""
        y_true, y_pred, y_proba = sample_data
        odds = sample_odds[:len(y_true)]

        result = metrics_calculator.evaluate_all(
            y_true, y_pred, y_proba, odds
        )

        # 验证返回类型
        assert isinstance(result, MetricsResult)

        # 验证基本属性
        assert hasattr(result, 'metrics')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'timestamp')

        # 验证包含所有指标类型
        assert "accuracy" in result.metrics
        assert "brier_score_avg" in result.metrics

        if result.metrics.get("total_bets", 0) > 0:
            assert "roi" in result.metrics

    def test_evaluate_all_without_odds(self, metrics_calculator, sample_data):
        """测试无赔率数据的完整评估"""
        y_true, y_pred, y_proba = sample_data

        result = metrics_calculator.evaluate_all(y_true, y_pred, y_proba)

        # 不应有博彩相关指标
        assert "total_bets" not in result.metrics
        assert "roi" not in result.metrics

        # 但应有分类和校准指标
        assert "accuracy" in result.metrics
        assert "brier_score_avg" in result.metrics

    @patch('src.evaluation.metrics.HAS_SKLEARN', False)
    def test_sklearn_unavailable(self, metrics_calculator, sample_data):
        """测试sklearn不可用时的行为"""
        y_true, y_pred, y_proba = sample_data

        # 分类指标应为空
        metrics = metrics_calculator.classification_metrics(y_true, y_pred, y_proba)
        assert metrics == {}

        # 校准指标应为空
        cal_metrics = metrics_calculator.calibration_metrics(y_true, y_proba)
        assert cal_metrics == {}

    def test_invalid_inputs(self, metrics_calculator):
        """测试无效输入处理"""
        # 空数据
        with pytest.raises((ValueError, IndexError)):
            metrics_calculator.classification_metrics([], [], None)

        # 不匹配的长度
        with pytest.raises((ValueError, IndexError)):
            y_true = [0, 1, 2]
            y_pred = [0, 1]  # 长度不匹配
            metrics_calculator.classification_metrics(y_true, y_pred, None)

        # 无效的概率矩阵
        with pytest.raises((ValueError, IndexError)):
            y_true = [0, 1, 2]
            y_pred = [0, 1, 2]
            y_proba = [[0.3, 0.7]]  # 形状不正确
            metrics_calculator.classification_metrics(y_true, y_pred, y_proba)


class TestMetricsResult:
    """MetricsResult类测试"""

    @pytest.fixture
    def sample_metrics_result(self):
        """创建样本MetricsResult"""
        metrics = {
            "accuracy": 0.85,
            "precision_weighted": 0.83,
            "recall_weighted": 0.85,
            "f1_weighted": 0.84
        }
        metadata = {
            "n_samples": 100,
            "model_name": "test_model"
        }

        return MetricsResult(
            metrics=metrics,
            metadata=metadata,
            timestamp="2024-01-01T00:00:00"
        )

    def test_metrics_result_creation(self, sample_metrics_result):
        """测试MetricsResult创建"""
        assert sample_metrics_result.metrics["accuracy"] == 0.85
        assert sample_metrics_result.metadata["n_samples"] == 100
        assert sample_metrics_result.timestamp == "2024-01-01T00:00:00"

    def test_metrics_result_to_dict(self, sample_metrics_result):
        """测试MetricsResult转字典"""
        result_dict = sample_metrics_result.to_dict()

        assert "metrics" in result_dict
        assert "metadata" in result_dict
        assert "timestamp" in result_dict
        assert result_dict["metrics"]["accuracy"] == 0.85

    def test_metrics_result_to_json(self, sample_metrics_result):
        """测试MetricsResult转JSON"""
        json_str = sample_metrics_result.to_json()

        # 验证是有效JSON
        import json
        parsed = json.loads(json_str)
        assert parsed["metrics"]["accuracy"] == 0.85


class TestEvaluateModel:
    """evaluate_model便捷函数测试"""

    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        np.random.seed(42)
        n_samples = 50

        y_true = np.random.randint(0, 3, n_samples)
        y_pred = y_true.copy()

        # 添加一些错误
        error_indices = np.random.choice(n_samples, size=int(n_samples * 0.2), replace=False)
        y_pred[error_indices] = np.random.randint(0, 3, len(error_indices))

        y_proba = np.random.dirichlet([1, 1, 1], n_samples)
        for i, pred in enumerate(y_pred):
            y_proba[i, pred] = max(y_proba[i, pred], 0.4)
            y_proba[i] = y_proba[i] / y_proba[i].sum()

        return y_true, y_pred, y_proba

    def test_evaluate_model_function(self, sample_data):
        """测试evaluate_model函数"""
        y_true, y_pred, y_proba = sample_data

        result = evaluate_model(y_true, y_pred, y_proba)

        # 验证返回类型
        assert isinstance(result, MetricsResult)

        # 验证包含基本指标
        assert "accuracy" in result.metrics
        assert "brier_score_avg" in result.metrics

    def test_evaluate_model_without_probabilities(self, sample_data):
        """测试无概率的evaluate_model函数"""
        y_true, y_pred, _ = sample_data

        result = evaluate_model(y_true, y_pred)

        # 应该仍能工作
        assert isinstance(result, MetricsResult)
        assert "accuracy" in result.metrics
        assert "logloss" not in result.metrics

    def test_evaluate_model_with_odds(self, sample_data):
        """测试包含赔率的evaluate_model函数"""
        y_true, y_pred, y_proba = sample_data

        # 创建简单赔率
        odds = np.random.uniform(2.0, 5.0, (len(y_true), 3))

        result = evaluate_model(y_true, y_pred, y_proba, odds=odds)

        # 应该包含博彩指标
        assert isinstance(result, MetricsResult)
        # 注意：由于高EV阈值，可能没有投注


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
