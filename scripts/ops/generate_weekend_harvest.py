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
    if isinstance(val, str):
        return json.loads(val)
    # 处理其他类型（如datetime）返回空dict
    return {}


def extract_features(row):
    """提取30维特征"""
    import math
    
    elo = parse_jsonb(row.get('elo_features'))
    golden = parse_jsonb(row.get('golden_features'))
    tactical = parse_jsonb(row.get('tactical_features'))
    rolling = parse_jsonb(row.get('rolling_features'))
    efficiency = parse_jsonb(row.get('efficiency_features'))
    draw = parse_jsonb(row.get('draw_features'))
    
    # 优先使用JOIN得到的真实ELO
    home_elo = float(row.get('home_elo_real', 1500))
    away_elo = float(row.get('away_elo_real', 1500))
    
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
    
    # 获取真实ELO数据 - 只选当前赛季20252026
    cur.execute("""
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
          AND m.match_id LIKE '%_20252026_%'
        ORDER BY m.match_date
    """)
    
    # 获取列名
    colnames = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # 转换为字典列表
    dict_rows = []
    for row in rows:
        dict_row = {}
        for i, col in enumerate(colnames):
            dict_row[col] = row[i]
        dict_rows.append(dict_row)
    
    logger.info(f"未来48小时比赛总数: {len(rows)}")
    
    # 预测所有比赛 - 按match_id去重
    predictions = []
    seen_match_ids = set()
    
    for row in dict_rows:
        match_id = row.get('match_id')
        if match_id in seen_match_ids:
            continue
        seen_match_ids.add(match_id)
        
        try:
            features = extract_features(row)
            X = pd.DataFrame([features], columns=TITAN_COMBAT_FEATURES)
            X_scaled = scaler.transform(X)
            
            proba = model.predict_proba(X_scaled)[0]
            pred_class = np.argmax(proba)
            max_proba = np.max(proba)
            
            # 只保留高置信度信号
            if max_proba >= threshold:
                # 直接从row获取真实ELO（因为JSONB中的elo_features可能为空）
                home_elo_real = float(row.get('home_elo_real', 1500))
                away_elo_real = float(row.get('away_elo_real', 1500))
                elo_diff = home_elo_real - away_elo_real
                
                # 更新features中的ELO值
                features['home_elo_pre'] = home_elo_real
                features['away_elo_pre'] = away_elo_real
                features['elo_diff'] = elo_diff
                
                # 分析特征关键点
                key_factors = []
                if features['h2h_home_win_ratio'] > 0.6:
                    key_factors.append("H2H压制")
                if abs(elo_diff) > 100:
                    key_factors.append("战力代差" if elo_diff > 0 else "战力劣势")
                if features['home_last5_win_rate'] > 0.6:
                    key_factors.append("状态火热")
                if features['home_last5_xg_avg'] > 1.5:
                    key_factors.append("进攻强劲")
                if features['match_stalemate_index'] > 0.8:
                    key_factors.append("僵局风险")
                if features['home_mv_share'] > 0.65:
                    key_factors.append("身价碾压")
                
                key_factor_str = " | ".join(key_factors[:2]) if key_factors else "综合优势"
                
                # 凯利准则计算仓位
                p = max_proba  # 模型胜率
                b = 0.8        # 平均赔率假设为1.80 (净赔率0.80)
                kelly_fraction = (p * (1 + b) - 1) / b if b > 0 else 0
                kelly_fraction = max(0.01, min(0.025, kelly_fraction * 0.25))  # 保守1/4凯利，限制1%-2.5%
                
                match_date = row.get('match_date')
                match_time_str = match_date.strftime('%m-%d %H:%M') if hasattr(match_date, 'strftime') else str(match_date)
                
                predictions.append({
                    'match_id': row.get('match_id'),
                    'home_team': row.get('home_team'),
                    'away_team': row.get('away_team'),
                    'match_time': match_time_str,
                    'league': row.get('league_name', 'Unknown'),
                    'prediction': RESULT_NAMES[pred_class],
                    'confidence': max_proba,
                    'elo_diff': elo_diff,
                    'proba_away': proba[0],
                    'proba_draw': proba[1],
                    'proba_home': proba[2],
                    'key_factors': key_factor_str,
                    'kelly_stake': kelly_fraction
                })
        except Exception as e:
            logger.warning(f"预测失败 [{row[0]}]: {e}")
    
    # 按置信度排序
    predictions.sort(key=lambda x: x['confidence'], reverse=True)
    
    logger.info(f"符合阈值({threshold})的比赛: {len(predictions)}")
    logger.info("")
    
    # 输出Top N
    print("\n" + "=" * 110)
    print("🏆 TITAN V5.0 周末黄金信号收割清单")
    print("=" * 110)
    print(f"{'排名':<4} {'联赛':<12} {'对阵':<30} {'预测':<6} {'置信度':<8} {'战力差':<8} {'核心因子':<20} {'仓位':<6}")
    print("-" * 110)
    
    for i, pred in enumerate(predictions[:top_n], 1):
        matchup = f"{pred['home_team']} vs {pred['away_team']}"
        if len(matchup) > 28:
            matchup = matchup[:25] + "..."
        
        elo_sign = "+" if pred['elo_diff'] > 0 else ""
        kelly_pct = pred.get('kelly_stake', 0.01) * 100
        print(f"{i:<4} {pred['league']:<12} {matchup:<30} {pred['prediction']:<6} "
              f"{pred['confidence']*100:>6.1f}%  {elo_sign}{pred['elo_diff']:<7.0f} {pred.get('key_factors', ''):<20} {kelly_pct:>5.1f}%")
    
    print("=" * 110)
    print(f"\n✅ 以上 {min(top_n, len(predictions))} 场比赛符合 TITAN V5.0 黄金信号标准")
    print(f"   概率阈值: {threshold} | 预期胜率: {max_proba*100:.1f}% | 仓位计算: 1/4凯利准则 (保守)")
    print(f"   盈亏平衡: 赔率 > {1/max_proba:.2f} | 建议资金: 100单位本金")
    print("=" * 110)
    
    return predictions[:top_n]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.58, help='概率阈值')
    parser.add_argument('--top-n', type=int, default=10, help='Top N数量')
    args = parser.parse_args()
    
    generate_harvest_list(threshold=args.threshold, top_n=args.top_n)
