"""
Unit tests for Football Prediction Evaluation Visualizer module.

测试足球预测评估可视化模块的各项功能。
"""

import pytest
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from src.evaluation.visualizer import (
    EvaluationVisualizer,
    create_evaluation_plots,
)


class TestEvaluationVisualizer:
    """EvaluationVisualizer类测试"""

    @pytest.fixture
    def visualizer(self):
        """创建EvaluationVisualizer实例"""
        return EvaluationVisualizer()

    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        np.random.seed(42)
        n_samples = 100

        y_true = np.random.randint(0, 3, n_samples)
        y_pred = y_true.copy()

        # 添加一些错误预测
        error_indices = np.random.choice(
            n_samples, size=int(n_samples * 0.3), replace=False
        )
        y_pred[error_indices] = np.random.randint(0, 3, len(error_indices))

        # 生成概率矩阵
        y_proba = np.random.dirichlet([1, 1, 1], n_samples)
        for i, pred in enumerate(y_pred):
            y_proba[i, pred] = max(y_proba[i, pred], 0.4)
            y_proba[i] = y_proba[i] / y_proba[i].sum()

        return y_true, y_pred, y_proba

    @pytest.fixture
    def sample_backtest_result(self):
        """创建样本回测结果"""
        from src.evaluation.backtest import BacktestResult, Bet, BetType

        bets = [
            Bet(
                "match_1",
                "2024-01-01",
                0,
                [0.6, 0.3, 0.1],
                [2.5, 3.2, 4.0],
                10.0,
                BetType.HOME_WIN,
                0,
                True,
                15.0,
                0.5,
                0.6,
            ),
            Bet(
                "match_2",
                "2024-01-02",
                1,
                [0.2, 0.6, 0.2],
                [2.8, 3.0, 4.2],
                10.0,
                BetType.DRAW,
                1,
                True,
                20.0,
                0.8,
                0.6,
            ),
            Bet(
                "match_3",
                "2024-01-03",
                2,
                [0.1, 0.2, 0.7],
                [3.0, 3.5, 2.8],
                10.0,
                BetType.AWAY_WIN,
                0,
                False,
                -10.0,
                0.3,
                0.7,
            ),
        ]

        equity_curve = [1000.0, 1015.0, 1035.0, 1025.0]

        return BacktestResult(
            initial_bankroll=1000.0,
            final_bankroll=1025.0,
            total_bets=3,
            winning_bets=2,
            losing_bets=1,
            total_stake=30.0,
            total_winnings=45.0,
            net_profit=15.0,
            roi=50.0,
            win_rate=66.67,
            avg_odds=2.9,
            max_consecutive_losses=1,
            max_consecutive_wins=2,
            max_drawdown=10.0,
            max_drawdown_percentage=1.0,
            sharpe_ratio=1.5,
            calmar_ratio=15.0,
            profit_factor=3.0,
            avg_profit_per_bet=5.0,
            std_profit_per_bet=12.5,
            bets=bets,
            equity_curve=equity_curve,
            metadata={"test": True},
        )

    def test_initialization(self, visualizer):
        """测试EvaluationVisualizer初始化"""
        assert visualizer.dpi == 300
        assert visualizer.class_names == ["主胜(H)", "平局(D)", "客胜(A)"]
        assert visualizer.class_colors == ["#28a745", "#ffc107", "#dc3545"]

    def test_initialization_custom_output_dir(self):
        """测试自定义输出目录初始化"""
        custom_dir = "/tmp/test_visualizer"
        visualizer = EvaluationVisualizer(output_dir=custom_dir)

        assert visualizer.output_dir == Path(custom_dir)

    @patch("matplotlib.pyplot.savefig")
    def test_save_figure(self, mock_savefig, visualizer):
        """测试保存图表功能"""
        # 创建模拟图表
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot([1, 2, 3], [1, 2, 3])

        filename = "test_plot"
        formats = ["png", "pdf"]

        # 调用保存函数
        saved_paths = visualizer.save_figure(fig, filename, formats)

        # 验证返回的路径数量
        assert len(saved_paths) == len(formats)

        # 验证matplotlib.savefig被调用
        assert mock_savefig.call_count == len(formats)

        plt.close(fig)

    @patch("src.evaluation.visualizer.HAS_SKLEARN", True)
    def test_plot_roc_curves(self, visualizer, sample_data):
        """测试ROC曲线绘制"""
        y_true, y_pred, y_proba = sample_data

        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.plot_roc_curves(y_true, y_proba)

            assert isinstance(result, list)
            mock_save.assert_called_once()

    @patch("src.evaluation.visualizer.HAS_SKLEARN", False)
    def test_plot_roc_curves_no_sklearn(self, visualizer, sample_data):
        """测试无sklearn时的ROC曲线绘制"""
        y_true, _, y_proba = sample_data

        result = visualizer.plot_roc_curves(y_true, y_proba)

        # 应该返回空列表
        assert result == []

    @patch("src.evaluation.visualizer.HAS_SKLEARN", True)
    def test_plot_calibration_curves(self, visualizer, sample_data):
        """测试校准曲线绘制"""
        y_true, _, y_proba = sample_data

        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.plot_calibration_curves(y_true, y_proba)

            assert isinstance(result, list)
            mock_save.assert_called_once()

    def test_plot_prediction_distribution(self, visualizer, sample_data):
        """测试预测分布绘制"""
        y_true, y_pred, y_proba = sample_data

        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.plot_prediction_distribution(y_true, y_pred, y_proba)

            assert isinstance(result, list)
            mock_save.assert_called_once()

    def test_plot_backtest_results(self, visualizer, sample_backtest_result):
        """测试回测结果绘制"""
        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.plot_backtest_results(sample_backtest_result)

            assert isinstance(result, list)
            mock_save.assert_called_once()

    def test_plot_backtest_results_empty(self, visualizer):
        """测试空回测结果绘制"""
        from src.evaluation.backtest import BacktestResult

        empty_result = BacktestResult(
            initial_bankroll=1000.0,
            final_bankroll=1000.0,
            total_bets=0,
            winning_bets=0,
            losing_bets=0,
            total_stake=0.0,
            total_winnings=0.0,
            net_profit=0.0,
            roi=0.0,
            win_rate=0.0,
            avg_odds=0.0,
            max_consecutive_losses=0,
            max_consecutive_wins=0,
            max_drawdown=0.0,
            max_drawdown_percentage=0.0,
            sharpe_ratio=0.0,
            calmar_ratio=0.0,
            profit_factor=0.0,
            avg_profit_per_bet=0.0,
            std_profit_per_bet=0.0,
            bets=[],
            equity_curve=[1000.0],
            metadata={},
        )

        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.plot_backtest_results(empty_result)

            assert isinstance(result, list)
            # 空结果应该仍能绘制图表
            mock_save.assert_called_once()

    def test_plot_metrics_summary(self, visualizer):
        """测试指标总览绘制"""
        from src.evaluation.metrics import MetricsResult
        from datetime import datetime

        metrics_result = MetricsResult(
            metrics={
                "accuracy": 0.85,
                "f1_weighted": 0.83,
                "logloss": 0.45,
                "brier_score_avg": 0.25,
                "roi": 15.0,
            },
            metadata={"test": True},
            timestamp=datetime.now().isoformat(),
        )

        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.plot_metrics_summary(metrics_result)

            assert isinstance(result, list)
            mock_save.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    def test_create_comprehensive_report(
        self, visualizer, sample_data, sample_backtest_result
    ):
        """测试综合报告创建"""
        y_true, y_pred, y_proba = sample_data
        from src.evaluation.metrics import MetricsResult
        from datetime import datetime

        metrics_result = MetricsResult(
            metrics={"accuracy": 0.85, "logloss": 0.45},
            metadata={"test": True},
            timestamp=datetime.now().isoformat(),
        )

        with patch.object(visualizer, "save_figure") as mock_save:
            mock_save.return_value = ["test_path.png"]

            result = visualizer.create_comprehensive_report(
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                backtest_result=sample_backtest_result,
                metrics_result=metrics_result,
                model_name="Test Model",
            )

            assert isinstance(result, dict)
            # 应该生成多种类型的图表
            assert len(result) >= 1

    @patch("pandas.DataFrame.to_csv")
    def test_export_data_for_tableau(self, visualizer, sample_data):
        """测试Tableau数据导出"""
        y_true, y_pred, y_proba = sample_data

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write.return_value = None

            result = visualizer.export_data_for_tableau(
                y_true=y_true, y_pred=y_pred, y_proba=y_proba
            )

            assert isinstance(result, str)
            # 应该调用文件写入
            mock_file.assert_called()

    @patch("pandas.DataFrame.to_csv")
    def test_export_data_for_tableau_with_backtest(
        self, visualizer, sample_data, sample_backtest_result
    ):
        """测试包含回测数据的Tableau导出"""
        y_true, y_pred, y_proba = sample_data

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write.return_value = None

            result = visualizer.export_data_for_tableau(
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                backtest_result=sample_backtest_result,
            )

            assert isinstance(result, str)
            # 应该调用文件写入（主数据和投注数据）
            assert mock_file.call_count >= 1


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        np.random.seed(42)
        n_samples = 50

        y_true = np.random.randint(0, 3, n_samples)
        y_pred = y_true.copy()
        error_indices = np.random.choice(
            n_samples, size=int(n_samples * 0.2), replace=False
        )
        y_pred[error_indices] = np.random.randint(0, 3, len(error_indices))

        y_proba = np.random.dirichlet([1, 1, 1], n_samples)
        for i, pred in enumerate(y_pred):
            y_proba[i, pred] = max(y_proba[i, pred], 0.4)
            y_proba[i] = y_proba[i] / y_proba[i].sum()

        return y_true, y_pred, y_proba

    @patch("matplotlib.pyplot.savefig")
    def test_create_evaluation_plots(self, sample_data):
        """测试create_evaluation_plots便捷函数"""
        y_true, y_pred, y_proba = sample_data

        with patch(
            "src.evaluation.visualizer.EvaluationVisualizer"
        ) as mock_visualizer_class:
            mock_visualizer = MagicMock()
            mock_visualizer_class.return_value = mock_visualizer
            mock_visualizer.create_comprehensive_report.return_value = {
                "roc_curves": ["test.png"],
                "calibration_curves": ["test.png"],
            }

            result = create_evaluation_plots(
                y_true=y_true, y_pred=y_pred, y_proba=y_proba, output_dir="/tmp/test"
            )

            assert isinstance(result, dict)
            mock_visualizer.create_comprehensive_report.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    def test_create_evaluation_plots_with_backtest(self, sample_data):
        """测试包含回测数据的create_evaluation_plots"""
        y_true, y_pred, y_proba = sample_data

        # 创建简单回测结果
        from src.evaluation.backtest import BacktestResult

        backtest_result = BacktestResult(
            initial_bankroll=1000.0,
            final_bankroll=1050.0,
            total_bets=10,
            winning_bets=6,
            losing_bets=4,
            total_stake=100.0,
            total_winnings=150.0,
            net_profit=50.0,
            roi=50.0,
            win_rate=60.0,
            avg_odds=2.5,
            max_consecutive_losses=2,
            max_consecutive_wins=3,
            max_drawdown=20.0,
            max_drawdown_percentage=2.0,
            sharpe_ratio=1.0,
            calmar_ratio=25.0,
            profit_factor=2.5,
            avg_profit_per_bet=5.0,
            std_profit_per_bet=10.0,
            bets=[],
            equity_curve=[1000.0, 1050.0],
            metadata={},
        )

        from src.evaluation.metrics import MetricsResult
        from datetime import datetime

        metrics_result = MetricsResult(
            metrics={"accuracy": 0.85, "logloss": 0.45},
            metadata={"test": True},
            timestamp=datetime.now().isoformat(),
        )

        with patch(
            "src.evaluation.visualizer.EvaluationVisualizer"
        ) as mock_visualizer_class:
            mock_visualizer = MagicMock()
            mock_visualizer_class.return_value = mock_visualizer
            mock_visualizer.create_comprehensive_report.return_value = {
                "roc_curves": ["test.png"],
                "backtest_results": ["test.png"],
            }

            result = create_evaluation_plots(
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                backtest_result=backtest_result,
                metrics_result=metrics_result,
                model_name="Test Model",
            )

            assert isinstance(result, dict)
            # 验证调用参数
            call_args = mock_visualizer.create_comprehensive_report.call_args
            assert call_args[1]["backtest_result"] == backtest_result
            assert call_args[1]["metrics_result"] == metrics_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
