#!/usr/bin/env python3
"""
增强版基线模型训练脚本 - V2增强特征实验
专注于优化滚动特征和时序特征工程

核心功能:
1. 在诚实基线基础上添加增强特征
2. 添加滚动的胜率/状态特征
3. 添加赛季内表现趋势特征
4. 对比V1基线性能

作者: Lead Algorithm Engineer
创建时间: 2025-12-10
版本: 2.0.0 - Enhanced Features
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, log_loss, classification_report
from xgboost import XGBClassifier

# 导入基线训练器
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from train_baseline import BaselineTrainer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedFeaturesTrainer(BaselineTrainer):
    """增强特征训练器"""

    def __init__(self):
        super().__init__()
        self.enhanced_features_cache = {}

    def calculate_enhanced_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算增强的滚动特征"""
        logger.info("🚀 计算增强滚动特征")

        # 基础滚动特征已存在，我们添加更多高级特征

        enhanced_df = df.copy()

        # 1. 主客场表现差异特征
        for window in [3, 5, 10]:
            # 主客场xG差异
            enhanced_df[f'h2h_xg_diff_{window}'] = (
                enhanced_df[f'home_last_{window}_avg_xg'] -
                enhanced_df[f'away_last_{window}_avg_xg']
            )

            # 主客场进球差异
            enhanced_df[f'h2h_goals_diff_{window}'] = (
                enhanced_df[f'home_last_{window}_avg_goals_scored'] -
                enhanced_df[f'away_last_{window}_avg_goals_scored']
            )

            # 主客场胜率差异
            enhanced_df[f'h2h_win_rate_diff_{window}'] = (
                enhanced_df[f'home_last_{window}_win_rate'] -
                enhanced_df[f'away_last_{window}_win_rate']
            )

        # 2. 近期趋势特征
        # 3场vs5场表现对比
        if 'home_last_3_avg_xg' in enhanced_df.columns and 'home_last_5_avg_xg' in enhanced_df.columns:
            enhanced_df['form_trend_xg_3_vs_5'] = (
                enhanced_df['home_last_3_avg_xg'] - enhanced_df['home_last_5_avg_xg']
            )

        # 5场vs10场表现对比
        if 'home_last_5_avg_xg' in enhanced_df.columns and 'home_last_10_avg_xg' in enhanced_df.columns:
            enhanced_df['form_trend_xg_5_vs_10'] = (
                enhanced_df['home_last_5_avg_xg'] - enhanced_df['home_last_10_avg_xg']
            )

        # 3场vs5场进球对比
        if 'home_last_3_avg_goals_scored' in enhanced_df.columns and 'home_last_5_avg_goals_scored' in enhanced_df.columns:
            enhanced_df['form_trend_goals_3_vs_5'] = (
                enhanced_df['home_last_3_avg_goals_scored'] - enhanced_df['home_last_5_avg_goals_scored']
            )

        # 3. 攻防平衡特征
        for window in [3, 5, 10]:
            # 攻防平衡指数 = 进球能力 - 失球防守能力
            enhanced_df[f'attack_defense_balance_home_{window}'] = (
                enhanced_df[f'home_last_{window}_avg_goals_scored'] -
                enhanced_df[f'home_last_{window}_avg_goals_conceded']
            )

            enhanced_df[f'attack_defense_balance_away_{window}'] = (
                enhanced_df[f'away_last_{window}_avg_goals_scored'] -
                enhanced_df[f'away_last_{window}_avg_goals_conceded']
            )

            # 总体战斗指数
            enhanced_df[f'total_battle_index_{window}'] = (
                enhanced_df[f'home_last_{window}_avg_xg'] +
                enhanced_df[f'away_last_{window}_avg_xg']
            )

        # 4. 状态稳定性特征
        for window in [5, 10]:
            # 表现稳定性 (通过标准差计算，这里简化为变异系数的估计)
            enhanced_df[f'performance_stability_home_{window}'] = (
                1.0 / (1.0 + enhanced_df[f'home_last_{window}_avg_goal_diff'].abs())
            )

            enhanced_df[f'performance_stability_away_{window}'] = (
                1.0 / (1.0 + enhanced_df[f'away_last_{window}_avg_goal_diff'].abs())
            )

        # 5. 时间特征增强
        enhanced_df['month_sin'] = np.sin(2 * np.pi * enhanced_df['month'] / 12)
        enhanced_df['month_cos'] = np.cos(2 * np.pi * enhanced_df['month'] / 12)
        enhanced_df['day_of_week_sin'] = np.sin(2 * np.pi * enhanced_df['day_of_week'] / 7)
        enhanced_df['day_of_week_cos'] = np.cos(2 * np.pi * enhanced_df['day_of_week'] / 7)

        logger.info(f"   ✅ 增强特征计算完成")
        logger.info(f"   📊 原始特征: {len(df.columns)}")
        logger.info(f"   ⚡ 增强后特征: {len(enhanced_df.columns)}")

        return enhanced_df

    def select_enhanced_features(self, df: pd.DataFrame) -> tuple:
        """选择增强特征"""
        logger.info("🎯 选择增强特征")

        # 基础滚动特征
        rolling_features = [col for col in df.columns if 'last_' in col]

        # 增强特征
        enhanced_feature_patterns = [
            'h2h_', 'form_trend_', 'attack_defense_balance_',
            'total_battle_index_', 'performance_stability_',
            'month_sin', 'month_cos', 'day_of_week_sin', 'day_of_week_cos'
        ]

        enhanced_features = []
        for pattern in enhanced_feature_patterns:
            enhanced_features.extend([col for col in df.columns if pattern in col])

        # 基础上下文特征
        context_features = [
            'year', 'month', 'day_of_week', 'is_weekend',
            'month_sin', 'month_cos', 'day_of_week_sin', 'day_of_week_cos'
        ]

        context_features = [col for col in context_features if col in df.columns]

        # 合并所有特征
        all_feature_columns = rolling_features + enhanced_features + context_features

        logger.info(f"   ✅ 滚动特征: {len(rolling_features)}")
        logger.info(f"   ⚡ 增强特征: {len(enhanced_features)}")
        logger.info(f"   📅 上下文特征: {len(context_features)}")
        logger.info(f"   📋 总特征数: {len(all_feature_columns)}")

        # 提取特征和目标
        X = df[all_feature_columns].copy()
        y = df['true_result'].copy()

        # 处理缺失值
        X = X.fillna(0)

        logger.info(f"   📊 特征矩阵形状: {X.shape}")
        logger.info(f"   🎯 目标变量形状: {y.shape}")

        return X, y, all_feature_columns

    def train_enhanced_model(self, data_path: str) -> dict:
        """完整的增强模型训练流程"""
        logger.info("🚀 开始增强模型训练流程")

        # 1. 加载数据
        df = self.load_and_prepare_data(data_path)

        # 2. 计算增强特征
        df_enhanced = self.calculate_enhanced_rolling_features(df)

        # 3. 选择增强特征
        X, y, feature_columns = self.select_enhanced_features(df_enhanced)

        # 4. 时序分割
        X_train, X_test, y_train_enc, y_test_enc, y_train_orig, y_test_orig = \
            self.split_data_chronological(X, y)

        # 5. 训练模型
        self.feature_names = feature_columns
        self.train_xgboost(X_train, y_train_enc)

        # 6. 评估模型
        results = self.evaluate_model(X_test, y_test_enc, y_test_orig)

        # 7. 特征重要性
        self.plot_feature_importance()

        logger.info("🎉 增强模型训练完成!")
        return results


