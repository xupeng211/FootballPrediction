#!/usr/bin/env python3
"""
TITAN-V4.46.6 战斗训练管道
===========================

11维纯净特征集:
- Elo 核心 (5项)
- 金钱力量 (3项)
- 历史压制 (3项)

@version V4.46.6-COMBAT
"""

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, log_loss
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# 添加 os 模块
import posixpath
from posix import environ

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

RESULT_MAP = {"H": 2, "D": 1, "A": 0}
RESULT_NAMES = ["AWAY", "DRAW", "HOME"]

# 11维战斗特征集
TITAN_COMBAT_FEATURES = [
    "home_elo_pre", "away_elo_pre", "elo_diff", "expected_home_win", "expected_away_win",
    "log_home_squad_value", "log_away_squad_value", "home_mv_share",
    "h2h_home_win_ratio", "h2h_draw_ratio", "h2h_avg_goal_diff",
]

DEFAULT_VALUES = {
    "home_elo_pre": 1500.0, "away_elo_pre": 1500.0, "elo_diff": 0.0,
    "expected_home_win": 0.45, "expected_away_win": 0.30,
    "log_home_squad_value": 18.0, "log_away_squad_value": 18.0, "home_mv_share": 0.50,
    "h2h_home_win_ratio": 0.40, "h2h_draw_ratio": 0.25, "h2h_avg_goal_diff": 0.0,
}


def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d


def safe_log10(v, d=0.0):
    try: return math.log10(v) if v and v > 0 else d
    except: return d


def parse_jsonb(d):
    if not d: return {}
    if isinstance(d, str):
        try: return json.loads(d)
        except: return {}
    return d if isinstance(d, dict) else {}


def extract_features(elo_data, lineup_data, h2h_data):
    """提取11维战斗特征"""
    f = {}
    elo = parse_jsonb(elo_data)
    lineup = parse_jsonb(lineup_data)
    h2h = parse_jsonb(h2h_data)

    # Elo (5)
    home_elo = safe_float(elo.get('home_elo_pre', elo.get('home_elo', 1500)), 1500)
    away_elo = safe_float(elo.get('away_elo_pre', elo.get('away_elo', 1500)), 1500)
    f['home_elo_pre'] = home_elo
    f['away_elo_pre'] = away_elo
    f['elo_diff'] = safe_float(elo.get('elo_diff', home_elo - away_elo))
    f['expected_home_win'] = safe_float(elo.get('expected_home_win', 0.45))
    f['expected_away_win'] = safe_float(elo.get('expected_away_win', 0.30))

    # 身价 (3) - 从 lineup 获取
    home_mv = safe_float(lineup.get('home_squad_value_eur', 0), 0)
    away_mv = safe_float(lineup.get('away_squad_value_eur', 0), 0)
    f['log_home_squad_value'] = safe_log10(home_mv, 18.0) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = safe_log10(away_mv, 18.0) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

    # H2H (3)
    f['h2h_home_win_ratio'] = safe_float(h2h.get('h2h_home_win_ratio', h2h.get('home_win_ratio', 0.4)), 0.4)
    f['h2h_draw_ratio'] = safe_float(h2h.get('h2h_draw_ratio', h2h.get('draw_ratio', 0.25)), 0.25)
    f['h2h_avg_goal_diff'] = safe_float(h2h.get('h2h_avg_goal_diff', h2h.get('avg_goal_diff', 0)), 0)

    # 填充默认值
    return {k: f.get(k, DEFAULT_VALUES.get(k, 0.0)) for k in TITAN_COMBAT_FEATURES}


def get_db():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )


