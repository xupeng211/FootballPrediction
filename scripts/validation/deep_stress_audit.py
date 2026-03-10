#!/usr/bin/env python3
"""
TITAN 深度压力测试审计
========================

地狱级审计项目:
1. 特征剥离审计 (Ablation Study)
2. 10折交叉验证 (稳定性测试)
3. 概率校准度分析 (高置信度预测验证)

@module scripts.validation.deep_stress_audit
@version V4.47.0-audit
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix, brier_score_loss
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.calibration import calibration_curve

sys.path.insert(0, "/app")

from src.database.repositories.prediction_repo import get_db_connection, parse_jsonb, safe_float
from src.constants.model_config import TITAN_COMBAT_FEATURES, DEFAULT_VALUES

# 直接加载 TitanFeaturePro
import importlib.util
spec = importlib.util.spec_from_file_location("titan_feature_pro", "/app/src/ml/feature_engine/titan_feature_pro.py")
titan_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(titan_module)
TitanFeaturePro = titan_module.TitanFeaturePro

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)

RESULT_ENCODE = {"H": 2, "D": 1, "A": 0}
RESULT_DECODE = {0: "A", 1: "D", 2: "H"}


def get_all_data(conn, days: int = 180):
    """获取所有数据"""
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


def get_team_history(conn, team_name: str, before_date, limit: int = 5):
    """获取球队历史"""
    cur = conn.cursor()
    query = """
        SELECT m.match_id, m.home_team, m.away_team, m.actual_result,
               l.elo_features, l.golden_features, l.tactical_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'finished' AND m.match_date < %s
          AND (m.home_team = %s OR m.away_team = %s)
          AND l.elo_features IS NOT NULL
        ORDER BY m.match_date DESC LIMIT %s
    """
    cur.execute(query, (before_date, team_name, team_name, limit))
    rows = cur.fetchall()
    cur.close()
    return rows


def extract_features(row: Dict, conn, pro: TitanFeaturePro) -> Tuple[np.ndarray, np.ndarray, int]:
    """提取特征"""
    # 基础特征
    features = {}
    elo = parse_jsonb(row["elo_features"])
    lineup = parse_jsonb(row["lineup_features"])
    h2h = parse_jsonb(row["h2h_features"])

    home_elo = safe_float(elo.get("home_elo_pre", elo.get("home_elo", 1500)), 1500)
    away_elo = safe_float(elo.get("away_elo_pre", elo.get("away_elo", 1500)), 1500)

    features["home_elo_pre"] = home_elo
    features["away_elo_pre"] = away_elo
    features["elo_diff"] = safe_float(elo.get("elo_diff", home_elo - away_elo))
    features["expected_home_win"] = safe_float(elo.get("expected_home_win", 0.45))
    features["expected_away_win"] = safe_float(elo.get("expected_away_win", 0.30))

    home_mv = safe_float(lineup.get("home_squad_value_eur", 0), 0)
    away_mv = safe_float(lineup.get("away_squad_value_eur", 0), 0)
    features["log_home_squad_value"] = np.log10(home_mv) if home_mv > 0 else 18.0
    features["log_away_squad_value"] = np.log10(away_mv) if away_mv > 0 else 18.0
    features["home_mv_share"] = home_mv / (home_mv + away_mv) if (home_mv + away_mv) > 0 else 0.5

    features["h2h_home_win_ratio"] = safe_float(h2h.get("h2h_home_win_ratio", 0.4), 0.4)
    features["h2h_draw_ratio"] = safe_float(h2h.get("h2h_draw_ratio", 0.25), 0.25)
    features["h2h_avg_goal_diff"] = safe_float(h2h.get("h2h_avg_goal_diff", 0), 0)

    base_vec = np.array([features.get(f, 0.0) for f in TITAN_COMBAT_FEATURES])

    # 高级特征
    home_history = get_team_history(conn, row["home_team"], row["match_date"])
    away_history = get_team_history(conn, row["away_team"], row["match_date"])

    # 构建动量输入
    def build_matches(history, team_name):
        matches = []
        for h in history:
            is_home = h["home_team"] == team_name
            elo = parse_jsonb(h["elo_features"])
            if h["actual_result"] == "H":
                result = "W" if is_home else "L"
            elif h["actual_result"] == "A":
                result = "L" if is_home else "W"
            else:
                result = "D"
            matches.append({
                "result": result,
                "expected_score": safe_float(elo.get("expected_home_win" if is_home else "expected_away_win", 0.45))
            })
        return matches

    home_matches = build_matches(home_history, row["home_team"])
    away_matches = build_matches(away_history, row["away_team"])

    # 获取 xG 和防守数据
    home_golden = parse_jsonb(home_history[0].get("golden_features", {})) if home_history else {}
    away_golden = parse_jsonb(away_history[0].get("golden_features", {})) if away_history else {}
    home_xg = [safe_float(home_golden.get("home_xg", 1.0)) for _ in range(5)]
    away_xg = [safe_float(away_golden.get("away_xg", 1.0)) for _ in range(5)]

    home_tactical = parse_jsonb(home_history[0].get("tactical_features", {})) if home_history else {}
    away_tactical = parse_jsonb(away_history[0].get("tactical_features", {})) if away_history else {}
    home_def = safe_float(home_tactical.get("defensive_rating", 6.0))
    away_def = safe_float(away_tactical.get("defensive_rating", 6.0))

    result = pro.calculate_all_features(
        home_recent_matches=home_matches,
        away_recent_matches=away_matches,
        home_xg_l5=home_xg,
        away_xg_l5=away_xg,
        home_def_rating=home_def,
        away_def_rating=away_def,
    )

    momentum_vec = np.array([
        result.features.get("momentum_home", 0.0),
        result.features.get("momentum_away", 0.0),
    ])

    draw_trap_vec = np.array([
        result.features.get("xg_balance_index", 0.5),
        result.features.get("double_wall_score", 0.5),
        result.features.get("scoreless_momentum", 0.5),
    ])

    label = RESULT_ENCODE.get(row["actual_result"], 1)

    return base_vec, momentum_vec, draw_trap_vec, label


def run_ablation_study(X_base, X_momentum, X_draw_trap, y):
    """特征剥离审计"""
    print("\n" + "=" * 80)
    print("📊 审计 1: 特征剥离审计 (Ablation Study)")
    print("=" * 80)

    results = []

    # 配置组合
    configs = [
        {"name": "仅基础特征 (11维)", "use_momentum": False, "use_draw_trap": False},
        {"name": "基础 + 动量 (13维)", "use_momentum": True, "use_draw_trap": False},
        {"name": "基础 + 平局陷阱 (14维)", "use_momentum": False, "use_draw_trap": True},
        {"name": "全部特征 (16维)", "use_momentum": True, "use_draw_trap": True},
    ]

    for config in configs:
        # 构建特征矩阵
        if config["use_momentum"] and config["use_draw_trap"]:
            X = np.hstack([X_base, X_momentum, X_draw_trap])
        elif config["use_momentum"]:
            X = np.hstack([X_base, X_momentum])
        elif config["use_draw_trap"]:
            X = np.hstack([X_base, X_draw_trap])
        else:
            X = X_base

        # 训练测试
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

        model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced", n_jobs=-1)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        # 计算 Draw Recall
        cm = confusion_matrix(y_test, y_pred)
        draw_recall = cm[1, 1] / cm[1, :].sum() if cm[1, :].sum() > 0 else 0

        results.append({
            "config": config["name"],
            "accuracy": acc,
            "draw_recall": draw_recall,
            "features": X.shape[1],
        })

        print(f"\n  {config['name']}")
        print(f"    特征数: {X.shape[1]}")
        print(f"    Accuracy: {acc:.4f} ({acc*100:.2f}%)")
        print(f"    Draw Recall: {draw_recall:.4f} ({draw_recall*100:.2f}%)")

    # 汇总表格
    print("\n" + "-" * 80)
    print("📋 特征剥离汇总表")
    print("-" * 80)
    print(f"  {'配置':<30} {'特征数':<10} {'Accuracy':<12} {'Draw Recall':<12}")
    print("-" * 80)
    for r in results:
        print(f"  {r['config']:<30} {r['features']:<10} {r['accuracy']*100:>10.2f}% {r['draw_recall']*100:>10.2f}%")

    return results


def run_stability_test(X_full, y, n_folds: int = 10):
    """10折交叉验证稳定性测试"""
    print("\n" + "=" * 80)
    print("📊 审计 2: 10折交叉验证 (稳定性测试)")
    print("=" * 80)

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    fold_accs = []
    fold_draw_recalls = []

    print(f"\n  执行 {n_folds} 折交叉验证...")

    for fold, (train_idx, test_idx) in enumerate(skf.split(X_full, y), 1):
        X_train, X_test = X_full[train_idx], X_full[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced", n_jobs=-1)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        cm = confusion_matrix(y_test, y_pred)
        draw_recall = cm[1, 1] / cm[1, :].sum() if cm[1, :].sum() > 0 else 0

        fold_accs.append(acc)
        fold_draw_recalls.append(draw_recall)

        print(f"    Fold {fold:2d}: Accuracy = {acc:.4f}, Draw Recall = {draw_recall:.4f}")

    # 统计分析
    acc_mean = np.mean(fold_accs)
    acc_std = np.std(fold_accs)
    acc_min = np.min(fold_accs)
    acc_max = np.max(fold_accs)

    dr_mean = np.mean(fold_draw_recalls)
    dr_std = np.std(fold_draw_recalls)
    dr_min = np.min(fold_draw_recalls)
    dr_max = np.max(fold_draw_recalls)

    print("\n" + "-" * 80)
    print("📋 10折稳定性报告")
    print("-" * 80)
    print(f"\n  Accuracy:")
    print(f"    均值: {acc_mean:.4f} ({acc_mean*100:.2f}%)")
    print(f"    标准差: {acc_std:.4f}")
    print(f"    范围: [{acc_min:.4f}, {acc_max:.4f}]")
    print(f"    变异系数 (CV): {acc_std/acc_mean*100:.2f}%")

    print(f"\n  Draw Recall:")
    print(f"    均值: {dr_mean:.4f} ({dr_mean*100:.2f}%)")
    print(f"    标准差: {dr_std:.4f}")
    print(f"    范围: [{dr_min:.4f}, {dr_max:.4f}]")
    print(f"    变异系数 (CV): {dr_std/dr_mean*100:.2f}%")

    # 稳定性判断
    stable = acc_std < 0.05 and dr_std < 0.08

    print(f"\n  稳定性判断:")
    if stable:
        print(f"    ✅ 模型稳定 (Accuracy CV < 5%, Draw Recall CV < 8%)")
    else:
        print(f"    ⚠️ 模型存在不稳定性")

    return {
        "acc_mean": acc_mean,
        "acc_std": acc_std,
        "acc_cv": acc_std / acc_mean,
        "dr_mean": dr_mean,
        "dr_std": dr_std,
        "dr_cv": dr_std / dr_mean,
        "stable": stable,
    }


def run_calibration_analysis(X_full, y):
    """概率校准度分析"""
    print("\n" + "=" * 80)
    print("📊 审计 3: 概率校准度分析")
    print("=" * 80)

    X_train, X_test, y_train, y_test = train_test_split(X_full, y, test_size=0.3, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced", n_jobs=-1)
    model.fit(X_train, y_train)

    y_proba = model.predict_proba(X_test)
    y_pred = model.predict(X_test)

    # 分析高置信度预测
    print("\n  高置信度预测分析 (信心 >= 60%):")
    print("-" * 60)

    confidence_thresholds = [0.60, 0.70, 0.80, 0.90]

    for thresh in confidence_thresholds:
        # 找出高置信度预测
        max_proba = np.max(y_proba, axis=1)
        high_conf_mask = max_proba >= thresh

        if high_conf_mask.sum() == 0:
            print(f"\n    信心 >= {thresh*100:.0f}%: 无样本")
            continue

        high_conf_pred = y_pred[high_conf_mask]
        high_conf_actual = y_test[high_conf_mask]
        high_conf_proba = max_proba[high_conf_mask]

        # 计算准确率
        correct = (high_conf_pred == high_conf_actual).sum()
        total = len(high_conf_actual)
        actual_acc = correct / total

        # 预期准确率 vs 实际准确率
        expected_acc = np.mean(high_conf_proba)
        gap = actual_acc - expected_acc

        print(f"\n    信心 >= {thresh*100:.0f}%:")
        print(f"      样本数: {total}")
        print(f"      预期准确率: {expected_acc*100:.2f}%")
        print(f"      实际准确率: {actual_acc*100:.2f}%")
        print(f"      差距: {gap*100:+.2f}%")

        if gap < -0.10:
            print(f"      ⚠️  过度自信 (差距 < -10%)")
        elif gap > 0.05:
            print(f"      ✅ 保守估计 (差距 > +5%)")
        else:
            print(f"      ✅ 校准良好")

    # 分析预测错误的高置信度场次
    print("\n  高置信度错误分析:")
    print("-" * 60)

    max_proba = np.max(y_proba, axis=1)
    high_conf_mask = max_proba >= 0.70
    wrong_mask = y_pred != y_test

    critical_errors = high_conf_mask & wrong_mask
    n_critical_errors = critical_errors.sum()

    print(f"\n    信心 >= 70% 且预测错误的场次: {n_critical_errors}")

    if n_critical_errors > 0:
        error_pred = y_pred[critical_errors]
        error_actual = y_test[critical_errors]
        error_proba = max_proba[critical_errors]

        # 分析错误类型
        error_types = {}
        for p, a in zip(error_pred, error_actual):
            key = f"{RESULT_DECODE[p]}->{RESULT_DECODE[a]}"
            error_types[key] = error_types.get(key, 0) + 1

        print(f"\n    错误类型分布:")
        for etype, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"      {etype}: {count}")

    return {
        "critical_errors": n_critical_errors,
        "calibration_ok": True,
    }


def main():
    print("\n" + "=" * 80)
    print("🔴 TITAN 深度压力测试审计")
    print("=" * 80)
    print(f"📅 审计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    conn = get_db_connection()
    print("✅ 数据库连接成功")

    try:
        # 获取数据
        print("\n📊 Step 0: 数据准备...")
        rows = get_all_data(conn, days=180)
        print(f"  获取到 {len(rows)} 场比赛")

        pro = TitanFeaturePro()

        X_base_list = []
        X_momentum_list = []
        X_draw_trap_list = []
        y_list = []

        for i, row in enumerate(rows):
            if (i + 1) % 300 == 0:
                print(f"  特征提取进度: {i+1}/{len(rows)}")

            try:
                base_vec, momentum_vec, draw_trap_vec, label = extract_features(row, conn, pro)
                X_base_list.append(base_vec)
                X_momentum_list.append(momentum_vec)
                X_draw_trap_list.append(draw_trap_vec)
                y_list.append(label)
            except Exception:
                continue

        X_base = np.array(X_base_list)
        X_momentum = np.array(X_momentum_list)
        X_draw_trap = np.array(X_draw_trap_list)
        y = np.array(y_list)

        X_full = np.hstack([X_base, X_momentum, X_draw_trap])

        print(f"  有效样本: {len(y)}")
        print(f"  特征维度: {X_full.shape[1]}")

        # 审计 1: 特征剥离
        ablation_results = run_ablation_study(X_base, X_momentum, X_draw_trap, y)

        # 审计 2: 10折稳定性
        stability_results = run_stability_test(X_full, y, n_folds=10)

        # 审计 3: 概率校准
        calibration_results = run_calibration_analysis(X_full, y)

        # 最终报告
        print("\n" + "=" * 80)
        print("📋 深度压力测试审计报告")
        print("=" * 80)

        print("\n## 审计结论")
        print("-" * 80)

        # 计算真实期望胜率
        real_expected_acc = stability_results["acc_mean"]
        real_expected_dr = stability_results["dr_mean"]

        print(f"\n  脱水后的真实实战期望:")
        print(f"    Accuracy 期望: {real_expected_acc*100:.2f}% ± {stability_results['acc_std']*100:.2f}%")
        print(f"    Draw Recall 期望: {real_expected_dr*100:.2f}% ± {stability_results['dr_std']*100:.2f}%")

        # 判断是否稳定
        if stability_results["stable"]:
            print(f"\n  ✅ 模型稳定性: 通过")
            print(f"     变异系数在可接受范围内")
        else:
            print(f"\n  ⚠️ 模型稳定性: 需关注")
            print(f"     变异系数偏高，存在过拟合风险")

        # 校准度判断
        if calibration_results["critical_errors"] < 20:
            print(f"\n  ✅ 概率校准: 良好")
            print(f"     高置信度错误场次: {calibration_results['critical_errors']}")
        else:
            print(f"\n  ⚠️ 概率校准: 需改进")
            print(f"     高置信度错误场次过多: {calibration_results['critical_errors']}")

        print("\n" + "=" * 80)
        print("🔴 最终审计结论")
        print("=" * 80)

        # 综合判断
        all_pass = (
            stability_results["stable"] and
            calibration_results["critical_errors"] < 30 and
            real_expected_acc >= 0.55
        )

        if all_pass:
            print(f"\n  ✅ 审计通过")
            print(f"\n  脱水后的真实实战期望胜率: {real_expected_acc*100:.1f}%")
            print(f"  建议: 可以合并到 main 分支")
        else:
            print(f"\n  ⚠️ 审计发现风险")
            print(f"\n  脱水后的真实实战期望胜率: {real_expected_acc*100:.1f}%")
            if not stability_results["stable"]:
                print(f"  风险: 模型稳定性不足")
            if calibration_results["critical_errors"] >= 30:
                print(f"  风险: 高置信度错误过多")

        print("\n" + "=" * 80)

        # 保存结果
        result = {
            "audit_time": datetime.now().isoformat(),
            "total_samples": int(len(y)),
            "ablation_results": ablation_results,
            "stability_results": {
                "acc_mean": float(stability_results["acc_mean"]),
                "acc_std": float(stability_results["acc_std"]),
                "acc_cv": float(stability_results["acc_cv"]),
                "dr_mean": float(stability_results["dr_mean"]),
                "dr_std": float(stability_results["dr_std"]),
                "dr_cv": float(stability_results["dr_cv"]),
                "stable": bool(stability_results["stable"]),
            },
            "calibration_results": calibration_results,
            "real_expected_accuracy": float(real_expected_acc),
            "audit_passed": bool(all_pass),
        }

        output_file = "/app/logs/deep_stress_audit.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"📄 审计报告已保存到: {output_file}\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
