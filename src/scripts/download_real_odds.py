#!/usr/bin/env python3
"""
V9.0 真实赔率下载器 - 从 football-data.co.uk
下载英超 23/24 和 24/25 赛季的真实历史赔率
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def download_odds_data():
    """下载真实赔率数据"""

    print("📊 从 football-data.co.uk 下载真实赔率数据")
    print("=" * 60)

    # 数据源URLs
    urls = {
        "23/24": "https://www.football-data.co.uk/mmz4281/2324/E0.csv",  # 英超
        "24/25": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",  # 英超
    }

    all_data = []

    for season, url in urls.items():
        print(f"\n📅 下载 {season} 赛季赔率数据...")
        try:
            # 下载数据
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # 读取CSV
            df = pd.read_csv(url)
            df['Season'] = season

            print(f"  ✅ 成功下载: {len(df)} 场比赛")
            print(f"  📋 列名: {list(df.columns)[:10]}...")

            # 标准化列名
            df = standardize_columns(df)
            all_data.append(df)

        except Exception as e:
            print(f"  ❌ 下载失败: {e}")

    if all_data:
        # 合并所有赛季数据
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\n✅ 合并完成: {len(combined_df)} 场比赛")

        # 保存到文件
        output_path = "/home/user/projects/FootballPrediction/data/real_odds_raw.csv"
        combined_df.to_csv(output_path, index=False)
        print(f"✅ 原始赔率数据已保存: {output_path}")

        return combined_df
    else:
        print("❌ 未下载到任何数据")
        return None


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化列名"""

    # 赔率数据常见列名映射
    column_mapping = {
        'Date': 'match_date',
        'HomeTeam': 'home_team',
        'AwayTeam': 'away_team',
        'B365H': 'b365_home_odds',  # Bet365 主胜赔率
        'B365D': 'b365_draw_odds',  # Bet365 平局赔率
        'B365A': 'b365_away_odds',  # Bet365 客胜赔率
        'BWH': 'bw_home_odds',      # Betway
        'BWD': 'bw_draw_odds',
        'BWA': 'bw_away_odds',
        'IWH': 'iw_home_odds',      # Interwetten
        'IWD': 'iw_draw_odds',
        'IWA': 'iw_away_odds',
        'PSH': 'ps_home_odds',      # Pinnacle
        'PSD': 'ps_draw_odds',
        'PSA': 'ps_away_odds',
        'WHH': 'wh_home_odds',      # William Hill
        'WHD': 'wh_draw_odds',
        'WHA': 'wh_away_odds',
        'VCH': 'vc_home_odds',      # VC Bet
        'VCD': 'vc_draw_odds',
        'VCA': 'vc_away_odds',
        'MaxH': 'max_home_odds',    # 最高赔率
        'MaxD': 'max_draw_odds',
        'MaxA': 'max_away_odds',
        'AvgH': 'avg_home_odds',    # 平均赔率
        'AvgD': 'avg_draw_odds',
        'AvgA': 'avg_away_odds',
    }

    # 重命名列
    df = df.rename(columns=column_mapping)

    # 处理日期格式
    if 'match_date' in df.columns:
        # 尝试多种日期格式
        for date_format in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                df['match_date'] = pd.to_datetime(df['match_date'], format=date_format)
                break
            except:
                continue

        # 如果还是字符串，尝试自动解析
        if df['match_date'].dtype == 'object':
            df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')

    # 标准化球队名称（英超）
    team_name_mapping = {
        # 赔率数据 -> 预测数据
        'Bournemouth': 'AFC Bournemouth',
        'Ipswich': 'Ipswich Town',  # 24/25新升级
        'Leicester': 'Leicester City',
        'Luton': 'Luton Town',
        'Sheffield United': 'Sheffield United',
        'Southampton': 'Southampton',
        'West Ham': 'West Ham United',
        'Wolves': 'Wolverhampton Wanderers',
        'Nott\'m Forest': 'Nottingham Forest',
    }

    if 'home_team' in df.columns:
        df['home_team'] = df['home_team'].replace(team_name_mapping)
    if 'away_team' in df.columns:
        df['away_team'] = df['away_team'].replace(team_name_mapping)

    # 过滤掉不在预测数据中的球队
    valid_teams = {
        'AFC Bournemouth', 'Arsenal', 'Aston Villa', 'Brentford',
        'Brighton & Hove Albion', 'Burnley', 'Chelsea', 'Crystal Palace',
        'Everton', 'Fulham', 'Leeds United', 'Liverpool', 'Manchester City',
        'Manchester United', 'Newcastle United', 'Nottingham Forest',
        'Sunderland', 'Tottenham Hotspur', 'West Ham United',
        'Wolverhampton Wanderers'
    }

    df = df[
        (df['home_team'].isin(valid_teams)) &
        (df['away_team'].isin(valid_teams))
    ]

    print(f"  🔍 过滤后保留: {len(df)} 场比赛")

    return df


