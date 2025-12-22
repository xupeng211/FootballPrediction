#!/usr/bin/env python3
"""
V9.2 校准方法对比 - Platt Scaling vs Isotonic Regression
比较两种校准方法在英超市场中的表现
"""

import pandas as pd
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss
import lightgbm as lgb
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class CalibrationComparator:
    """校准方法对比器"""

    def __init__(self):
        self.results = {}

    def prepare_data(self, data_path):
        """准备数据"""
        print("📊 准备训练数据...")
        df = pd.read_csv(data_path)
        print(f"  数据量: {len(df)} 场比赛")

        # 过滤有效数据
        df = df[
            df['real_home_odds'].notna() &
            df['real_draw_odds'].notna() &
            df['real_away_odds'].notna()
        ]
        print(f"  有效数据: {len(df)} 场比赛")

        # 准备特征 (简化版 15 维)
        features = []
        for _, row in df.iterrows():
            features.append([
                row.get('home_avg_xg', 1.2),
                row.get('home_avg_goals', 1.2),
                row.get('home_avg_shots', 12),
                row.get('home_avg_shots_on_target', 4),
                row.get('home_avg_possession', 50),
                row.get('home_avg_pass_accuracy', 80),
                row.get('home_avg_rating', 6.5),
                row.get('home_win_rate', 0.33),
                row.get('home_draw_rate', 0.25),
                row.get('home_loss_rate', 0.42),
                row.get('away_avg_xg', 1.0),
                row.get('away_avg_goals', 1.0),
                row.get('away_avg_rating', 6.0),
                row.get('away_win_rate', 0.33),
                row.get('xg_diff', 0.2),
            ])

        X = np.array(features)

        # 准备标签 (预测主胜)
        y = (df['actual_result'] == 'H').astype(int)

        print(f"  特征维度: {X.shape}")
        print(f"  主胜样本: {y.sum()} ({y.mean()*100:.1f}%)")

        return X, y, df

    def train_and_evaluate(self, X, y):
        """训练和评估模型"""
        print("\n" + "=" * 60)
        print("🎯 校准方法对比")
        print("=" * 60)

        # 分割数据
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.4, random_state=42, stratify=y
        )
        X_cal, X_test, y_cal, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
        )

        print(f"  训练集: {len(X_train)} 样本")
        print(f"  校准集: {len(X_cal)} 样本")
        print(f"  测试集: {len(X_test)} 样本")

        # 训练基础模型
        print("\n🔧 训练基础 LightGBM 模型...")
        base_model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=-1
        )
        base_model.fit(X_train, y_train)

        # 计算原始 Brier Score
        raw_probs = base_model.predict_proba(X_test)[:, 1]
        raw_brier = brier_score_loss(y_test, raw_probs)
        print(f"  原始 Brier Score: {raw_brier:.4f}")

        # 方法 1: Platt Scaling
        print("\n📈 方法 1: Platt Scaling (Sigmoid 校准)")
        platt_model = CalibratedClassifierCV(
            base_model, method='sigmoid', cv=3
        )
        platt_model.fit(X_cal, y_cal)
        platt_probs = platt_model.predict_proba(X_test)[:, 1]
        platt_brier = brier_score_loss(y_test, platt_probs)
        print(f"  Platt Scaling Brier Score: {platt_brier:.4f}")

        # 方法 2: Isotonic Regression
        print("\n📈 方法 2: Isotonic Regression (单调回归)")
        isotonic_model = CalibratedClassifierCV(
            base_model, method='isotonic', cv=3
        )
        isotonic_model.fit(X_cal, y_cal)
        isotonic_probs = isotonic_model.predict_proba(X_test)[:, 1]
        isotonic_brier = brier_score_loss(y_test, isotonic_probs)
        print(f"  Isotonic Regression Brier Score: {isotonic_brier:.4f}")

        # 对比结果
        print("\n" + "=" * 60)
        print("📊 校准效果对比")
        print("=" * 60)
        print(f"  原始 (未校准):    {raw_brier:.4f}")
        print(f"  Platt Scaling:    {platt_brier:.4f} (改进 {((raw_brier - platt_brier)/raw_brier*100):+.1f}%)")
        print(f"  Isotonic Regression: {isotonic_brier:.4f} (改进 {((raw_brier - isotonic_brier)/raw_brier*100):+.1f}%)")

        # 选择最佳方法
        if platt_brier < isotonic_brier:
            best_method = 'Platt Scaling'
            best_brier = platt_brier
            best_probs = platt_probs
            best_model = platt_model
        else:
            best_method = 'Isotonic Regression'
            best_brier = isotonic_brier
            best_probs = isotonic_probs
            best_model = isotonic_model

        print(f"\n🏆 最佳方法: {best_method}")
        print(f"   Brier Score: {best_brier:.4f}")

        # 保存结果
        self.results = {
            'raw_brier': raw_brier,
            'platt_brier': platt_brier,
            'isotonic_brier': isotonic_brier,
            'best_method': best_method,
            'best_brier': best_brier,
            'y_test': y_test,
            'raw_probs': raw_probs,
            'platt_probs': platt_probs,
            'isotonic_probs': isotonic_probs,
            'best_probs': best_probs,
            'best_model': best_model
        }

        return best_model, best_method

    def plot_reliability_curves(self):
        """绘制可靠性曲线"""
        print("\n📈 生成可靠性曲线图...")

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle('Probability Calibration Comparison', fontsize=16, fontweight='bold')

        methods = [
            ('Raw (Uncalibrated)', self.results['raw_probs'], 'blue'),
            ('Platt Scaling', self.results['platt_probs'], 'green'),
            ('Isotonic Regression', self.results['isotonic_probs'], 'red')
        ]

        for idx, (name, probs, color) in enumerate(methods):
            ax = axes[idx]

            # 计算可靠性曲线数据
            from sklearn.calibration import calibration_curve
            fraction_of_positives, mean_predicted_value = calibration_curve(
                self.results['y_test'], probs, n_bins=10
            )

            # 绘制可靠性曲线
            ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Perfect calibration')
            ax.plot(mean_predicted_value, fraction_of_positives,
                   'o-', color=color, label=name, linewidth=2, markersize=6)

            ax.set_xlabel('Mean Predicted Probability')
            ax.set_ylabel('Fraction of Positives')
            ax.set_title(f'{name}\nBrier Score: {self.results[name.split()[0].lower() + "_brier"]:.4f}')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.set_xlim([0, 1])
            ax.set_ylim([0, 1])

        plt.tight_layout()
        plt.savefig('/home/user/projects/FootballPrediction/V9_2_CALIBRATION_COMPARISON.png',
                   dpi=150, bbox_inches='tight')
        plt.close()

        print("  ✅ 可靠性曲线图已保存: V9_2_CALIBRATION_COMPARISON.png")

    def save_results(self):
        """保存结果"""
        results_df = pd.DataFrame({
            'Method': ['Raw (Uncalibrated)', 'Platt Scaling', 'Isotonic Regression'],
            'Brier_Score': [
                self.results['raw_brier'],
                self.results['platt_brier'],
                self.results['isotonic_brier']
            ],
            'Improvement': [
                0,
                (self.results['raw_brier'] - self.results['platt_brier']) / self.results['raw_brier'] * 100,
                (self.results['raw_brier'] - self.results['isotonic_brier']) / self.results['raw_brier'] * 100
            ]
        })

        results_df.to_csv('/home/user/projects/FootballPrediction/V9_2_CALIBRATION_RESULTS.csv', index=False)
        print("  ✅ 结果已保存: V9_2_CALIBRATION_RESULTS.csv")


