#!/usr/bin/env python3
"""
豪门球队ROI分析脚本
专门分析豪门球队的投注表现
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import accuracy_score

# 加载训练数据
df = pd.read_csv("/home/user/projects/FootballPrediction/training_set.csv")

# 定义豪门球队
BIG_TEAMS = {
    "Arsenal",
    "Chelsea",
    "Liverpool",
    "Manchester City",
    "Manchester Utd",
    "Tottenham",
    "Barcelona",
    "Real Madrid",
    "Atletico Madrid",
    "Bayern Munich",
    "Borussia Dortmund",
    "AC Milan",
    "Inter",
    "Juventus",
}

print("🏆 豪门球队ROI详细分析")
print("=" * 80)

# 1. 基础统计
print("\n📊 基础统计:")
print(f"  总比赛数: {len(df)}")
big_team_games = df[
    (df["home_team"].isin(BIG_TEAMS)) | (df["away_team"].isin(BIG_TEAMS))
]
print(f"  豪门球队比赛数: {len(big_team_games)} ({len(big_team_games)/len(df):.2%})")

# 2. 各豪门球队比赛数
print("\n👑 各豪门球队比赛数:")
for team in sorted(BIG_TEAMS):
    count = len(df[(df["home_team"] == team) | (df["away_team"] == team)])
    if count > 0:
        print(f"  {team:20s}: {count:2d} 场比赛")

# 3. 训练模型
feature_cols = [
    col
    for col in df.columns
    if col
    not in [
        "result",
        "match_id",
        "date",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
    ]
]
X = df[feature_cols].fillna(0)
y = df["result"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 获取测试集的原始数据索引
test_indices = X_test.index

model = xgb.XGBClassifier(
    objective="multi:softprob",
    num_class=3,
    max_depth=6,
    learning_rate=0.1,
    n_estimators=100,
    random_state=42,
)
model.fit(X_train, y_train)

y_pred_proba = model.predict_proba(X_test)

# 4. ROI分析 - 宽松策略
print("\n💰 ROI分析 (宽松策略 - 期望回报>5%):")
results_loose = []
total_bet = 0
total_winnings = 0
big_teams_bets = 0
big_teams_winnings = 0

for i, idx in enumerate(test_indices):
    match_data = df.loc[idx]
    home_team = match_data["home_team"]
    away_team = match_data["away_team"]

    prob_home_win = y_pred_proba[i][2]
    prob_draw = y_pred_proba[i][1]

    home_odds = match_data["home_odds"]
    draw_odds = match_data["draw_odds"]
    implied_home = 1 / home_odds

    bet_placed = False
    bet_on = None

    # 宽松策略
    if prob_home_win > implied_home and (prob_home_win * home_odds - 1) > 0.05:
        bet_placed = True
        bet_on = "home"
    elif prob_draw > (1 / draw_odds) and (prob_draw * draw_odds - 1) > 0.05:
        bet_placed = True
        bet_on = "draw"

    if bet_placed:
        total_bet += 1
        is_big_team = home_team in BIG_TEAMS or away_team in BIG_TEAMS

        actual_result = match_data["result"]
        won = False
        payout = 0

        if bet_on == "home" and actual_result == 2:
            won = True
            payout = 1 * home_odds
        elif bet_on == "draw" and actual_result == 1:
            won = True
            payout = 1 * draw_odds

        net_winnings = payout - 1
        total_winnings += net_winnings

        if is_big_team:
            big_teams_bets += 1
            big_teams_winnings += net_winnings

        results_loose.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "bet_on": bet_on,
                "won": won,
                "net_winnings": net_winnings,
                "is_big_team": is_big_team,
            }
        )

roi = (total_winnings / total_bet * 100) if total_bet > 0 else 0
big_teams_roi = (big_teams_winnings / big_teams_bets * 100) if big_teams_bets > 0 else 0

print(f"  宽松策略结果:")
print(f"    总投注: {total_bet} 次")
print(f"    总盈亏: {total_winnings:.2f}")
print(f"    整体ROI: {roi:.2f}%")
print(f"    豪门投注: {big_teams_bets} 次")
print(f"    豪门盈亏: {big_teams_winnings:.2f}")
print(f"    豪门ROI: {big_teams_roi:.2f}%")

# 5. ROI分析 - 激进策略
print("\n🚀 ROI分析 (激进策略 - 期望回报>0%):")
results_aggressive = []
total_bet = 0
total_winnings = 0
big_teams_bets = 0
big_teams_winnings = 0

for i, idx in enumerate(test_indices):
    match_data = df.loc[idx]
    home_team = match_data["home_team"]
    away_team = match_data["away_team"]

    prob_home_win = y_pred_proba[i][2]
    prob_draw = y_pred_proba[i][1]

    home_odds = match_data["home_odds"]
    draw_odds = match_data["draw_odds"]
    implied_home = 1 / home_odds

    bet_placed = False
    bet_on = None

    # 激进策略：只要有正期望值就投注
    if prob_home_win > implied_home and (prob_home_win * home_odds - 1) > 0:
        bet_placed = True
        bet_on = "home"
    elif prob_draw > (1 / draw_odds) and (prob_draw * draw_odds - 1) > 0:
        bet_placed = True
        bet_on = "draw"

    if bet_placed:
        total_bet += 1
        is_big_team = home_team in BIG_TEAMS or away_team in BIG_TEAMS

        actual_result = match_data["result"]
        won = False
        payout = 0

        if bet_on == "home" and actual_result == 2:
            won = True
            payout = 1 * home_odds
        elif bet_on == "draw" and actual_result == 1:
            won = True
            payout = 1 * draw_odds

        net_winnings = payout - 1
        total_winnings += net_winnings

        if is_big_team:
            big_teams_bets += 1
            big_teams_winnings += net_winnings

        results_aggressive.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "bet_on": bet_on,
                "won": won,
                "net_winnings": net_winnings,
                "is_big_team": is_big_team,
            }
        )

roi = (total_winnings / total_bet * 100) if total_bet > 0 else 0
big_teams_roi = (big_teams_winnings / big_teams_bets * 100) if big_teams_bets > 0 else 0

print(f"  激进策略结果:")
print(f"    总投注: {total_bet} 次")
print(f"    总盈亏: {total_winnings:.2f}")
print(f"    整体ROI: {roi:.2f}%")
print(f"    豪门投注: {big_teams_bets} 次")
print(f"    豪门盈亏: {big_teams_winnings:.2f}")
print(f"    豪门ROI: {big_teams_roi:.2f}%")

# 6. 豪门球队详细分析
print("\n🔍 豪门球队详细表现:")
big_team_results = {}
for result in results_aggressive:
    if result["is_big_team"]:
        # 记录豪门球队的比赛
        home_team = result["home_team"]
        away_team = result["away_team"]
        team_key = f"{home_team} vs {away_team}"

        if team_key not in big_team_results:
            big_team_results[team_key] = []
        big_team_results[team_key].append(result)

if big_team_results:
    print(f"  豪门球队投注详情:")
    for team_key, bets in big_team_results.items():
        wins = sum(1 for bet in bets if bet["won"])
        total_bet = len(bets)
        net = sum(bet["net_winnings"] for bet in bets)
        print(f"    {team_key:30s}: {wins}/{total_bet} 胜, 盈亏: {net:6.2f}")
else:
    print("  ⚠️  激进策略下也没有豪门球队投注")
    print("     这说明豪门球队的比赛预测难度较大，模型难以找到价值投注机会")

# 7. 结论
print("\n" + "=" * 80)
print("🎯 结论:")
if big_teams_bets > 0 and big_teams_roi > 0:
    print(f"  ✅ 投豪门可以赚钱！ROI: {big_teams_roi:.2f}%")
elif big_teams_bets > 0:
    print(f"  ❌ 投豪门亏钱，亏损 {abs(big_teams_roi):.2f}%")
else:
    print(f"  ⚠️  豪门球队比赛预测难度大，模型难以找到价值投注")
    print(f"     建议:")
    print(f"     1. 降低投注阈值 (当前使用期望回报>5%)")
    print(f"     2. 专门训练豪门球队预测模型")
    print(f"     3. 结合其他信息源 (新闻、伤病等)")

print("=" * 80)
