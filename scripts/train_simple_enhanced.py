#!/usr/bin/env python3
"""
简化增强特征实验
专注于安全的基础增强特征

作者: Lead Algorithm Engineer
创建时间: 2025-12-10
"""

import pandas as pd
import numpy as np
import logging
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, log_loss, classification_report
from xgboost import XGBClassifier

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入基线训练器
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from train_baseline import BaselineTrainer


class SimpleEnhancedTrainer(BaselineTrainer):
    """简化增强特征训练器"""

    def select_enhanced_features(self, df: pd.DataFrame) -> tuple:
        """选择基础增强特征"""
        logger.info("🎯 选择基础增强特征")

        # 基础滚动特征
        rolling_features = [col for col in df.columns if 'last_' in col]

        # 基础上下文特征
        context_features = [
            'year', 'month', 'day_of_week', 'is_weekend'
        ]

        context_features = [col for col in context_features if col in df.columns]

        # 简单增强特征
        simple_enhanced = []

        # 1. 主客场xG对比
        for window in [3, 5, 10]:
            home_xg_col = f'home_last_{window}_avg_xg'
            away_xg_col = f'away_last_{window}_avg_xg'

            if home_xg_col in df.columns and away_xg_col in df.columns:
                df[f'xg_diff_{window}'] = df[home_xg_col] - df[away_xg_col]
                simple_enhanced.append(f'xg_diff_{window}')

            # 2. 主客场进球对比
            home_goals_col = f'home_last_{window}_avg_goals_scored'
            away_goals_col = f'away_last_{window}_avg_goals_scored'

            if home_goals_col in df.columns and away_goals_col in df.columns:
                df[f'goals_diff_{window}'] = df[home_goals_col] - df[away_goals_col]
                simple_enhanced.append(f'goals_diff_{window}')

            # 3. 主客场胜率对比
            home_win_col = f'home_last_{window}_win_rate'
            away_win_col = f'away_last_{window}_win_rate'

            if home_win_col in df.columns and away_win_col in df.columns:
                df[f'win_rate_diff_{window}'] = df[home_win_col] - df[away_win_col]
                simple_enhanced.append(f'win_rate_diff_{window}')

        # 4. 攻防平衡指数
        for window in [3, 5]:
            home_goals_col = f'home_last_{window}_avg_goals_scored'
            home_conceded_col = f'home_last_{window}_avg_goals_conceded'
            away_goals_col = f'away_last_{window}_avg_goals_scored'
            away_conceded_col = f'away_last_{window}_avg_goals_conceded'

            if all(col in df.columns for col in [home_goals_col, home_conceded_col]):
                df[f'home_attack_defense_balance_{window}'] = (
                    df[home_goals_col] - df[home_conceded_col]
                )
                simple_enhanced.append(f'home_attack_defense_balance_{window}')

            if all(col in df.columns for col in [away_goals_col, away_conceded_col]):
                df[f'away_attack_defense_balance_{window}'] = (
                    df[away_goals_col] - df[away_conceded_col]
                )
                simple_enhanced.append(f'away_attack_defense_balance_{window}')

        # 合并所有特征
        all_feature_columns = rolling_features + context_features + simple_enhanced

        logger.info(f"   ✅ 滚动特征: {len(rolling_features)}")
        logger.info(f"   ⚡ 增强特征: {len(simple_enhanced)}")
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


def run_enhanced_experiment():
    """运行增强特征实验"""
    print("🔬 简化增强特征实验")
    print("="*60)

    # 1. 基线结果
    baseline_acc = 0.5553
    baseline_logloss = 1.0396

    print(f"\n📊 基线模型性能:")
    print(f"   准确率: {baseline_acc:.4f}")
    print(f"   Log Loss: {baseline_logloss:.4f}")

    # 2. 训练增强模型
    print(f"\n🚀 训练增强模型...")

    trainer = SimpleEnhancedTrainer()

    # 加载和准备数据
    df = trainer.load_and_prepare_data("data/processed/features_v2_rolling.csv")

    # 选择增强特征
    X, y, feature_columns = trainer.select_enhanced_features(df)

    # 时序分割
    X_train, X_test, y_train_enc, y_test_enc, y_train_orig, y_test_orig = \
        trainer.split_data_chronological(X, y)

    # 训练模型
    trainer.feature_names = feature_columns
    trainer.train_xgboost(X_train, y_train_enc)

    # 评估模型
    results = trainer.evaluate_model(X_test, y_test_enc, y_test_orig)

    # 特征重要性
    trainer.plot_feature_importance()

    # 3. 性能对比
    enhanced_acc = results['accuracy']
    enhanced_logloss = results['log_loss']

    acc_improvement = ((enhanced_acc - baseline_acc) / baseline_acc) * 100
    logloss_improvement = ((baseline_logloss - enhanced_logloss) / baseline_logloss) * 100

    print(f"\n📈 性能对比:")
    print(f"{'指标':<15} {'基线':<10} {'增强':<10} {'改进':<10}")
    print("-" * 50)
    print(f"{'准确率':<15} {baseline_acc:<10.4f} {enhanced_acc:<10.4f} {acc_improvement:+.2f}%")
    print(f"{'Log Loss':<15} {baseline_logloss:<10.4f} {enhanced_logloss:<10.4f} {logloss_improvement:+.2f}%")

    if acc_improvement > 0.5:
        print(f"\n🎉 增强特征显著提升了模型性能!")
    elif acc_improvement > 0:
        print(f"\n📈 增强特征轻微提升了模型性能")
    else:
        print(f"\n➡️ 增强特征对性能影响有限")

    return results


if __name__ == "__main__":
    run_enhanced_experiment()