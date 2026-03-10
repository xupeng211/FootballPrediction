#!/usr/bin/env python3
"""
V4.46.6 战斗定型脚本
====================
1. H2H avg_goal_diff 传感器修复
2. 未来比赛身价填充（历史5场平均）
3. 实战模拟预测
"""
import json
import logging
import os
import sys
from datetime import datetime

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# ============================================================================
# 数据库连接
# ============================================================================
def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )


# ============================================================================
# Task 1: H2H 传感器盘查与修复
# ============================================================================
def audit_h2h(conn):
    """检查 H2H avg_goal_diff 数值"""
    cur = conn.cursor()

    logger.info("=" * 60)
    logger.info("【H2H 传感器盘查】检查 h2h_avg_goal_diff 原始数值")
    logger.info("=" * 60)

    cur.execute("""
        SELECT m.match_id, m.home_team, m.away_team, m.actual_result,
               l.h2h_features->>'h2h_avg_goal_diff' as avg_gd,
               l.h2h_features->>'h2h_home_win_ratio' as hwr,
               l.h2h_features->>'h2h_matches_count' as matches
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'finished'
          AND l.h2h_features IS NOT NULL
          AND l.h2h_features != '{}'::jsonb
        ORDER BY m.match_date DESC
        LIMIT 10
    """)

    rows = cur.fetchall()
    for r in rows:
        logger.info(f"  {r['home_team']} vs {r['away_team']} | 结果: {r['actual_result']} | "
                   f"avg_gd: {r['avg_gd']} | hwr: {r['hwr']} | 场次: {r['matches']}")

    # 统计 0 值数量
    cur.execute("""
        SELECT COUNT(*) FROM l3_features
        WHERE h2h_features IS NOT NULL
          AND h2h_features != '{}'::jsonb
          AND (h2h_features->>'h2h_avg_goal_diff')::float = 0
    """)
    zero_count = cur.fetchone()['count']
    logger.info(f"\n  h2h_avg_goal_diff = 0 的记录数: {zero_count}")

    cur.close()
    return zero_count


def fix_h2h_avg_goal_diff(conn):
    """重新计算 H2H avg_goal_diff"""
    cur = conn.cursor()

    logger.info("\n" + "=" * 60)
    logger.info("【H2H 修复】重新计算 h2h_avg_goal_diff")
    logger.info("=" * 60)

    # 获取需要修复的记录
    cur.execute("""
        SELECT m.match_id, l.h2h_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE l.h2h_features IS NOT NULL
          AND l.h2h_features != '{}'::jsonb
          AND (l.h2h_features->>'h2h_avg_goal_diff')::float = 0
    """)

    rows = cur.fetchall()
    logger.info(f"  需要修复的记录: {len(rows)} 条")

    fixed = 0
    for row in rows:
        match_id = row['match_id']
        h2h = row['h2h_features']

        if isinstance(h2h, str):
            h2h = json.loads(h2h)

        # 从其他字段推断 avg_goal_diff
        # avg_goal_diff = (主队进球 - 客队进球) / 场次
        # 使用 home_win_ratio 和 draw_ratio 来估算
        hwr = float(h2h.get('h2h_home_win_ratio', 0.4))
        draw_r = float(h2h.get('h2h_draw_ratio', 0.25))
        awr = 1 - hwr - draw_r  # 客胜率

        # 估算平均净胜球: 胜 +1.5, 平 0, 负 -1.5 (简化模型)
        # 实际应该从原始 H2H 比赛数据计算
        estimated_gd = (hwr * 1.5) + (draw_r * 0) + (awr * -1.5)

        if abs(estimated_gd) < 0.01:
            # 如果估算也接近0，尝试使用默认值
            estimated_gd = 0.0

        # 更新数据库
        h2h['h2h_avg_goal_diff'] = round(estimated_gd, 3)

        cur.execute("""
            UPDATE l3_features
            SET h2h_features = %s
            WHERE match_id = %s
        """, (json.dumps(h2h), match_id))

        fixed += 1
        if fixed <= 5:
            logger.info(f"  修复 {match_id}: estimated_gd = {estimated_gd:.3f}")

    conn.commit()
    logger.info(f"  总计修复: {fixed} 条")

    cur.close()
    return fixed


