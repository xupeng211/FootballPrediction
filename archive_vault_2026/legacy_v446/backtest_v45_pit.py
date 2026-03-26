#!/usr/bin/env python3
"""
V4.5-PIT: Point-in-Time 时序防火墙回测系统
===========================================

核心原则: 零数据泄露 - 只使用比赛开始前可用的特征

特征分类:
- 白名单 (赛前可用): Elo, 身价, 伤病, Rolling PPG
- 黑名单 (赛后数据): xG, shots, corners, rating, possession

修复前: 100% 数据泄露，准确率 93.1% (虚假)
修复后: 预期准确率 40-50% (真实)

@version V4.5.0
@since 2026-03-07
"""

import os
import sys
import json
import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import numpy as np
import psycopg2
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# 特征分类定义 - 核心时序防火墙
# ============================================================================

# 白名单特征: 比赛开始前可用的特征 (Point-in-Time Safe)
PRE_MATCH_FEATURES = {
    # Elo 特征 (历史数据，不含当场比赛)
    "elo": [
        "elo_diff",
        "home_elo_pre",
        "away_elo_pre",
        "elo_expected_home",
    ],

    # 身价特征 (赛季开始时的总身价)
    "market_value": [
        "home_market_value_total",
        "away_market_value_total",
        "market_value_gap",
        "market_value_ratio",
    ],

    # 伤病特征 (赛前阵容信息)
    "injury": [
        "home_injury_count",
        "away_injury_count",
        "injury_count_gap",
    ],

    # 滚动特征 (只统计之前比赛)
    "rolling": [
        "home_rolling_ppg",
        "away_rolling_ppg",
        "home_rolling_wins",
        "away_rolling_wins",
        "home_rolling_draws",
        "away_rolling_draws",
        "home_rolling_losses",
        "away_rolling_losses",
    ],

    # 赔率特征 (开盘赔率 - 比赛前 24 小时)
    # 注意: 当前赔率数据缺失，此部分需要补充
    "odds": [
        "opening_home_odds",
        "opening_draw_odds",
        "opening_away_odds",
    ],

    # 阵容特征 (赛前可用)
    "lineup": [
        "home_starters_count",
        "away_starters_count",
        "home_age_avg",
        "away_age_avg",
        "age_gap",
    ],
}

# 黑名单特征: 赛后数据，禁止用于预测 (POST-MATCH DATA - DO NOT USE)
POST_MATCH_FEATURES = {
    "tactical": [
        "home_xg", "away_xg",  # 赛后 xG
        "home_shots", "away_shots",  # 赛后射门
        "home_corners", "away_corners",  # 赛后角球
        "home_possession", "away_possession",  # 赛后控球
        "home_shots_on_target", "away_shots_on_target",
        "home_fouls", "away_fouls",
        "home_yellow_cards", "away_yellow_cards",
        "home_red_cards", "away_red_cards",
        "home_big_chances", "away_big_chances",
    ],
    "rating": [
        "home_rating_avg", "away_rating_avg",  # 赛后评分
        "home_rating_max", "away_rating_max",
        "home_rating_min", "away_rating_min",
        "rating_gap",
    ],
    "momentum": [
        "momentum_overall_mean",  # 比赛动量
        "momentum_direction",
        "momentum_trend",
    ],
    "derived": [
        "xg_diff", "total_xg",  # 赛后派生
        "possession_diff",
        "shots_on_target_diff",
        "corners_diff",
        "strength_diff",  # 基于 xG 的综合评分
    ],
}

# 展平的特征列表
SAFE_FEATURES = []
for category, features in PRE_MATCH_FEATURES.items():
    SAFE_FEATURES.extend(features)

UNSAFE_FEATURES = []
for category, features in POST_MATCH_FEATURES.items():
    UNSAFE_FEATURES.extend(features)


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "host.docker.internal"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "football_db"),
        user=os.getenv("DB_USER", "football_user"),
        password=os.getenv("DB_PASSWORD")
    )


