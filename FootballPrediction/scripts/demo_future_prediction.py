#!/usr/bin/env python3
"""
未来比赛预测演示 / Future Match Prediction Demo

该脚本演示如何使用训练好的模型对未来的比赛进行预测。

This script demonstrates how to use the trained model to predict future matches.

使用方法 / Usage:
    python scripts/demo_future_prediction.py
"""

import sys
import pandas as pd
import xgboost as xgb
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def demo_future_prediction():
    """演示未来比赛预测功能."""

    try:
        # 加载模型
        model = xgb.XGBClassifier()
        model.load_model("models/football_model_v1.json")

        # 加载元数据
        with open("models/football_model_v1_metadata.json", encoding="utf-8") as f:
            metadata = json.load(f)

        feature_names = metadata["feature_names"]
        result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}

        # 创建一些模拟的未来比赛数据
        future_matches = [
            {
                "home_team_id": 3,  # Manchester United
                "away_team_id": 6,  # Liverpool
                "home_team_name": "Manchester United",
                "away_team_name": "Liverpool",
                "match_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "home_last_5_points": 9,
                "away_last_5_points": 15,
                "home_last_5_avg_goals": 1.6,
                "away_last_5_avg_goals": 2.2,
                "h2h_last_3_home_wins": 1,
            },
            {
                "home_team_id": 20,  # Man City
                "away_team_id": 7,  # Arsenal
                "home_team_name": "Manchester City",
                "away_team_name": "Arsenal",
                "match_date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
                "home_last_5_points": 12,
                "away_last_5_points": 7,
                "home_last_5_avg_goals": 2.8,
                "away_last_5_avg_goals": 1.5,
                "h2h_last_3_home_wins": 2,
            },
            {
                "home_team_id": 19,  # Chelsea
                "away_team_id": 5,  # Tottenham
                "home_team_name": "Chelsea",
                "away_team_name": "Tottenham",
                "match_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
                "home_last_5_points": 6,
                "away_last_5_points": 11,
                "home_last_5_avg_goals": 1.2,
                "away_last_5_avg_goals": 1.8,
                "h2h_last_3_home_wins": 0,
            },
            {
                "home_team_id": 15,  # West Ham
                "away_team_id": 4,  # Fulham
                "home_team_name": "West Ham",
                "away_team_name": "Fulham",
                "match_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "home_last_5_points": 8,
                "away_last_5_points": 4,
                "home_last_5_avg_goals": 1.4,
                "away_last_5_avg_goals": 0.8,
                "h2h_last_3_home_wins": 3,
            },
        ]

        # 进行预测
        for _i, match in enumerate(future_matches, 1):
            # 准备特征数据
            features = {key: match[key] for key in feature_names}
            X = pd.DataFrame([features])

            # 预测
            model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]

            # 格式化输出
            for _j, (_result_name, _prob) in enumerate(
                zip(result_names.values(), probabilities, strict=False)
            ):
                pass

        return True

    except Exception:
        return False


if __name__ == "__main__":
    success = demo_future_prediction()
    sys.exit(0 if success else 1)
