#!/usr/bin/env python3
"""
TITAN FeaturePro 集成测试
========================

验证目标:
- Accuracy >= 57.1%
- Draw Recall >= 35%

@module scripts.validation.integration_test
@version V4.47.0
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix
from sklearn.model_selection import train_test_split

sys.path.insert(0, "/app")

from src.database.repositories.prediction_repo import (
    get_db_connection,
    parse_jsonb,
    safe_float,
)
from src.constants.model_config import TITAN_COMBAT_FEATURES, DEFAULT_VALUES

# 直接加载 TitanFeaturePro，绕过 __init__.py 编码问题
import importlib.util
spec = importlib.util.spec_from_file_location(
    "titan_feature_pro",
    "/app/src/ml/feature_engine/titan_feature_pro.py"
)
titan_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(titan_module)
TitanFeaturePro = titan_module.TitanFeaturePro

# 配置日志
logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RESULT_ENCODE = {"H": 2, "D": 1, "A": 0}
RESULT_DECODE = {0: "A", 1: "D", 2: "H"}


def get_finished_matches(conn, days: int = 180) -> List[Dict]:
    """获取已完赛比赛"""
    cur = conn.cursor()
    query = f"""
        SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.actual_result,
               l.elo_features, l.lineup_features, l.h2h_features, l.golden_features, l.tactical_features
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


def get_team_match_history(conn, team_name: str, before_date, limit: int = 5) -> List[Dict]:
    """获取球队比赛历史"""
    cur = conn.cursor()
    query = """
        SELECT m.match_id, m.home_team, m.away_team, m.actual_result, m.home_score, m.away_score,
               l.elo_features, l.golden_features, l.tactical_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'finished'
          AND m.match_date < %s
          AND (m.home_team = %s OR m.away_team = %s)
          AND l.elo_features IS NOT NULL
        ORDER BY m.match_date DESC LIMIT %s
    """
    cur.execute(query, (before_date, team_name, team_name, limit))
    rows = cur.fetchall()
    cur.close()
    return rows


def extract_base_features(row: Dict) -> Dict[str, float]:
    """提取 11 维基础特征"""
    features = {}

    elo = parse_jsonb(row["elo_features"])
    home_elo = safe_float(elo.get("home_elo_pre", elo.get("home_elo", 1500)), 1500)
    away_elo = safe_float(elo.get("away_elo_pre", elo.get("away_elo", 1500)), 1500)

    features["home_elo_pre"] = home_elo
    features["away_elo_pre"] = away_elo
    features["elo_diff"] = safe_float(elo.get("elo_diff", home_elo - away_elo))
    features["expected_home_win"] = safe_float(elo.get("expected_home_win", 0.45))
    features["expected_away_win"] = safe_float(elo.get("expected_away_win", 0.30))

    lineup = parse_jsonb(row["lineup_features"])
    home_mv = safe_float(lineup.get("home_squad_value_eur", 0), 0)
    away_mv = safe_float(lineup.get("away_squad_value_eur", 0), 0)

    features["log_home_squad_value"] = np.log10(home_mv) if home_mv > 0 else DEFAULT_VALUES["log_home_squad_value"]
    features["log_away_squad_value"] = np.log10(away_mv) if away_mv > 0 else DEFAULT_VALUES["log_away_squad_value"]
    total_mv = home_mv + away_mv
    features["home_mv_share"] = home_mv / total_mv if total_mv > 0 else 0.5

    h2h = parse_jsonb(row["h2h_features"])
    features["h2h_home_win_ratio"] = safe_float(h2h.get("h2h_home_win_ratio", h2h.get("home_win_ratio", 0.4)), 0.4)
    features["h2h_draw_ratio"] = safe_float(h2h.get("h2h_draw_ratio", h2h.get("draw_ratio", 0.25)), 0.25)
    features["h2h_avg_goal_diff"] = safe_float(h2h.get("h2h_avg_goal_diff", h2h.get("avg_goal_diff", 0)), 0)

    return features


