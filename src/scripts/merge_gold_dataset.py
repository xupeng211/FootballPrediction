#!/usr/bin/env python3
"""
V9.2 黄金数据集合并器
将 gold_dataset_v1 与多赛季赔率数据合并
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import warnings
warnings.filterwarnings('ignore')

# 球队名称映射表 (赔率数据 -> 预测数据)
TEAM_NAME_MAPPING = {
    'Bournemouth': 'AFC Bournemouth',
    'Brighton': 'Brighton & Hove Albion',
    'Leicester': 'Leicester City',
    'Luton': 'Luton Town',
    'Sheffield United': 'Sheffield United',
    'Southampton': 'Southampton',
    'West Ham': 'West Ham United',
    'Wolves': 'Wolverhampton Wanderers',
    'Nott\'m Forest': 'Nottingham Forest',
    'Tottenham': 'Tottenham Hotspur',
    'Man United': 'Manchester United',
    'Man City': 'Manchester City',
    'Newcastle': 'Newcastle United',
    'Leeds': 'Leeds United',
    'Everton': 'Everton',
    'Burnley': 'Burnley',
    'Crystal Palace': 'Crystal Palace',
    'Aston Villa': 'Aston Villa',
    'Chelsea': 'Chelsea',
    'Arsenal': 'Arsenal',
    'Liverpool': 'Liverpool',
    'Brentford': 'Brentford',
    'Fulham': 'Fulham',
    'West Brom': 'West Bromwich Albion',
    'Watford': 'Watford',
    'Norwich': 'Norwich City',
}

def similarity(a, b):
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_match(team_name, team_list, threshold=0.8):
    """在球队列表中找到最佳匹配"""
    best_match = None
    best_score = 0

    # 首先尝试直接映射
    if team_name in TEAM_NAME_MAPPING:
        mapped_name = TEAM_NAME_MAPPING[team_name]
        if mapped_name in team_list:
            return mapped_name, 1.0

    # 然后尝试模糊匹配
    for team in team_list:
        score = similarity(team_name, team)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = team

    return best_match, best_score

def merge_gold_dataset():
    """合并黄金数据集与赔率数据"""
    print("🔗 黄金数据集与赔率数据合并")
    print("=" * 60)

    # 加载数据
    odds_df = pd.read_csv("/home/user/projects/FootballPrediction/data/real_odds_raw.csv")
    gold_df = pd.read_csv("/home/user/projects/FootballPrediction/data/gold_dataset_v1.csv")

    print(f"  赔率数据: {len(odds_df)} 场")
    print(f"  黄金数据集: {len(gold_df)} 场")

    # 转换日期格式
    gold_df['match_time'] = pd.to_datetime(gold_df['match_time'])
    odds_df['match_date'] = pd.to_datetime(odds_df['match_date'])

    # 获取黄金数据集中的所有球队
    gold_teams = set(gold_df['home_team'].unique()) | set(gold_df['away_team'].unique())
    print(f"  黄金数据集中的球队: {len(gold_teams)} 支")

    # 合并数据
    merged_data = []
    matched_count = 0
    unmatched_count = 0

    for idx, odds_row in odds_df.iterrows():
        home_team_odds = odds_row['home_team']
        away_team_odds = odds_row['away_team']

        # 查找最佳匹配
        home_match, home_score = find_best_match(home_team_odds, gold_teams)
        away_match, away_score = find_best_match(away_team_odds, gold_teams)

        if home_match and away_score > 0.8:
            # 找到匹配，在黄金数据中查找对应比赛
            # 使用日期匹配 (允许误差 ±3 天)
            odds_date = odds_row['match_date'].date()

            # 简化匹配: 只基于球队名称匹配
            matches = gold_df[
                (gold_df['home_team'] == home_match) &
                (gold_df['away_team'] == away_match)
            ]

            if len(matches) > 0:
                # 取第一个匹配
                match = matches.iloc[0]

                # 合并数据
                merged_row = match.copy()
                merged_row['real_home_odds'] = odds_row['b365_home_odds']
                merged_row['real_draw_odds'] = odds_row['b365_draw_odds']
                merged_row['real_away_odds'] = odds_row['b365_away_odds']
                merged_row['real_match_date'] = odds_row['match_date']
                merged_row['real_season'] = odds_row['Season']
                merged_row['actual_home_goals'] = odds_row.get('FTHG', np.nan)
                merged_row['actual_away_goals'] = odds_row.get('FTAG', np.nan)
                merged_row['actual_result'] = odds_row.get('FTR', np.nan)

                merged_data.append(merged_row)
                matched_count += 1

                if matched_count % 50 == 0:
                    print(f"  已匹配: {matched_count} 场...")
            else:
                unmatched_count += 1
        else:
            unmatched_count += 1

    # 创建DataFrame
    if merged_data:
        merged_df = pd.DataFrame(merged_data)
        print(f"\n✅ 合并成功: {len(merged_df)} 场比赛")
        print(f"  匹配成功: {matched_count}")
        print(f"  未匹配: {unmatched_count}")

        # 保存
        output_path = "/home/user/projects/FootballPrediction/data/gold_dataset_with_odds.csv"
        merged_df.to_csv(output_path, index=False)
        print(f"✅ 合并数据已保存: {output_path}")

        # 显示赛季分布
        if 'real_season' in merged_df.columns:
            print(f"\n📊 赛季分布:")
            for season in merged_df['real_season'].unique():
                count = len(merged_df[merged_df['real_season'] == season])
                print(f"  {season}: {count} 场")

        # 显示样本
        print(f"\n📋 样本数据:")
        sample_cols = ['home_team', 'away_team', 'real_season', 'real_home_odds', 'real_draw_odds', 'real_away_odds']
        if all(col in merged_df.columns for col in sample_cols):
            print(merged_df[sample_cols].head(10))

        return merged_df
    else:
        print("  ❌ 未找到匹配的比赛")
        return None

def main():
    merged_df = merge_gold_dataset()

    if merged_df is not None:
        print("\n" + "=" * 60)
        print("✅ 黄金数据集合并完成")
        print("=" * 60)
        print(f"  📊 总比赛数: {len(merged_df)}")
        print(f"  🎯 目标: 500+ 场")
        print(f"  ✅ 是否达标: {'是' if len(merged_df) >= 500 else '否 (当前 ' + str(len(merged_df)) + ' 场)'}")
    else:
        print("\n❌ 数据合并失败")

if __name__ == "__main__":
    main()
