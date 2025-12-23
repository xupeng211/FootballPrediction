#!/usr/bin/env python3
"""
V19.0 概率校准器 - Step C 核心实现

使用 Isotonic Regression 对 XGBoost 输出进行概率校准
目标：确保模型说"胜率 60%"时，10 场里真的能赢 6 场

Author: V19.0 Quant Team
Purpose: 消除过度自信，实现真实概率预测
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import joblib
import json

from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
import xgboost as xgb

logger = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """校准结果"""
    brier_score_before: float
    brier_score_after: float
    brier_score_improvement: float
    log_loss_before: float
    log_loss_after: float
    calibration_data: Dict[str, Any]
    reliability_diagram: List[Dict[str, float]]


class V19ProbabilityCalibrator:
    """
    V19.0 概率校准器

    核心功能：
    1. 使用 Isotonic Regression 对 XGBoost 概率输出进行校准
    2. 确保校准后的概率具有真实含义
    3. 生成可靠性图表 (Reliability Diagram)
    4. 计算 Brier Score 改进

    校准方法对比：
    - Platt Scaling (Sigmoid): 适合小样本，但假设Sigmoid形状
    - Isotonic Regression: 更灵活，适合大多数情况，本系统采用此方法
    """

    def __init__(self, method: str = 'isotonic', n_bins: int = 10):
        """
        初始化概率校准器

        Args:
            method: 校准方法 ('isotonic' 或 'platt')
            n_bins: 可靠性图表的分组数量
        """
        self.method = method
        self.n_bins = n_bins

        self.calibrators: Dict[str, Any] = {}  # 每个类别的校准器
        self.is_fitted = False

        # 校准统计
        self.stats = {
            'brier_score_before': None,
            'brier_score_after': None,
            'brier_score_improvement_pct': None,
            'log_loss_before': None,
            'log_loss_after': None,
        }

        logger.info(f"V19.0 概率校准器初始化完成 (方法: {method})")

    def fit(
        self,
        model: xgb.XGBClassifier,
        X_calib: np.ndarray,
        y_calib: np.ndarray,
        class_names: List[str] = None
    ) -> CalibrationResult:
        """
        拟合概率校准器

        Args:
            model: 已训练的 XGBoost 模型
            X_calib: 校准集特征
            y_calib: 校准集标签
            class_names: 类别名称 ['Away', 'Draw', 'Home']

        Returns:
            CalibrationResult: 校准结果
        """
        if class_names is None:
            class_names = ['Away', 'Draw', 'Home']

        logger.info(f"开始拟合概率校准器...")
        logger.info(f"  校准集大小: {len(X_calib)}")
        logger.info(f"  类别分布: {np.bincount(y_calib)}")

        # 获取原始概率
        raw_proba = model.predict_proba(X_calib)

        # 计算 Brier Score (校准前)
        brier_before = self._calculate_brier_score(y_calib, raw_proba)
        log_loss_before = log_loss(y_calib, raw_proba)

        logger.info(f"  校准前 Brier Score: {brier_before:.4f}")
        logger.info(f"  校准前 Log Loss: {log_loss_before:.4f}")

        # 对每个类别进行独立的 Isotonic Regression 校准
        calibrated_proba = np.zeros_like(raw_proba)

        for class_idx, class_name in enumerate(class_names):
            if self.method == 'isotonic':
                # Isotonic Regression
                calibrator = IsotonicRegression(out_of_bounds='clip')
            else:
                # Platt Scaling 使用 sklearn 的 CalibratedClassifierCV
                calibrator = CalibratedClassifierCV(
                    base_estimator=model,
                    method='sigmoid',
                    cv='prefit'
                )
                calibrator.fit(X_calib, y_calib)
                self.calibrators[class_name] = calibrator
                continue

            # 拟合 Isotonic Regression
            calibrator.fit(raw_proba[:, class_idx], (y_calib == class_idx).astype(int))

            # 存储校准器
            self.calibrators[class_name] = calibrator

            # 应用校准
            if self.method == 'isotonic':
                calibrated_proba[:, class_idx] = calibrator.predict(raw_proba[:, class_idx])

        # 归一化校准后的概率
        calibrated_proba = calibrated_proba / calibrated_proba.sum(axis=1, keepdims=True)

        # 计算 Brier Score (校准后)
        brier_after = self._calculate_brier_score(y_calib, calibrated_proba)
        log_loss_after = log_loss(y_calib, calibrated_proba)

        improvement = (brier_before - brier_after) / brier_before * 100

        logger.info(f"  校准后 Brier Score: {brier_after:.4f}")
        logger.info(f"  校准后 Log Loss: {log_loss_after:.4f}")
        logger.info(f"  改进幅度: {improvement:.1f}%")

        # 存储统计
        self.stats['brier_score_before'] = brier_before
        self.stats['brier_score_after'] = brier_after
        self.stats['brier_score_improvement_pct'] = improvement
        self.stats['log_loss_before'] = log_loss_before
        self.stats['log_loss_after'] = log_loss_after

        # 生成可靠性图表数据
        reliability_diagram = self._generate_reliability_diagram(y_calib, calibrated_proba)

        self.is_fitted = True

        # 校准数据
        calibration_data = {
            'raw_proba_mean': raw_proba.mean(axis=0).tolist(),
            'calibrated_proba_mean': calibrated_proba.mean(axis=0).tolist(),
            'class_names': class_names,
        }

        return CalibrationResult(
            brier_score_before=brier_before,
            brier_score_after=brier_after,
            brier_score_improvement=improvement,
            log_loss_before=log_loss_before,
            log_loss_after=log_loss_after,
            calibration_data=calibration_data,
            reliability_diagram=reliability_diagram
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        预测校准后的概率

        Args:
            X: 特征矩阵

        Returns:
            np.ndarray: 校准后的概率 (n_samples, n_classes)
        """
        if not self.is_fitted:
            raise ValueError("校准器尚未拟合，请先调用 fit() 方法")

        # 首先使用模型获取原始概率
        if hasattr(self, '_model') and self._model is not None:
            raw_proba = self._model.predict_proba(X)
        else:
            raise ValueError("未找到基础模型")

        # 应用校准
        calibrated_proba = np.zeros_like(raw_proba)

        for class_idx, (class_name, calibrator) in enumerate(self.calibrators.items()):
            if isinstance(calibrator, IsotonicRegression):
                calibrated_proba[:, class_idx] = calibrator.predict(raw_proba[:, class_idx])
            elif hasattr(calibrator, 'predict_proba'):
                # CalibratedClassifierCV
                calibrated_proba = calibrator.predict_proba(X)
                break

        # 归一化
        if not any(isinstance(c, CalibratedClassifierCV) for c in self.calibrators.values()):
            calibrated_proba = calibrated_proba / calibrated_proba.sum(axis=1, keepdims=True)

        return calibrated_proba

    def set_base_model(self, model: xgb.XGBClassifier):
        """设置基础模型（用于 predict_proba）"""
        self._model = model

    def _calculate_brier_score(self, y_true: np.ndarray, y_proba: np.ndarray) -> float:
        """
        计算 Brier Score

        Args:
            y_true: 真实标签
            y_proba: 预测概率

        Returns:
            float: Brier Score
        """
        # 多类别 Brier Score
        n_classes = y_proba.shape[1]
        y_one_hot = np.zeros_like(y_proba)

        for i in range(n_classes):
            y_one_hot[:, i] = (y_true == i).astype(int)

        return np.mean((y_proba - y_one_hot) ** 2)

    def _generate_reliability_diagram(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = None
    ) -> List[Dict[str, float]]:
        """
        生成可靠性图表数据

        Args:
            y_true: 真实标签
            y_proba: 预测概率
            n_bins: 分组数量

        Returns:
            List[Dict]: 可靠性数据
        """
        if n_bins is None:
            n_bins = self.n_bins

        reliability_data = []
        n_classes = y_proba.shape[1]

        for class_idx in range(n_classes):
            # 获取该类别的预测概率
            class_proba = y_proba[:, class_idx]
            class_actual = (y_true == class_idx).astype(int)

            # 分组
            bin_edges = np.linspace(0, 1, n_bins + 1)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

            for i in range(n_bins):
                mask = (class_proba >= bin_edges[i]) & (class_proba < bin_edges[i + 1])
                mask |= (class_proba == 1.0) & (i == n_bins - 1)  # 包含边界

                if mask.sum() == 0:
                    continue

                avg_predicted = class_proba[mask].mean()
                avg_actual = class_actual[mask].mean()
                count = mask.sum()

                reliability_data.append({
                    'class': class_idx,
                    'bin': i,
                    'predicted': avg_predicted,
                    'actual': avg_actual,
                    'count': count,
                })

        return reliability_data

    def save(self, path: str):
        """保存校准器"""
        save_data = {
            'calibrators': self.calibrators,
            'method': self.method,
            'n_bins': self.n_bins,
            'is_fitted': self.is_fitted,
            'stats': self.stats,
        }

        joblib.dump(save_data, path)
        logger.info(f"✅ 校准器已保存: {path}")

    def load(self, path: str) -> 'V19ProbabilityCalibrator':
        """加载校准器"""
        save_data = joblib.load(path)

        self.calibrators = save_data['calibrators']
        self.method = save_data['method']
        self.n_bins = save_data['n_bins']
        self.is_fitted = save_data['is_fitted']
        self.stats = save_data['stats']

        logger.info(f"✅ 校准器已加载: {path}")
        return self

    def get_calibration_report(self) -> str:
        """生成校准报告"""
        if not self.is_fitted:
            return "校准器尚未拟合"

        report = []
        report.append("=" * 80)
        report.append("V19.0 概率校准报告")
        report.append("=" * 80)
        report.append("")
        report.append(f"校准方法: {self.method.upper()}")
        report.append("")
        report.append("Brier Score (越低越好):")
        report.append(f"  校准前: {self.stats['brier_score_before']:.4f}")
        report.append(f"  校准后: {self.stats['brier_score_after']:.4f}")
        report.append(f"  改进: {self.stats['brier_score_improvement_pct']:.1f}%")
        report.append("")
        report.append("Log Loss (越低越好):")
        report.append(f"  校准前: {self.stats['log_loss_before']:.4f}")
        report.append(f"  校准后: {self.stats['log_loss_after']:.4f}")
        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def calibrate_xgboost_model(
    model_path: str,
    X_calib: np.ndarray,
    y_calib: np.ndarray,
    output_path: str = None,
    method: str = 'isotonic'
) -> Tuple[V19ProbabilityCalibrator, CalibrationResult]:
    """
    校准 XGBoost 模型

    Args:
        model_path: 模型路径
        X_calib: 校准集特征
        y_calib: 校准集标签
        output_path: 输出路径
        method: 校准方法

    Returns:
        Tuple[校准器, 校准结果]
    """
    # 加载模型
    model = xgb.XGBClassifier()
    model.load_model(model_path)

    logger.info(f"已加载模型: {model_path}")

    # 创建并拟合校准器
    calibrator = V19ProbabilityCalibrator(method=method)
    result = calibrator.fit(model, X_calib, y_calib)

    # 保存校准器
    if output_path:
        calibrator.save(output_path)

    return calibrator, result


