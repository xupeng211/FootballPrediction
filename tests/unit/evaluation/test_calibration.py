"""
Unit tests for Football Prediction Calibration module.

测试足球预测概率校准模块的各项功能。
"""

import pytest
import numpy as np
from unittest.mock import patch

from src.evaluation.calibration import (
    BaseCalibrator,
    IsotonicCalibrator,
    PlattCalibrator,
    AutoCalibrator,
    CalibrationResult,
    calibrate_probabilities,
)


class TestCalibrationResult:
    """CalibrationResult类测试"""

    @pytest.fixture
    def sample_calibration_result(self):
        """创建样本CalibrationResult"""
        return CalibrationResult(
            is_calibrated=True,
            calibration_method="isotonic",
            original_score=0.25,
            calibrated_score=0.18,
            improvement=0.07,
            calibration_params={"param1": "value1"},
            metadata={"test": True},
        )

    def test_calibration_result_creation(self, sample_calibration_result):
        """测试CalibrationResult创建"""
        assert sample_calibration_result.is_calibrated is True
        assert sample_calibration_result.calibration_method == "isotonic"
        assert sample_calibration_result.improvement == 0.07

    def test_calibration_result_to_dict(self, sample_calibration_result):
        """测试CalibrationResult转字典"""
        result_dict = sample_calibration_result.to_dict()

        assert result_dict["is_calibrated"] is True
        assert result_dict["calibration_method"] == "isotonic"
        assert result_dict["improvement"] == 0.07

    def test_calibration_result_to_json(self, sample_calibration_result):
        """测试CalibrationResult转JSON"""
        json_str = sample_calibration_result.to_json()

        import json

        parsed = json.loads(json_str)
        assert parsed["is_calibrated"] is True
        assert parsed["calibration_method"] == "isotonic"


class TestBaseCalibrator:
    """BaseCalibrator类测试"""

    @pytest.fixture
    def base_calibrator(self):
        """创建BaseCalibrator实例"""
        return BaseCalibrator(n_classes=3)

    def test_initialization(self, base_calibrator):
        """测试BaseCalibrator初始化"""
        assert base_calibrator.n_classes == 3
        assert base_calibrator.class_names == ["H", "D", "A"]
        assert base_calibrator.is_fitted is False
        assert base_calibrator.calibrators == {}

    def test_needs_calibration_positive(self, base_calibrator):
        """测试需要校准的情况"""
        # 创建 poorly calibrated probabilities
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_proba = np.array(
            [
                [0.9, 0.05, 0.05],  # 过度自信
                [0.8, 0.1, 0.1],  # 过度自信
                [0.1, 0.8, 0.1],  # 过度自信
                [0.05, 0.9, 0.05],  # 过度自信
                [0.05, 0.05, 0.9],  # 过度自信
                [0.1, 0.1, 0.8],  # 过度自信
            ]
        )

        needs_cal = base_calibrator.needs_calibration(y_true, y_proba, threshold=0.1)
        assert needs_cal is True

    def test_needs_calibration_negative(self, base_calibrator):
        """测试不需要校准的情况"""
        # 创建 well-calibrated probabilities
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_proba = np.array(
            [
                [0.7, 0.2, 0.1],
                [0.6, 0.3, 0.1],
                [0.1, 0.6, 0.3],
                [0.2, 0.7, 0.1],
                [0.1, 0.2, 0.7],
                [0.3, 0.1, 0.6],
            ]
        )

        needs_cal = base_calibrator.needs_calibration(y_true, y_proba, threshold=0.1)
        assert needs_cal is False

    @patch("src.evaluation.calibration.HAS_SKLEARN", False)
    def test_sklearn_unavailable(self, base_calibrator):
        """测试sklearn不可用时的情况"""
        y_true = np.array([0, 1, 2])
        y_proba = np.array([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]])

        needs_cal = base_calibrator.needs_calibration(y_true, y_proba)
        assert needs_cal is False


