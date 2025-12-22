#!/usr/bin/env python3
"""
V9.0 真实赔率合并器 - 简化版
基于球队名称合并预测数据和真实赔率
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher


def similarity(a, b):
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, a, b).ratio()


def find_best_match(team_name, team_list, threshold=0.8):
    """在球队列表中找到最佳匹配"""
    best_match = None
    best_score = 0

    for team in team_list:
        score = similarity(team_name, team)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = team

    return best_match, best_score


def merge_odds_and_predictions():
    """合并赔率和预测数据"""

    print("🔗 合并真实赔率与预测数据...")
    print("=" * 60)

    # 加载数据
    odds_df = pd.read_csv("/home/user/projects/FootballPrediction/data/real_odds_raw.csv")
    pred_df = pd.read_csv("/home/user/projects/FootballPrediction/data/multi_season_v85.csv")

    print(f"  赔率数据: {len(odds_df)} 场")
    print(f"  预测数据: {len(pred_df)} 场")

    # 创建合并后的数据列表
    merged_data = []

    for idx, pred_row in pred_df.iterrows():
        pred_home = pred_row['home_team']
        pred_away = pred_row['away_team']

        # 在赔率数据中找到匹配的比赛
        matches = odds_df[
            (odds_df['home_team'] == pred_home) &
            (odds_df['away_team'] == pred_away)
        ]

        if len(matches) > 0:
            # 取第一个匹配（如果有多个，取最新的）
            match = matches.iloc[-1]

            # 合并数据
            merged_row = pred_row.copy()
            merged_row['real_home_odds'] = match['b365_home_odds']
            merged_row['real_draw_odds'] = match['b365_draw_odds']
            merged_row['real_away_odds'] = match['b365_away_odds']
            merged_row['real_match_date'] = match['match_date']
            merged_row['actual_home_goals'] = match.get('FTHG', np.nan)
            merged_row['actual_away_goals'] = match.get('FTAG', np.nan)
            merged_row['actual_result'] = match.get('FTR', np.nan)

            merged_data.append(merged_row)

    # 创建DataFrame
    if merged_data:
        merged_df = pd.DataFrame(merged_data)
        print(f"  ✅ 合并成功: {len(merged_df)} 场比赛")

        # 保存
        output_path = "/home/user/projects/FootballPrediction/data/merged_real_odds.csv"
        merged_df.to_csv(output_path, index=False)
        print(f"✅ 合并数据已保存: {output_path}")

        # 显示赔率覆盖
        print(f"\n📊 赔率覆盖统计:")
        print(f"  Bet365 主胜赔率: {merged_df['real_home_odds'].notna().sum()}")
        print(f"  Bet365 平局赔率: {merged_df['real_draw_odds'].notna().sum()}")
        print(f"  Bet365 客胜赔率: {merged_df['real_away_odds'].notna().sum()}")

        # 显示样本
        print(f"\n📋 样本数据:")
        sample_cols = ['home_team', 'away_team', 'real_home_odds', 'real_draw_odds', 'real_away_odds']
        print(merged_df[sample_cols].head())

        return merged_df
    else:
        print("  ❌ 未找到匹配的比赛")
        return None


def main():
    merged_df = merge_odds_and_predictions()

    if merged_df is not None:
        print("\n" + "=" * 60)
        print("✅ 真实赔率数据合并完成")
        print("=" * 60)
        print(f"  📊 可用比赛: {len(merged_df)}")
        print(f"  💰 Bet365 赔率覆盖: ✅")
        print(f"  📅 数据范围: {merged_df['match_time'].min()} ~ {merged_df['match_time'].max()}")
    else:
        print("\n❌ 数据合并失败")


if __name__ == "__main__":
    main()