def merge_with_predictions(real_odds_path: str, predictions_path: str) -> pd.DataFrame:
    """
    将真实赔率与预测数据合并

    Args:
        real_odds_path: 真实赔率数据路径
        predictions_path: 预测数据路径

    Returns:
        合并后的DataFrame
    """
    print("\n🔗 合并真实赔率与预测数据...")

    # 加载数据
    odds_df = pd.read_csv(real_odds_path)
    pred_df = pd.read_csv(predictions_path)

    print(f"  赔率数据: {len(odds_df)} 场")
    print(f"  预测数据: {len(pred_df)} 场")

    # 确保日期格式一致
    if 'match_time' in pred_df.columns:
        pred_df['match_time'] = pd.to_datetime(pred_df['match_time'])
    if 'match_date' in odds_df.columns:
        odds_df['match_date'] = pd.to_datetime(odds_df['match_date'])

    # 创建合并键
    # 方法1: 基于日期和球队名称
    merged_df = pd.merge(
        pred_df,
        odds_df,
        left_on=['home_team', 'away_team'],
        right_on=['home_team', 'away_team'],
        how='inner',
        suffixes=('_pred', '_odds')
    )

    # 进一步筛选日期范围（允许误差±3天）
    if 'match_time' in merged_df.columns and 'match_date' in merged_df.columns:
        # 转换为naive datetime以便比较
        match_time = merged_df['match_time'].dt.tz_localize(None)
        match_date = merged_df['match_date'].dt.tz_localize(None)

        merged_df['date_diff'] = abs(
            (match_time - match_date).dt.days
        )
        merged_df = merged_df[merged_df['date_diff'] <= 3]

    print(f"  ✅ 合并成功: {len(merged_df)} 场比赛")

    # 保存合并数据
    output_path = "/home/user/projects/FootballPrediction/data/merged_real_odds.csv"
    merged_df.to_csv(output_path, index=False)
    print(f"✅ 合并数据已保存: {output_path}")

    return merged_df


def main():
    """主函数"""
    # 下载真实赔率
    odds_df = download_odds_data()

    if odds_df is not None:
        # 合并数据
        pred_path = "/home/user/projects/FootballPrediction/data/multi_season_v85.csv"
        merged_df = merge_with_predictions(
            "/home/user/projects/FootballPrediction/data/real_odds_raw.csv",
            pred_path
        )

        print("\n" + "=" * 60)
        print("✅ 真实赔率数据接入完成")
        print("=" * 60)
        print(f"  📊 可用比赛: {len(merged_df)}")
        print(f"  💰 Bet365 赔率覆盖: {'✅' if 'b365_home_odds' in merged_df.columns else '❌'}")
        print(f"  📅 数据范围: {merged_df['match_time'].min()} ~ {merged_df['match_time'].max()}")
    else:
        print("\n❌ 真实赔率数据下载失败")


if __name__ == "__main__":
    main()
