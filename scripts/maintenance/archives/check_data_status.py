#!/usr/bin/env python3
"""检查数据库纯净样本状态"""
import os
import psycopg2

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'host.docker.internal'),
    port=int(os.getenv('DB_PORT', 5432)),
    database=os.getenv('DB_NAME', 'football_db'),
    user=os.getenv('DB_USER', 'football_user'),
    password=os.getenv('DB_PASSWORD', 'football_pass')
)

cur = conn.cursor()

# 1. 纯净样本统计
cur.execute("""
SELECT COUNT(*) as total_finished,
       COUNT(CASE WHEN l.elo_features IS NOT NULL AND l.elo_features != '{}'::jsonb THEN 1 END) as has_elo,
       COUNT(CASE WHEN l.lineup_features IS NOT NULL AND l.lineup_features != '{}'::jsonb THEN 1 END) as has_lineup,
       COUNT(CASE WHEN l.h2h_features IS NOT NULL AND l.h2h_features != '{}'::jsonb THEN 1 END) as has_h2h
FROM matches m
INNER JOIN l3_features l ON m.match_id = l.match_id
WHERE m.status = 'finished' AND m.actual_result IN ('H', 'D', 'A')
""")
row = cur.fetchone()
print(f'已完赛: {row[0]} | Elo: {row[1]} | 身价: {row[2]} | H2H: {row[3]}')

# 2. 纯净样本（三特征齐全）
cur.execute("""
SELECT COUNT(*) FROM matches m
INNER JOIN l3_features l ON m.match_id = l.match_id
WHERE m.status = 'finished' AND m.actual_result IN ('H', 'D', 'A')
  AND l.elo_features IS NOT NULL AND l.elo_features != '{}'::jsonb
  AND l.lineup_features IS NOT NULL AND l.lineup_features != '{}'::jsonb
  AND l.h2h_features IS NOT NULL AND l.h2h_features != '{}'::jsonb
""")
pure = cur.fetchone()[0]
print(f'纯净样本（三特征齐全）: {pure}')

# 3. 身价字段检查
cur.execute("""
SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as home_mv,
       (l.lineup_features->>'away_squad_value_eur')::numeric as away_mv
FROM matches m
INNER JOIN l3_features l ON m.match_id = l.match_id
WHERE m.status = 'finished'
  AND l.lineup_features IS NOT NULL
  AND l.lineup_features->>'home_squad_value_eur' IS NOT NULL
ORDER BY m.match_date DESC NULLS LAST
LIMIT 5
""")
print('\n最新5场身价数据 (单位: 欧元):')
for r in cur.fetchall():
    print(f'  主队: {r[0]:,.0f} | 客队: {r[1]:,.0f}')

# 4. 身价统计
cur.execute("""
SELECT
    AVG((l.lineup_features->>'home_squad_value_eur')::numeric) as avg_home,
    MIN((l.lineup_features->>'home_squad_value_eur')::numeric) as min_home,
    MAX((l.lineup_features->>'home_squad_value_eur')::numeric) as max_home
FROM matches m
INNER JOIN l3_features l ON m.match_id = l.match_id
WHERE m.status = 'finished'
  AND l.lineup_features->>'home_squad_value_eur' IS NOT NULL
""")
stats = cur.fetchone()
print(f'\n身价统计 (欧元):')
print(f'  平均: {float(stats[0]):,.0f}')
print(f'  最小: {float(stats[1]):,.0f}')
print(f'  最大: {float(stats[2]):,.0f}')

# 5. 检查是否有旧字段残留
cur.execute("""
SELECT COUNT(*) FROM l3_features
WHERE lineup_features->>'home_market_value' IS NOT NULL
""")
old_field = cur.fetchone()[0]
print(f'\n旧字段 home_market_value 残留: {old_field}')

conn.close()
