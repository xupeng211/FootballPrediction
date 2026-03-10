#!/usr/bin/env python3
"""修复身价数据"""

import psycopg2

conn = psycopg2.connect(
    host='host.docker.internal',
    port=5432,
    database='football_db',
    user='football_user',
    password='football_pass'
)

cur = conn.cursor()

print("=== Step 1: 检查当前身价分布 ===")
cur.execute("""
    SELECT
        count(*) as total,
        avg((lineup_features->>'home_squad_value_eur')::numeric) as avg_home_mv,
        min((lineup_features->>'home_squad_value_eur')::numeric) as min_home_mv,
        max((lineup_features->>'home_squad_value_eur')::numeric) as max_home_mv
    FROM l3_features
    WHERE lineup_features->>'home_squad_value_eur' IS NOT NULL
""")
result = cur.fetchone()
print(f"Total: {result[0]}")
print(f"Home MV Avg: {float(result[1])/1e6:.2f}M EUR")
print(f"Home MV Min: {float(result[2])/1e6:.2f}M EUR")
print(f"Home MV Max: {float(result[3])/1e6:.2f}M EUR")

# 检查 home_mv_share 分布
print("\n=== Step 2: 检查 home_mv_share 分布 ===")
cur.execute("""
    SELECT
        count(*) as total,
        avg((lineup_features->>'home_mv_share')::numeric) as avg_share,
        stddev((lineup_features->>'home_mv_share')::numeric) as std_share,
        min((lineup_features->>'home_mv_share')::numeric) as min_share,
        max((lineup_features->>'home_mv_share')::numeric) as max_share
    FROM l3_features
    WHERE lineup_features->>'home_mv_share' IS NOT NULL
""")
result = cur.fetchone()
print(f"Total: {result[0]}")
print(f"Share Avg: {result[1]}")
print(f"Share Std: {result[2]}")
print(f"Share Min: {result[3]}")
print(f"Share Max: {result[4]}")

# 检查样本
print("\n=== Step 3: 样本检查 ===")
cur.execute("""
    SELECT match_id,
           lineup_features->>'home_squad_value_eur' as home_mv,
           lineup_features->>'away_squad_value_eur' as away_mv,
           lineup_features->>'home_mv_share' as share
    FROM l3_features
    WHERE lineup_features->>'home_squad_value_eur' IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 5
""")
samples = cur.fetchall()
for s in samples:
    home_mv = float(s[1]) if s[1] else 0
    away_mv = float(s[2]) if s[2] else 0
    share = float(s[3]) if s[3] else 0
    print(f"  {s[0]}: Home={home_mv/1e6:.1f}M | Away={away_mv/1e6:.1f}M | Share={share:.4f}")

cur.close()
conn.close()