def compare_models(baseline_results: dict, enhanced_results: dict):
    """比较两个模型的性能"""
    print("\n" + "="*80)
    print("🏆 MODEL COMPARISON SUMMARY")
    print("="*80)

    print(f"\n📊 性能对比:")
    print(f"{'指标':<20} {'基线模型':<15} {'增强模型':<15} {'改进':<10}")
    print("-" * 70)

    acc_baseline = baseline_results['accuracy']
    acc_enhanced = enhanced_results['accuracy']
    acc_improvement = ((acc_enhanced - acc_baseline) / acc_baseline) * 100

    print(f"{'准确率 (Accuracy)':<20} {acc_baseline:<15.4f} {acc_enhanced:<15.4f} {acc_improvement:+.2f}%")

    ll_baseline = baseline_results['log_loss']
    ll_enhanced = enhanced_results['log_loss']
    ll_improvement = ((ll_baseline - ll_enhanced) / ll_baseline) * 100

    print(f"{'对数损失 (Log Loss)':<20} {ll_baseline:<15.4f} {ll_enhanced:<15.4f} {ll_improvement:+.2f}%")

    print(f"\n✅ 结论:")
    if acc_improvement > 1.0:
        print(f"   🚀 增强特征显著提升了模型性能!")
    elif acc_improvement > 0.5:
        print(f"   📈 增强特征轻微提升了模型性能")
    elif acc_improvement > -0.5:
        print(f"   ➡️ 增强特征对性能影响不大")
    else:
        print(f"   📉 增强特征降低了模型性能")

    print("="*80)


def main():
    """主函数"""
    print("🔬 V2 增强特征实验开始")
    print("="*80)

    try:
        # 1. 训练基线模型 (作为对比)
        print("\n1️⃣ 训练基线模型 (V1)...")
        baseline_trainer = BaselineTrainer()
        baseline_results = baseline_trainer.train_baseline_model(
            data_path="data/processed/features_v2_rolling.csv"
        )

        # 2. 训练增强模型 (V2)
        print("\n2️⃣ 训练增强模型 (V2)...")
        enhanced_trainer = EnhancedFeaturesTrainer()
        enhanced_results = enhanced_trainer.train_enhanced_model(
            data_path="data/processed/features_v2_rolling.csv"
        )

        # 3. 模型对比
        compare_models(baseline_results, enhanced_results)

        # 保存增强特征重要性
        enhanced_trainer.plot_feature_importance()

    except Exception as e:
        logger.error(f"❌ 实验失败: {e}")
        raise


if __name__ == "__main__":
    main()