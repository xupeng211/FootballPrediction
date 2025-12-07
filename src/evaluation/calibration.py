"""
Football Prediction Model Calibration

模型概率校准模块，提供多种校准方法来改善预测概率的质量。
支持Isotonic回归和Platt缩放（sigmoid）两种主流校准方法。

Author: Football Prediction Team
Version: 1.0.0
"""

import json
import pickle
import numpy as np
import pandas as pd
from typing import Optional, Union, Any
from dataclasses import dataclass
from pathlib import Path
import logging
import warnings

try:
    from sklearn.calibration import CalibratedClassifierCV, calibration_curve
    from sklearn.isotonic import IsotonicRegression
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import brier_score_loss

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("sklearn not available - calibration features disabled")

logger = logging.getLogger(__name__)

# 忽略IsotonicRegression的收敛警告
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.isotonic")


@dataclass
class CalibrationResult:
    """校准结果数据类"""

    is_calibrated: bool
    calibration_method: str
    original_score: float
    calibrated_score: float
    improvement: float
    calibration_params: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "is_calibrated": self.is_calibrated,
            "calibration_method": self.calibration_method,
            "original_score": self.original_score,
            "calibrated_score": self.calibrated_score,
            "improvement": self.improvement,
            "calibration_params": self.calibration_params,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class BaseCalibrator:
    """校准器基类"""

    def __init__(self, n_classes: int = 3):
        """
        初始化校准器

        Args:
            n_classes: 分类数量（默认3类：H/D/A）
        """
        self.n_classes = n_classes
        self.class_names = ["H", "D", "A"]
        self.is_fitted = False
        self.calibrators = {}
        self.calibration_method = "base"

    def fit(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
    ) -> "BaseCalibrator":
        """
        训练校准器

        Args:
            y_true: 真实标签
            y_proba: 预测概率矩阵

        Returns:
            训练后的校准器
        """
        raise NotImplementedError("Subclasses must implement fit method")

    def transform(self, y_proba: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        应用校准

        Args:
            y_proba: 原始预测概率

        Returns:
            校准后的概率
        """
        raise NotImplementedError("Subclasses must implement transform method")

    def fit_transform(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
    ) -> np.ndarray:
        """训练并应用校准"""
        return self.fit(y_true, y_proba).transform(y_proba)

    def needs_calibration(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
        threshold: float = 0.05,
    ) -> bool:
        """
        判断是否需要校准

        Args:
            y_true: 真实标签
            y_proba: 预测概率
            threshold: 校准阈值

        Returns:
            是否需要校准
        """
        if not HAS_SKLEARN:
            return False

        y_true = np.array(y_true)
        y_proba = np.array(y_proba)

        # 计算平均Brier分数
        brier_scores = []
        for i in range(self.n_classes):
            y_true_binary = (y_true == i).astype(int)
            y_prob_class = y_proba[:, i]
            brier = brier_score_loss(y_true_binary, y_prob_class)
            brier_scores.append(brier)

        avg_brier = np.mean(brier_scores)

        # 如果Brier分数过高，说明需要校准
        # 注意：这个阈值可能需要根据实际情况调整
        return avg_brier > threshold

    def save(self, filepath: Union[str, Path]) -> None:
        """保存校准器"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        calibration_data = {
            "calibrators": self.calibrators,
            "n_classes": self.n_classes,
            "class_names": self.class_names,
            "is_fitted": self.is_fitted,
            "calibration_method": self.calibration_method,
        }

        with open(filepath, "wb") as f:
            pickle.dump(calibration_data, f)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "BaseCalibrator":
        """加载校准器"""
        filepath = Path(filepath)

        with open(filepath, "rb") as f:
            calibration_data = pickle.load(f)

        calibrator = cls(n_classes=calibration_data["n_classes"])
        calibrator.calibrators = calibration_data["calibrators"]
        calibrator.class_names = calibration_data["class_names"]
        calibrator.is_fitted = calibration_data["is_fitted"]
        calibrator.calibration_method = calibration_data["calibration_method"]

        return calibrator