class TestIsotonicCalibrator:
    """IsotonicCalibrator类测试"""

    @pytest.fixture
    def isotonic_calibrator(self):
        """创建IsotonicCalibrator实例"""
        return IsotonicCalibrator(n_classes=3)

    @pytest.fixture
    def sample_calibration_data(self):
        """创建校准样本数据"""
        np.random.seed(42)
        n_samples = 100

        y_true = np.random.randint(0, 3, n_samples)

        # 创建一些需要校准的概率
        y_proba = np.zeros((n_samples, 3))
        for i in range(n_samples):
            true_class = y_true[i]
            # 给正确类别偏高概率，但需要校准
            y_proba[i] = np.random.dirichlet([1, 1, 1])
            y_proba[i, true_class] = max(y_proba[i, true_class], 0.6)

        return y_true, y_proba

    def test_initialization(self, isotonic_calibrator):
        """测试IsotonicCalibrator初始化"""
        assert isotonic_calibrator.n_classes == 3
        assert isotonic_calibrator.calibration_method == "isotonic"

    def test_fit_and_transform(self, isotonic_calibrator, sample_calibration_data):
        """测试IsotonicCalibrator的拟合和变换"""
        y_true, y_proba = sample_calibration_data

        # 训练校准器
        fitted_calibrator = isotonic_calibrator.fit(y_true, y_proba)
        assert fitted_calibrator is isotonic_calibrator
        assert isotonic_calibrator.is_fitted is True

        # 应用校准
        calibrated_proba = isotonic_calibrator.transform(y_proba)

        # 验证输出形状
        assert calibrated_proba.shape == y_proba.shape

        # 验证概率和为1
        prob_sums = calibrated_proba.sum(axis=1)
        np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    def test_fit_transform(self, isotonic_calibrator, sample_calibration_data):
        """测试fit_transform方法"""
        y_true, y_proba = sample_calibration_data

        calibrated_proba = isotonic_calibrator.fit_transform(y_true, y_proba)

        assert isotonic_calibrator.is_fitted is True
        assert calibrated_proba.shape == y_proba.shape

    def test_transform_without_fit(self, isotonic_calibrator, sample_calibration_data):
        """测试未拟合时的变换"""
        _, y_proba = sample_calibration_data

        with pytest.raises(ValueError, match="Calibrator must be fitted"):
            isotonic_calibrator.transform(y_proba)

    def test_save_and_load(
        self, isotonic_calibrator, sample_calibration_data, tmp_path
    ):
        """测试保存和加载功能"""
        y_true, y_proba = sample_calibration_data

        # 训练并保存
        isotonic_calibrator.fit(y_true, y_proba)
        save_path = tmp_path / "isotonic_calibrator.pkl"
        isotonic_calibrator.save(save_path)

        assert save_path.exists()

        # 加载
        loaded_calibrator = IsotonicCalibrator.load(save_path)

        assert loaded_calibrator.n_classes == isotonic_calibrator.n_classes
        assert loaded_calibrator.is_fitted is True
        assert (
            loaded_calibrator.calibration_method
            == isotonic_calibrator.calibration_method
        )

    def test_invalid_probabilities(self, isotonic_calibrator):
        """测试无效概率处理"""
        y_true = np.array([0, 1, 2])
        # 形状不正确的概率
        y_proba = np.array([[0.5, 0.5]])  # 应该是3列

        with pytest.raises(ValueError, match="Expected 3 classes"):
            isotonic_calibrator.fit(y_true, y_proba)


class TestPlattCalibrator:
    """PlattCalibrator类测试"""

    @pytest.fixture
    def platt_calibrator(self):
        """创建PlattCalibrator实例"""
        return PlattCalibrator(n_classes=3)

    @pytest.fixture
    def sample_calibration_data(self):
        """创建校准样本数据"""
        np.random.seed(42)
        n_samples = 50

        y_true = np.random.randint(0, 3, n_samples)
        y_proba = np.random.dirichlet([1, 1, 1], n_samples)

        return y_true, y_proba

    def test_initialization(self, platt_calibrator):
        """测试PlattCalibrator初始化"""
        assert platt_calibrator.n_classes == 3
        assert platt_calibrator.calibration_method == "platt"

    def test_fit_and_transform(self, platt_calibrator, sample_calibration_data):
        """测试PlattCalibrator的拟合和变换"""
        y_true, y_proba = sample_calibration_data

        # 训练校准器
        fitted_calibrator = platt_calibrator.fit(y_true, y_proba)
        assert fitted_calibrator is platt_calibrator
        assert platt_calibrator.is_fitted is True

        # 应用校准
        calibrated_proba = platt_calibrator.transform(y_proba)

        # 验证输出形状
        assert calibrated_proba.shape == y_proba.shape

        # 验证概率和为1
        prob_sums = calibrated_proba.sum(axis=1)
        np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    def test_save_and_load(self, platt_calibrator, sample_calibration_data, tmp_path):
        """测试保存和加载功能"""
        y_true, y_proba = sample_calibration_data

        # 训练并保存
        platt_calibrator.fit(y_true, y_proba)
        save_path = tmp_path / "platt_calibrator.pkl"
        platt_calibrator.save(save_path)

        # 加载
        loaded_calibrator = PlattCalibrator.load(save_path)

        assert loaded_calibrator.n_classes == platt_calibrator.n_classes
        assert loaded_calibrator.is_fitted is True


