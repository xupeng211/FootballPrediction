#!/usr/bin/env python3
"""
评估模块测试运行器
运行所有评估模块的核心测试，避免pytest依赖问题
"""

import sys
import traceback
import importlib
from pathlib import Path

def test_module(module_name, tests):
    """测试一个模块"""
    print(f"\n{'='*60}")
    print(f"测试模块: {module_name}")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    for test_name, test_func in tests.items():
        try:
            print(f"运行 {test_name}...", end=" ")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
            traceback.print_exc()

    return passed, failed

def test_metrics():
    """测试指标模块"""
    from src.evaluation.metrics import Metrics
    import numpy as np

    np.random.seed(42)
    n_samples = 100

    # 创建测试数据
    y_true = np.random.randint(0, 3, n_samples)
    y_pred = np.random.randint(0, 3, n_samples)
    y_proba = np.random.dirichlet([1, 1, 1], n_samples)
    odds = np.random.uniform(1.5, 5.0, (n_samples, 3))

    metrics = Metrics()

    # 测试分类指标
    result = metrics.classification_metrics(y_true, y_pred, y_proba)
    assert "accuracy" in result
    assert "f1_weighted" in result

    # 测试完整评估
    result = metrics.evaluate_all(y_true, y_pred, y_proba, odds)
    assert hasattr(result, 'metrics')
    assert hasattr(result, 'metadata')
    assert result.metadata["n_samples"] == n_samples

def test_calibration():
    """测试校准模块"""
    from src.evaluation.calibration import IsotonicCalibrator, AutoCalibrator
    import numpy as np

    np.random.seed(42)
    n_samples = 50

    # 创建测试数据
    y_true = np.random.randint(0, 3, n_samples)
    y_proba = np.random.dirichlet([1, 1, 1], n_samples)

    # 测试Isotonic校准
    calibrator = IsotonicCalibrator(n_classes=3)

    # 训练
    fitted = calibrator.fit(y_true, y_proba)
    assert fitted is calibrator
    assert calibrator.is_fitted is True

    # 预测
    calibrated_proba = calibrator.transform(y_proba)
    assert calibrated_proba.shape == y_proba.shape

    # 验证概率和为1
    prob_sums = calibrated_proba.sum(axis=1)
    np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    # 测试自动校准
    auto_calibrator = AutoCalibrator(n_classes=3)
    result = auto_calibrator.calibrate(y_true, y_proba)
    assert hasattr(result, 'is_calibrated')

def test_backtest():
    """测试回测模块"""
    from src.evaluation.backtest import (
        Backtester, FlatStakingStrategy, KellyStakingStrategy,
        PercentageStakingStrategy, ValueBettingStrategy
    )
    import numpy as np
    import pandas as pd

    np.random.seed(42)
    n_samples = 50

    # 创建测试数据
    predictions = pd.DataFrame({
        'prob_H': np.random.uniform(0.2, 0.7, n_samples),
        'prob_D': np.random.uniform(0.1, 0.4, n_samples),
        'prob_A': np.random.uniform(0.1, 0.5, n_samples),
        'predicted_class': np.random.randint(0, 3, n_samples),
        'actual_result': np.random.randint(0, 3, n_samples),
    })

    # 归一化概率
    prob_cols = ['prob_H', 'prob_D', 'prob_A']
    predictions[prob_cols] = predictions[prob_cols].div(
        predictions[prob_cols].sum(axis=1), axis=0
    )

    odds = pd.DataFrame({
        'odds_H': np.random.uniform(1.8, 4.0, n_samples),
        'odds_D': np.random.uniform(2.8, 4.5, n_samples),
        'odds_A': np.random.uniform(2.5, 6.0, n_samples)
    })

    # 测试Backtester
    backtester = Backtester(initial_bankroll=1000.0)

    # 测试固定投注策略
    flat_strategy = FlatStakingStrategy(stake_amount=10.0)
    result = backtester.simulate(predictions, odds, flat_strategy)

    assert result.initial_bankroll == 1000.0
    assert result.total_bets >= 0
    assert len(result.equity_curve) >= 1

    # 测试凯利策略
    kelly_strategy = KellyStakingStrategy(kelly_fraction=0.25)
    result_kelly = backtester.simulate(predictions, odds, kelly_strategy)

    # 测试百分比投注策略
    percent_strategy = PercentageStakingStrategy(percentage=0.02)
    result_percent = backtester.simulate(predictions, odds, percent_strategy)

    # 测试价值投注策略
    value_strategy = ValueBettingStrategy(min_ev_threshold=0.05)
    result_value = backtester.simulate(predictions, odds, value_strategy)

def test_visualizer():
    """测试可视化模块"""
    from src.evaluation.visualizer import EvaluationVisualizer
    import numpy as np

    np.random.seed(42)
    n_samples = 50

    # 创建测试数据
    y_true = np.random.randint(0, 3, n_samples)
    y_pred = y_true.copy()

    # 添加一些错误预测
    error_indices = np.random.choice(n_samples, size=int(n_samples * 0.3), replace=False)
    y_pred[error_indices] = np.random.randint(0, 3, len(error_indices))

    # 生成概率矩阵
    y_proba = np.random.dirichlet([1, 1, 1], n_samples)
    for i, pred in enumerate(y_pred):
        y_proba[i, pred] = max(y_proba[i, pred], 0.4)
        y_proba[i] = y_proba[i] / y_proba[i].sum()

    visualizer = EvaluationVisualizer()

    # 测试预测分布图
    try:
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互后端
        import matplotlib.pyplot as plt

        # 测试保存图表功能
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot([1, 2, 3], [1, 2, 3])

        saved_paths = visualizer.save_figure(fig, "test_plot", ['png'])
        assert len(saved_paths) == 1

        plt.close(fig)
        print("可视化测试通过（matplotlib可用）")
    except ImportError:
        print("可视化测试跳过（matplotlib不可用）")

def main():
    """运行所有测试"""
    print("开始运行评估模块测试...")

    # 测试套件
    test_suites = {
        "metrics": {
            "test_classification_metrics": test_metrics,
        },
        "calibration": {
            "test_isotonic_calibration": test_calibration,
        },
        "backtest": {
            "test_backtest_strategies": test_backtest,
        },
        "visualizer": {
            "test_visualization": test_visualizer,
        }
    }

    total_passed = 0
    total_failed = 0

    for module_name, tests in test_suites.items():
        passed, failed = test_module(module_name, tests)
        total_passed += passed
        total_failed += failed

    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"总通过: {total_passed}")
    print(f"总失败: {total_failed}")
    print(f"总计: {total_passed + total_failed}")

    if total_failed == 0:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 存在测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())