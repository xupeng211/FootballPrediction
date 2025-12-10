#!/usr/bin/env python3
"""
详细检查赔率数据状态
"""

import pandas as pd

def check_odds_detailed():
    """详细检查赔率数据"""
    print("🔍 检查原始数据中的赔率列")

    # 检查原始数据
    df_original = pd.read_csv("data/processed/features_with_teams.csv")
    odds_cols = ['home_win_odds', 'draw_odds', 'away_win_odds']

    print("\n📊 原始数据 (features_with_teams.csv):")
    print(f"   形状: {df_original.shape}")

    for col in odds_cols:
        if col in df_original.columns:
            non_null_count = df_original[col].notna().sum()
            null_count = df_original[col].isna().sum()
            print(f"   {col}: {non_null_count}/{len(df_original)} ({non_null_count/len(df_original)*100:.1f}%) 非空")

            if non_null_count > 0:
                print(f"      样本值: {df_original[col].dropna().head(3).tolist()}")
        else:
            print(f"   {col}: ❌ 列不存在")

    # 检查当前V2数据
    try:
        df_v2 = pd.read_csv("data/processed/features_v2_rolling.csv")
        print(f"\n📊 当前V2数据 (features_v2_rolling.csv):")
        print(f"   形状: {df_v2.shape}")

        for col in odds_cols:
            if col in df_v2.columns:
                non_null_count = df_v2[col].notna().sum()
                print(f"   {col}: {non_null_count}/{len(df_v2)} ({non_null_count/len(df_v2)*100:.1f}%) 非空")
            else:
                print(f"   {col}: ❌ 列已丢失")
    except FileNotFoundError:
        print(f"\n❌ V2数据文件不存在")

    # 检查是否有其他可能的赔率列
    print(f"\n🔍 搜索其他可能的赔率列:")
    potential_odds_cols = [col for col in df_original.columns if any(keyword in col.lower() for keyword in ['odds', 'price', 'bet', 'win'])]
    if potential_odds_cols:
        print(f"   发现可能的赔率列: {potential_odds_cols}")
    else:
        print(f"   ❌ 未发现任何赔率相关列")

if __name__ == "__main__":
    check_odds_detailed()