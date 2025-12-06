"""
Football Prediction Evaluation Metrics

核心评估指标模块，提供足球预测模型的全套评估指标。
包含分类指标、概率质量指标、以及博彩相关指标。

Author: Football Prediction Team
Version: 1.0.0
"""

import json
import numpy as np
import pandas as pd
from typing import Optional, Union, Any
from dataclasses import dataclass
import logging

try:
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        log_loss,
        brier_score_loss,
        roc_auc_score,
        roc_curve,
        classification_report,
        confusion_matrix,
    )
    from sklearn.preprocessing import label_binarize
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("sklearn not available - some metrics will be disabled")

logger = logging.getLogger(__name__)


@dataclass
class MetricsResult:
    """评估指标结果数据类"""
    metrics: dict[str, float]
    metadata: dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "metrics": self.metrics,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class Metrics:
    """
    足球预测评估指标计算器

    支持三大类指标：
    1. 分类指标：准确率、精确率、召回率、F1、LogLoss等
    2. 概率质量指标：校准误差、最大校准误差、Brier分数等
    3. 博彩相关指标：期望值、收益率、投注建议等
    """

    def __init__(self):
        """初始化评估指标计算器"""
        self.supported_classes = ["H", "D", "A"]  # Home, Draw, Away
        self.class_mapping = {0: "H", 1: "D", 2: "A"}

    def classification_metrics(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_pred: Union[np.ndarray, pd.Series, list],
        y_proba: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        average: str = "weighted"
    ) -> dict[str, float]:
        """
        计算分类指标

        Args:
            y_true: 真实标签 (0=H, 1=D, 2=A)
            y_pred: 预测标签
            y_proba: 预测概率矩阵 (n_samples, 3)
            average: 多分类平均方法 ('weighted', 'macro', 'micro')

        Returns:
            分类指标字典
        """
        if not HAS_SKLEARN:
            logger.error("sklearn not available - cannot compute classification metrics")
            return {}

        # 转换为numpy数组
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        metrics = {}

        try:
            # 基本分类指标
            metrics["accuracy"] = float(accuracy_score(y_true, y_pred))

            # 多分类精确率、召回率、F1
            metrics["precision_weighted"] = float(precision_score(
                y_true, y_pred, average=average, zero_division=0
            ))
            metrics["recall_weighted"] = float(recall_score(
                y_true, y_pred, average=average, zero_division=0
            ))
            metrics["f1_weighted"] = float(f1_score(
                y_true, y_pred, average=average, zero_division=0
            ))

            # Macro平均（对每个类别平等看待）
            metrics["precision_macro"] = float(precision_score(
                y_true, y_pred, average="macro", zero_division=0
            ))
            metrics["recall_macro"] = float(recall_score(
                y_true, y_pred, average="macro", zero_division=0
            ))
            metrics["f1_macro"] = float(f1_score(
                y_true, y_pred, average="macro", zero_division=0
            ))

            # LogLoss (需要概率预测)
            if y_proba is not None:
                y_proba = np.array(y_proba)
                if y_proba.shape[1] == 3:  # 三分类
                    metrics["logloss"] = float(log_loss(y_true, y_proba))
                else:
                    logger.warning(f"Expected 3 classes for probabilities, got {y_proba.shape[1]}")

            # 各类别单独指标
            for i, class_name in self.supported_classes:
                if i < len(np.unique(y_true)):
                    metrics[f"precision_{class_name}"] = float(precision_score(
                        y_true, y_pred, labels=[i], average="binary", zero_division=0
                    ))
                    metrics[f"recall_{class_name}"] = float(recall_score(
                        y_true, y_pred, labels=[i], average="binary", zero_division=0
                    ))
                    metrics[f"f1_{class_name}"] = float(f1_score(
                        y_true, y_pred, labels=[i], average="binary", zero_division=0
                    ))

        except Exception as e:
            logger.error(f"Error calculating classification metrics: {e}")

        return metrics

    def calibration_metrics(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
        n_bins: int = 10
    ) -> dict[str, float]:
        """
        计算概率校准指标

        Args:
            y_true: 真实标签 (0=H, 1=D, 2=A)
            y_proba: 预测概率矩阵 (n_samples, 3)
            n_bins: 校准区间数

        Returns:
            校准指标字典
        """
        if not HAS_SKLEARN:
            logger.error("sklearn not available - cannot compute calibration metrics")
            return {}

        y_true = np.array(y_true)
        y_proba = np.array(y_proba)

        metrics = {}

        try:
            if y_proba.shape[1] != 3:
                logger.warning(f"Expected 3 classes for calibration, got {y_proba.shape[1]}")
                return metrics

            # 计算每个类别的校准指标
            for i, class_name in self.supported_classes:
                # 二值化当前类别的标签
                y_true_binary = (y_true == i).astype(int)
                y_prob_class = y_proba[:, i]

                # Brier分数（概率预测质量的经典指标）
                metrics[f"brier_score_{class_name}"] = float(
                    brier_score_loss(y_true_binary, y_prob_class)
                )

                # 计算校准曲线和误差
                try:
                    from sklearn.calibration import calibration_curve
                    fraction_of_positives, mean_predicted_value = calibration_curve(
                        y_true_binary, y_prob_class, n_bins=n_bins
                    )

                    # 期望校准误差 (Expected Calibration Error, ECE)
                    ece = self._calculate_ece(
                        fraction_of_positives, mean_predicted_value, y_prob_class, n_bins
                    )
                    metrics[f"ece_{class_name}"] = float(ece)

                    # 最大校准误差 (Maximum Calibration Error, MCE)
                    mce = np.max(np.abs(fraction_of_positives - mean_predicted_value))
                    metrics[f"mce_{class_name}"] = float(mce)

                except Exception as e:
                    logger.warning(f"Error calculating calibration for class {class_name}: {e}")

            # 总体校准指标
            if len(metrics) > 0:
                # 平均Brier分数
                brier_scores = [metrics[k] for k in metrics.keys() if k.startswith("brier_score_")]
                metrics["brier_score_avg"] = float(np.mean(brier_scores))

                # 平均ECE
                ece_scores = [metrics[k] for k in metrics.keys() if k.startswith("ece_")]
                metrics["ece_avg"] = float(np.mean(ece_scores))

                # 平均MCE
                mce_scores = [metrics[k] for k in metrics.keys() if k.startswith("mce_")]
                metrics["mce_avg"] = float(np.mean(mce_scores))

        except Exception as e:
            logger.error(f"Error calculating calibration metrics: {e}")

        return metrics

    def odds_metrics(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_proba: Union[np.ndarray, pd.DataFrame],
        odds: Union[np.ndarray, pd.DataFrame],
        stake: float = 1.0,
        threshold: float = 0.1
    ) -> dict[str, float]:
        """
        计算博彩相关指标

        Args:
            y_true: 真实结果 (0=H, 1=D, 2=A)
            y_proba: 预测概率矩阵 (n_samples, 3)
            odds: 赔率矩阵 (n_samples, 3) - 注意：这里是decimal odds
            stake: 每注投注金额
            threshold: 价值投注阈值 (EV > threshold)

        Returns:
            博彩指标字典
        """
        y_true = np.array(y_true)
        y_proba = np.array(y_proba)
        odds = np.array(odds)

        metrics = {}

        try:
            if y_proba.shape != odds.shape:
                logger.error(f"Probability shape {y_proba.shape} doesn't match odds shape {odds.shape}")
                return metrics

            n_samples = len(y_true)
            total_stake = 0.0
            total_winnings = 0.0
            total_bets = 0
            winning_bets = 0

            # 计算每场比赛的期望值和实际收益
            ev_values = []
            actual_returns = []

            for i in range(n_samples):
                true_class = y_true[i]
                prob_pred = y_proba[i]
                odds_values = odds[i]

                # 找到期望值最高的投注选项
                ev_per_class = []
                for j in range(3):
                    # EV = (probability * odds) - 1
                    ev = (prob_pred[j] * odds_values[j]) - 1
                    ev_per_class.append(ev)

                best_bet_class = np.argmax(ev_per_class)
                best_ev = ev_per_class[best_bet_class]

                # 只对有价值的选择下注
                if best_ev > threshold:
                    total_bets += 1
                    total_stake += stake

                    # 计算实际收益
                    if best_bet_class == true_class:
                        winnings = stake * odds_values[best_bet_class]
                        total_winnings += winnings
                        winning_bets += 1
                        actual_return = winnings - stake  # 净收益
                    else:
                        actual_return = - stake  # 损失

                    ev_values.append(best_ev)
                    actual_returns.append(actual_return)

            # 计算关键指标
            if total_bets > 0:
                metrics["total_bets"] = float(total_bets)
                metrics["win_rate"] = float(winning_bets / total_bets)
                metrics["total_stake"] = float(total_stake)
                metrics["total_winnings"] = float(total_winnings)
                metrics["net_profit"] = float(total_winnings - total_stake)
                metrics["roi"] = float(((total_winnings - total_stake) / total_stake) * 100)

                if ev_values:
                    metrics["avg_ev"] = float(np.mean(ev_values))
                    metrics["avg_actual_return"] = float(np.mean(actual_returns))
                    metrics["total_actual_return"] = float(np.sum(actual_returns))

                    # 夏普比率（收益/风险）
                    if len(actual_returns) > 1:
                        return_std = np.std(actual_returns)
                        if return_std > 0:
                            metrics["sharpe_ratio"] = float(np.mean(actual_returns) / return_std)

                # 胜率与期望胜率对比
                if ev_values:
                    expected_win_rate = np.mean([1/3 for _ in ev_values])  # 假设随机胜率33%
                    actual_win_rate = winning_bets / total_bets
                    metrics["win_rate_vs_random"] = float(actual_win_rate - expected_win_rate)

        except Exception as e:
            logger.error(f"Error calculating odds metrics: {e}")

        return metrics

    def _calculate_ece(
        self,
        fraction_of_positives: np.ndarray,
        mean_predicted_value: np.ndarray,
        y_prob: np.ndarray,
        n_bins: int
    ) -> float:
        """计算期望校准误差 (Expected Calibration Error)"""
        try:
            # 计算每个区间的样本数
            bin_edges = np.linspace(0, 1, n_bins + 1)
            bin_indices = np.digitize(y_prob, bin_edges) - 1

            ece = 0.0
            for i in range(n_bins):
                mask = (bin_indices == i)
                if np.sum(mask) > 0:
                    bin_weight = np.sum(mask) / len(y_prob)
                    ece += bin_weight * np.abs(
                        fraction_of_positives[i] - mean_predicted_value[i]
                    )

            return ece
        except Exception:
            return 0.0

    def evaluate_all(
        self,
        y_true: Union[np.ndarray, pd.Series, list],
        y_pred: Union[np.ndarray, pd.Series, list],
        y_proba: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        odds: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        **kwargs
    ) -> MetricsResult:
        """
        计算所有评估指标

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_proba: 预测概率
            odds: 赔率矩阵
            **kwargs: 其他参数

        Returns:
            完整的评估结果
        """
        from datetime import datetime

        all_metrics = {}

        # 分类指标
        classification_metrics = self.classification_metrics(y_true, y_pred, y_proba)
        all_metrics.update(classification_metrics)

        # 校准指标（需要概率预测）
        if y_proba is not None:
            calibration_metrics = self.calibration_metrics(y_true, y_proba)
            all_metrics.update(calibration_metrics)

        # 博彩指标（需要赔率）
        if odds is not None and y_proba is not None:
            odds_metrics = self.odds_metrics(y_true, y_proba, odds, **kwargs)
            all_metrics.update(odds_metrics)

        # 元数据
        metadata = {
            "n_samples": len(y_true),
            "n_classes": len(np.unique(y_true)),
            "has_probabilities": y_proba is not None,
            "has_odds": odds is not None,
            "classes": [self.class_mapping.get(i, f"class_{i}") for i in sorted(np.unique(y_true))]
        }

        return MetricsResult(
            metrics=all_metrics,
            metadata=metadata,
            timestamp=datetime.now().isoformat()
        )


# 便捷函数
def evaluate_model(
    y_true: Union[np.ndarray, pd.Series, list],
    y_pred: Union[np.ndarray, pd.Series, list],
    y_proba: Optional[Union[np.ndarray, pd.DataFrame]] = None,
    odds: Optional[Union[np.ndarray, pd.DataFrame]] = None,
    **kwargs
) -> MetricsResult:
    """
    便捷的模型评估函数

    Args:
        y_true: 真实标签
        y_pred: 预测标签
        y_proba: 预测概率
        odds: 赔率矩阵
        **kwargs: 其他参数

    Returns:
        评估结果
    """
    calculator = Metrics()
    return calculator.evaluate_all(y_true, y_pred, y_proba, odds, **kwargs)
