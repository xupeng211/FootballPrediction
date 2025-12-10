#!/usr/bin/env python3
"""
检查数据集中的赔率特征
"""

import pandas as pd

def check_odds_data():
    """检查赔率数据"""
    df = pd.read_csv("data/processed/features_v2_rolling.csv")

    odds_cols = [col for col in df.columns if 'odds' in col.lower()]

    print("📊 赔率相关列:")
    if odds_cols:
        for col in odds_cols:
            non_null_count = df[col].notna().sum()
            print(f"   {col}: {non_null_count}/{len(df)} ({non_null_count/len(df)*100:.1f}%)")

        print(f"\n💰 赔率数据样本:")
        print(df[odds_cols].head())

        if non_null_count > 0:
            print(f"\n✅ 发现可用赔率数据")
        else:
            print(f"\n❌ 赔率数据为空")
    else:
        print("   ❌ 未发现赔率相关列")
        print(f"\n📋 可用列预览:")
        print([col for col in df.columns if 'win' in col.lower() or 'draw' in col.lower() or 'away' in col.lower()])

if __name__ == "__main__":
    check_odds_data()