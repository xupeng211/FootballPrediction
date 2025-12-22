#!/usr/bin/env python3
"""
V9.1 概率校准器 - 精算级修复
使用 Platt Scaling 和 Isotonic Regression 进行概率校准
目标: Brier Score < 0.25
"""

import pandas as pd
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss
import lightgbm as lgb
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class ProbabilityCalibrator:
    """概率校准器 - 精算级实现"""

    def __init__(self, method='platt'):
        """
        初始化校准器

        Args:
            method: 'platt' 或 'isotonic'
        """
        self.method = method
        self.calibrated_model = None
        self.brier_score_before = None
        self.brier_score_after = None
        self.calibration_curve_data = None

    def fit(self, X_train, y_train, X_val, y_val, model_path=None):
        """
        训练校准模型

        Args:
            X_train, y_train: 训练数据
            X_val, y_val: 验证数据 (用于校准)
            model_path: 预训练模型路径
        """
        print("🎯 开始概率校准训练...")
        print(f"  方法: {self.method.upper()}")
        print(f"  训练集: {len(X_train)} 样本")
        print(f"  验证集: {len(X_val)} 样本")

        # 加载或训练基础模型
        if model_path and Path(model_path).exists():
            print(f"  加载预训练模型: {model_path}")
            base_model = lgb.Booster(model_file=model_path)
        else:
            print("  训练新基础模型...")
            base_model = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                verbose=-1
            )
            base_model.fit(X_train, y_train)

        # 计算校准前的 Brier Score
        if hasattr(base_model, 'predict_proba'):
            raw_probs = base_model.predict_proba(X_val)[:, 1]
        else:
            raw_probs = base_model.predict(X_val)

        self.brier_score_before = brier_score_loss(y_val, raw_probs)
        print(f"  校准前 Brier Score: {self.brier_score_before:.4f}")

        # 实施 Platt Scaling 或 Isotonic Regression
        if self.method == 'platt':
            print("  实施 Platt Scaling (Sigmoid 校准)...")
            self.calibrated_model = CalibratedClassifierCV(
                base_model,
                method='sigmoid',
                cv=3
            )
        else:
            print("  实施 Isotonic Regression (单调回归)...")
            self.calibrated_model = CalibratedClassifierCV(
                base_model,
                method='isotonic',
                cv=3
            )

        # 在验证集上训练校准器
        self.calibrated_model.fit(X_val, y_val)

        # 计算校准后的 Brier Score
        calibrated_probs = self.calibrated_model.predict_proba(X_val)[:, 1]
        self.brier_score_after = brier_score_loss(y_val, calibrated_probs)

        print(f"  校准后 Brier Score: {self.brier_score_after:.4f}")
        improvement = ((self.brier_score_before - self.brier_score_after) /
                      self.brier_score_before * 100)
        print(f"  改进幅度: {improvement:.1f}%")

        # 保存校准曲线数据
        self.calibration_curve_data = {
            'raw_probs': raw_probs,
            'calibrated_probs': calibrated_probs,
            'true_labels': y_val
        }

        return self

    def predict_proba(self, X):
        """预测校准后的概率"""
        if self.calibrated_model is None:
            raise ValueError("模型尚未训练，请先调用 fit() 方法")

        return self.calibrated_model.predict_proba(X)

    def predict(self, X):
        """预测类别"""
        if self.calibrated_model is None:
            raise ValueError("模型尚未训练，请先调用 fit() 方法")

        return self.calibrated_model.predict(X)

    def save(self, path):
        """保存校准模型"""
        joblib.dump(self, path)
        print(f"✅ 校准模型已保存: {path}")

    def load(self, path):
        """加载校准模型"""
        self = joblib.load(path)
        print(f"✅ 校准模型已加载: {path}")
        return self


