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
    print("=" * 60)
    print("🔮 未来比赛预测演示")
    print("=" * 60)

    try:
        # 加载模型
        print("📁 加载训练好的模型...")
        model = xgb.XGBClassifier()
        model.load_model('models/football_model_v1.json')

        # 加载元数据
        with open('models/football_model_v1_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        feature_names = metadata['feature_names']
        result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}

        print("✅ 模型加载成功")
        print(f"📋 特征列表: {feature_names}")
        print(f"🎯 预测类别: {list(result_names.values())}")
        print()

        # 创建一些模拟的未来比赛数据
        future_matches = [
            {
                'home_team_id': 3,   # Manchester United
                'away_team_id': 6,   # Liverpool
                'home_team_name': 'Manchester United',
                'away_team_name': 'Liverpool',
                'match_date': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'home_last_5_points': 9,
                'away_last_5_points': 15,
                'home_last_5_avg_goals': 1.6,
                'away_last_5_avg_goals': 2.2,
                'h2h_last_3_home_wins': 1
            },
            {
                'home_team_id': 20,  # Man City
                'away_team_id': 7,   # Arsenal
                'home_team_name': 'Manchester City',
                'away_team_name': 'Arsenal',
                'match_date': (datetime.now() + timedelta(days=4)).strftime('%Y-%m-%d'),
                'home_last_5_points': 12,
                'away_last_5_points': 7,
                'home_last_5_avg_goals': 2.8,
                'away_last_5_avg_goals': 1.5,
                'h2h_last_3_home_wins': 2
            },
            {
                'home_team_id': 19,  # Chelsea
                'away_team_id': 5,   # Tottenham
                'home_team_name': 'Chelsea',
                'away_team_name': 'Tottenham',
                'match_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                'home_last_5_points': 6,
                'away_last_5_points': 11,
                'home_last_5_avg_goals': 1.2,
                'away_last_5_avg_goals': 1.8,
                'h2h_last_3_home_wins': 0
            },
            {
                'home_team_id': 15,  # West Ham
                'away_team_id': 4,   # Fulham
                'home_team_name': 'West Ham',
                'away_team_name': 'Fulham',
                'match_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                'home_last_5_points': 8,
                'away_last_5_points': 4,
                'home_last_5_avg_goals': 1.4,
                'away_last_5_avg_goals': 0.8,
                'h2h_last_3_home_wins': 3
            }
        ]

        print("📅 未来比赛预测结果:")
        print("=" * 60)

        # 进行预测
        for i, match in enumerate(future_matches, 1):
            # 准备特征数据
            features = {key: match[key] for key in feature_names}
            X = pd.DataFrame([features])

            # 预测
            prediction = model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]

            # 格式化输出
            print(f"比赛 {i}: [{match['match_date']}] {match['home_team_name']} (主) vs {match['away_team_name']} (客)")
            print(f"📊 球队状态:")
            print(f"   主队近期表现: {match['home_last_5_points']}分, 平均进球 {match['home_last_5_avg_goals']:.1f}")
            print(f"   客队近期表现: {match['away_last_5_points']}分, 平均进球 {match['away_last_5_avg_goals']:.1f}")
            print(f"   历史交锋: 主队近期{match['h2h_last_3_home_wins']}次获胜")
            print(f"🔮 预测结果: {result_names[prediction]}")
            print(f"📈 预测概率:")
            for j, (result_name, prob) in enumerate(zip(result_names.values(), probabilities)):
                status = "✅" if j == prediction else "  "
                print(f"   {status} {result_name:6s}: {prob:.1%}")
            print("-" * 50)

        print("\n💡 预测说明:")
        print("• 模型基于球队近期战绩、进球能力和历史交锋进行预测")
        print("• 概率越高表示模型对该结果的信心越强")
        print("• 建议结合其他信息（如伤病、天气、主客场优势等）综合判断")

        return True

    except Exception as e:
        print(f"❌ 预测演示失败: {e}")
        return False


if __name__ == "__main__":
    success = demo_future_prediction()
    sys.exit(0 if success else 1)