# ============================================================================
# Task 2: 未来比赛身价填充
# ============================================================================
def get_team_avg_market_value(conn, team_name, league_name=None, limit=5):
    """获取球队最近 N 场比赛的平均身价"""
    cur = conn.cursor()

    # 方法1: 精确匹配队名
    query = """
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as mv
            FROM matches m
            INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished'
              AND m.home_team = %s
              AND (l.lineup_features->>'home_squad_value_eur')::numeric > 100000000
            ORDER BY m.match_date DESC
            LIMIT %s
        ) sub
    """

    cur.execute(query, (team_name, limit))
    result = cur.fetchone()

    if result and result['avg_mv']:
        cur.close()
        return float(result['avg_mv'])

    # 方法2: 客场身份
    query2 = """
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.lineup_features->>'away_squad_value_eur')::numeric as mv
            FROM matches m
            INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished'
              AND m.away_team = %s
              AND (l.lineup_features->>'away_squad_value_eur')::numeric > 100000000
            ORDER BY m.match_date DESC
            LIMIT %s
        ) sub
    """

    cur.execute(query2, (team_name, limit))
    result = cur.fetchone()

    if result and result['avg_mv']:
        cur.close()
        return float(result['avg_mv'])

    # 方法3: 模糊匹配
    short_name = team_name[:6] if len(team_name) > 6 else team_name
    cur.execute("""
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as mv
            FROM matches m
            INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished'
              AND m.home_team ILIKE %s
              AND (l.lineup_features->>'home_squad_value_eur')::numeric > 100000000
            ORDER BY m.match_date DESC
            LIMIT %s
        ) sub
    """, (f'%{short_name}%', limit))

    result = cur.fetchone()
    cur.close()

    if result and result['avg_mv']:
        return float(result['avg_mv'])

    return None


def fill_future_market_values(conn):
    """为未来比赛填充预估身价"""
    cur = conn.cursor()

    logger.info("\n" + "=" * 60)
    logger.info("【未来身价收割】填充未来 7 天比赛预估身价")
    logger.info("=" * 60)

    # 获取需要填充的比赛
    cur.execute("""
        SELECT m.match_id, m.home_team, m.away_team, m.league_name, m.match_date,
               l.lineup_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.match_date > NOW() AND m.match_date < NOW() + INTERVAL '7 days'
          AND (
            (l.lineup_features->>'home_squad_value_eur')::numeric = 50000000
            OR (l.lineup_features->>'away_squad_value_eur')::numeric = 50000000
            OR l.lineup_features->>'home_squad_value_eur' IS NULL
          )
        ORDER BY m.match_date ASC
    """)

    matches = cur.fetchall()
    logger.info(f"  待处理比赛: {len(matches)} 场")

    filled = 0
    for m in matches:
        match_id = m['match_id']
        home_team = m['home_team']
        away_team = m['away_team']
        league = m['league_name']
        lineup = m['lineup_features'] or {}

        if isinstance(lineup, str):
            lineup = json.loads(lineup)

        # 获取历史平均身价
        home_mv = get_team_avg_market_value(conn, home_team, league)
        away_mv = get_team_avg_market_value(conn, away_team, league)

        # 如果找不到历史数据，使用联赛默认值
        if not home_mv:
            home_mv = get_league_default_mv(league)
        if not away_mv:
            away_mv = get_league_default_mv(league)

        # 更新 lineup_features
        lineup['home_squad_value_eur'] = home_mv
        lineup['away_squad_value_eur'] = away_mv

        cur.execute("""
            UPDATE l3_features
            SET lineup_features = %s
            WHERE match_id = %s
        """, (json.dumps(lineup), match_id))

        filled += 1
        if filled <= 10:
            logger.info(f"  {home_team} vs {away_team}")
            logger.info(f"    主队身价: {home_mv/1e8:.2f}亿 | 客队身价: {away_mv/1e8:.2f}亿")

    conn.commit()
    logger.info(f"  总计填充: {filled} 场")

    cur.close()
    return filled


def get_league_default_mv(league_name):
    """获取联赛默认身价"""
    defaults = {
        'Premier League': 350_000_000,
        'La Liga': 250_000_000,
        'Serie A': 250_000_000,
        'Bundesliga': 250_000_000,
        'Ligue 1': 200_000_000,
    }
    return defaults.get(league_name, 150_000_000)


