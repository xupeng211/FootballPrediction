#!/usr/bin/env python3
"""
验证滚动特征数据集
"""

import pandas as pd

def validate_rolling_features():
    """验证滚动特征数据集"""

    # 加载数据集
    df = pd.read_csv("data/processed/features_v2_rolling.csv")

    print("=" * 80)
    print("🏆 滚动特征数据集验证")
    print("=" * 80)

    print(f"📊 数据集概况:")
    print(f"   数据形状: {df.shape}")
    print(f"   特征数量: {len(df.columns)}")

    # 查找滚动特征
    rolling_cols = [col for col in df.columns if 'last_5_avg' in col]
    print(f"\n🎯 Last 5 场平均特征 ({len(rolling_cols)}个):")

    # 显示基础信息列 + 前5个滚动特征
    base_cols = ['match_id', 'home_score', 'away_score']
    sample_cols = base_cols + rolling_cols[:5]
    existing_cols = [col for col in sample_cols if col in df.columns]

    print(f"\n📋 前3行数据样本:")
    print(df[existing_cols].head(3).to_string(index=False))

    # 显示滚动特征的基本统计
    if rolling_cols:
        print(f"\n📈 滚动特征统计:")
        for col in rolling_cols[:3]:
            if col in df.columns:
                print(f"   {col}: mean={df[col].mean():.3f}, std={df[col].std():.3f}")

    print(f"\n✅ 滚动特征数据集验证完成")

    return df

if __name__ == "__main__":
    validate_rolling_features()