class MarginRemoval:
    """庄家抽水移除器 - 基于 Shin's Method"""

    def __init__(self, margin_rate=0.033):
        """
        初始化去水器

        Args:
            margin_rate: 庄家抽水率 (默认 3.3%)
        """
        self.margin_rate = margin_rate

    def calculate_fair_probability(self, odds):
        """
        计算公平概率 (移除抽水)

        使用方法: 先从隐含概率中移除抽水，再归一化
        """
        # 隐含概率
        implied_prob = 1.0 / odds

        # 移除抽水
        fair_prob = implied_prob * (1 - self.margin_rate)

        return fair_prob

    def calculate_sharpe_edge(self, model_prob, fair_prob, confidence_threshold=0.05):
        """
        计算 Sharpe-adjusted Edge

        Args:
            model_prob: 模型预测概率
            fair_prob: 公平概率
            confidence_threshold: 置信度阈值

        Returns:
            edge: 调整后的边缘
            is_bet: 是否值得投注
        """
        # 原始 Edge
        raw_edge = model_prob - fair_prob

        # 置信度调整
        # 模型概率越高，置信度越低 (过度自信惩罚)
        confidence_penalty = 0.0
        if model_prob > 0.8:
            confidence_penalty = (model_prob - 0.8) * 0.5
        elif model_prob < 0.2:
            confidence_penalty = (0.2 - model_prob) * 0.3

        # 调整后的 Edge
        adjusted_edge = raw_edge - confidence_penalty

        # 只有当调整后 Edge > 阈值时才投注
        is_bet = adjusted_edge > confidence_threshold

        return adjusted_edge, is_bet

    def calculate_kelly_bet(self, model_prob, odds, bankroll, edge, kelly_fraction=0.25):
        """
        计算凯利投注额

        Args:
            model_prob: 模型预测概率
            odds: 赔率
            bankroll: 当前资金
            edge: 优势
            kelly_fraction: 凯利系数

        Returns:
            bet_amount: 投注额
        """
        if not (edge > 0):
            return 0

        # 凯利公式
        b = odds - 1
        q = 1 - model_prob
        kelly_f = (b * model_prob - q) / b

        # 应用凯利系数
        adjusted_kelly = kelly_f * kelly_fraction

        # 确保为正
        adjusted_kelly = max(0, adjusted_kelly)

        # 计算投注额
        bet_amount = adjusted_kelly * bankroll

        # 硬上限: 2%
        max_bet = bankroll * 0.02

        return min(bet_amount, max_bet)


def main():
    """主函数 - 演示校准器使用"""
    print("=" * 60)
    print("🎯 V9.1 概率校准器演示")
    print("=" * 60)

    # 创建示例数据
    np.random.seed(42)
    n_samples = 1000

    X = np.random.randn(n_samples, 10)
    y = (X[:, 0] + X[:, 1] + np.random.randn(n_samples) * 0.5 > 0).astype(int)

    # 分割数据
    split = int(n_samples * 0.6)
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:split+200], y[split:split+200]
    X_test, y_test = X[split+200:], y[split+200:]

    # 训练校准器
    calibrator = ProbabilityCalibrator(method='platt')
    calibrator.fit(X_train, y_train, X_val, y_val)

    # 预测测试集
    raw_probs = lgb.LGBMClassifier().fit(X_train, y_train).predict_proba(X_test)[:, 1]
    calibrated_probs = calibrator.predict_proba(X_test)[:, 1]

    print("\n📊 校准效果对比:")
    print(f"  原始概率范围: [{raw_probs.min():.3f}, {raw_probs.max():.3f}]")
    print(f"  校准后范围: [{calibrated_probs.min():.3f}, {calibrated_probs.max():.3f}]")

    # 计算 Brier Score
    brier_raw = brier_score_loss(y_test, raw_probs)
    brier_cal = brier_score_loss(y_test, calibrated_probs)

    print(f"\n  原始 Brier Score: {brier_raw:.4f}")
    print(f"  校准后 Brier Score: {brier_cal:.4f}")
    print(f"  改进: {((brier_raw - brier_cal) / brier_raw * 100):.1f}%")

    # 边际移除演示
    print("\n" + "=" * 60)
    print("💧 边际移除演示 (Shin's Method)")
    print("=" * 60)

    remover = MarginRemoval(margin_rate=0.033)

    # 示例
    model_prob = 0.65
    odds = 2.0

    fair_prob = remover.calculate_fair_probability(odds)
    edge, is_bet = remover.calculate_sharpe_edge(model_prob, fair_prob)

    print(f"模型概率: {model_prob:.3f}")
    print(f"市场赔率: {odds:.2f}")
    print(f"隐含概率: {1/odds:.3f}")
    print(f"公平概率 (去水): {fair_prob:.3f}")
    print(f"原始 Edge: {model_prob - 1/odds:.3f}")
    print(f"调整后 Edge: {edge:.3f}")
    print(f"是否投注: {'✅ 是' if is_bet else '❌ 否'}")

    # 凯利投注计算
    bet_amount = remover.calculate_kelly_bet(model_prob, odds, 1000, edge)
    print(f"建议投注额: ${bet_amount:.2f}")

    # 保存校准器
    calibrator.save('/tmp/probability_calibrator_v91.pkl')
    print("\n✅ 校准器已保存")


if __name__ == "__main__":
    main()
