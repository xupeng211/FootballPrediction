#!/usr/bin/env python3
"""
分析匹配缺口
为什么 420 场赔率数据只匹配到 264 场？
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

def analyze_matching_gaps():
    """分析匹配缺口"""
    print("🔍 匹配缺口分析")
    print("=" * 60)

    # 加载数据
    features_df = pd.read_csv("/home/user/projects/FootballPrediction/data/processed/features_v2_rolling.csv")
    odds_df = pd.read_csv("/home/user/projects/FootballPrediction/data/real_odds_raw.csv")

    # 转换日期
    features_df['match_date'] = pd.to_datetime(features_df['match_date'])
    odds_df['match_date'] = pd.to_datetime(odds_df['match_date'])

    # 添加赛季列
    features_df['season'] = features_df['match_date'].apply(
        lambda x: f'{x.year-1}/{x.year}' if x.month <= 7 else f'{x.year}/{x.year+1}'
    )
    odds_df['season'] = odds_df['Season']

    print(f"特征数据: {len(features_df)} 场")
    print(f"赔率数据: {len(odds_df)} 场")

    # 按赛季和球队统计
    print(f"\n📊 按赛季分析:")

    for season in ['22/23', '23/24']:
        print(f"\n=== 赛季 {season} ===")

        # 该赛季的赔率数据
        season_odds = odds_df[odds_df['season'] == season]
        print(f"赔率数据: {len(season_odds)} 场")

        # 该赛季的特征数据
        season_features = features_df[features_df['season'] == season]
        print(f"特征数据: {len(season_features)} 场")

        # 赔率数据中的球队
        odds_teams = set(season_odds['home_team'].unique()) | set(season_odds['away_team'].unique())
        print(f"赔率球队: {sorted(odds_teams)}")

        # 特征数据中的球队
        feat_teams = set(season_features['home_team_name'].unique()) | set(season_features['away_team_name'].unique())
        print(f"特征球队: {sorted(feat_teams)}")

        # 共同球队
        common_teams = odds_teams & feat_teams
        print(f"共同球队: {sorted(common_teams)} ({len(common_teams)}/{len(odds_teams)})")

        # 检查每个球队的比赛数
        print(f"\n球队比赛数对比:")
        for team in sorted(odds_teams):
            odds_count = len(season_odds[(season_odds['home_team'] == team) | (season_odds['away_team'] == team)])
            feat_count = len(season_features[(season_features['home_team_name'] == team) | (season_features['away_team_name'] == team)])
            print(f"  {team:25} 赔率:{odds_count:3d} 特征:{feat_count:3d} 差值:{feat_count-odds_count:+3d}")

    # 尝试扩大日期范围匹配
    print(f"\n🔄 尝试扩大日期范围匹配 (7天)...")

    merged_data = []
    matched_count = 0
    unmatched_odds = []

    for idx, odds_row in odds_df.iterrows():
        home_team_odds = odds_row['home_team']
        away_team_odds = odds_row['away_team']
        odds_date = odds_row['match_date'].date()

        # 扩大日期范围到 ±7 天
        date_min = odds_date - timedelta(days=7)
        date_max = odds_date + timedelta(days=7)

        matches = features_df[
            (features_df['match_date'].dt.date >= date_min) &
            (features_df['match_date'].dt.date <= date_max) &
            (features_df['home_team_name'] == home_team_odds) &
            (features_df['away_team_name'] == away_team_odds)
        ]

        if len(matches) > 0:
            matched_count += 1
        else:
            unmatched_odds.append({
                'home_team': home_team_odds,
                'away_team': away_team_odds,
                'date': odds_date,
                'season': odds_row['season']
            })

    print(f"扩大范围后匹配数: {matched_count}/{len(odds_df)} ({matched_count/len(odds_df)*100:.1f}%)")

    # 分析未匹配的样本
    if unmatched_odds:
        unmatched_df = pd.DataFrame(unmatched_odds)
        print(f"\n❌ 未匹配样本 (前20个):")
        print(unmatched_df.head(20))

        print(f"\n📊 未匹配按赛季统计:")
        print(unmatched_df['season'].value_counts())

        print(f"\n📊 未匹配按球队统计:")
        team_unmatched = {}
        for _, row in unmatched_df.iterrows():
            team_unmatched[row['home_team']] = team_unmatched.get(row['home_team'], 0) + 1
            team_unmatched[row['away_team']] = team_unmatched.get(row['away_team'], 0) + 1

        for team, count in sorted(team_unmatched.items(), key=lambda x: x[1], reverse=True):
            print(f"  {team:25}: {count} 场未匹配")

    return unmatched_odds

def main():
    """主函数"""
    unmatched = analyze_matching_gaps()

if __name__ == "__main__":
    main()
