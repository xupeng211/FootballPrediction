#!/usr/bin/env python3
"""
TITAN 模型深度审计脚本
审计主场偏见、特征权重、决策边界
"""

import sys
import os
sys.path.insert(0, '/app')

import json
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
import joblib

# 数据库连接
def get_db_connection():
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

def load_model():
    """加载模型"""
    model_path = '/app/models/titan_v4466.joblib'
    scaler_path = '/app/models/titan_v4466_scaler.joblib'
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    return model, scaler

def load_training_data():
    """加载训练数据"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT
        m.match_id,
        m.home_team,
        m.away_team,
        m.actual_result,
        l.elo_features,
        l.odds_features
    FROM matches m
    INNER JOIN l3_features l ON m.match_id = l.match_id
    WHERE m.status = 'finished'
      AND m.actual_result IN ('H', 'D', 'A')
      AND l.elo_features IS NOT null
    ORDER BY RANDOM()
    LIMIT 1000
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows

def extract_features_for_audit(row):
    """提取特征"""
    from scripts.ops.predict_pipeline import extract_pre_match_features

    elo_data = row['elo_features']
    odds_data = row['odds_features']

    return extract_pre_match_features(elo_data, odds_data)

def main():
    print("=" * 80)
    print("TITAN-V4.46.6 模型深度审计报告")
    print("=" * 80)

    # 1. 加载模型
    model, scaler = load_model()
    print("✅ 模型和 Scaler 加载成功")

    # 2. 加载训练数据
    print("\n📊 加载训练数据...")
    rows = load_training_data()
    print(f"✅ 加载了 {len(rows)} 场训练数据")

    # 3. 统计训练集标签分布
    labels = [row['actual_result'] for row in rows]
    h_count = labels.count('H')
    d_count = labels.count('D')
    a_count = labels.count('A')
    print(f"\n📊 训练集标签分布:")
    print(f"   主胜: {h_count} ({h_count/len(labels)*100:.1f}%)")
    print(f"   平局: {d_count} ({d_count/len(labels)*100:.1f}%)")
    print(f"   客胜: {a_count} ({a_count/len(labels)*100:.1f}%)")

    # 4. 提取特征并预测
    features_list = []
    for row in rows:
        features = extract_features_for_audit(row)
        features_list.append(features)

    # 构建特征矩阵
    feature_names = [
        'home_elo_pre', 'away_elo_pre', 'elo_diff', 'expected_home_win', 'expected_away_win',
        'initial_home_odds', 'initial_draw_odds', 'initial_away_odds',
        'implied_prob_home', 'implied_prob_draw', 'implied_prob_away',
        'odds_ratio_home_away', 'elo_odds_home_diff'
    ]
    X = np.array([[f.get(name, 0.0) for name in feature_names] for f in features_list])
    X_scaled = scaler.transform(X)
    probs = model.predict_proba(X_scaled)
    preds = np.argmax(probs, axis=1)

    # 5. 模型预测分布
    pred_h = np.sum(preds == 2)
    pred_d = np.sum(preds == 1)
    pred_a = np.sum(preds == 0)

    print(f"\n🤖 模型预测分布:")
    print(f"   主胜: {pred_h} ({pred_h/len(preds)*100:.1f}%)")
    print(f"   平局: {pred_d} ({pred_d/len(preds)*100:.1f}%)")
    print(f"   客胜: {pred_a} ({pred_a/len(preds)*100:.1f}%)")

    # 6. Baseline 分析
    baseline_acc = max(h_count, d_count, a_count) / len(labels)
    model_acc = accuracy_score([{'H': 2, 'D': 1, 'A': 0}[l] for l in labels], preds)
    print(f"\n📈 Baseline 分析:")
    print(f"   无脑猜主胜准确率: {baseline_acc:.2%}")
    print(f"   模型准确率: {model_acc:.2%}")
    print(f"   提升: {(model_acc - baseline_acc)*100:.2f}%")

    # 7. 特征重要性
    print(f"\n📊 特征重要性排名:")
    importance = model.feature_importances_
    for i, (name, imp) in enumerate(sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)):
        print(f"   {i+1}. {name}: {imp:.4f}")

    # 8. 赔率数据审计
    print(f"\n💰 赔率数据审计:")
    home_odds_values = [f['initial_home_odds'] for f in features_list]
    unique_home_odds = set(home_odds_values)
    print(f"   主胜赔率唯一值数量: {len(unique_home_odds)}")
    print(f"   默认值 (2.2) 占比: {home_odds_values.count(2.2) / len(home_odds_values) * 100:.1f}%")

    # 检查赔率是否都是默认值
    if len(unique_home_odds) == 1:
        print(f"   ⚠️ 所有赔率都是默认值！赔率特征实际上是常数！")

    # 9. 决策边界分析 - 找出预测为客胜的样本
    away_indices = np.where(preds == 0)[0]
    if len(away_indices) > 0:
        print(f"\n🔍 决策边界分析 - 客胜预测样本 ({len(away_indices)} 个):")
        for idx in away_indices[:5]:
            row = rows[idx]
            features = features_list[idx]
            print(f"\n   样本 {idx+1}: {row['home_team']} vs {row['away_team']}")
            print(f"      实际结果: {row['actual_result']}")
            print(f"      Elo 差: {features['elo_diff']:.1f}")
            print(f"      预测概率: 主{probs[idx][2]:.1%} 平{probs[idx][1]:.1%} 客{probs[idx][0]:.1%}")
    else:
        print(f"\n   ⚠️ 模型从未预测过客胜！")

    # 10. 找出预测为平局的样本
    draw_indices = np.where(preds == 1)[0]
    if len(draw_indices) > 0:
        print(f"\n🔍 决策边界分析 - 平局预测样本 ({len(draw_indices)} 个):")
        for idx in draw_indices[:5]:
            row = rows[idx]
            features = features_list[idx]
            print(f"\n   样本 {idx+1}: {row['home_team']} vs {row['away_team']}")
            print(f"      实际结果: {row['actual_result']}")
            print(f"      Elo 差: {features['elo_diff']:.1f}")
            print(f"      预测概率: 主{probs[idx][2]:.1%} 平{probs[idx][1]:.1%} 客{probs[idx][0]:.1%}")
    else:
        print(f"\n   ⚠️ 模型从未预测过平局！")

    # 11. Elo 差值分析
    print(f"\n📊 Elo 差值与预测关系:")
    elo_diffs = [f['elo_diff'] for f in features_list]

    # 分组统计
    for threshold in [50, 100, 150, 200]:
        high_elo = [(i, d, preds[i], labels[i]) for i, d in enumerate(elo_diffs) if d > threshold]
        if high_elo:
            pred_h_high = sum(1 for _, _, p, _ in high_elo if p == 2)
            actual_h_high = sum(1 for _, _, _, a in high_elo if a == 'H')
            print(f"   Elo差 > {threshold}: {len(high_elo)} 场")
            print(f"      预测主胜: {pred_h_high} ({pred_h_high/len(high_elo)*100:.1f}%)")
            print(f"      实际主胜: {actual_h_high} ({actual_h_high/len(high_elo)*100:.1f}%)")

    # 最终评级
    print("\n" + "=" * 80)
    print("📋 模型可靠性评级")
    print("=" * 80)

if __name__ == '__main__':
    main()
