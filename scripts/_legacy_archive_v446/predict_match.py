#!/usr/bin/env python3
"""
V193.4 西甲实战预测脚本
预测本周末的西甲焦点战
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.ml.inference.model_dispatcher import ModelDispatcher

def run_prediction():
    """
    执行预测
    """
    # 初始化预测器
    dispatcher = ModelDispatcher()

    # 比赛1: Celta Vigo vs Real Madrid
    matches_data_1 = {
        'match_id': '87_20242025_4837372',
        'home_team': 'Celta Vigo',
        'away_team': 'Real Madrid',
        'league_name': 'La Liga',
        'league_id': 87,
        'market_value_gap': -464825650,
        'injury_count_gap': -7,
        'rating_gap': 0,
        'home_possession': 50,
        'away_possession': 50,
        'xg_diff': 0,
        'shots_diff': 1
    }

    result1 = dispatcher.predict(matches_data_1)

    # 比赛2: Athletic Club vs Barcelona
    matches_data_2 = {
        'match_id': '87_20242025_4837370',
        'home_team': 'Athletic Club',
        'away_team': 'Barcelona',
        'league_name': 'La Liga',
        'league_id': 87,
        'market_value_gap': -464000000,
        'injury_count_gap': -2,
        'rating_gap': 0,
        'home_possession': 50,
        'away_possession': 50,
        'xg_diff': 0,
        'shots_diff': 1
    }

    result2 = dispatcher.predict(matches_data_2)

    # 打印预测结果
    print("\n" + "=" * 80)
    print("   V193.4 西甲焦点战预测报告")
    print("=" * 80)
    print("\n   比赛1: Celta Vigo vs Real Madrid")
    print("   日期: 3/6 20:00 | Celta Vigo | Real Madrid")
    print("-" * 40)
    print(f"   预测: {result1['prediction']}")
    print(f"   置信度: {result1['confidence'] * 100:.1f}%")
    print(f"   概率分布: 主胜 {result1['probabilities']['Home']:.1%} | 平 {result1['probabilities']['Draw']:.1%} | 客胜 {result1['probabilities']['Away']:.1f}%")
    print(f"   模型来源: {result1['model_source']}")

    print("\n   比赛2: Athletic Club vs Barcelona")
    print("   日期: 3/7 20:00 | Athletic Club | Barcelona")
    print("-" * 40)
    print(f"   预测: {result2['prediction']}")
    print(f"   置信度: {result2['confidence'] * 100:.1f}%")
    print(f"   概率分布: 主胜 {result2['probabilities']['Home']:.1%} | 平 {result2['probabilities']['Draw']:.1%} | 客胜 {result2['probabilities']['Away']:.1f}%")
    print(f"   模型来源: {result2['model_source']}")
    print("\n" + "=" * 80)
    print("   投注建议:")
    print("   1. 皇马客战塞尔塔 - 信心足，可考虑客让球")
    print("   2. 巴萨客战毕尔塔 - 客队优势明显，建议关注客胜")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_prediction()