def main():
    """演示概率校准"""
    print("V19.0 概率校准器演示")
    print("=" * 80)

    # 创建示例数据
    np.random.seed(42)
    n_samples = 1000

    X = np.random.randn(n_samples, 20)
    y = np.random.randint(0, 3, n_samples)

    # 分割数据
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42)
    X_calib, X_test, y_calib, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    print(f"训练集: {len(X_train)} 样本")
    print(f"校准集: {len(X_calib)} 样本")
    print(f"测试集: {len(X_test)} 样本")

    # 训练基础模型
    print("\n训练 XGBoost 模型...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='mlogloss'
    )
    model.fit(X_train, y_train)

    # 校准
    print("\n进行概率校准...")
    calibrator = V19ProbabilityCalibrator(method='isotonic')
    calibrator.set_base_model(model)
    result = calibrator.fit(model, X_calib, y_calib)

    # 测试
    print("\n测试集评估:")
    raw_proba = model.predict_proba(X_test)
    calibrated_proba = calibrator.predict_proba(X_test)

    test_brier_raw = calibrator._calculate_brier_score(y_test, raw_proba)
    test_brier_cal = calibrator._calculate_brier_score(y_test, calibrated_proba)

    print(f"  原始 Brier Score: {test_brier_raw:.4f}")
    print(f"  校准后 Brier Score: {test_brier_cal:.4f}")
    print(f"  改进: {(test_brier_raw - test_brier_cal) / test_brier_raw * 100:.1f}%")

    # 打印报告
    print("\n" + calibrator.get_calibration_report())


if __name__ == "__main__":
    main()
