#!/usr/bin/env python3
"""
数据泄露分析脚本
识别后比赛统计数据，设计时序特征工程方案
"""

import pandas as pd


def analyze_data_leakage():
    """分析数据泄露问题"""

    # 加载数据集
    df = pd.read_csv("data/processed/features_v1.csv")

    print("=== 数据泄露分析 ===")
    print(f"数据集形状: {df.shape}")
    print(f"日期范围: {df['year'].min()}-{df['year'].max()}")

    # 分析存在泄露风险的后比赛统计特征
    post_match_leakage_features = [
        "home_total_shots",
        "away_total_shots",
        "home_shots_on_target",
        "away_shots_on_target",
        "home_shots_off_target",
        "away_shots_off_target",
        "home_blocked_shots",
        "away_blocked_shots",
        "home_offsides",
        "away_offsides",
        "home_total_passes",
        "away_total_passes",
        "home_pass_accuracy",
        "away_pass_accuracy",
    ]

    print(f"\n🚨 存在泄露风险的后比赛统计特征 ({len(post_match_leakage_features)}个):")
    for feature in post_match_leakage_features:
        if feature in df.columns:
            non_null_count = df[feature].notna().sum()
            print(
                f"  {feature:25}: {non_null_count:4,}/{len(df):4,} ({non_null_count / len(df) * 100:5.1f}%)"
            )

    # 安全的预测特征（赛前可获得）
    safe_pre_match_features = [
        "home_xg",
        "away_xg",
        "xg_difference",
        "year",
        "month",
        "day_of_week",
        "is_weekend",
    ]

    print(f"\n✅ 安全的赛前特征 ({len(safe_pre_match_features)}个):")
    for feature in safe_pre_match_features:
        if feature in df.columns:
            non_null_count = df[feature].notna().sum()
            print(
                f"  {feature:20}: {non_null_count:4,}/{len(df):4,} ({non_null_count / len(df) * 100:5.1f}%)"
            )

    print("\n📋 建议的时序特征工程方案:")
    print("  1. 从进球数据推导历史表现指标")
    print("  2. 计算球队最近N场比赛的滚动平均")
    print("  3. 使用xG的时序趋势作为预测特征")
    print("  4. 构建主客场表现差异指标")

    return df, post_match_leakage_features


if __name__ == "__main__":
    df, leakage_features = analyze_data_leakage()
