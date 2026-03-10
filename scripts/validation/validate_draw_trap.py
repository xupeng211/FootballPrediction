#!/usr/bin/env python3
"""
TITAN 平局陷阱特征验证
====================

目标: 提升 Draw Recall 从 26.8% 到 20%+

策略:
1. 添加"拉锯战"特征集 (xG平衡、双强防守、低比分动量)
2. 使用 class_weight='balanced' 平衡类别
3. 阈值调优 (Threshold Tuning)

@module scripts.validation.validate_draw_trap
@version lab/draw-trap-v1
@created 2026-03-11
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import train_test_split

# 添加项目根目录到路径
sys.path.insert(0, "/app")

from src.database.repositories.prediction_repo import (
    get_db_connection,
    parse_jsonb,
    safe_float,
)
from src.constants.model_config import TITAN_COMBAT_FEATURES, DEFAULT_VALUES

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 结果编码
RESULT_ENCODE = {"H": 2, "D": 1, "A": 0}
RESULT_DECODE = {0: "A", 1: "D", 2: "H"}


# ============================================================================
# 数据获取
# ============================================================================


def get_finished_matches(conn, days: int = 180) -> List[Dict]:
    """获取已完赛比赛数据"""
    cur = conn.cursor()

    query = f"""
        SELECT
            m.match_id, m.home_team, m.away_team, m.league_name, m.match_date,
            m.home_score, m.away_score, m.actual_result,
            l.elo_features, l.lineup_features, l.h2h_features,
            l.golden_features, l.tactical_features, l.rolling_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'finished'
          AND m.actual_result IN ('H', 'D', 'A')
          AND m.match_date >= NOW() - INTERVAL '{days} days'
          AND l.elo_features IS NOT NULL
        ORDER BY m.match_date DESC
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()

    return rows


def get_team_stats_for_draw_features(
    conn, team_name: str, before_date, limit: int = 5
) -> Tuple[List[float], List[List[int]], float]:
    """
    获取球队统计数据用于平局特征计算

    Returns:
        (xg_list, scores_list, def_rating)
    """
    cur = conn.cursor()

    query = """
        SELECT
            m.match_id, m.home_team, m.away_team,
            m.home_score, m.away_score,
            l.golden_features, l.tactical_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'finished'
          AND m.match_date < %s
          AND (m.home_team = %s OR m.away_team = %s)
          AND l.golden_features IS NOT NULL
        ORDER BY m.match_date DESC
        LIMIT %s
    """

    cur.execute(query, (before_date, team_name, team_name, limit))
    rows = cur.fetchall()
    cur.close()

    xg_list = []
    scores_list = []
    def_ratings = []

    for row in rows:
        is_home = row["home_team"] == team_name
        golden = parse_jsonb(row["golden_features"])
        tactical = parse_jsonb(row["tactical_features"])

        # 获取 xG
        if is_home:
            xg = safe_float(golden.get("home_xg", golden.get("xg_home", 1.0)), 1.0)
        else:
            xg = safe_float(golden.get("away_xg", golden.get("xg_away", 1.0)), 1.0)
        xg_list.append(xg)

        # 获取比分
        if is_home:
            scores_list.append([row["home_score"], row["away_score"]])
        else:
            scores_list.append([row["away_score"], row["home_score"]])

        # 获取防守评级
        def_rating = safe_float(
            tactical.get("defensive_rating" if is_home else "away_def_rating", 6.0), 6.0
        )
        def_ratings.append(def_rating)

    avg_def = np.mean(def_ratings) if def_ratings else 6.0

    return xg_list, scores_list, avg_def


# ============================================================================
# 特征提取
# ============================================================================