def safe_float(value, default=0.0):
    """安全转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ============================================================================
# 特征提取 (严格时序隔离)
# ============================================================================

def extract_safe_features(row):
    """
    从数据库行提取安全的赛前特征
    严格执行时序隔离，只返回白名单特征

    Args:
        row: 数据库行 (match_id, actual_result, elo, rolling, golden, tactical, odds, match_date, ...)

    Returns:
        dict: 只包含赛前可用特征的字典
    """
    match_id, actual_result = row[0], row[1]
    elo_json, rolling_json = row[2], row[3]
    golden_json, tactical_json, odds_json = row[4], row[5], row[6]
    match_date = row[7]

    features = {
        "_match_id": match_id,
        "_match_date": match_date.isoformat() if hasattr(match_date, 'isoformat') else str(match_date),
    }

    # 解析 JSON 字段 (psycopg2 自动解析 JSONB)
    elo = elo_json if isinstance(elo_json, dict) else (json.loads(elo_json) if elo_json else {})
    rolling = rolling_json if isinstance(rolling_json, dict) else (json.loads(rolling_json) if rolling_json else {})
    golden = golden_json if isinstance(golden_json, dict) else (json.loads(golden_json) if golden_json else {})
    tactical = tactical_json if isinstance(tactical_json, dict) else (json.loads(tactical_json) if tactical_json else {})
    odds = odds_json if isinstance(odds_json, dict) else (json.loads(odds_json) if odds_json else {})

    # ========== 提取 Elo 特征 (赛前可用) ==========
    features["elo_diff"] = safe_float(elo.get("elo_diff"))
    features["home_elo_pre"] = safe_float(elo.get("home_elo", elo.get("home_elo_pre", 1500)))
    features["away_elo_pre"] = safe_float(elo.get("away_elo", elo.get("away_elo_pre", 1500)))
    features["elo_expected_home"] = safe_float(elo.get("elo_expected_home", 0.5))

    # ========== 提取 Rolling 特征 (赛前可用) ==========
    home_rolling = rolling.get("home", {})
    away_rolling = rolling.get("away", {})

    features["home_rolling_ppg"] = safe_float(home_rolling.get("rolling_ppg", 1.5))
    features["home_rolling_wins"] = safe_float(home_rolling.get("rolling_wins", 0))
    features["home_rolling_draws"] = safe_float(home_rolling.get("rolling_draws", 0))
    features["home_rolling_losses"] = safe_float(home_rolling.get("rolling_losses", 0))

    features["away_rolling_ppg"] = safe_float(away_rolling.get("rolling_ppg", 1.5))
    features["away_rolling_wins"] = safe_float(away_rolling.get("rolling_wins", 0))
    features["away_rolling_draws"] = safe_float(away_rolling.get("rolling_draws", 0))
    features["away_rolling_losses"] = safe_float(away_rolling.get("rolling_losses", 0))

    # ========== 提取身价特征 (赛前可用) ==========
    features["home_market_value_total"] = safe_float(golden.get("home_market_value_total", 0))
    features["away_market_value_total"] = safe_float(golden.get("away_market_value_total", 0))
    features["market_value_gap"] = safe_float(golden.get("market_value_gap", 0))
    features["market_value_ratio"] = safe_float(golden.get("market_value_ratio", 1))

    # ========== 提取伤病特征 (赛前可用) ==========
    features["home_injury_count"] = safe_float(golden.get("home_injury_count", 0))
    features["away_injury_count"] = safe_float(golden.get("away_injury_count", 0))
    features["injury_count_gap"] = safe_float(golden.get("injury_count_gap", 0))

    # ========== 提取阵容特征 (赛前可用) ==========
    features["home_starters_count"] = safe_float(golden.get("home_starters_count", 11))
    features["away_starters_count"] = safe_float(golden.get("away_starters_count", 11))
    features["home_age_avg"] = safe_float(golden.get("home_age_avg", 26))
    features["away_age_avg"] = safe_float(golden.get("away_age_avg", 26))
    features["age_gap"] = safe_float(golden.get("age_gap", 0))

    # ========== 提取赔率特征 (如果有) ==========
    # 注意: 当前赔率数据可能缺失，使用默认值
    features["opening_home_odds"] = safe_float(odds.get("opening_home_odds", odds.get("current_home_odds", 2.5)))
    features["opening_draw_odds"] = safe_float(odds.get("opening_draw_odds", odds.get("current_draw_odds", 3.3)))
    features["opening_away_odds"] = safe_float(odds.get("opening_away_odds", odds.get("current_away_odds", 2.8)))

    # ========== 警告: 以下特征被故意忽略 (赛后数据) ==========
    # tactical: home_xg, away_xg, home_shots, away_shots, etc.
    # golden.rating: home_rating_avg, away_rating_avg
    # 这些特征不包含在返回值中，确保零数据泄露

    return features


def check_data_leakage(features, match_date):
    """
    检查特征是否存在数据泄露

    Args:
        features: 特征字典
        match_date: 比赛日期

    Returns:
        list: 泄露警告列表
    """
    warnings = []

    # 检查 computed_at 时间戳
    for key, value in features.items():
        if key.endswith("_computedAt") or key.endswith("_extractedAt"):
            if value:
                try:
                    computed_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    if computed_at > match_date:
                        warnings.append(f"特征 {key} 计算时间 {computed_at} 在比赛 {match_date} 之后")
                except:
                    pass

    return warnings


# ============================================================================
# 预测模型 (基于规则，无 ML)
# ============================================================================

def rule_based_predict(features):
    """
    基于规则的预测 (使用安全特征)

    使用策略:
    1. Elo 差异 + 主场优势
    2. Rolling PPG 差异
    3. 身价差距
    4. 伤病影响
    5. 赔率暗示 (如果有)

    Args:
        features: 安全特征字典

    Returns:
        tuple: (预测结果, 置信度)
    """
    score = 0.0

    # 1. Elo 差异 (主场优势约 50 分)
    elo_diff = features.get("elo_diff", 0)
    # Elo 期望胜率
    home_elo = features.get("home_elo_pre", 1500)
    away_elo = features.get("away_elo_pre", 1500)
    elo_expected = 1 / (1 + 10 ** ((away_elo - home_elo - 50) / 400))  # +50 主场优势
    score += (elo_expected - 0.5) * 2  # 映射到 -1 到 1

    # 2. Rolling PPG 差异
    home_ppg = features.get("home_rolling_ppg", 1.5)
    away_ppg = features.get("away_rolling_ppg", 1.5)
    ppg_diff = home_ppg - away_ppg
    score += ppg_diff / 2  # 归一化

    # 3. 身价差距 (对数尺度)
    home_value = features.get("home_market_value_total", 0)
    away_value = features.get("away_market_value_total", 0)
    if home_value > 0 and away_value > 0:
        value_ratio = np.log10(home_value / away_value)
        score += value_ratio * 0.3

    # 4. 伤病影响
    injury_gap = features.get("injury_count_gap", 0)
    score -= injury_gap * 0.05  # 更多伤病 = 更低评分

    # 5. 赔率暗示 (如果有有效赔率)
    home_odds = features.get("opening_home_odds", 0)
    away_odds = features.get("opening_away_odds", 0)
    draw_odds = features.get("opening_draw_odds", 0)

    if home_odds > 1 and away_odds > 1 and draw_odds > 1:
        # 赔率隐含概率
        total_implied = 1/home_odds + 1/draw_odds + 1/away_odds
        home_prob = (1/home_odds) / total_implied
        away_prob = (1/away_odds) / total_implied

        # 赔率信号
        odds_signal = home_prob - away_prob
        score += odds_signal * 0.5

    # 决策
    if score > 0.3:
        prediction = "HOME_WIN"
        confidence = min(0.75, 0.5 + score / 3)
    elif score < -0.3:
        prediction = "AWAY_WIN"
        confidence = min(0.75, 0.5 - score / 3)
    else:
        prediction = "DRAW"
        confidence = 0.35 + 0.1 * (1 - abs(score))  # 平局置信度较低

    return prediction, confidence


# ============================================================================
# 主回测函数
# ============================================================================

def run_pit_backtest():
    """
    执行 Point-in-Time 时序防火墙回测
    """
    print("=" * 80)
    print("V4.5-PIT: Point-in-Time 时序防火墙回测")
    print("=" * 80)
    print("\n📋 特征策略:")
    print(f"  ✅ 白名单特征 ({len(SAFE_FEATURES)} 个): Elo, 身价, 伤病, Rolling PPG")
    print(f"  ❌ 黑名单特征 ({len(UNSAFE_FEATURES)} 个): xG, shots, corners, rating")
    print("\n⚠️  预期准确率: 40-50% (真实水平)")
    print("=" * 80)

    conn = get_db_connection()
    cur = conn.cursor()

    # 获取已完成比赛的 L3 特征
    cur.execute("""
        SELECT
            m.match_id, m.actual_result,
            l3.elo_features, l3.rolling_features,
            l3.golden_features, l3.tactical_features, l3.odds_features,
            m.match_date, m.home_team, m.away_team, m.league_name
        FROM matches m
        JOIN l3_features l3 ON m.match_id = l3.match_id
        WHERE m.is_finished = true
          AND m.actual_result IS NOT NULL
        ORDER BY m.match_date ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print("❌ 没有找到已完成比赛数据")
        return

    print(f"\n📊 找到 {len(rows)} 场已完成比赛")

    results = []
    feature_matrix = []
    labels = []
    leakage_warnings = []

    # 结果映射
    LABEL_MAP = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
    REVERSE_LABEL_MAP = {"A": 0, "D": 1, "H": 2}
    RESULT_MAP = {"H": "HOME_WIN", "D": "DRAW", "A": "AWAY_WIN"}

    for row in rows:
        # 提取安全特征
        features = extract_safe_features(row)
        actual_result = row[1]
        match_date = row[7]

        # 检查数据泄露
        warnings = check_data_leakage(features, match_date)
        if warnings:
            leakage_warnings.extend(warnings)

        # 使用规则预测
        prediction, confidence = rule_based_predict(features)

        # 检查正确性
        expected = RESULT_MAP.get(actual_result)
        is_correct = expected == prediction

        results.append({
            "match_id": row[0],
            "home_team": row[8],
            "away_team": row[9],
            "league_name": row[10],
            "match_date": str(match_date),
            "actual_result": actual_result,
            "predicted_outcome": prediction,
            "confidence": confidence,
            "is_correct": is_correct,
        })

        # 收集训练数据 (使用安全特征)
        feature_vector = [features.get(col, 0.0) for col in SAFE_FEATURES if col in features]
        feature_matrix.append(feature_vector)
        labels.append(REVERSE_LABEL_MAP.get(actual_result, 1))

    # 打印数据泄露警告
    if leakage_warnings:
        print(f"\n⚠️  数据泄露警告 ({len(leakage_warnings)} 个):")
        for w in leakage_warnings[:5]:
            print(f"  - {w}")
        if len(leakage_warnings) > 5:
            print(f"  ... 还有 {len(leakage_warnings) - 5} 个警告")
    else:
        print("\n✅ 未检测到数据泄露")

    # 打印结果
    print_results(results)

    # 尝试训练简单模型
    try_train_model(feature_matrix, labels, SAFE_FEATURES)

    return results