def main():
    print("\n" + "=" * 80)
    print("🔬 TITAN FeaturePro 集成测试")
    print("=" * 80)
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    conn = get_db_connection()
    print("✅ 数据库连接成功")

    try:
        # Step 1: 获取数据
        print("\n📊 Step 1: 获取测试数据 (180 天)...")
        rows = get_finished_matches(conn, days=180)
        print(f"  获取到 {len(rows)} 场比赛")

        if len(rows) < 100:
            print("❌ 数据量不足")
            return

        # Step 2: 特征提取
        print("\n📊 Step 2: 特征提取...")
        pro = TitanFeaturePro()

        X_base = []
        X_exp = []
        y = []

        for i, row in enumerate(rows):
            if (i + 1) % 200 == 0:
                print(f"  进度: {i+1}/{len(rows)}")

            try:
                # 基础特征
                base_features = extract_base_features(row)
                base_vec = [base_features.get(f, 0.0) for f in TITAN_COMBAT_FEATURES]

                # 计算高级特征
                home_history = get_team_match_history(conn, row["home_team"], row["match_date"])
                away_history = get_team_match_history(conn, row["away_team"], row["match_date"])

                # 构建动量输入
                home_matches = []
                for h in home_history:
                    is_home = h["home_team"] == row["home_team"]
                    elo = parse_jsonb(h["elo_features"])
                    if h["actual_result"] == "H":
                        result = "W" if is_home else "L"
                    elif h["actual_result"] == "A":
                        result = "L" if is_home else "W"
                    else:
                        result = "D"
                    home_matches.append({
                        "result": result,
                        "expected_score": safe_float(elo.get("expected_home_win" if is_home else "expected_away_win", 0.45))
                    })

                away_matches = []
                for h in away_history:
                    is_home = h["home_team"] == row["away_team"]
                    elo = parse_jsonb(h["elo_features"])
                    if h["actual_result"] == "H":
                        result = "W" if is_home else "L"
                    elif h["actual_result"] == "A":
                        result = "L" if is_home else "W"
                    else:
                        result = "D"
                    away_matches.append({
                        "result": result,
                        "expected_score": safe_float(elo.get("expected_home_win" if is_home else "expected_away_win", 0.45))
                    })

                # 获取 xG 数据
                home_golden = parse_jsonb(home_history[0].get("golden_features", {})) if home_history else {}
                away_golden = parse_jsonb(away_history[0].get("golden_features", {})) if away_history else {}
                home_xg = [safe_float(home_golden.get("home_xg", 1.0)) for _ in range(5)]
                away_xg = [safe_float(away_golden.get("away_xg", 1.0)) for _ in range(5)]

                # 获取防守评级
                home_tactical = parse_jsonb(home_history[0].get("tactical_features", {})) if home_history else {}
                away_tactical = parse_jsonb(away_history[0].get("tactical_features", {})) if away_history else {}
                home_def = safe_float(home_tactical.get("defensive_rating", 6.0))
                away_def = safe_float(away_tactical.get("defensive_rating", 6.0))

                # 计算高级特征
                result = pro.calculate_all_features(
                    home_recent_matches=home_matches,
                    away_recent_matches=away_matches,
                    home_xg_l5=home_xg,
                    away_xg_l5=away_xg,
                    home_def_rating=home_def,
                    away_def_rating=away_def,
                )

                if result.success:
                    exp_features = result.features
                    exp_vec = base_vec + [
                        exp_features.get("momentum_home", 0.0),
                        exp_features.get("momentum_away", 0.0),
                        exp_features.get("xg_balance_index", 0.5),
                        exp_features.get("double_wall_score", 0.5),
                        exp_features.get("scoreless_momentum", 0.5),
                    ]
                else:
                    exp_vec = base_vec + [0.0, 0.0, 0.5, 0.5, 0.5]

                X_base.append(base_vec)
                X_exp.append(exp_vec)
                y.append(RESULT_ENCODE.get(row["actual_result"], 1))

            except Exception as e:
                continue

        X_base = np.array(X_base)
        X_exp = np.array(X_exp)
        y = np.array(y)

        print(f"\n  有效样本: {len(X_base)}")

        # 类别分布
        unique, counts = np.unique(y, return_counts=True)
        print(f"\n  类别分布:")
        for u, c in zip(unique, counts):
            print(f"    {RESULT_DECODE[u]}: {c} ({c/len(y)*100:.1f}%)")

        # 划分数据
        X_base_train, X_base_test, X_exp_train, X_exp_test, y_train, y_test = train_test_split(
            X_base, X_exp, y, test_size=0.3, random_state=42, stratify=y
        )

        print(f"  训练集: {len(X_base_train)} | 测试集: {len(X_base_test)}")

        # Step 3: 模型训练
        print("\n📊 Step 3: 模型训练...")

        model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced", n_jobs=-1)
        model.fit(X_exp_train, y_train)

        y_pred = model.predict(X_exp_test)
        y_proba = model.predict_proba(X_exp_test)

        acc = accuracy_score(y_test, y_pred)
        ll = log_loss(y_test, y_proba)

        cm = confusion_matrix(y_test, y_pred)

        # 计算召回率
        draw_recall = cm[1, 1] / cm[1, :].sum() if cm[1, :].sum() > 0 else 0

        # 结果输出
        print("\n" + "=" * 80)
        print("📋 集成测试结果")
        print("=" * 80)

        print("\n## 混淆矩阵")
        print("-" * 60)
        print("                预测")
        print("              A     D     H")
        for i, label in enumerate(["实际 A", "实际 D", "实际 H"]):
            print(f"  {label}  {cm[i][0]:>5} {cm[i][1]:>5} {cm[i][2]:>5}")

        print("\n## 核心指标")
        print("-" * 60)
        print(f"  Accuracy:     {acc:.4f} ({acc*100:.2f}%)")
        print(f"  Log-Loss:     {ll:.4f}")
        print(f"  Draw Recall:  {draw_recall:.4f} ({draw_recall*100:.2f}%)")

        print("\n## 验收标准")
        print("-" * 60)
        acc_pass = acc >= 0.571
        draw_pass = draw_recall >= 0.35

        print(f"  Accuracy >= 57.1%:   {'✅ 通过' if acc_pass else '❌ 未通过'} ({acc*100:.2f}%)")
        print(f"  Draw Recall >= 35%:  {'✅ 通过' if draw_pass else '❌ 未通过'} ({draw_recall*100:.2f}%)")

        print("\n" + "=" * 80)
        if acc_pass and draw_pass:
            print("✅ 集成测试通过！可以合并到 main 分支")
        else:
            print("❌ 集成测试未通过，需要进一步优化")
        print("=" * 80 + "\n")

        # 保存结果
        result = {
            "test_time": datetime.now().isoformat(),
            "total_samples": int(len(X_base)),
            "test_samples": int(len(X_base_test)),
            "accuracy": float(acc),
            "log_loss": float(ll),
            "draw_recall": float(draw_recall),
            "confusion_matrix": cm.tolist(),
            "accuracy_pass": bool(acc_pass),
            "draw_recall_pass": bool(draw_pass),
            "overall_pass": bool(acc_pass and draw_pass),
        }

        output_file = "/app/logs/integration_test.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"📄 结果已保存到: {output_file}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
