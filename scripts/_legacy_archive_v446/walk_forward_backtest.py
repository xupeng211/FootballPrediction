#!/usr/bin/env python3
"""
V4.5-WALK-FORWARD: 步进式时序验证引擎
====================================

真正的时序回测方法:
1. 按 match_date 排序所有比赛
2. 使用前 N 天数据训练，预测后 M 天
3. 滑动窗口重复，模拟真实预测场景
4. 每个窗口独立评估，避免数据泄露

与随机分割的区别:
- 随机分割 (train_test_split): 会用未来数据训练，导致数据泄露
- Walk-forward: 严格时序隔离，只使用过去数据预测未来

@version V4.5.0
@since 2026-03-07
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
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
# 配置
# ============================================================================

# 默认窗口配置
DEFAULT_TRAIN_WINDOW_DAYS = 90   # 训练窗口: 90 天
DEFAULT_TEST_WINDOW_DAYS = 30    # 测试窗口: 30 天
MIN_TRAIN_SAMPLES = 50           # 最小训练样本数

# 安全特征 (与 backtest_v45_pit.py 保持一致)
SAFE_FEATURES = [
    # Elo
    "elo_diff", "home_elo_pre", "away_elo_pre",
    # Rolling
    "home_rolling_ppg", "away_rolling_ppg",
    "home_rolling_wins", "away_rolling_wins",
    "home_rolling_draws", "away_rolling_draws",
    "home_rolling_losses", "away_rolling_losses",
    # Market Value
    "home_market_value_total", "away_market_value_total",
    "market_value_gap", "market_value_ratio",
    # Injury
    "home_injury_count", "away_injury_count", "injury_count_gap",
    # Lineup
    "home_starters_count", "away_starters_count",
    "home_age_avg", "away_age_avg", "age_gap",
    # Odds
    "opening_home_odds", "opening_draw_odds", "opening_away_odds",
]


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
# 数据加载
# ============================================================================

def load_matches_with_features():
    """
    加载所有已完成比赛及其 L3 特征

    Returns:
        pd.DataFrame: 包含所有比赛和特征的 DataFrame
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            m.match_id,
            m.match_date,
            m.home_team,
            m.away_team,
            m.league_name,
            m.actual_result,
            m.home_score,
            m.away_score,
            l3.elo_features,
            l3.rolling_features,
            l3.golden_features,
            l3.tactical_features,
            l3.odds_features
        FROM matches m
        JOIN l3_features l3 ON m.match_id = l3.match_id
        WHERE m.is_finished = true
          AND m.actual_result IS NOT NULL
          AND m.match_date IS NOT NULL
        ORDER BY m.match_date ASC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return pd.DataFrame()

    # 构建 DataFrame
    data = []
    for row in rows:
        (match_id, match_date, home_team, away_team, league_name,
         actual_result, home_score, away_score,
         elo_json, rolling_json, golden_json, tactical_json, odds_json) = row

        # 解析 JSON
        elo = elo_json if isinstance(elo_json, dict) else (json.loads(elo_json) if elo_json else {})
        rolling = rolling_json if isinstance(rolling_json, dict) else (json.loads(rolling_json) if rolling_json else {})
        golden = golden_json if isinstance(golden_json, dict) else (json.loads(golden_json) if golden_json else {})
        odds = odds_json if isinstance(odds_json, dict) else (json.loads(odds_json) if odds_json else {})

        # 提取安全特征
        features = {
            "match_id": match_id,
            "match_date": match_date,
            "home_team": home_team,
            "away_team": away_team,
            "league_name": league_name,
            "actual_result": actual_result,
            "home_score": home_score,
            "away_score": away_score,

            # Elo
            "elo_diff": safe_float(elo.get("elo_diff")),
            "home_elo_pre": safe_float(elo.get("home_elo", elo.get("home_elo_pre", 1500))),
            "away_elo_pre": safe_float(elo.get("away_elo", elo.get("away_elo_pre", 1500))),

            # Rolling
            "home_rolling_ppg": safe_float(rolling.get("home", {}).get("rolling_ppg", 1.5)),
            "away_rolling_ppg": safe_float(rolling.get("away", {}).get("rolling_ppg", 1.5)),
            "home_rolling_wins": safe_float(rolling.get("home", {}).get("rolling_wins", 0)),
            "away_rolling_wins": safe_float(rolling.get("away", {}).get("rolling_wins", 0)),
            "home_rolling_draws": safe_float(rolling.get("home", {}).get("rolling_draws", 0)),
            "away_rolling_draws": safe_float(rolling.get("away", {}).get("rolling_draws", 0)),
            "home_rolling_losses": safe_float(rolling.get("home", {}).get("rolling_losses", 0)),
            "away_rolling_losses": safe_float(rolling.get("away", {}).get("rolling_losses", 0)),

            # Market Value
            "home_market_value_total": safe_float(golden.get("home_market_value_total", 0)),
            "away_market_value_total": safe_float(golden.get("away_market_value_total", 0)),
            "market_value_gap": safe_float(golden.get("market_value_gap", 0)),
            "market_value_ratio": safe_float(golden.get("market_value_ratio", 1)),

            # Injury
            "home_injury_count": safe_float(golden.get("home_injury_count", 0)),
            "away_injury_count": safe_float(golden.get("away_injury_count", 0)),
            "injury_count_gap": safe_float(golden.get("injury_count_gap", 0)),

            # Lineup
            "home_starters_count": safe_float(golden.get("home_starters_count", 11)),
            "away_starters_count": safe_float(golden.get("away_starters_count", 11)),
            "home_age_avg": safe_float(golden.get("home_age_avg", 26)),
            "away_age_avg": safe_float(golden.get("away_age_avg", 26)),
            "age_gap": safe_float(golden.get("age_gap", 0)),

            # Odds
            "opening_home_odds": safe_float(odds.get("opening_home_odds", odds.get("current_home_odds", 2.5))),
            "opening_draw_odds": safe_float(odds.get("opening_draw_odds", odds.get("current_draw_odds", 3.3))),
            "opening_away_odds": safe_float(odds.get("opening_away_odds", odds.get("current_away_odds", 2.8))),
        }

        data.append(features)

    df = pd.DataFrame(data)
    df["match_date"] = pd.to_datetime(df["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)

    return df


# ============================================================================
# Walk-Forward 验证
# ============================================================================

def walk_forward_validation(
    df,
    train_window_days=DEFAULT_TRAIN_WINDOW_DAYS,
    test_window_days=DEFAULT_TEST_WINDOW_DAYS,
    feature_cols=None,
    min_train_samples=MIN_TRAIN_SAMPLES
):
    """
    步进式验证

    流程:
    1. 按 match_date 排序
    2. 用前 train_window_days 天数据训练，预测后 test_window_days 天
    3. 滑动窗口重复

    Args:
        df: 包含 match_date 和特征的 DataFrame
        train_window_days: 训练窗口天数
        test_window_days: 测试窗口天数
        feature_cols: 使用的特征列
        min_train_samples: 最小训练样本数

    Yields:
        dict: 每个窗口的结果
    """
    if feature_cols is None:
        feature_cols = [col for col in SAFE_FEATURES if col in df.columns]

    # 确保按日期排序
    df = df.sort_values("match_date").reset_index(drop=True)

    # 获取日期范围
    min_date = df["match_date"].min()
    max_date = df["match_date"].max()

    # 计算窗口数
    total_days = (max_date - min_date).days
    step_days = test_window_days

    window_id = 0

    # 滑动窗口
    current_date = min_date + timedelta(days=train_window_days)

    while current_date < max_date:
        window_id += 1

        # 定义训练和测试期间
        train_start = current_date - timedelta(days=train_window_days)
        train_end = current_date
        test_start = current_date
        test_end = current_date + timedelta(days=test_window_days)

        # 分割数据
        train_df = df[(df["match_date"] >= train_start) & (df["match_date"] < train_end)]
        test_df = df[(df["match_date"] >= test_start) & (df["match_date"] < test_end)]

        # 检查样本量
        if len(train_df) < min_train_samples or len(test_df) == 0:
            current_date += timedelta(days=step_days)
            continue

        # 准备特征和标签
        X_train = train_df[feature_cols].values
        y_train = train_df["actual_result"].map({"H": 2, "D": 1, "A": 0}).values

        X_test = test_df[feature_cols].values
        y_test = test_df["actual_result"].map({"H": 2, "D": 1, "A": 0}).values

        yield {
            "window_id": window_id,
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "X_train": X_train,
            "y_train": y_train,
            "X_test": X_test,
            "y_test": y_test,
            "test_df": test_df,
            "feature_cols": feature_cols,
        }

        # 滑动窗口
        current_date += timedelta(days=step_days)


def run_walk_forward_backtest(
    train_window_days=90,
    test_window_days=30,
    model_type="random_forest"
):
    """
    执行 Walk-Forward 回测

    Args:
        train_window_days: 训练窗口天数
        test_window_days: 测试窗口天数
        model_type: 模型类型 ("random_forest", "logistic", "xgboost")
    """
    print("=" * 80)
    print("V4.5-WALK-FORWARD: 步进式时序验证")
    print("=" * 80)
    print(f"\n⚙️  配置:")
    print(f"  训练窗口: {train_window_days} 天")
    print(f"  测试窗口: {test_window_days} 天")
    print(f"  模型类型: {model_type}")
    print(f"  特征数量: {len(SAFE_FEATURES)}")

    # 加载数据
    print("\n📥 加载比赛数据...")
    df = load_matches_with_features()

    if df.empty:
        print("❌ 没有找到数据")
        return

    print(f"  找到 {len(df)} 场比赛")
    print(f"  日期范围: {df['match_date'].min().date()} 至 {df['match_date'].max().date()}")

    # 结果收集
    window_results = []
    all_predictions = []

    # 导入模型
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    except ImportError:
        print("❌ sklearn 未安装")
        return

    # 选择模型
    if model_type == "random_forest":
        model_class = lambda: RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=42, n_jobs=-1
        )
    elif model_type == "logistic":
        model_class = lambda: LogisticRegression(
            max_iter=1000, random_state=42
        )
    else:
        model_class = lambda: RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=42, n_jobs=-1
        )

    print("\n" + "=" * 80)
    print("🔄 开始 Walk-Forward 验证")
    print("=" * 80)

    # 执行 Walk-Forward
    for window in walk_forward_validation(
        df,
        train_window_days=train_window_days,
        test_window_days=test_window_days
    ):
        window_id = window["window_id"]

        # 标准化
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(window["X_train"])
        X_test_scaled = scaler.transform(window["X_test"])

        # 训练模型
        model = model_class()
        model.fit(X_train_scaled, window["y_train"])

        # 预测
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)

        # 计算准确率
        accuracy = accuracy_score(window["y_test"], y_pred)

        # 详细统计
        precision, recall, f1, _ = precision_recall_fscore_support(
            window["y_test"], y_pred, average='weighted', zero_division=0
        )

        # 保存窗口结果
        window_result = {
            "window_id": window_id,
            "train_period": f"{window['train_start'].date()} ~ {window['train_end'].date()}",
            "test_period": f"{window['test_start'].date()} ~ {window['test_end'].date()}",
            "train_samples": window["train_samples"],
            "test_samples": window["test_samples"],
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        window_results.append(window_result)

        # 保存每个预测
        for i, (idx, row) in enumerate(window["test_df"].iterrows()):
            result_map = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
            pred_label = result_map.get(y_pred[i], "UNKNOWN")
            actual_label = result_map.get(window["y_test"][i], "UNKNOWN")

            # 置信度 = 最大概率
            confidence = float(max(y_prob[i]))

            all_predictions.append({
                "window_id": window_id,
                "match_id": row["match_id"],
                "match_date": str(row["match_date"].date()),
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "actual_result": actual_label,
                "predicted_outcome": pred_label,
                "confidence": confidence,
                "is_correct": pred_label == actual_label,
            })

        # 打印进度
        print(f"  窗口 {window_id}: 训练 {window['train_samples']:3d} 场 | "
              f"测试 {window['test_samples']:3d} 场 | "
              f"准确率 {accuracy*100:5.1f}% | "
              f"测试期 {window['test_start'].date()} ~ {window['test_end'].date()}")

    # 汇总结果
    print_summary(window_results, all_predictions)

    return window_results, all_predictions


def print_summary(window_results, all_predictions):
    """打印汇总结果"""
    print("\n" + "=" * 80)
    print("📊 Walk-Forward 验证结果汇总")
    print("=" * 80)

    # 窗口统计
    accuracies = [w["accuracy"] for w in window_results]
    avg_accuracy = np.mean(accuracies)
    std_accuracy = np.std(accuracies)

    print(f"\n📈 窗口统计 ({len(window_results)} 个窗口):")
    print(f"  平均准确率: {avg_accuracy*100:.1f}% (+/- {std_accuracy*200:.1f}%)")
    print(f"  最高准确率: {max(accuracies)*100:.1f}%")
    print(f"  最低准确率: {min(accuracies)*100:.1f}%")
    print(f"  随机基准: 33.3%")

    # 总体预测统计
    total = len(all_predictions)
    correct = sum(1 for p in all_predictions if p["is_correct"])
    overall_accuracy = correct / total * 100 if total > 0 else 0

    print(f"\n🎯 总体预测:")
    print(f"  总预测数: {total}")
    print(f"  正确预测: {correct}")
    print(f"  总准确率: {overall_accuracy:.1f}%")

    # 按结果类型统计
    outcome_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    for p in all_predictions:
        outcome = p["predicted_outcome"]
        outcome_stats[outcome]["total"] += 1
        if p["is_correct"]:
            outcome_stats[outcome]["correct"] += 1

    print(f"\n📊 预测分布:")
    for outcome in ["HOME_WIN", "DRAW", "AWAY_WIN"]:
        stats = outcome_stats[outcome]
        if stats["total"] > 0:
            pct = stats["total"] / total * 100
            acc = stats["correct"] / stats["total"] * 100
            print(f"  {outcome}: {stats['total']} 场 ({pct:.1f}%) | 准确率 {acc:.1f}%")

    # 置信度分析
    print(f"\n🎯 置信度分析:")
    for threshold in [0.4, 0.5, 0.6]:
        high_conf = [p for p in all_predictions if p["confidence"] >= threshold]
        if high_conf:
            high_correct = sum(1 for p in high_conf if p["is_correct"])
            high_acc = high_correct / len(high_conf) * 100
            print(f"  置信度 >= {threshold}: {len(high_conf)} 场 ({len(high_conf)/total*100:.1f}%) | 准确率 {high_acc:.1f}%")

    # 各窗口详情
    print(f"\n📋 各窗口详情:")
    print(f"  {'窗口':>4} | {'训练期':>24} | {'测试期':>24} | {'训练':>5} | {'测试':>5} | {'准确率':>6}")
    print(f"  {'-'*4}-+-{'-'*24}-+-{'-'*24}-+-{'-'*5}-+-{'-'*5}-+-{'-'*6}")
    for w in window_results:
        print(f"  {w['window_id']:>4} | {w['train_period']:>24} | {w['test_period']:>24} | "
              f"{w['train_samples']:>5} | {w['test_samples']:>5} | {w['accuracy']*100:>5.1f}%")

    # 与随机分割对比
    print(f"\n" + "=" * 40)
    print("⚠️  方法对比")
    print("=" * 40)
    print(f"  随机分割 (train_test_split): 会有数据泄露")
    print(f"  Walk-Forward: 严格时序隔离，真实准确率")
    print(f"\n  当前 Walk-Forward 准确率: {overall_accuracy:.1f}%")

    if overall_accuracy >= 45:
        print(f"  ✅ 模型有预测能力 (高于随机 33.3%)")
    else:
        print(f"  ⚠️  模型预测能力较弱")

    print("\n" + "=" * 80)
    print("Walk-Forward 验证完成!")
    print("=" * 80)


# ============================================================================
# 主入口
# ============================================================================

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V4.5 Walk-Forward 时序验证")
    parser.add_argument("--train-days", type=int, default=90, help="训练窗口天数")
    parser.add_argument("--test-days", type=int, default=30, help="测试窗口天数")
    parser.add_argument("--model", type=str, default="random_forest",
                        choices=["random_forest", "logistic"], help="模型类型")

    args = parser.parse_args()

    run_walk_forward_backtest(
        train_window_days=args.train_days,
        test_window_days=args.test_days,
        model_type=args.model
    )


if __name__ == "__main__":
    main()
