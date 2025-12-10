"""
Metrics Calculator - 指标计算器

统一的模型评估指标计算。
支持分类、回归和自定义指标。
"""

from __future__ import annotations

import logging
from typing import , , Optional, , Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """模型评估指标计算器."""

    @staticmethod
    def calculate_classification_metrics(
        y_true: Union[np.ndarray, pd.Series],
        y_pred: Union[np.ndarray, pd.Series],
        y_pred_proba: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        average: str = "weighted",
    ) -> dict[str, float]:
        """
        计算分类指标.

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_pred_proba: 预测概率
            average: 多分类平均方式

        Returns:
            指标字典
        """
        metrics = {}

        try:
            # 基础分类指标
            metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
            metrics["precision"] = float(
                precision_score(y_true, y_pred, average=average, zero_division=0)
            )
            metrics["recall"] = float(
                recall_score(y_true, y_pred, average=average, zero_division=0)
            )
            metrics["f1_score"] = float(
                f1_score(y_true, y_pred, average=average, zero_division=0)
            )

            # 混淆矩阵
            cm = confusion_matrix(y_true, y_pred)
            metrics["confusion_matrix"] = cm.tolist()

            # 计算每个类别的指标
            unique_labels = np.unique(np.concatenate([y_true, y_pred]))
            for i, label in enumerate(unique_labels):
                if i < len(cm):
                    tp = cm[i, i]
                    fp = cm[:, i].sum() - tp
                    fn = cm[i, :].sum() - tp
                    cm.sum() - tp - fp - fn

                    metrics[f"class_{label}_precision"] = (
                        tp / (tp + fp) if (tp + fp) > 0 else 0.0
                    )
                    metrics[f"class_{label}_recall"] = (
                        tp / (tp + fn) if (tp + fn) > 0 else 0.0
                    )
                    metrics[f"class_{label}_f1"] = (
                        2 * tp / (2 * tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
                    )

            # 概率相关指标
            if y_pred_proba is not None:
                try:
                    metrics["log_loss"] = float(log_loss(y_true, y_pred_proba))

                    # ROC AUC (二分类或多分类)
                    if len(unique_labels) == 2:
                        if y_pred_proba.ndim == 2:
                            metrics["roc_auc"] = float(
                                roc_auc_score(y_true, y_pred_proba[:, 1])
                            )
                        else:
                            metrics["roc_auc"] = float(
                                roc_auc_score(y_true, y_pred_proba)
                            )
                    else:
                        metrics["roc_auc"] = float(
                            roc_auc_score(
                                y_true, y_pred_proba, multi_class="ovr", average=average
                            )
                        )

                    # Brier Score (概率校准)
                    if len(unique_labels) == 2 and y_pred_proba.ndim == 2:
                        metrics["brier_score"] = float(
                            brier_score_loss(y_true, y_pred_proba[:, 1])
                        )

                except Exception as e:
                    logger.warning(f"Probability metrics calculation failed: {e}")

        except Exception as e:
            logger.error(f"Metrics calculation failed: {e}")
            return {"error": str(e)}

        return metrics

    @staticmethod
    def calculate_regression_metrics(
        y_true: Union[np.ndarray, pd.Series],
        y_pred: Union[np.ndarray, pd.Series],
    ) -> dict[str, float]:
        """
        计算回归指标.

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            指标字典
        """
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        metrics = {}

        try:
            metrics["mse"] = float(mean_squared_error(y_true, y_pred))
            metrics["rmse"] = float(np.sqrt(metrics["mse"]))
            metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
            metrics["r2_score"] = float(r2_score(y_true, y_pred))

            # 平均绝对百分比误差
            metrics["mape"] = float(
                np.mean(np.abs((y_true - y_pred) / np.where(y_true != 0, y_true, 1)))
            )

        except Exception as e:
            logger.error(f"Regression metrics calculation failed: {e}")
            return {"error": str(e)}

        return metrics

    @staticmethod
    def generate_classification_report(
        y_true: Union[np.ndarray, pd.Series],
        y_pred: Union[np.ndarray, pd.Series],
        y_pred_proba: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        class_names: Optional[list[str]] = None,
    ) -> dict[str, any]:
        """
        生成详细分类报告.

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_pred_proba: 预测概率
            class_names: 类别名称

        Returns:
            详细报告字典
        """
        report = {
            "classification_metrics": MetricsCalculator.calculate_classification_metrics(
                y_true, y_pred, y_pred_proba
            )
        }

        # 添加sklearn分类报告
        try:
            sklearn_report = classification_report(
                y_true,
                y_pred,
                target_names=class_names,
                output_dict=True,
                zero_division=0,
            )
            report["sklearn_classification_report"] = sklearn_report

            # 转换numpy类型为原生类型
            def convert_numpy_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                else:
                    return obj

            report["sklearn_classification_report"] = convert_numpy_types(
                sklearn_report
            )

        except Exception as e:
            logger.warning(f"Sklearn classification report failed: {e}")

        return report

    @staticmethod
    def calculate_custom_metrics(
        y_true: Union[np.ndarray, pd.Series],
        y_pred: Union[np.ndarray, pd.Series],
        custom_functions: dict[str, callable],
    ) -> dict[str, float]:
        """
        计算自定义指标.

        Args:
            y_true: 真实值
            y_pred: 预测值
            custom_functions: 自定义指标函数字典

        Returns:
            自定义指标字典
        """
        metrics = {}

        for name, func in custom_functions.items():
            try:
                metric_value = func(y_true, y_pred)
                if isinstance(metric_value, int | float | np.number):
                    metrics[name] = float(metric_value)
                else:
                    logger.warning(
                        f"Custom metric '{name}' did not return a numeric value: {metric_value}"
                    )
            except Exception as e:
                logger.error(f"Custom metric '{name}' calculation failed: {e}")

        return metrics

    @staticmethod
    def compare_models(
        y_true: Union[np.ndarray, pd.Series],
        predictions_dict: dict[str, Union[np.ndarray, pd.Series]],
        probabilities_dict: Optional[dict[str, Union[np.ndarray, pd.DataFrame]]] = None,
    ) -> pd.DataFrame:
        """
        比较多个模型的性能.

        Args:
            y_true: 真实标签
            predictions_dict: 模型预测字典 {model_name: y_pred}
            probabilities_dict: 模型概率字典 {model_name: y_pred_proba}

        Returns:
            比较结果DataFrame
        """
        results = []

        for model_name, y_pred in predictions_dict.items():
            y_pred_proba = (
                probabilities_dict.get(model_name) if probabilities_dict else None
            )

            metrics = MetricsCalculator.calculate_classification_metrics(
                y_true, y_pred, y_pred_proba
            )
            metrics["model"] = model_name
            results.append(metrics)

        return pd.DataFrame(results)

    @staticmethod
    def calculate_calibration_metrics(
        y_true: Union[np.ndarray, pd.Series],
        y_pred_proba: Union[np.ndarray, pd.DataFrame],
        n_bins: int = 10,
    ) -> dict[str, float]:
        """
        计算概率校准指标.

        Args:
            y_true: 真实标签
            y_pred_proba: 预测概率
            n_bins: 校准区间数

        Returns:
            校准指标字典
        """
        try:
            from sklearn.calibration import calibration_curve

            if len(np.unique(y_true)) != 2:
                logger.warning("Calibration metrics only support binary classification")
                return {}

            # 获取正类概率
            if y_pred_proba.ndim == 2:
                prob_positive = y_pred_proba[:, 1]
            else:
                prob_positive = y_pred_proba

            # 计算校准曲线
            fraction_of_positives, mean_predicted_value = calibration_curve(
                y_true, prob_positive, n_bins=n_bins
            )

            # 计算校准误差
            calibration_error = np.mean(
                np.abs(fraction_of_positives - mean_predicted_value)
            )

            return {
                "calibration_error": float(calibration_error),
                "brier_score": float(brier_score_loss(y_true, prob_positive)),
                "n_bins": n_bins,
            }

        except Exception as e:
            logger.error(f"Calibration metrics calculation failed: {e}")
            return {}