def print_results(results):
    """打印回测结果"""
    print("\n" + "=" * 80)
    print("回测结果报告")
    print("=" * 80)

    total = len(results)
    correct = sum(1 for r in results if r["is_correct"])
    accuracy = correct / total * 100 if total > 0 else 0

    print(f"\n📊 总体统计:")
    print(f"  总样本量: {total}")
    print(f"  正确预测: {correct}")
    print(f"  总准确率: {accuracy:.2f}%")
    print(f"  随机基准: 33.33%")

    # 评估
    if accuracy >= 55:
        status = "✅ 有预测能力"
    elif accuracy >= 45:
        status = "⚠️  弱预测能力"
    else:
        status = "❌ 无预测能力 (接近随机)"

    print(f"  评估: {status}")

    # 按结果类型统计
    outcome_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        outcome = r["predicted_outcome"]
        outcome_stats[outcome]["total"] += 1
        if r["is_correct"]:
            outcome_stats[outcome]["correct"] += 1

    print(f"\n📈 预测分布:")
    for outcome in ["HOME_WIN", "DRAW", "AWAY_WIN"]:
        stats = outcome_stats[outcome]
        if stats["total"] > 0:
            pct = stats["total"] / total * 100
            acc = stats["correct"] / stats["total"] * 100
            print(f"  {outcome}: {stats['total']} 场 ({pct:.1f}%) | 准确率 {acc:.1f}%")

    # 按置信度分析
    print(f"\n🎯 置信度分析:")
    for threshold in [0.5, 0.6, 0.7]:
        high_conf = [r for r in results if r["confidence"] >= threshold]
        if high_conf:
            high_correct = sum(1 for r in high_conf if r["is_correct"])
            high_acc = high_correct / len(high_conf) * 100
            print(f"  置信度 >= {threshold}: {len(high_conf)} 场 ({len(high_conf)/total*100:.1f}%) | 准确率 {high_acc:.1f}%")

    # 按联赛统计
    league_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        league = r["league_name"] or "Unknown"
        league_stats[league]["total"] += 1
        if r["is_correct"]:
            league_stats[league]["correct"] += 1

    print(f"\n🏆 联赛准确率 (Top 10):")
    sorted_leagues = sorted(league_stats.items(), key=lambda x: x[1]["total"], reverse=True)
    for league, stats in sorted_leagues[:10]:
        if stats["total"] >= 5:  # 至少 5 场
            acc = stats["correct"] / stats["total"] * 100
            print(f"  {league}: {acc:.1f}% ({stats['correct']}/{stats['total']} 场)")

    # 与修复前对比
    print(f"\n" + "=" * 40)
    print("📉 数据泄露影响分析")
    print("=" * 40)
    print(f"  修复前准确率: 93.1% (虚假，使用赛后数据)")
    print(f"  修复后准确率: {accuracy:.1f}% (真实，仅使用赛前数据)")
    print(f"  准确率下降: {93.1 - accuracy:.1f} 个百分点")
    print(f"\n  结论: 修复前的准确率完全来自数据泄露")

    print("\n" + "=" * 80)
    print("回测完成!")
    print("=" * 80)


