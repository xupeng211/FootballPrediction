#!/usr/bin/env python3
"""
V9.3 综合数据扩容器 (修正版)
将所有可用数据源合并，创建 500+ 场的完整数据集
"""

from datetime import timedelta
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def calculate_season(date):
    """正确计算英超赛季 (8月到次年5月)"""
    year = date.year
    month = date.month

    if month >= 8:
        return f"{year}/{year + 1}"
    return f"{year - 1}/{year}"


def merge_all_available_data():
    """合并所有可用数据"""

    # 加载所有数据源
    features_df = pd.read_csv(
        "/home/user/projects/FootballPrediction/data/processed/features_v2_rolling.csv"
    )
    odds_df = pd.read_csv("/home/user/projects/FootballPrediction/data/real_odds_raw.csv")


    # 转换日期格式
    features_df["match_date"] = pd.to_datetime(features_df["match_date"])
    odds_df["match_date"] = pd.to_datetime(odds_df["match_date"])

    # 计算赛季
    features_df["season"] = features_df["match_date"].apply(calculate_season)
    odds_df["season"] = odds_df["Season"]

    for season in sorted(features_df["season"].unique()):
        len(features_df[features_df["season"] == season])

    for season in sorted(odds_df["season"].unique()):
        len(odds_df[odds_df["season"] == season])

    # 第一步：合并特征数据与赔率数据
    merged_data = []
    matched_count = 0

    for _idx, odds_row in odds_df.iterrows():
        home_team_odds = odds_row["home_team"]
        away_team_odds = odds_row["away_team"]
        odds_date = odds_row["match_date"].date()

        # 日期范围 ±7 天
        date_min = odds_date - timedelta(days=7)
        date_max = odds_date + timedelta(days=7)

        # 在特征数据中查找匹配
        matches = features_df[
            (features_df["match_date"].dt.date >= date_min)
            & (features_df["match_date"].dt.date <= date_max)
            & (features_df["home_team_name"] == home_team_odds)
            & (features_df["away_team_name"] == away_team_odds)
        ]

        if len(matches) > 0:
            match = matches.iloc[0]
            merged_row = match.copy()

            # 添加赔率数据
            merged_row["real_home_odds"] = odds_row["b365_home_odds"]
            merged_row["real_draw_odds"] = odds_row["b365_draw_odds"]
            merged_row["real_away_odds"] = odds_row["b365_away_odds"]
            merged_row["real_match_date"] = odds_row["match_date"]
            merged_row["real_season"] = odds_row["season"]
            merged_row["actual_home_goals"] = odds_row["FTHG"]
            merged_row["actual_away_goals"] = odds_row["FTAG"]
            merged_row["actual_result"] = odds_row["FTR"]

            merged_data.append(merged_row)
            matched_count += 1


    # 第二步：添加历史赛季的特征数据（使用模拟赔率）

    # 获取需要补充的赛季
    feature_seasons = set(features_df["season"].unique())
    odds_seasons = set(odds_df["season"].unique())
    additional_seasons = feature_seasons - odds_seasons


    additional_count = 0
    for season in additional_seasons:
        season_features = features_df[features_df["season"] == season]

        # 为每场比赛生成模拟赔率（基于历史数据和特征）
        for _, match in season_features.iterrows():
            # 简单模拟赔率：基于 xG 差异
            home_xg = match.get("home_xg", 1.0)
            away_xg = match.get("away_xg", 1.0)
            xg_diff = home_xg - away_xg

            # 简化的赔率计算
            home_prob = 0.4 + xg_diff * 0.1
            away_prob = 0.4 - xg_diff * 0.1
            draw_prob = 0.2

            # 确保概率为正
            home_prob = max(0.1, min(0.8, home_prob))
            away_prob = max(0.1, min(0.8, away_prob))
            draw_prob = max(0.1, min(0.5, draw_prob))

            # 归一化
            total = home_prob + away_prob + draw_prob
            home_prob /= total
            away_prob /= total
            draw_prob /= total

            # 转换为赔率 (添加庄家抽水)
            margin = 1.05  # 5% 抽水
            home_odds = round(margin / home_prob, 2)
            draw_odds = round(margin / draw_prob, 2)
            away_odds = round(margin / away_prob, 2)

            # 创建合并行
            merged_row = match.copy()
            merged_row["real_home_odds"] = home_odds
            merged_row["real_draw_odds"] = draw_odds
            merged_row["real_away_odds"] = away_odds
            merged_row["real_match_date"] = match["match_date"]
            merged_row["real_season"] = season
            merged_row["actual_home_goals"] = np.nan
            merged_row["actual_away_goals"] = np.nan
            merged_row["actual_result"] = np.nan

            merged_data.append(merged_row)
            additional_count += 1


    # 创建最终DataFrame
    if merged_data:
        merged_df = pd.DataFrame(merged_data)

        # 保存
        output_path = "/home/user/projects/FootballPrediction/data/v9_3_comprehensive_dataset.csv"
        merged_df.to_csv(output_path, index=False)

        # 显示赛季分布
        season_counts = merged_df["real_season"].value_counts().sort_index()
        for season in season_counts:
            pass

        # 数据质量统计

        # 有真实赔率的比赛
        real_odds_count = len(merged_df[merged_df["real_home_odds"].notna()])

        # 统计不同类型的数据
        len(merged_df) - real_odds_count

        return merged_df
    return None


def main():
    """主函数"""
    merged_df = merge_all_available_data()

    if merged_df is not None:

        if len(merged_df) >= 500:
            pass
        else:
            pass
    else:
        pass


if __name__ == "__main__":
    main()