class IsotonicCalibrator(BaseCalibrator):
    """Isotonic回归校准器"""

    def __init__(self, n_classes: int = 3, out_of_bounds: str = "clip"):
        """
        初始化Isotonic校准器

        Args:
            n_classes: 分类数量
            out_of_bounds: 超出训练数据范围的处理方式
        """
        super().__init__(n_classes)
        self.calibration_method = "isotonic"
        self.out_of_bounds = out_of_bounds

        if not HAS_SKLEARN:
            raise ImportError("sklearn is required for IsotonicCalibrator")

    def fit(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
    ) -> "IsotonicCalibrator":
        """
        训练Isotonic校准器

        Args:
            y_true: 真实标签
            y_proba: 预测概率矩阵

        Returns:
            训练后的校准器
        """
        y_true = np.array(y_true)
        y_proba = np.array(y_proba)

        if y_proba.shape[1] != self.n_classes:
            raise ValueError(
                f"Expected {self.n_classes} classes, got {y_proba.shape[1]}"
            )

        # 为每个类别训练独立的Isotonic回归器
        for i in range(self.n_classes):
            # 二值化当前类别的标签
            y_true_binary = (y_true == i).astype(int)
            y_prob_class = y_proba[:, i]

            # 训练Isotonic回归器
            isotonic = IsotonicRegression(
                out_of_bounds=self.out_of_bounds, increasing=True
            )

            # 处理极端概率值，避免数值问题
            y_prob_class_clipped = np.clip(y_prob_class, 1e-6, 1 - 1e-6)

            try:
                isotonic.fit(y_prob_class_clipped, y_true_binary)
                self.calibrators[i] = isotonic
            except Exception as e:
                logger.warning(f"Failed to fit isotonic regression for class {i}: {e}")
                # 如果拟合失败，使用恒等函数
                self.calibrators[i] = None

        self.is_fitted = True
        return self

    def transform(self, y_proba: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        应用Isotonic校准

        Args:
            y_proba: 原始预测概率

        Returns:
            校准后的概率
        """
        if not self.is_fitted:
            raise ValueError("Calibrator must be fitted before transformation")

        y_proba = np.array(y_proba)
        if y_proba.shape[1] != self.n_classes:
            raise ValueError(
                f"Expected {self.n_classes} classes, got {y_proba.shape[1]}"
            )

        calibrated_proba = np.zeros_like(y_proba)

        for i in range(self.n_classes):
            y_prob_class = y_proba[:, i]
            y_prob_class_clipped = np.clip(y_prob_class, 1e-6, 1 - 1e-6)

            if self.calibrators[i] is not None:
                calibrated_proba[:, i] = self.calibrators[i].transform(
                    y_prob_class_clipped
                )
            else:
                # 如果校准器拟合失败，使用原始概率
                calibrated_proba[:, i] = y_prob_class

        # 确保概率和为1
        calibrated_proba = calibrated_proba / calibrated_proba.sum(
            axis=1, keepdims=True
        )

        return calibrated_proba


class PlattCalibrator(BaseCalibrator):
    """Platt缩放校准器（Sigmoid校准）"""

    def __init__(self, n_classes: int = 3, method: str = "sigmoid"):
        """
        初始化Platt校准器

        Args:
            n_classes: 分类数量
            method: 校准方法 ("sigmoid" 或 "isotonic")
        """
        super().__init__(n_classes)
        self.calibration_method = "platt"
        self.method = method

        if not HAS_SKLEARN:
            raise ImportError("sklearn is required for PlattCalibrator")

    def fit(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
    ) -> "PlattCalibrator":
        """
        训练Platt校准器

        Args:
            y_true: 真实标签
            y_proba: 预测概率矩阵

        Returns:
            训练后的校准器
        """
        y_true = np.array(y_true)
        y_proba = np.array(y_proba)

        if y_proba.shape[1] != self.n_classes:
            raise ValueError(
                f"Expected {self.n_classes} classes, got {y_proba.shape[1]}"
            )

        # 使用sklearn的CalibratedClassifierCV进行Platt缩放
        # 注意：我们需要一个基础分类器来包装
        from sklearn.base import BaseEstimator, ClassifierMixin

        class DummyClassifier(BaseEstimator, ClassifierMixin):
            """虚拟分类器，用于包装概率预测"""

            def __init__(self, proba_matrix):
                self.proba_matrix = proba_matrix

            def fit(self, X, y):
                return self

            def predict_proba(self, X):
                return self.proba_matrix

            def predict(self, X):
                return np.argmax(self.proba_matrix, axis=1)

        try:
            # 创建虚拟分类器
            dummy_clf = DummyClassifier(y_proba)

            # 使用CalibratedClassifierCV进行校准
            calibrated_clf = CalibratedClassifierCV(
                dummy_clf, method=self.method, cv="prefit"  # 使用已拟合的分类器
            )

            # 拟合校准器
            calibrated_clf.fit(np.arange(len(y_true)).reshape(-1, 1), y_true)
            self.calibrators["main"] = calibrated_clf

        except Exception as e:
            logger.warning(f"Failed to fit Platt calibration: {e}")
            self.calibrators["main"] = None

        self.is_fitted = True
        return self

    def transform(self, y_proba: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        应用Platt校准

        Args:
            y_proba: 原始预测概率

        Returns:
            校准后的概率
        """
        if not self.is_fitted:
            raise ValueError("Calibrator must be fitted before transformation")

        if self.calibrators["main"] is None:
            # 如果校准失败，返回原始概率
            return np.array(y_proba)

        calibrated_proba = self.calibrators["main"].predict_proba(
            np.arange(len(y_proba)).reshape(-1, 1)
        )

        return calibrated_proba


class AutoCalibrator:
    """自动选择最佳校准方法的校准器"""

    def __init__(self, n_classes: int = 3, calibration_threshold: float = 0.05):
        """
        初始化自动校准器

        Args:
            n_classes: 分类数量
            calibration_threshold: 校准阈值
        """
        self.n_classes = n_classes
        self.calibration_threshold = calibration_threshold
        self.best_calibrator = None
        self.calibration_result = None

    def calibrate(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
    ) -> CalibrationResult:
        """
        自动选择并应用最佳校准方法

        Args:
            y_true: 真实标签
            y_proba: 预测概率矩阵

        Returns:
            校准结果
        """
        if not HAS_SKLEARN:
            return CalibrationResult(
                is_calibrated=False,
                calibration_method="none",
                original_score=0.0,
                calibrated_score=0.0,
                improvement=0.0,
                calibration_params={},
                metadata={"error": "sklearn not available"},
            )

        y_true = np.array(y_true)
        y_proba = np.array(y_proba)

        # 计算原始Brier分数
        original_brier = self._calculate_average_brier(y_true, y_proba)

        # 检查是否需要校准
        base_calibrator = BaseCalibrator(self.n_classes)
        needs_calibration = base_calibrator.needs_calibration(
            y_true, y_proba, self.calibration_threshold
        )

        if not needs_calibration:
            return CalibrationResult(
                is_calibrated=False,
                calibration_method="none",
                original_score=original_brier,
                calibrated_score=original_brier,
                improvement=0.0,
                calibration_params={},
                metadata={"message": "No calibration needed"},
            )

        # 尝试不同的校准方法
        calibrators_to_try = [
            ("isotonic", IsotonicCalibrator),
            ("platt", PlattCalibrator),
        ]

        best_score = original_brier
        best_calibrator = None
        best_method = "none"
        best_params = {}

        for method_name, calibrator_class in calibrators_to_try:
            try:
                calibrator = calibrator_class(self.n_classes)

                # 交叉验证方式训练和评估
                calibrated_proba = self._cross_validate_calibration(
                    calibrator, y_true, y_proba
                )

                calibrated_brier = self._calculate_average_brier(
                    y_true, calibrated_proba
                )

                if calibrated_brier < best_score:
                    best_score = calibrated_brier
                    best_calibrator = calibrator
                    best_method = method_name
                    best_params = calibrator.calibrators

                logger.info(
                    f"{method_name} calibration: {original_brier:.4f} -> {calibrated_brier:.4f}"
                )

            except Exception as e:
                logger.warning(f"Failed to test {method_name} calibration: {e}")

        # 训练最佳校准器
        if best_calibrator is not None:
            best_calibrator.fit(y_true, y_proba)
            self.best_calibrator = best_calibrator

        improvement = original_brier - best_score

        result = CalibrationResult(
            is_calibrated=best_calibrator is not None,
            calibration_method=best_method,
            original_score=original_brier,
            calibrated_score=best_score,
            improvement=improvement,
            calibration_params=best_params,
            metadata={
                "n_samples": len(y_true),
                "n_classes": self.n_classes,
                "threshold": self.calibration_threshold,
                "tested_methods": [method for method, _ in calibrators_to_try],
            },
        )

        self.calibration_result = result
        return result

    def _calculate_average_brier(
        self, y_true: np.ndarray, y_proba: np.ndarray
    ) -> float:
        """计算平均Brier分数"""
        brier_scores = []
        for i in range(self.n_classes):
            y_true_binary = (y_true == i).astype(int)
            y_prob_class = y_proba[:, i]
            brier = brier_score_loss(y_true_binary, y_prob_class)
            brier_scores.append(brier)
        return np.mean(brier_scores)

    def _cross_validate_calibration(
        self,
        calibrator: BaseCalibrator,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        cv_folds: int = 5,
    ) -> np.ndarray:
        """交叉验证评估校准效果"""
        from sklearn.model_selection import StratifiedKFold

        len(y_true)
        calibrated_proba = np.zeros_like(y_proba)

        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)

        for train_idx, val_idx in skf.split(y_proba, y_true):
            # 训练集校准
            calibrator_fold = calibrator.__class__(self.n_classes)
            calibrator_fold.fit(y_true[train_idx], y_proba[train_idx])

            # 验证集应用校准
            calibrated_proba[val_idx] = calibrator_fold.transform(y_proba[val_idx])

        return calibrated_proba

    def transform(self, y_proba: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """应用训练好的最佳校准器"""
        if self.best_calibrator is None:
            raise ValueError("No calibrator has been trained. Call calibrate() first.")
        return self.best_calibrator.transform(y_proba)

    def save(self, filepath: Union[str, Path]) -> None:
        """保存自动校准器"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        calibration_data = {
            "best_calibrator": self.best_calibrator,
            "calibration_result": self.calibration_result,
            "n_classes": self.n_classes,
            "calibration_threshold": self.calibration_threshold,
        }

        with open(filepath, "wb") as f:
            pickle.dump(calibration_data, f)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "AutoCalibrator":
        """加载自动校准器"""
        filepath = Path(filepath)

        with open(filepath, "rb") as f:
            calibration_data = pickle.load(f)

        auto_calibrator = cls(
            n_classes=calibration_data["n_classes"],
            calibration_threshold=calibration_data["calibration_threshold"],
        )
        auto_calibrator.best_calibrator = calibration_data["best_calibrator"]
        auto_calibrator.calibration_result = calibration_data["calibration_result"]

        return auto_calibrator


# 便捷函数
def calibrate_probabilities(
    y_true: Union[np.ndarray, pd.Series, list],
    y_proba: Union[np.ndarray, pd.DataFrame],
    method: str = "auto",
    **kwargs,
) -> tuple[np.ndarray, CalibrationResult]:
    """
    便捷的概率校准函数

    Args:
        y_true: 真实标签
        y_proba: 预测概率矩阵
        method: 校准方法 ("auto", "isotonic", "platt")
        **kwargs: 其他参数

    Returns:
        校准后的概率和校准结果
    """
    if method == "auto":
        calibrator = AutoCalibrator(**kwargs)
        result = calibrator.calibrate(y_true, y_proba)
        if result.is_calibrated:
            calibrated_proba = calibrator.transform(y_proba)
        else:
            calibrated_proba = y_proba
        return calibrated_proba, result

    elif method == "isotonic":
        calibrator = IsotonicCalibrator(**kwargs)
        calibrator.fit(y_true, y_proba)
        calibrated_proba = calibrator.transform(y_proba)
        result = CalibrationResult(
            is_calibrated=True,
            calibration_method="isotonic",
            original_score=0.0,  # 需要计算
            calibrated_score=0.0,  # 需要计算
            improvement=0.0,  # 需要计算
            calibration_params=calibrator.calibrators,
            metadata={},
        )
        return calibrated_proba, result

    elif method == "platt":
        calibrator = PlattCalibrator(**kwargs)
        calibrator.fit(y_true, y_proba)
        calibrated_proba = calibrator.transform(y_proba)
        result = CalibrationResult(
            is_calibrated=True,
            calibration_method="platt",
            original_score=0.0,  # 需要计算
            calibrated_score=0.0,  # 需要计算
            improvement=0.0,  # 需要计算
            calibration_params=calibrator.calibrators,
            metadata={},
        )
        return calibrated_proba, result

    else:
        raise ValueError(f"Unknown calibration method: {method}")