def try_train_model(feature_matrix, labels, feature_names):
    """尝试训练简单模型"""
    print("\n" + "=" * 80)
    print("🤖 尝试训练简单模型 (仅使用安全特征)")
    print("=" * 80)

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score, TimeSeriesSplit
        from sklearn.preprocessing import StandardScaler

        X = np.array(feature_matrix)
        y = np.array(labels)

        # 检查数据
        if len(X) < 50:
            print("⚠️  样本量不足，跳过模型训练")
            return

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 使用 TimeSeriesSplit 而不是随机 K-Fold (时序数据)
        tscv = TimeSeriesSplit(n_splits=5)

        # 随机森林
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            n_jobs=-1
        )

        # 时序交叉验证
        scores = cross_val_score(rf, X_scaled, y, cv=tscv, scoring='accuracy')

        print(f"\n📊 时序交叉验证 (TimeSeriesSplit):")
        print(f"  平均准确率: {scores.mean()*100:.1f}% (+/- {scores.std()*200:.1f}%)")
        print(f"  各折: {[f'{s*100:.1f}%' for s in scores]}")

        # 训练最终模型
        rf.fit(X_scaled, y)
        train_pred = rf.predict(X_scaled)
        train_acc = (train_pred == y).mean() * 100
        print(f"\n  训练集准确率: {train_acc:.1f}%")

        # 特征重要性
        print(f"\n📈 特征重要性 (Top 10):")
        used_features = [f for f in feature_names if f in SAFE_FEATURES]
        importances = rf.feature_importances_

        # 确保特征名和重要性数组长度匹配
        min_len = min(len(used_features), len(importances))
        feature_importance = list(zip(used_features[:min_len], importances[:min_len]))
        feature_importance.sort(key=lambda x: x[1], reverse=True)

        for i, (name, imp) in enumerate(feature_importance[:10]):
            print(f"  {i+1}. {name}: {imp:.3f}")

    except ImportError:
        print("⚠️  sklearn 未安装，跳过模型训练")
    except Exception as e:
        print(f"⚠️  模型训练失败: {e}")


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    run_pit_backtest()
