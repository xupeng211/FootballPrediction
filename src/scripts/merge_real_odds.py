#!/usr/bin/env python3
"""
V9.0 真实赔率合并器 - 简化版
基于球队名称合并预测数据和真实赔率
"""

from difflib import SequenceMatcher

import numpy as np
import pandas as pd


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


    # 加载数据
    odds_df = pd.read_csv("/home/user/projects/FootballPrediction/data/real_odds_raw.csv")
    pred_df = pd.read_csv("/home/user/projects/FootballPrediction/data/multi_season_v85.csv")


    # 创建合并后的数据列表
    merged_data = []

    for _idx, pred_row in pred_df.iterrows():
        pred_home = pred_row["home_team"]
        pred_away = pred_row["away_team"]

        # 在赔率数据中找到匹配的比赛
        matches = odds_df[(odds_df["home_team"] == pred_home) & (odds_df["away_team"] == pred_away)]

        if len(matches) > 0:
            # 取第一个匹配（如果有多个，取最新的）
            match = matches.iloc[-1]

            # 合并数据
            merged_row = pred_row.copy()
            merged_row["real_home_odds"] = match["b365_home_odds"]
            merged_row["real_draw_odds"] = match["b365_draw_odds"]
            merged_row["real_away_odds"] = match["b365_away_odds"]
            merged_row["real_match_date"] = match["match_date"]
            merged_row["actual_home_goals"] = match.get("FTHG", np.nan)
            merged_row["actual_away_goals"] = match.get("FTAG", np.nan)
            merged_row["actual_result"] = match.get("FTR", np.nan)

            merged_data.append(merged_row)

    # 创建DataFrame
    if merged_data:
        merged_df = pd.DataFrame(merged_data)

        # 保存
        output_path = "/home/user/projects/FootballPrediction/data/merged_real_odds.csv"
        merged_df.to_csv(output_path, index=False)

        # 显示赔率覆盖

        # 显示样本

        return merged_df
    return None


def main():
    merged_df = merge_odds_and_predictions()

    if merged_df is not None:
        pass
    else:
        pass


if __name__ == "__main__":
    main()