def extract_base_features(row: Dict) -> Dict[str, float]:
    """提取 11 维基础特征"""
    features = {}

    # Elo 特征 (5 维)
    elo = parse_jsonb(row["elo_features"])
    home_elo = safe_float(elo.get("home_elo_pre", elo.get("home_elo", 1500)), 1500)
    away_elo = safe_float(elo.get("away_elo_pre", elo.get("away_elo", 1500)), 1500)

    features["home_elo_pre"] = home_elo
    features["away_elo_pre"] = away_elo
    features["elo_diff"] = safe_float(elo.get("elo_diff", home_elo - away_elo))
    features["expected_home_win"] = safe_float(elo.get("expected_home_win", 0.45))
    features["expected_away_win"] = safe_float(elo.get("expected_away_win", 0.30))

    # 身价特征 (3 维)
    lineup = parse_jsonb(row["lineup_features"])
    home_mv = safe_float(lineup.get("home_squad_value_eur", 0), 0)
    away_mv = safe_float(lineup.get("away_squad_value_eur", 0), 0)

    features["log_home_squad_value"] = (
        np.log10(home_mv) if home_mv > 0 else DEFAULT_VALUES["log_home_squad_value"]
    )
    features["log_away_squad_value"] = (
        np.log10(away_mv) if away_mv > 0 else DEFAULT_VALUES["log_away_squad_value"]
    )

    total_mv = home_mv + away_mv
    features["home_mv_share"] = home_mv / total_mv if total_mv > 0 else 0.5

    # H2H 特征 (3 维)
    h2h = parse_jsonb(row["h2h_features"])
    features["h2h_home_win_ratio"] = safe_float(
        h2h.get("h2h_home_win_ratio", h2h.get("home_win_ratio", 0.4)), 0.4
    )
    features["h2h_draw_ratio"] = safe_float(
        h2h.get("h2h_draw_ratio", h2h.get("draw_ratio", 0.25)), 0.25
    )
    features["h2h_avg_goal_diff"] = safe_float(
        h2h.get("h2h_avg_goal_diff", h2h.get("avg_goal_diff", 0)), 0
    )

    return features


def extract_draw_features(
    conn, row: Dict
) -> Tuple[float, float, float]:
    """
    提取平局陷阱特征

    Returns:
        (xg_balance_index, double_wall_score, scoreless_momentum)
    """
    match_date = row["match_date"]

    # 获取主队统计
    home_xg, home_scores, home_def = get_team_stats_for_draw_features(
        conn, row["home_team"], match_date, limit=5
    )

    # 获取客队统计
    away_xg, away_scores, away_def = get_team_stats_for_draw_features(
        conn, row["away_team"], match_date, limit=5
    )

    # 计算特征 A: xG 平衡指数
    if home_xg and away_xg:
        home_xg_mean = np.mean(home_xg)
        away_xg_mean = np.mean(away_xg)
        xg_diff = abs(home_xg_mean - away_xg_mean)
        xg_balance = min(1.0, 1.0 / (xg_diff + 0.1) / 10.0)
    else:
        xg_balance = 0.5

    # 计算特征 B: 双强防守指数
    avg_def = (home_def + away_def) / 2.0
    double_wall = min(1.0, (avg_def / 10.0) ** 1.2)

    # 计算特征 C: 低比分动量
    all_scores = home_scores + away_scores
    if all_scores:
        low_score_count = sum(1 for s in all_scores if sum(s) <= 2)
        scoreless_momentum = low_score_count / len(all_scores)
    else:
        scoreless_momentum = 0.5

    return xg_balance, double_wall, scoreless_momentum


# ============================================================================
# 模型训练与评估
# ============================================================================


def train_and_evaluate(
    X_base_train,
    X_base_test,
    X_exp_train,
    X_exp_test,
    y_train,
    y_test,
    use_balanced: bool = True,
):
    """
    训练并评估模型

    Args:
        use_balanced: 是否使用 class_weight='balanced'
    """
    class_weight = "balanced" if use_balanced else None

    # 基准模型 (11 维)
    base_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1,
        class_weight=class_weight,
    )
    base_model.fit(X_base_train, y_train)
    base_pred = base_model.predict(X_base_test)
    base_proba = base_model.predict_proba(X_base_test)

    # 实验模型 (14 维 = 11 + 3 平局特征)
    exp_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1,
        class_weight=class_weight,
    )
    exp_model.fit(X_exp_train, y_train)
    exp_pred = exp_model.predict(X_exp_test)
    exp_proba = exp_model.predict_proba(X_exp_test)

    return {
        "base_model": base_model,
        "exp_model": exp_model,
        "base_pred": base_pred,
        "exp_pred": exp_pred,
        "base_proba": base_proba,
        "exp_proba": exp_proba,
    }


