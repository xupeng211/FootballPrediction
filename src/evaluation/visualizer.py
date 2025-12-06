"""
Football Prediction Evaluation Visualizer

足球预测评估可视化模块，提供全面的图表和报告生成功能。
支持ROC曲线、校准图、收益曲线等多种可视化。

Author: Football Prediction Team
Version: 1.0.0
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Union, Any
from pathlib import Path
from datetime import datetime
import logging

try:
    from sklearn.metrics import roc_curve, auc, precision_recall_curve
    from sklearn.calibration import calibration_curve
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("sklearn not available - some visualizations will be disabled")

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 设置样式
sns.set_style("whitegrid")
plt.style.use('default')

logger = logging.getLogger(__name__)


class EvaluationVisualizer:
    """评估可视化器"""

    def __init__(self, output_dir: Union[str, Path] = None, dpi: int = 300):
        """
        初始化可视化器

        Args:
            output_dir: 输出目录
            dpi: 图片分辨率
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(f"artifacts/eval/evaluation_{timestamp}")
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi

        # 颜色配置
        self.colors = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'success': '#2ca02c',
            'danger': '#d62728',
            'warning': '#ff7f0e',
            'info': '#17a2b8',
            'light': '#f8f9fa',
            'dark': '#343a40'
        }

        self.class_names = ['主胜(H)', '平局(D)', '客胜(A)']
        self.class_colors = ['#28a745', '#ffc107', '#dc3545']

    def save_figure(self, fig: plt.Figure, filename: str,
                   formats: list[str] = None, bbox_inches: str = 'tight') -> list[str]:
        """
        保存图表到多种格式

        Args:
            fig: matplotlib图表对象
            filename: 文件名（不含扩展名）
            formats: 保存格式列表
            bbox_inches: 边界框设置

        Returns:
            保存的文件路径列表
        """
        if formats is None:
            formats = ['png']
        saved_paths = []
        for fmt in formats:
            filepath = self.output_dir / f"{filename}.{fmt}"
            fig.savefig(filepath, dpi=self.dpi, bbox_inches=bbox_inches,
                       facecolor='white', edgecolor='none')
            saved_paths.append(str(filepath))
            logger.info(f"Saved figure: {filepath}")

        return saved_paths

    def plot_roc_curves(self, y_true: np.ndarray, y_proba: np.ndarray,
                       title: str = "ROC曲线分析", save_name: str = "roc_curves") -> list[str]:
        """
        绘制ROC曲线

        Args:
            y_true: 真实标签
            y_proba: 预测概率矩阵
            title: 图表标题
            save_name: 保存文件名

        Returns:
            保存的文件路径列表
        """
        if not HAS_SKLEARN:
            logger.error("sklearn not available - cannot plot ROC curves")
            return []

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # 绘制每个类别的ROC曲线
        for i, (class_name, color) in enumerate(zip(self.class_names, self.class_colors, strict=False)):
            ax = axes[i // 2, i % 2] if i < 3 else axes[1, 1]

            # 二值化当前类别的标签
            y_true_binary = (y_true == i).astype(int)
            y_prob_class = y_proba[:, i]

            # 计算ROC曲线
            fpr, tpr, _ = roc_curve(y_true_binary, y_prob_class)
            roc_auc = auc(fpr, tpr)

            # 绘制ROC曲线
            ax.plot(fpr, tpr, color=color, linewidth=2,
                   label=f'{class_name} (AUC = {roc_auc:.3f})')
            ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.7)

            ax.set_xlabel('假正率 (FPR)', fontsize=12)
            ax.set_ylabel('真正率 (TPR)', fontsize=12)
            ax.set_title(f'{class_name} - ROC曲线', fontsize=14, fontweight='bold')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)

        # 微平均ROC曲线
        if len(self.class_names) <= 3:
            ax = axes[1, 1]
            ax.clear()

            # 计算微平均ROC曲线
            from sklearn.preprocessing import label_binarize
            y_true_bin = label_binarize(y_true, classes=range(len(self.class_names)))

            fpr, tpr, _ = roc_curve(y_true_bin.ravel(), y_proba.ravel())
            roc_auc = auc(fpr, tpr)

            ax.plot(fpr, tpr, color=self.colors['primary'], linewidth=3,
                   label=f'微平均 (AUC = {roc_auc:.3f})')
            ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.7)

            ax.set_xlabel('假正率 (FPR)', fontsize=12)
            ax.set_ylabel('真正率 (TPR)', fontsize=12)
            ax.set_title('微平均ROC曲线', fontsize=14, fontweight='bold')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return self.save_figure(fig, save_name)

    def plot_calibration_curves(self, y_true: np.ndarray, y_proba: np.ndarray,
                               n_bins: int = 10, title: str = "概率校准曲线",
                               save_name: str = "calibration_curves") -> list[str]:
        """
        绘制校准曲线

        Args:
            y_true: 真实标签
            y_proba: 预测概率矩阵
            n_bins: 校准区间数
            title: 图表标题
            save_name: 保存文件名

        Returns:
            保存的文件路径列表
        """
        if not HAS_SKLEARN:
            logger.error("sklearn not available - cannot plot calibration curves")
            return []

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # 绘制每个类别的校准曲线
        for i, (class_name, color) in enumerate(zip(self.class_names, self.class_colors, strict=False)):
            ax = axes[i // 2, i % 2] if i < 3 else axes[1, 1]

            # 二值化当前类别的标签
            y_true_binary = (y_true == i).astype(int)
            y_prob_class = y_proba[:, i]

            # 计算校准曲线
            fraction_of_positives, mean_predicted_value = calibration_curve(
                y_true_binary, y_prob_class, n_bins=n_bins
            )

            # 绘制校准曲线
            ax.plot(mean_predicted_value, fraction_of_positives, "s-",
                   color=color, linewidth=2, markersize=6, label=f'{class_name}')
            ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.7, label='完美校准')

            # 添加直方图
            ax.hist(y_prob_class, bins=20, range=(0, 1), alpha=0.3,
                   color=color, density=True)

            ax.set_xlabel('平均预测概率', fontsize=12)
            ax.set_ylabel('实际正例比例', fontsize=12)
            ax.set_title(f'{class_name} - 校准曲线', fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)

        # 整体校准评估
        if len(self.class_names) <= 3:
            ax = axes[1, 1]
            ax.clear()

            # 计算整体校准误差
            calibration_errors = []
            for i in range(len(self.class_names)):
                y_true_binary = (y_true == i).astype(int)
                y_prob_class = y_proba[:, i]

                fraction_of_positives, mean_predicted_value = calibration_curve(
                    y_true_binary, y_prob_class, n_bins=n_bins
                )

                ce = np.mean(np.abs(fraction_of_positives - mean_predicted_value))
                calibration_errors.append(ce)

            # 绘制校准误差柱状图
            bars = ax.bar(self.class_names, calibration_errors, color=self.class_colors)
            ax.set_ylabel('校准误差 (ECE)', fontsize=12)
            ax.set_title('各类别校准误差', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')

            # 添加数值标签
            for bar, error in zip(bars, calibration_errors, strict=False):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{error:.3f}', ha='center', va='bottom')

        plt.tight_layout()
        return self.save_figure(fig, save_name)

    def plot_prediction_distribution(self, y_true: np.ndarray, y_pred: np.ndarray,
                                   y_proba: np.ndarray, title: str = "预测分布分析",
                                   save_name: str = "prediction_distribution") -> list[str]:
        """
        绘制预测分布图

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_proba: 预测概率矩阵
            title: 图表标题
            save_name: 保存文件名

        Returns:
            保存的文件路径列表
        """
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # 概率分布直方图
        for i, (class_name, color) in enumerate(zip(self.class_names, self.class_colors, strict=False)):
            ax = axes[0, i]

            # 预测概率分布
            y_prob_class = y_proba[:, i]
            ax.hist(y_prob_class, bins=30, alpha=0.7, color=color,
                   label=f'{class_name} 预测概率', edgecolor='black')

            # 添加统计信息
            mean_prob = np.mean(y_prob_class)
            ax.axvline(mean_prob, color='red', linestyle='--', linewidth=2,
                      label=f'均值: {mean_prob:.3f}')

            ax.set_xlabel('预测概率', fontsize=12)
            ax.set_ylabel('频次', fontsize=12)
            ax.set_title(f'{class_name} 概率分布', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

        # 混淆矩阵热力图
        ax_cm = axes[1, 0]
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_true, y_pred)

        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax_cm,
                   xticklabels=self.class_names, yticklabels=self.class_names)
        ax_cm.set_xlabel('预测标签', fontsize=12)
        ax_cm.set_ylabel('真实标签', fontsize=12)
        ax_cm.set_title('混淆矩阵', fontsize=14, fontweight='bold')

        # 预测置信度分布
        ax_conf = axes[1, 1]
        confidences = np.max(y_proba, axis=1)
        ax_conf.hist(confidences, bins=30, alpha=0.7, color=self.colors['primary'],
                    edgecolor='black')
        ax_conf.axvline(np.mean(confidences), color='red', linestyle='--', linewidth=2,
                       label=f'平均置信度: {np.mean(confidences):.3f}')
        ax_conf.set_xlabel('最大预测概率', fontsize=12)
        ax_conf.set_ylabel('频次', fontsize=12)
        ax_conf.set_title('预测置信度分布', fontsize=14, fontweight='bold')
        ax_conf.legend()
        ax_conf.grid(True, alpha=0.3)

        # 置信度vs准确率分析
        ax_acc = axes[1, 2]
        confidence_bins = np.linspace(0.5, 1.0, 10)
        accuracy_by_conf = []
        confidence_centers = []

        for i in range(len(confidence_bins) - 1):
            lower, upper = confidence_bins[i], confidence_bins[i + 1]
            mask = (confidences >= lower) & (confidences < upper)

            if np.sum(mask) > 0:
                accuracy = np.mean(y_pred[mask] == y_true[mask])
                accuracy_by_conf.append(accuracy)
                confidence_centers.append((lower + upper) / 2)

        if accuracy_by_conf:
            ax_acc.plot(confidence_centers, accuracy_by_conf, 'o-',
                        color=self.colors['primary'], linewidth=2, markersize=6)
            ax_acc.plot([0.5, 1.0], [0.5, 1.0], 'k--', linewidth=1, alpha=0.7,
                       label='完美校准')
            ax_acc.set_xlabel('置信度', fontsize=12)
            ax_acc.set_ylabel('实际准确率', fontsize=12)
            ax_acc.set_title('置信度vs准确率', fontsize=14, fontweight='bold')
            ax_acc.legend()
            ax_acc.grid(True, alpha=0.3)
            ax_acc.set_ylim([0, 1])

        plt.tight_layout()
        return self.save_figure(fig, save_name)

    def plot_backtest_results(self, backtest_result, title: str = "回测结果分析",
                             save_name: str = "backtest_results") -> list[str]:
        """
        绘制回测结果图表

        Args:
            backtest_result: 回测结果对象
            title: 图表标题
            save_name: 保存文件名

        Returns:
            保存的文件路径列表
        """
        if not backtest_result.bets:
            logger.warning("No bets to visualize")
            return []

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # 1. 资金曲线
        ax_equity = axes[0, 0]
        equity_curve = backtest_result.equity_curve
        bet_indices = list(range(len(equity_curve)))

        ax_equity.plot(bet_indices, equity_curve, color=self.colors['primary'],
                      linewidth=2, label='资金曲线')
        ax_equity.axhline(y=backtest_result.initial_bankroll, color='red',
                          linestyle='--', linewidth=1, alpha=0.7,
                          label=f'初始资金: {backtest_result.initial_bankroll:.0f}')

        ax_equity.set_xlabel('投注序号', fontsize=12)
        ax_equity.set_ylabel('资金', fontsize=12)
        ax_equity.set_title(f'资金曲线 (ROI: {backtest_result.roi:.2f}%)',
                          fontsize=14, fontweight='bold')
        ax_equity.legend()
        ax_equity.grid(True, alpha=0.3)

        # 2. 累计收益
        ax_cumulative = axes[0, 1]
        profits = [bet.profit for bet in backtest_result.bets]
        cumulative_profits = np.cumsum(profits)

        ax_cumulative.plot(range(1, len(cumulative_profits) + 1), cumulative_profits,
                          color=self.colors['success'] if backtest_result.net_profit > 0 else self.colors['danger'],
                          linewidth=2)
        ax_cumulative.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        ax_cumulative.set_xlabel('投注序号', fontsize=12)
        ax_cumulative.set_ylabel('累计收益', fontsize=12)
        ax_cumulative.set_title(f'累计收益曲线 (总收益: {backtest_result.net_profit:.2f})',
                               fontsize=14, fontweight='bold')
        ax_cumulative.grid(True, alpha=0.3)

        # 3. 每笔收益分布
        ax_profits = axes[0, 2]
        positive_profits = [p for p in profits if p > 0]
        negative_profits = [p for p in profits if p < 0]

        ax_profits.hist(positive_profits, bins=30, alpha=0.7, color=self.colors['success'],
                       label=f'盈利 ({len(positive_profits)}笔)', edgecolor='black')
        ax_profits.hist(negative_profits, bins=30, alpha=0.7, color=self.colors['danger'],
                       label=f'亏损 ({len(negative_profits)}笔)', edgecolor='black')
        ax_profits.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        ax_profits.set_xlabel('单笔收益', fontsize=12)
        ax_profits.set_ylabel('频次', fontsize=12)
        ax_profits.set_title(f'收益分布 (平均: {backtest_result.avg_profit_per_bet:.2f})',
                            fontsize=14, fontweight='bold')
        ax_profits.legend()
        ax_profits.grid(True, alpha=0.3)

        # 4. 投注类型分布
        ax_bet_types = axes[1, 0]
        bet_types = [bet.bet_type.value for bet in backtest_result.bets]
        bet_type_counts = pd.Series(bet_types).value_counts()

        colors = [self.class_colors[i] for i in range(len(bet_type_counts))]
        bars = ax_bet_types.bar(bet_type_counts.index, bet_type_counts.values, color=colors)
        ax_bet_types.set_xlabel('投注类型', fontsize=12)
        ax_bet_types.set_ylabel('投注次数', fontsize=12)
        ax_bet_types.set_title('投注类型分布', fontsize=14, fontweight='bold')
        ax_bet_types.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for bar, count in zip(bars, bet_type_counts.values, strict=False):
            height = bar.get_height()
            ax_bet_types.text(bar.get_x() + bar.get_width()/2., height,
                             f'{count}', ha='center', va='bottom')

        # 5. 胜率分析
        ax_winrate = axes[1, 1]
        categories = ['整体', '主胜', '平局', '客胜']
        win_rates = []

        # 整体胜率
        win_rates.append(backtest_result.win_rate / 100)

        # 各类别胜率
        for _i, class_name in enumerate(['H', 'D', 'A']):
            class_bets = [bet for bet in backtest_result.bets if bet.bet_type.value == class_name]
            if class_bets:
                class_win_rate = sum(1 for bet in class_bets if bet.won) / len(class_bets)
                win_rates.append(class_win_rate)
            else:
                win_rates.append(0)

        colors = [self.colors['primary']] + self.class_colors[:3]
        bars = ax_winrate.bar(categories, win_rates, color=colors)
        ax_winrate.set_ylabel('胜率', fontsize=12)
        ax_winrate.set_title('胜率分析', fontsize=14, fontweight='bold')
        ax_winrate.set_ylim([0, 1])
        ax_winrate.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for bar, rate in zip(bars, win_rates, strict=False):
            height = bar.get_height()
            ax_winrate.text(bar.get_x() + bar.get_width()/2., height,
                           f'{rate:.3f}', ha='center', va='bottom')

        # 6. 风险指标
        ax_risk = axes[1, 2]
        risk_metrics = {
            '最大回撤': backtest_result.max_drawdown,
            '最大连续亏损': backtest_result.max_consecutive_losses,
            '夏普比率': backtest_result.sharpe_ratio,
            '盈利因子': backtest_result.profit_factor if backtest_result.profit_factor != float('inf') else 10
        }

        metric_names = list(risk_metrics.keys())
        metric_values = list(risk_metrics.values())

        # 归一化到相同尺度进行比较
        normalized_values = []
        for name, value in zip(metric_names, metric_values, strict=False):
            if name == '最大回撤':
                normalized_values.append(value / backtest_result.initial_bankroll)
            elif name == '最大连续亏损':
                normalized_values.append(value / backtest_result.total_bets)
            else:
                normalized_values.append(value / 10)  # 缩放到0-1范围

        colors = [self.colors['warning'] if '回撤' in name or '亏损' in name
                 else self.colors['success'] if name == '盈利因子' else self.colors['info']
                 for name in metric_names]

        bars = ax_risk.barh(metric_names, normalized_values, color=colors)
        ax_risk.set_xlabel('归一化值', fontsize=12)
        ax_risk.set_title('风险指标', fontsize=14, fontweight='bold')
        ax_risk.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        return self.save_figure(fig, save_name)

    def plot_metrics_summary(self, metrics_result, title: str = "评估指标总览",
                           save_name: str = "metrics_summary") -> list[str]:
        """
        绘制评估指标总览图

        Args:
            metrics_result: 评估指标结果
            title: 图表标题
            save_name: 保存文件名

        Returns:
            保存的文件路径列表
        """
        metrics = metrics_result.metrics

        # 选择关键指标进行可视化
        key_metrics = {
            '准确率': metrics.get('accuracy', 0),
            '加权F1': metrics.get('f1_weighted', 0),
            '平均ECE': 1 - metrics.get('ece_avg', 0),  # 转换为准确率形式
            '平均Brier分数': 1 - metrics.get('brier_score_avg', 0)  # 转换为准确率形式
        }

        if 'roi' in metrics:
            key_metrics['投资回报率'] = max(0, metrics['roi'] / 100)  # 归一化

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # 1. 关键指标雷达图
        categories = list(key_metrics.keys())
        values = list(key_metrics.values())

        # 闭合雷达图
        categories += [categories[0]]
        values += [values[0]]

        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        ax1.plot(angles, values, 'o-', linewidth=2, color=self.colors['primary'])
        ax1.fill(angles, values, alpha=0.25, color=self.colors['primary'])
        ax1.set_xticks(angles[:-1])
        ax1.set_xticklabels(categories[:-1])
        ax1.set_ylim([0, 1])
        ax1.set_title('关键指标雷达图', fontsize=14, fontweight='bold')
        ax1.grid(True)

        # 2. 指标分布柱状图
        ax2.bar(categories[:-1], values[:-1], color=self.colors['primary'])
        ax2.set_ylabel('指标值', fontsize=12)
        ax2.set_title('指标值分布', fontsize=14, fontweight='bold')
        ax2.set_ylim([0, 1])
        ax2.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for i, (_cat, val) in enumerate(zip(categories[:-1], values[:-1], strict=False)):
            ax2.text(i, val + 0.02, f'{val:.3f}', ha='center', va='bottom')

        plt.tight_layout()
        return self.save_figure(fig, save_name)

    def create_comprehensive_report(self, y_true: np.ndarray, y_pred: np.ndarray,
                                  y_proba: np.ndarray, backtest_result=None,
                                  metrics_result=None,
                                  model_name: str = "Football Prediction Model") -> dict[str, list[str]]:
        """
        创建综合评估报告

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_proba: 预测概率矩阵
            backtest_result: 回测结果
            metrics_result: 评估指标结果
            model_name: 模型名称

        Returns:
            生成的图表文件路径字典
        """
        report_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. ROC曲线
        try:
            roc_files = self.plot_roc_curves(y_true, y_proba,
                                           title=f"{model_name} - ROC曲线分析",
                                           save_name=f"{timestamp}_roc_curves")
            report_files['roc_curves'] = roc_files
        except Exception as e:
            logger.error(f"Error plotting ROC curves: {e}")

        # 2. 校准曲线
        try:
            calibration_files = self.plot_calibration_curves(y_true, y_proba,
                                                          title=f"{model_name} - 概率校准曲线",
                                                          save_name=f"{timestamp}_calibration_curves")
            report_files['calibration_curves'] = calibration_files
        except Exception as e:
            logger.error(f"Error plotting calibration curves: {e}")

        # 3. 预测分布
        try:
            distribution_files = self.plot_prediction_distribution(y_true, y_pred, y_proba,
                                                               title=f"{model_name} - 预测分布分析",
                                                               save_name=f"{timestamp}_prediction_distribution")
            report_files['prediction_distribution'] = distribution_files
        except Exception as e:
            logger.error(f"Error plotting prediction distribution: {e}")

        # 4. 回测结果
        if backtest_result:
            try:
                backtest_files = self.plot_backtest_results(backtest_result,
                                                         title=f"{model_name} - 回测结果分析",
                                                         save_name=f"{timestamp}_backtest_results")
                report_files['backtest_results'] = backtest_files
            except Exception as e:
                logger.error(f"Error plotting backtest results: {e}")

        # 5. 指标总览
        if metrics_result:
            try:
                metrics_files = self.plot_metrics_summary(metrics_result,
                                                        title=f"{model_name} - 评估指标总览",
                                                        save_name=f"{timestamp}_metrics_summary")
                report_files['metrics_summary'] = metrics_files
            except Exception as e:
                logger.error(f"Error plotting metrics summary: {e}")

        logger.info(f"Comprehensive report created with {len(report_files)} chart types")
        return report_files

    def export_data_for_tableau(self, y_true: np.ndarray, y_pred: np.ndarray,
                               y_proba: np.ndarray, backtest_result=None,
                               output_file: str = None) -> str:
        """
        导出Tableau可视化数据

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_proba: 预测概率矩阵
            backtest_result: 回测结果
            output_file: 输出文件路径

        Returns:
            导出文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"tableau_data_{timestamp}.csv"

        # 创建基础数据
        data = {
            'index': range(len(y_true)),
            'true_label': y_true,
            'predicted_label': y_pred,
            'is_correct': (y_true == y_pred).astype(int),
            'confidence': np.max(y_proba, axis=1)
        }

        # 添加各类别概率
        for i, class_name in enumerate(['H', 'D', 'A']):
            data[f'prob_{class_name}'] = y_proba[:, i]

        # 添加投注数据
        if backtest_result and backtest_result.bets:
            bet_data = []
            for i, bet in enumerate(backtest_result.bets):
                bet_info = {
                    'bet_index': i,
                    'match_id': bet.match_id,
                    'date': bet.date,
                    'prediction': bet.prediction,
                    'actual_result': bet.actual_result,
                    'stake': bet.stake,
                    'odds': bet.odds[bet.prediction],
                    'won': int(bet.won),
                    'profit': bet.profit,
                    'ev': bet.ev,
                    'confidence': bet.confidence,
                    'bet_type': bet.bet_type.value
                }
                bet_data.append(bet_info)

            bet_df = pd.DataFrame(bet_data)
            bet_df.to_csv(output_file.with_suffix('.bets.csv'), index=False)

        # 保存主要数据
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False)

        logger.info(f"Tableau data exported to {output_file}")
        return str(output_file)


# 便捷函数
def create_evaluation_plots(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray,
                          backtest_result=None, metrics_result=None,
                          output_dir: str = None, model_name: str = "Model") -> dict[str, list[str]]:
    """
    便捷的评估图表生成函数

    Args:
        y_true: 真实标签
        y_pred: 预测标签
        y_proba: 预测概率矩阵
        backtest_result: 回测结果
        metrics_result: 评估指标结果
        output_dir: 输出目录
        model_name: 模型名称

    Returns:
        生成的图表文件路径字典
    """
    visualizer = EvaluationVisualizer(output_dir=output_dir)
    return visualizer.create_comprehensive_report(
        y_true=y_true,
        y_pred=y_pred,
        y_proba=y_proba,
        backtest_result=backtest_result,
        metrics_result=metrics_result,
        model_name=model_name
    )