def load_data(conn):
    """加载纯净训练数据"""
    query = """
    SELECT m.match_id, m.actual_result, m.league_name,
           l.elo_features, l.lineup_features, l.h2h_features
    FROM matches m
    INNER JOIN l3_features l ON m.match_id = l.match_id
    WHERE m.status = 'finished'
      AND m.actual_result IN ('H', 'D', 'A')
      AND l.elo_features IS NOT NULL AND l.elo_features != '{}'::jsonb
      AND l.lineup_features IS NOT NULL AND l.lineup_features != '{}'::jsonb
      AND l.h2h_features IS NOT NULL AND l.h2h_features != '{}'::jsonb
    ORDER BY m.match_date ASC
    """
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()

    logger.info(f"加载 {len(rows)} 条纯净训练记录")

    features_list, labels, league_counts = [], [], {}
    for row in rows:
        f = extract_features(row['elo_features'], row['lineup_features'], row['h2h_features'])
        features_list.append(f)
        labels.append(RESULT_MAP[row['actual_result']])
        ln = row['league_name']
        league_counts[ln] = league_counts.get(ln, 0) + 1

    X = pd.DataFrame(features_list)[TITAN_COMBAT_FEATURES]
    y = pd.Series(labels, name='result')

    logger.info(f"标签分布: H={sum(y==2)}, D={sum(y==1)}, A={sum(y==0)}")
    for ln, cnt in sorted(league_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {ln}: {cnt} 场")

    return X, y, league_counts


def train_model(X, y, cv_folds=5):
    """XGBoost 300轮训练"""
    logger.info("开始 XGBoost 300轮深度训练...")
    start = datetime.now()

    X = X.fillna(0).replace([np.inf, -np.inf], 0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # 类别权重 (纠正主场偏见)
    weights = np.ones(len(y_train))
    for i, v in enumerate(y_train):
        if v == 1: weights[i] = 1.2  # 平局
        elif v == 0: weights[i] = 1.1  # 客胜

    model = xgb.XGBClassifier(
        objective='multi:softprob', num_class=3,
        max_depth=5, learning_rate=0.05, n_estimators=300,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1,
        early_stopping_rounds=50
    )

    model.fit(X_train_s, y_train, sample_weight=weights,
              eval_set=[(X_train_s, y_train), (X_test_s, y_test)], verbose=False)

    # 5-Fold CV
    logger.info(f"执行 {cv_folds} 折交叉验证...")
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    cv_scores = []
    for fold, (ti, vi) in enumerate(skf.split(X, y)):
        X_tr, X_val = X.iloc[ti], X.iloc[vi]
        y_tr, y_val = y.iloc[ti], y.iloc[vi]
        sc = StandardScaler()
        X_tr_s, X_val_s = sc.fit_transform(X_tr), sc.transform(X_val)
        m = xgb.XGBClassifier(objective='multi:softprob', num_class=3,
                              max_depth=5, learning_rate=0.05, n_estimators=300,
                              random_state=42, verbosity=0)
        m.fit(X_tr_s, y_tr, eval_set=[(X_val_s, y_val)], verbose=False)
        cv_scores.append(accuracy_score(y_val, m.predict(X_val_s)))
        logger.info(f"  Fold {fold+1}: {cv_scores[-1]:.4f}")

    # 测试集评估
    y_pred = model.predict(X_test_s)
    y_proba = model.predict_proba(X_test_s)

    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred, average='weighted'),
        'log_loss': log_loss(y_test, y_proba),
        'cv_mean': np.mean(cv_scores),
        'cv_std': np.std(cv_scores),
        'train_samples': len(X_train),
        'train_time': (datetime.now() - start).total_seconds(),
        'feature_importance': dict(sorted(zip(TITAN_COMBAT_FEATURES, model.feature_importances_),
                                          key=lambda x: -x[1])),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'report': classification_report(y_test, y_pred, target_names=RESULT_NAMES)
    }

    logger.info(f"训练完成! 耗时: {metrics['train_time']:.1f}s")
    logger.info(f"准确率: {metrics['accuracy']:.4f} | CV: {metrics['cv_mean']:.4f} (+/- {metrics['cv_std']:.4f})")

    return model, scaler, metrics


def save_model(model, scaler, metrics, name="titan_v4466_combat_ready"):
    """保存模型"""
    model_path = MODEL_DIR / f"{name}.joblib"
    scaler_path = MODEL_DIR / f"{name}_scaler.joblib"
    joblib.dump(model, str(model_path))
    joblib.dump(scaler, str(scaler_path))

    meta = {
        'version': 'V4.46.6-COMBAT', 'created_at': datetime.now().isoformat(),
        'feature_names': TITAN_COMBAT_FEATURES, 'scaler_path': str(scaler_path),
        'metrics': {k: v for k, v in metrics.items() if k not in ['confusion_matrix', 'report', 'feature_importance']},
        'feature_importance': {k: float(v) for k, v in metrics['feature_importance'].items()}
    }
    with open(MODEL_DIR / f"{name}_metadata.json", 'w') as f:
        json.dump(meta, f, indent=2)

    logger.info(f"模型已保存: {model_path}")
    return str(model_path), str(scaler_path)