class TestAutoCalibrator:
    """AutoCalibrator类测试"""

    @pytest.fixture
    def auto_calibrator(self):
        """创建AutoCalibrator实例"""
        return AutoCalibrator(n_classes=3)

    @pytest.fixture
    def sample_calibration_data(self):
        """创建校准样本数据"""
        np.random.seed(42)
        n_samples = 80

        y_true = np.random.randint(0, 3, n_samples)
        y_proba = np.random.dirichlet([1, 1, 1], n_samples)

        return y_true, y_proba

    def test_initialization(self, auto_calibrator):
        """测试AutoCalibrator初始化"""
        assert auto_calibrator.n_classes == 3
        assert auto_calibrator.calibration_threshold == 0.05
        assert auto_calibrator.best_calibrator is None

    def test_calibrate_success(self, auto_calibrator, sample_calibration_data):
        """测试自动校准成功"""
        y_true, y_proba = sample_calibration_data

        result = auto_calibrator.calibrate(y_true, y_proba)

        assert isinstance(result, CalibrationResult)
        assert hasattr(result, "is_calibrated")
        assert hasattr(result, "calibration_method")

    def test_calibrate_no_need(self, auto_calibrator):
        """测试不需要校准的情况"""
        # 创建perfect校准的数据
        y_true = np.array([0, 1, 2])
        y_proba = np.array([[0.9, 0.05, 0.05], [0.05, 0.9, 0.05], [0.05, 0.05, 0.9]])

        result = auto_calibrator.calibrate(y_true, y_proba)

        assert isinstance(result, CalibrationResult)

    def test_transform_after_calibrate(self, auto_calibrator, sample_calibration_data):
        """测试校准后的变换"""
        y_true, y_proba = sample_calibration_data

        # 先校准
        result = auto_calibrator.calibrate(y_true, y_proba)

        if result.is_calibrated:
            # 然后变换
            calibrated_proba = auto_calibrator.transform(y_proba)
            assert calibrated_proba.shape == y_proba.shape

            # 验证概率和为1
            prob_sums = calibrated_proba.sum(axis=1)
            np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    def test_transform_without_calibrate(
        self, auto_calibrator, sample_calibration_data
    ):
        """测试未校准时的变换"""
        _, y_proba = sample_calibration_data

        with pytest.raises(ValueError, match="No calibrator has been trained"):
            auto_calibrator.transform(y_proba)

    def test_save_and_load(self, auto_calibrator, sample_calibration_data, tmp_path):
        """测试保存和加载功能"""
        y_true, y_proba = sample_calibration_data

        # 校准并保存
        auto_calibrator.calibrate(y_true, y_proba)
        save_path = tmp_path / "auto_calibrator.pkl"
        auto_calibrator.save(save_path)

        # 加载
        loaded_calibrator = AutoCalibrator.load(save_path)

        assert loaded_calibrator.n_classes == auto_calibrator.n_classes
        assert (
            loaded_calibrator.calibration_threshold
            == auto_calibrator.calibration_threshold
        )


class TestCalibrationFunctions:
    """校准便捷函数测试"""

    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        np.random.seed(42)
        n_samples = 60

        y_true = np.random.randint(0, 3, n_samples)
        y_proba = np.random.dirichlet([1, 1, 1], n_samples)

        return y_true, y_proba

    def test_calibrate_probabilities_auto(self, sample_data):
        """测试自动校准函数"""
        y_true, y_proba = sample_data

        calibrated_proba, result = calibrate_probabilities(
            y_true, y_proba, method="auto"
        )

        assert isinstance(result, CalibrationResult)
        assert calibrated_proba.shape == y_proba.shape

        # 验证概率和为1
        prob_sums = calibrated_proba.sum(axis=1)
        np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    def test_calibrate_probabilities_isotonic(self, sample_data):
        """测试Isotonic校准函数"""
        y_true, y_proba = sample_data

        calibrated_proba, result = calibrate_probabilities(
            y_true, y_proba, method="isotonic"
        )

        assert isinstance(result, CalibrationResult)
        assert result.calibration_method == "isotonic"
        assert calibrated_proba.shape == y_proba.shape

    def test_calibrate_probabilities_platt(self, sample_data):
        """测试Platt校准函数"""
        y_true, y_proba = sample_data

        calibrated_proba, result = calibrate_probabilities(
            y_true, y_proba, method="platt"
        )

        assert isinstance(result, CalibrationResult)
        assert result.calibration_method == "platt"
        assert calibrated_proba.shape == y_proba.shape

    def test_calibrate_probabilities_invalid_method(self, sample_data):
        """测试无效校准方法"""
        y_true, y_proba = sample_data

        with pytest.raises(ValueError, match="Unknown calibration method"):
            calibrate_probabilities(y_true, y_proba, method="invalid_method")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