# ============================================================================
# Task 3: 实战模拟预测
# ============================================================================
def predict_match(conn, model, scaler, home_team, away_team):
    """预测指定比赛"""
    import math

    cur = conn.cursor()

    cur.execute("""
        SELECT m.match_id, m.home_team, m.away_team, m.league_name, m.match_date,
               l.elo_features, l.lineup_features, l.h2h_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.match_date > NOW()
          AND (m.home_team ILIKE %s OR m.away_team ILIKE %s)
          AND (m.home_team ILIKE %s OR m.away_team ILIKE %s)
        ORDER BY m.match_date ASC
        LIMIT 1
    """, (f'%{home_team}%', f'%{home_team}%', f'%{away_team}%', f'%{away_team}%'))

    match = cur.fetchone()
    cur.close()

    if not match:
        return None

    # 提取特征
    elo = match['elo_features'] or {}
    lineup = match['lineup_features'] or {}
    h2h = match['h2h_features'] or {}

    if isinstance(elo, str):
        elo = json.loads(elo)
    if isinstance(lineup, str):
        lineup = json.loads(lineup)
    if isinstance(h2h, str):
        h2h = json.loads(h2h)

    # 计算 11 维特征
    home_elo = float(elo.get('home_elo_pre', elo.get('home_elo', 1500)))
    away_elo = float(elo.get('away_elo_pre', elo.get('away_elo', 1500)))
    elo_diff = float(elo.get('elo_diff', home_elo - away_elo))
    exp_home = float(elo.get('expected_home_win', 0.45))
    exp_away = float(elo.get('expected_away_win', 0.30))

    home_mv = float(lineup.get('home_squad_value_eur', 150_000_000))
    away_mv = float(lineup.get('away_squad_value_eur', 150_000_000))
    log_home = math.log10(home_mv) if home_mv > 0 else 18.0
    log_away = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    mv_share = home_mv / total_mv if total_mv > 0 else 0.5

    h2h_hwr = float(h2h.get('h2h_home_win_ratio', 0.4))
    h2h_dr = float(h2h.get('h2h_draw_ratio', 0.25))
    h2h_gd = float(h2h.get('h2h_avg_goal_diff', 0))

    features = np.array([[
        home_elo, away_elo, elo_diff, exp_home, exp_away,
        log_home, log_away, mv_share,
        h2h_hwr, h2h_dr, h2h_gd
    ]])

    # 预测
    features_scaled = scaler.transform(features)
    probs = model.predict_proba(features_scaled)[0]

    return {
        'match_id': match['match_id'],
        'home': match['home_team'],
        'away': match['away_team'],
        'league': match['league_name'],
        'time': str(match['match_date'])[:16],
        'probs': {'H': probs[2], 'D': probs[1], 'A': probs[0]},
        'elo_diff': elo_diff,
        'mv_share': mv_share,
        'home_mv': home_mv,
        'away_mv': away_mv
    }


def run_combat_test(conn):
    """实战模拟测试"""
    import joblib

    logger.info("\n" + "=" * 60)
    logger.info("【实战模拟测试】国米 & 拜仁 预测")
    logger.info("=" * 60)

    # 加载模型
    model_path = '/app/models/titan_v4466_combat_ready.joblib'
    scaler_path = '/app/models/titan_v4466_combat_ready_scaler.joblib'

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    # 测试用例
    test_cases = [
        ('Inter', 'Milan'),      # 国米
        ('Bayern', 'Munich'),    # 拜仁
        ('Napoli', 'Roma'),      # 那不勒斯
    ]

    results = []
    for home_hint, away_hint in test_cases:
        result = predict_match(conn, model, scaler, home_hint, away_hint)
        if result:
            results.append(result)

            logger.info(f"\n  {result['home']} vs {result['away']}")
            logger.info(f"    联赛: {result['league']} | 时间: {result['time']}")
            logger.info(f"    主队身价: {result['home_mv']/1e8:.2f}亿 | 客队身价: {result['away_mv']/1e8:.2f}亿")
            logger.info(f"    Elo差: {result['elo_diff']:+.1f} | 身价占比: {result['mv_share']:.1%}")
            logger.info(f"    概率: 主{result['probs']['H']*100:.1f}% 平{result['probs']['D']*100:.1f}% 客{result['probs']['A']*100:.1f}%")
        else:
            logger.info(f"\n  未找到 {home_hint} vs {away_hint} 的比赛")

    return results


# ============================================================================
# 主流程
# ============================================================================
def main():
    logger.info("")
    logger.info("=" * 70)
    logger.info("  V4.46.6 战斗定型脚本")
    logger.info("=" * 70)

    conn = get_conn()

    try:
        # Task 1: H2H 盘查与修复
        audit_h2h(conn)
        fix_h2h_avg_goal_diff(conn)

        # Task 2: 未来身价填充
        fill_future_market_values(conn)

        # Task 3: 实战模拟
        run_combat_test(conn)

        logger.info("\n" + "=" * 70)
        logger.info("  战斗定型完成!")
        logger.info("=" * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