def main():
    """主函数"""
    print("=" * 60)
    print("🎯 V9.2 校准方法对比 - Platt vs Isotonic")
    print("=" * 60)

    comparator = CalibrationComparator()

    # 准备数据
    data_path = "/home/user/projects/FootballPrediction/data/combined_multi_season_odds.csv"
    X, y, df = comparator.prepare_data(data_path)

    # 训练和评估
    best_model, best_method = comparator.train_and_evaluate(X, y)

    # 绘制可靠性曲线
    comparator.plot_reliability_curves()

    # 保存结果
    comparator.save_results()

    # 最终建议
    print("\n" + "=" * 60)
    print("💡 校准方法建议")
    print("=" * 60)
    print(f"推荐方法: {best_method}")
    print(f"原因: 在英超市场中表现最佳 (Brier Score: {comparator.results['best_brier']:.4f})")
    print("\n📋 Brier Score 参考:")
    print("  < 0.25: 优秀")
    print("  0.25-0.30: 良好")
    print("  0.30-0.35: 一般")
    print("  > 0.35: 较差")

    if comparator.results['best_brier'] < 0.25:
        print(f"\n✅ 当前校准效果优秀! (Brier Score: {comparator.results['best_brier']:.4f})")
    elif comparator.results['best_brier'] < 0.30:
        print(f"\n✅ 当前校准效果良好 (Brier Score: {comparator.results['best_brier']:.4f})")
    else:
        print(f"\n⚠️ 当前校准效果一般 (Brier Score: {comparator.results['best_brier']:.4f})")
        print("  建议: 收集更多训练数据或调整模型参数")


if __name__ == "__main__":
    main()
