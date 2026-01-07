#!/usr/bin/env python3
"""
V26.7: 23/24 赛季历史数据收割验证
====================================

目标：收割英超 23/24 赛季数据，验证 SQL 中包含 2024-04-25 的比分
"""

import os
import sys

# V26.7 DBRE: 强制使用正确的数据库配置
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'football_db'
os.environ['DB_USER'] = 'football_user'
os.environ['DB_PASSWORD'] = 'football_pass'
os.environ['DB_PORT'] = '5432'

# 添加项目路径
sys.path.insert(0, '/home/user/projects/FootballPrediction')

from src.config_unified import reload_settings
reload_settings()

from src.api.collectors.fotmob_core import FotMobCoreCollector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 70)
print("V26.7: 23/24 赛季历史数据收割验证")
print("=" * 70)
print()

# 测试参数
LEAGUE_ID = 47  # 英超
SEASON_CODE = "2023/2024"  # 23/24 赛季（正确格式）
TARGET_DATE = "2024-04-25"
TARGET_MATCH = "Brighton 0-4 Manchester City"

print(f"🎯 目标: {TARGET_DATE} - {TARGET_MATCH}")
print(f"📊 联赛 ID: {LEAGUE_ID}")
print(f"🏆 赛季代码: {SEASON_CODE}")
print()

# 创建采集器
collector = FotMobCoreCollector()

print("🔄 开始收割...")
print()

# 执行全息 L1 采集
result = collector.enriched_l1_harvest(
    league_id=LEAGUE_ID,
    season_code=SEASON_CODE,
    league_name="Premier League",
    batch_size=100
)

print()
print("=" * 70)
print("📊 收割统计")
print("=" * 70)
print()
print(f"总发现: {result['total_discovered']} 场")
print(f"已结束: {result['total_finished']} 场")
print(f"成功入库: {result['total_upserted']} 场")
print()

# 显示前 5 场比赛
if result['match_details']:
    print("📋 前 5 场比赛样本:")
    print("-" * 70)
    for i, match in enumerate(result['match_details'][:5], 1):
        home = match.get('home_team', 'Unknown')
        away = match.get('away_team', 'Unknown')
        hs = match.get('home_score')
        as_ = match.get('away_score')
        date = match.get('match_date', 'N/A')
        status = match.get('status_str', 'N/A')

        print(f"{i}. {date} | {home} {hs}-{as_} {away} | {status}")

print()
print("=" * 70)
print("🔍 SQL 验证")
print("=" * 70)
print()

# SQL 验证
import psycopg2
from src.config_unified import get_settings

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=psycopg2.extras.RealDictCursor
)

with conn.cursor() as cur:
    # 1. 检查 23/24 赛季总比赛数
    cur.execute("SELECT COUNT(*) as count FROM matches WHERE season = '2324'")
    total_2324 = cur.fetchone()['count']
    print(f"23/24 赛季总比赛数: {total_2324}")

    # 2. 检查目标日期的比赛
    cur.execute("""
        SELECT home_team, away_team, home_score, away_score, match_date, status
        FROM matches
        WHERE match_date = %s AND season = '2324'
        ORDER BY home_team
    """, (TARGET_DATE,))

    target_matches = cur.fetchall()
    print(f"\n{TARGET_DATE} 比赛场数: {len(target_matches)}")

    if target_matches:
        print("\n目标日期比赛详情:")
        for match in target_matches:
            print(f"  {match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']} | {match['status']}")

    # 3. 搜索目标比赛
    cur.execute("""
        SELECT home_team, away_team, home_score, away_score, match_date, status, actual_result
        FROM matches
        WHERE home_team LIKE %s AND away_team LIKE %s
        AND season = '2324'
    """, ('%Brighton%', '%Manchester City%'))

    brighton_mancity = cur.fetchall()
    print(f"\n布莱顿 vs 曼城比赛数: {len(brighton_mancity)}")

    if brighton_mancity:
        print("\n所有布莱顿 vs 曼城比赛:")
        for match in brighton_mancity:
            print(f"  {match['match_date']}: {match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}")

conn.close()

print()
print("=" * 70)
print("收割完成")
print("=" * 70)
