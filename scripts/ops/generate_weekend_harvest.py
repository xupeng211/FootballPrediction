#!/usr/bin/env python3
"""
TITAN V5.0 周末收割清单生成器
=============================

输出符合58%阈值过滤后的Top 10黄金信号

@module scripts.ops.generate_weekend_harvest
@version V5.0.0-PROD
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psycopg2

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.constants.model_config import TITAN_COMBAT_FEATURES, MODEL_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("weekend_harvest")

RESULT_NAMES = {0: "客胜", 1: "平局", 2: "主胜"}


def parse_jsonb(val):
    """解析JSONB数据"""
    import json
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    return json.loads(val)


def extract_features(row):
    """提取30维特征"""
    import math
    
    elo = parse_jsonb(row[3])
    golden = parse_jsonb(row[4])
    tactical = parse_jsonb(row[5])
    rolling = parse_jsonb(row[6])
    efficiency = parse_jsonb(row[7])
    draw = parse_jsonb(row[8])
    
    home_elo = float(row[15]) if len(row) > 15 and row[15] and row[15] != 1500 else float(elo.get('home_elo', 1500))
    away_elo = float(row[16]) if len(row) > 16 and row[16] and row[16] != 1500 else float(elo.get('away_elo', 1500))
    
    f = {}
    f['home_elo_pre'] = home_elo
    f['away_elo_pre'] = away_elo
    f['elo_diff'] = home_elo - away_elo
    f['expected_home_win'] = float(elo.get('expected_home_win', 0.45))
    f['expected_away_win'] = float(elo.get('expected_away_win', 0.30))
    
    home_mv = float(golden.get('home_market_value_total', 1e8))
    away_mv = float(golden.get('away_market_value_total', 1e8))
    f['log_home_squad_value'] = math.log10(home_mv) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5
    
    f['h2h_home_win_ratio'] = float(tactical.get('h2h_home_win_ratio', 0.4))
    f['h2h_draw_ratio'] = float(tactical.get('h2h_draw_ratio', 0.25))
    f['h2h_avg_goal_diff'] = float(tactical.get('h2h_avg_goal_diff', 0.0))
    
    f['home_last5_xg_avg'] = float(rolling.get('home_last5_xg_avg', 0.0))
    f['away_last5_xg_avg'] = float(rolling.get('away_last5_xg_avg', 0.0))
    f['home_last5_win_rate'] = float(rolling.get('home_last5_win_rate', 0.0))
    f['away_last5_win_rate'] = float(rolling.get('away_last5_win_rate', 0.0))
    f['home_last5_draw_rate'] = float(rolling.get('home_last5_draw_rate', 0.0))
    f['away_last5_draw_rate'] = float(rolling.get('away_last5_draw_rate', 0.0))
    f['rest_days_diff'] = float(rolling.get('rest_days_diff', 0.0))
    
    f['home_shot_conversion'] = float(efficiency.get('home_shot_conversion', 0.0))
    f['away_shot_conversion'] = float(efficiency.get('away_shot_conversion', 0.0))
    f['home_finishing_efficiency'] = float(efficiency.get('home_finishing_efficiency', 0.0))
    f['away_finishing_efficiency'] = float(efficiency.get('away_finishing_efficiency', 0.0))
    f['finishing_efficiency_diff'] = float(efficiency.get('finishing_efficiency_diff', 0.0))
    
    f['home_draw_rate'] = float(draw.get('home_draw_rate', 0.0))
    f['away_draw_rate'] = float(draw.get('away_draw_rate', 0.0))
    f['home_draw_tendency'] = float(draw.get('home_draw_tendency', 0.0))
    f['away_draw_tendency'] = float(draw.get('away_draw_tendency', 0.0))
    f['combined_draw_probability'] = float(draw.get('combined_draw_probability', 0.0))
    f['match_stalemate_index'] = float(draw.get('match_stalemate_index', 0.0))
    f['tactical_stalemate_index'] = float(draw.get('tactical_stalemate_index', 0.0))
    
    return f


def get_db_connection():
    """获取数据库连接"""
    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        raise ValueError("缺少环境变量: DB_PASSWORD")
    
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "host.docker.internal"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "football_db"),
        user=os.getenv("DB_USER", "football_user"),
        password=db_password
    )


def load_model():
    """加载生产模型"""
    model_path = MODEL_DIR / "TITAN_CORE_V5_PROD.joblib"
    scaler_path = MODEL_DIR / "TITAN_CORE_V5_PROD_scaler.joblib"
    
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    return model, scaler


def generate_harvest_list(threshold=0.58, top_n=10):
    """生成周末收割清单"""
    logger.info("=" * 70)
    logger.info("🏆 TITAN V5.0 周末黄金信号收割清单")
    logger.info("=" * 70)
    logger.info(f"概率阈值: {threshold} (预期准确率: 68.94%)")
    logger.info("=" * 70)
    
    # 加载模型
    model, scaler = load_model()
    
    # 获取未来48小时比赛
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT 
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_date,
            l.elo_features, l.golden_features, l.tactical_features,
            l.rolling_features, l.efficiency_features, l.draw_features,
            COALESCE(home_elo.elo_rating, 1500) as home_elo_real,
            COALESCE(away_elo.elo_rating, 1500) as away_elo_real,
            m.league_name
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        LEFT JOIN team_elo_ratings home_elo ON m.home_team = home_elo.team_name
        LEFT JOIN team_elo_ratings away_elo ON m.away_team = away_elo.team_name
        WHERE m.match_date >= NOW()
          AND m.match_date <= NOW() + INTERVAL '48 hours'
          AND m.status = 'Harvested'
        ORDER BY m.match_date
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    logger.info(f"未来48小时比赛总数: {len(rows)}")
    
    # 预测所有比赛
    predictions = []
    
    for row in rows:
        try:
            features = extract_features(row)
            X = pd.DataFrame([features], columns=TITAN_COMBAT_FEATURES)
            X_scaled = scaler.transform(X)
            
            proba = model.predict_proba(X_scaled)[0]
            pred_class = np.argmax(proba)
            max_proba = np.max(proba)
            
            # 只保留高置信度信号
            if max_proba >= threshold:
                elo_diff = features['elo_diff']
                
                predictions.append({
                    'match_id': row[0],
                    'home_team': row[1],
                    'away_team': row[2],
                    'match_time': row[3].strftime('%m-%d %H:%M'),
                    'league': row[12] if len(row) > 12 else 'Unknown',
                    'prediction': RESULT_NAMES[pred_class],
                    'confidence': max_proba,
                    'elo_diff': elo_diff,
                    'proba_away': proba[0],
                    'proba_draw': proba[1],
                    'proba_home': proba[2]
                })
        except Exception as e:
            logger.warning(f"预测失败 [{row[0]}]: {e}")
    
    # 按置信度排序
    predictions.sort(key=lambda x: x['confidence'], reverse=True)
    
    logger.info(f"符合阈值({threshold})的比赛: {len(predictions)}")
    logger.info("")
    
    # 输出Top N
    print("\n" + "=" * 90)
    print("🏆 TITAN V5.0 周末黄金信号收割清单")
    print("=" * 90)
    print(f"{'排名':<4} {'联赛':<12} {'对阵':<35} {'预测':<6} {'置信度':<8} {'战力差':<8}")
    print("-" * 90)
    
    for i, pred in enumerate(predictions[:top_n], 1):
        matchup = f"{pred['home_team']} vs {pred['away_team']}"
        if len(matchup) > 33:
            matchup = matchup[:30] + "..."
        
        elo_sign = "+" if pred['elo_diff'] > 0 else ""
        print(f"{i:<4} {pred['league']:<12} {matchup:<35} {pred['prediction']:<6} "
              f"{pred['confidence']*100:>6.1f}%  {elo_sign}{pred['elo_diff']:.0f}")
    
    print("=" * 90)
    print(f"\n✅ 以上 {min(top_n, len(predictions))} 场比赛符合 TITAN V5.0 黄金信号标准")
    print(f"   概率阈值: {threshold} | 预期准确率: ~69% | 盈亏平衡点: 赔率 > 1.45")
    print("=" * 90)
    
    return predictions[:top_n]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.58, help='概率阈值')
    parser.add_argument('--top-n', type=int, default=10, help='Top N数量')
    args = parser.parse_args()
    
    generate_harvest_list(threshold=args.threshold, top_n=args.top_n)