def predict_upcoming(conn, model, scaler, limit=5):
    """预测即将开始的比赛"""
    query = f"""
    SELECT m.match_id, m.home_team, m.away_team, m.league_name, m.match_date,
           l.elo_features, l.lineup_features, l.h2h_features
    FROM matches m
    INNER JOIN l3_features l ON m.match_id = l.match_id
    WHERE m.match_date > NOW() AND m.match_date < NOW() + INTERVAL '7 days'
      AND l.elo_features IS NOT NULL
    ORDER BY m.match_date ASC LIMIT {limit}
    """
    cur = conn.cursor()
    cur.execute(query)
    matches = cur.fetchall()
    cur.close()

    if not matches:
        return []

    preds = []
    for m in matches:
        try:
            f = extract_features(m['elo_features'], m['lineup_features'], m['h2h_features'])
            vec = np.array([[f.get(n, 0) for n in TITAN_COMBAT_FEATURES]])
            vec_s = scaler.transform(vec)
            probs = model.predict_proba(vec_s)[0]

            rec = "HOME" if probs[2] >= probs[1] and probs[2] >= probs[0] else \
                  "DRAW" if probs[1] >= probs[0] else "AWAY"
            conf = max(probs)

            preds.append({
                'home': m['home_team'], 'away': m['away_team'],
                'league': m['league_name'], 'time': str(m['match_date'])[:16],
                'probs': {'H': f"{probs[2]*100:.1f}%", 'D': f"{probs[1]*100:.1f}%", 'A': f"{probs[0]*100:.1f}%"},
                'rec': rec, 'conf': f"{conf*100:.1f}%",
                'elo_diff': f.get('elo_diff', 0), 'mv_share': f.get('home_mv_share', 0.5)
            })
        except Exception as e:
            logger.warning(f"预测失败: {e}")

    return preds


def main():
    logger.info("")
    logger.info("=" * 70)
    logger.info("  TITAN-V4.46.6 战斗训练管道")
    logger.info("  特征: 11维纯净 (Elo + 身价 + H2H)")
    logger.info("  迭代: 300轮 | 深度: 5 | CV: 5折")
    logger.info("=" * 70)

    conn = get_db()
    try:
        X, y, league_counts = load_data(conn)
        model, scaler, metrics = train_model(X, y)
        model_path, scaler_path = save_model(model, scaler, metrics)

        # 打印特征重要性
        print("\n" + "=" * 70)
        print("  特征重要性 Top 10")
        print("=" * 70)
        for i, (name, imp) in enumerate(list(metrics['feature_importance'].items())[:10], 1):
            bar = "█" * int(imp * 50)
            print(f"  {i:2d}. {name.ljust(25)} {imp:.4f} {bar}")

        # 实战试射
        preds = predict_upcoming(conn, model, scaler)
        print("\n" + "=" * 70)
        print("  实战试射报告")
        print("=" * 70)
        if not preds:
            print("  无即将开始的比赛")
        else:
            for i, p in enumerate(preds, 1):
                print(f"\n  {i}. {p['home']} vs {p['away']}")
                print(f"     联赛: {p['league']} | 时间: {p['time']}")
                print(f"     概率: 主{p['probs']['H']} 平{p['probs']['D']} 客{p['probs']['A']}")
                print(f"     Elo差: {p['elo_diff']:+.1f} | 身价占比: {p['mv_share']:.1%}")
                print(f"     推荐: {p['rec']} (置信度: {p['conf']})")

        print("\n" + "=" * 70)
        print("  训练完成!")
        print(f"  准确率: {metrics['accuracy']:.2%}")
        print(f"  CV: {metrics['cv_mean']:.2%} (+/- {metrics['cv_std']:.2%})")
        print(f"  样本: {metrics['train_samples']}")
        print("=" * 70 + "\n")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
