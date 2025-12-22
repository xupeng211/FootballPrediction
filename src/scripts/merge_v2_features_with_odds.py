#!/usr/bin/env python3
"""
V9.3 大规模数据合并器
将 features_v2_rolling.csv (1900场) 与 real_odds_raw.csv (420场) 合并
目标: 创建 500+ 场的大规模数据集
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import warnings
warnings.filterwarnings('ignore')

# 球队名称映射表 (特征数据 -> 赔率数据)
TEAM_NAME_MAPPING = {
    'Brighton & Hove Albion': 'Brighton',
    'Leicester City': 'Leicester',
    'Luton Town': 'Luton',
    'Sheffield United': 'Sheffield United',
    'Southampton': 'Southampton',
    'West Bromwich Albion': 'West Brom',
    'Wolverhampton Wanderers': 'Wolves',
    'AFC Bournemouth': 'Bournemouth',
    'Nottingham Forest': "Nott'm Forest",
    'Manchester United': 'Man United',
    'Manchester City': 'Man City',
    'Newcastle United': 'Newcastle',
    'Leeds United': 'Leeds',
    'Tottenham Hotspur': 'Tottenham',
    'West Ham United': 'West Ham',
    'Norwich City': 'Norwich',
    'Watford': 'Watford',
    'Crystal Palace': 'Crystal Palace',
    'Aston Villa': 'Aston Villa',
    'Chelsea': 'Chelsea',
    'Arsenal': 'Arsenal',
    'Liverpool': 'Liverpool',
    'Brentford': 'Brentford',
    'Fulham': 'Fulham',
    'Burnley': 'Burnley',
    'Everton': 'Everton',
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

def merge_features_with_odds():
    """合并特征数据和赔率数据"""
    print("🔗 V9.3 大规模数据合并")
    print("=" * 60)

    # 加载数据
    features_df = pd.read_csv("/home/user/projects/FootballPrediction/data/processed/features_v2_rolling.csv")
    odds_df = pd.read_csv("/home/user/projects/FootballPrediction/data/real_odds_raw.csv")

    print(f"  特征数据: {len(features_df)} 场")
    print(f"  赔率数据: {len(odds_df)} 场")

    # 转换日期格式
    features_df['match_date'] = pd.to_datetime(features_df['match_date'])
    odds_df['match_date'] = pd.to_datetime(odds_df['match_date'])

    # 添加赛季列
    features_df['season'] = features_df['match_date'].apply(
        lambda x: f'{x.year-1}/{x.year}' if x.month <= 7 else f'{x.year}/{x.year+1}'
    )
    odds_df['season'] = odds_df['Season']

    print(f"\n📊 特征数据赛季分布:")
    for season in sorted(features_df['season'].unique()):
        count = len(features_df[features_df['season'] == season])
        print(f"  {season}: {count} 场")

    print(f"\n📊 赔率数据赛季分布:")
    for season in sorted(odds_df['season'].unique()):
        count = len(odds_df[odds_df['season'] == season])
        print(f"  {season}: {count} 场")

    # 获取赔率数据中的球队
    odds_teams = set(odds_df['home_team'].unique()) | set(odds_df['away_team'].unique())
    print(f"\n  赔率数据中的球队: {sorted(odds_teams)}")

    # 合并数据
    merged_data = []
    matched_count = 0
    unmatched_count = 0

    for idx, odds_row in odds_df.iterrows():
        home_team_odds = odds_row['home_team']
        away_team_odds = odds_row['away_team']
        odds_date = odds_row['match_date'].date()

        # 在特征数据中查找匹配的比赛
        # 使用日期匹配 (允许误差 ±3 天)
        date_min = odds_date.replace(day=max(1, odds_date.day - 3))
        date_max = odds_date.replace(day=min(28, odds_date.day + 3))

        matches = features_df[
            (features_df['match_date'].dt.date >= date_min) &
            (features_df['match_date'].dt.date <= date_max) &
            (features_df['home_team_name'] == home_team_odds) &
            (features_df['away_team_name'] == away_team_odds)
        ]

        if len(matches) > 0:
            # 找到匹配，取最接近的日期
            match = matches.iloc[0]

            # 合并数据
            merged_row = match.copy()

            # 添加赔率数据
            merged_row['real_home_odds'] = odds_row['b365_home_odds']
            merged_row['real_draw_odds'] = odds_row['b365_draw_odds']
            merged_row['real_away_odds'] = odds_row['b365_away_odds']
            merged_row['real_match_date'] = odds_row['match_date']
            merged_row['real_season'] = odds_row['season']
            merged_row['actual_home_goals'] = odds_row['FTHG']
            merged_row['actual_away_goals'] = odds_row['FTAG']
            merged_row['actual_result'] = odds_row['FTR']

            # 添加其他赔率
            merged_row['bw_home_odds'] = odds_row['bw_home_odds']
            merged_row['bw_draw_odds'] = odds_row['bw_draw_odds']
            merged_row['bw_away_odds'] = odds_row['bw_away_odds']

            merged_data.append(merged_row)
            matched_count += 1

            if matched_count % 50 == 0:
                print(f"  已匹配: {matched_count} 场...")
        else:
            unmatched_count += 1

    # 创建DataFrame
    if merged_data:
        merged_df = pd.DataFrame(merged_data)
        print(f"\n✅ 合并成功: {len(merged_df)} 场比赛")
        print(f"  匹配成功: {matched_count}")
        print(f"  未匹配: {unmatched_count}")
        print(f"  匹配率: {matched_count / (matched_count + unmatched_count) * 100:.1f}%")

        # 保存
        output_path = "/home/user/projects/FootballPrediction/data/v9_3_massive_merged_data.csv"
        merged_df.to_csv(output_path, index=False)
        print(f"\n✅ 合并数据已保存: {output_path}")

        # 显示赛季分布
        print(f"\n📊 合并数据的赛季分布:")
        for season in sorted(merged_df['real_season'].unique()):
            count = len(merged_df[merged_df['real_season'] == season])
            print(f"  {season}: {count} 场")

        # 显示样本
        print(f"\n📋 样本数据 (前5场):")
        sample_cols = ['home_team_name', 'away_team_name', 'real_season', 'real_home_odds', 'real_draw_odds', 'real_away_odds', 'actual_result']
        print(merged_df[sample_cols].head())

        # 统计
        print(f"\n🎯 V9.3 数据集统计:")
        print(f"  总比赛数: {len(merged_df)}")
        print(f"  目标: 500+ 场")
        print(f"  是否达标: {'✅ 是' if len(merged_df) >= 500 else '❌ 否'}")

        return merged_df
    else:
        print("\n❌ 未找到匹配的比赛")
        return None

def main():
    """主函数"""
    merged_df = merge_features_with_odds()

    if merged_df is not None:
        print("\n" + "=" * 60)
        print("✅ V9.3 大规模数据合并完成")
        print("=" * 60)
        print(f"  📊 总比赛数: {len(merged_df)}")
        print(f"  🎯 目标: 500+ 场")
        print(f"  ✅ 状态: {'达标' if len(merged_df) >= 500 else '未达标'}")
    else:
        print("\n❌ 数据合并失败")

if __name__ == "__main__":
    main()