def print_confusion_matrix(y_true, y_pred, title: str):
    """打印混淆矩阵"""
    cm = confusion_matrix(y_true, y_pred)
    print(f"\n  {title}")
    print("                  预测")
    print("                A     D     H")
    for i, row_label in enumerate(["实际 A", "实际 D", "实际 H"]):
        print(f"  {row_label}  {cm[i][0]:>5} {cm[i][1]:>5} {cm[i][2]:>5}")

    # 计算各类召回率
    recall_a = cm[0][0] / cm[0].sum() if cm[0].sum() > 0 else 0
    recall_d = cm[1][1] / cm[1].sum() if cm[1].sum() > 0 else 0
    recall_h = cm[2][2] / cm[2].sum() if cm[2].sum() > 0 else 0

    print(f"\n  召回率: A={recall_a:.1%}, D={recall_d:.1%}, H={recall_h:.1%}")

    return cm, recall_a, recall_d, recall_h


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🎯 TITAN 平局陷阱特征验证 - Draw Strategy Evolution")
    print("=" * 80)
    print(f"📅 实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌿 分支: lab/draw-trap-v1")
    print("=" * 80)

    # 连接数据库
    try:
        conn = get_db_connection()
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    try:
        # Step 1: 获取数据
        print("\n📊 Step 1: 数据采样 (180 天)...")
        rows = get_finished_matches(conn, days=180)
        print(f"  获取到 {len(rows)} 场已完赛比赛")

        # Step 2: 特征提取
        print("\n📊 Step 2: 特征提取...")
        X_base = []
        X_exp = []
        y = []

        for i, row in enumerate(rows):
            if (i + 1) % 200 == 0:
                print(f"  进度: {i+1}/{len(rows)}")

            try:
                # 基础特征
                base_features = extract_base_features(row)

                # 平局陷阱特征
                xg_bal, double_wall, scoreless = extract_draw_features(conn, row)

                # 构建向量
                base_vec = [base_features.get(f, 0.0) for f in TITAN_COMBAT_FEATURES]
                exp_vec = base_vec + [xg_bal, double_wall, scoreless]

                # 标签
                label = RESULT_ENCODE.get(row["actual_result"], 1)

                X_base.append(base_vec)
                X_exp.append(exp_vec)
                y.append(label)

            except Exception as e:
                continue

        X_base = np.array(X_base)
        X_exp = np.array(X_exp)
        y = np.array(y)

        print(f"  有效样本: {len(X_base)} 场")

        # 类别分布
        unique, counts = np.unique(y, return_counts=True)
        print(f"\n  类别分布:")
        for u, c in zip(unique, counts):
            print(f"    {RESULT_DECODE[u]}: {c} ({c/len(y)*100:.1f}%)")

        # 划分数据集
        X_base_train, X_base_test, X_exp_train, X_exp_test, y_train, y_test = train_test_split(
            X_base, X_exp, y, test_size=0.3, random_state=42, stratify=y
        )

        print(f"  训练集: {len(X_base_train)} | 测试集: {len(X_base_test)}")

        # Step 3: 模型训练 - 无平衡
        print("\n" + "=" * 80)
        print("📊 Step 3: 基准模型 (无类别平衡)")
        print("=" * 80)

        results_unbalanced = train_and_evaluate(
            X_base_train,
            X_base_test,
            X_exp_train,
            X_exp_test,
            y_train,
            y_test,
            use_balanced=False,
        )

        print("\n## 基准模型 (11 维, 无平衡)")
        cm_base, ra1, rd1, rh1 = print_confusion_matrix(
            y_test, results_unbalanced["base_pred"], "混淆矩阵"
        )
        acc_base = accuracy_score(y_test, results_unbalanced["base_pred"])
        ll_base = log_loss(y_test, results_unbalanced["base_proba"])
        print(f"  Accuracy: {acc_base:.4f} | Log-Loss: {ll_base:.4f}")

        print("\n## 实验模型 (14 维, 无平衡)")
        cm_exp, ra2, rd2, rh2 = print_confusion_matrix(
            y_test, results_unbalanced["exp_pred"], "混淆矩阵"
        )
        acc_exp = accuracy_score(y_test, results_unbalanced["exp_pred"])
        ll_exp = log_loss(y_test, results_unbalanced["exp_proba"])
        print(f"  Accuracy: {acc_exp:.4f} | Log-Loss: {ll_exp:.4f}")

        # Step 4: 模型训练 - 有平衡
        print("\n" + "=" * 80)
        print("📊 Step 4: 平衡模型 (class_weight='balanced')")
        print("=" * 80)

        results_balanced = train_and_evaluate(
            X_base_train,
            X_base_test,
            X_exp_train,
            X_exp_test,
            y_train,
            y_test,
            use_balanced=True,
        )

        print("\n## 平衡基准模型 (11 维, balanced)")
        cm_base_bal, ra3, rd3, rh3 = print_confusion_matrix(
            y_test, results_balanced["base_pred"], "混淆矩阵"
        )
        acc_base_bal = accuracy_score(y_test, results_balanced["base_pred"])
        ll_base_bal = log_loss(y_test, results_balanced["base_proba"])
        print(f"  Accuracy: {acc_base_bal:.4f} | Log-Loss: {ll_base_bal:.4f}")

        print("\n## 平衡实验模型 (14 维, balanced)")
        cm_exp_bal, ra4, rd4, rh4 = print_confusion_matrix(
            y_test, results_balanced["exp_pred"], "混淆矩阵"
        )
        acc_exp_bal = accuracy_score(y_test, results_balanced["exp_pred"])
        ll_exp_bal = log_loss(y_test, results_balanced["exp_proba"])
        print(f"  Accuracy: {acc_exp_bal:.4f} | Log-Loss: {ll_exp_bal:.4f}")

        # Step 5: 结果对比
        print("\n" + "=" * 80)
        print("📋 混淆矩阵对比总结")
        print("=" * 80)

        print("\n  模型                              Accuracy  Draw-Recall  变化")
        print("  " + "-" * 70)
        print(f"  基准 (11维, 无平衡)              {acc_base:.4f}    {rd1:.1%}")
        print(f"  实验 (14维, 无平衡)              {acc_exp:.4f}    {rd2:.1%}      {rd2-rd1:+.1%}")
        print(f"  基准 (11维, balanced)            {acc_base_bal:.4f}    {rd3:.1%}")
        print(f"  实验 (14维, balanced)            {acc_exp_bal:.4f}    {rd4:.1%}      {rd4-rd3:+.1%}")

        # Step 6: 结论
        print("\n" + "=" * 80)
        print("📋 实验结论")
        print("=" * 80)

        best_draw_recall = max(rd1, rd2, rd3, rd4)
        best_model_idx = [rd1, rd2, rd3, rd4].index(best_draw_recall)
        model_names = [
            "基准(无平衡)",
            "实验(无平衡)",
            "基准(balanced)",
            "实验(balanced)",
        ]
        best_model = model_names[best_model_idx]
        best_acc = [acc_base, acc_exp, acc_base_bal, acc_exp_bal][best_model_idx]

        print(f"\n  最佳 Draw Recall: {best_draw_recall:.1%} ({best_model})")
        print(f"  对应 Accuracy: {best_acc:.4f}")

        if best_draw_recall >= 0.20:
            print("\n  ✅ 成功！Draw Recall 达到 20% 以上")
        else:
            print(f"\n  ⚠️ 未达标。Draw Recall {best_draw_recall:.1%} < 20%")

        # 保存结果
        result = {
            "experiment_time": datetime.now().isoformat(),
            "branch": "lab/draw-trap-v1",
            "total_samples": len(X_base),
            "test_samples": len(y_test),
            "models": {
                "base_unbalanced": {
                    "accuracy": float(acc_base),
                    "log_loss": float(ll_base),
                    "draw_recall": float(rd1),
                },
                "exp_unbalanced": {
                    "accuracy": float(acc_exp),
                    "log_loss": float(ll_exp),
                    "draw_recall": float(rd2),
                },
                "base_balanced": {
                    "accuracy": float(acc_base_bal),
                    "log_loss": float(ll_base_bal),
                    "draw_recall": float(rd3),
                },
                "exp_balanced": {
                    "accuracy": float(acc_exp_bal),
                    "log_loss": float(ll_exp_bal),
                    "draw_recall": float(rd4),
                },
            },
            "best_model": best_model,
            "best_draw_recall": float(best_draw_recall),
            "target_achieved": bool(best_draw_recall >= 0.20),
        }

        output_file = "/app/logs/draw_trap_validation.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n📄 结果已保存到: {output_file}")
        print("\n" + "=" * 80)
        print("🎯 TITAN \"平局陷阱\" 第一阶段分析完成")
        print("=" * 80 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
