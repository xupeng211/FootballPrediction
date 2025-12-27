#!/usr/bin/env python3
"""
Process remaining records - full UPSERT version
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from src.data_engineering.multipath_extractor import MultiPathExtractor
from src.config_unified import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
conn = psycopg2.connect(
    host='db',
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
conn.autocommit = False
cur = conn.cursor(cursor_factory=RealDictCursor)

# 获取剩余未处理的比赛
logger.info("Fetching remaining records...")
cur.execute('''
    SELECT r.match_id, m.match_date, m.home_team, m.away_team,
           m.home_score, m.away_score, r.raw_data
    FROM raw_match_data r
    JOIN matches m ON r.match_id = m.match_id::text
    WHERE m.is_finished = true
      AND r.match_id::text NOT IN (
          SELECT match_id FROM match_features_training WHERE home_team_rating IS NOT NULL
      )
    LIMIT 500
''')
records = cur.fetchall()
logger.info(f"Found {len(records)} remaining records")

extractor = MultiPathExtractor()
success = 0
failed = 0

for i, rec in enumerate(records):
    if (i + 1) % 50 == 0:
        logger.info(f"Processing {i+1}/{len(records)}...")

    stats = extractor.extract_from_jsonb(
        match_id=rec['match_id'],
        raw_data=rec['raw_data'],
        match_date=str(rec['match_date']),
        home_team=rec['home_team'],
        away_team=rec['away_team']
    )

    if stats.extraction_success:
        # 准备 season
        match_date_obj = rec['match_date']
        if hasattr(match_date_obj, 'year'):
            year = match_date_obj.year
            month = match_date_obj.month
            if month >= 8:
                season = f"{str(year)[-2:]}{str(year + 1)[-2:]}"
            else:
                season = f"{str(year - 1)[-2:]}{str(year)[-2:]}"
        else:
            season = "2324"

        # UPSERT - 分两步执行
        # 先尝试 UPDATE（如果记录存在）
        update_sql = """
            UPDATE match_features_training SET
                home_xg = COALESCE(%s, home_xg),
                away_xg = COALESCE(%s, away_xg),
                home_possession = COALESCE(%s, home_possession),
                away_possession = COALESCE(%s, away_possession),
                home_shots = COALESCE(%s, home_shots),
                away_shots = COALESCE(%s, away_shots),
                home_shots_on_target = COALESCE(%s, home_shots_on_target),
                away_shots_on_target = COALESCE(%s, away_shots_on_target),
                home_passes = COALESCE(%s, home_passes),
                away_passes = COALESCE(%s, away_passes),
                home_team_rating = COALESCE(%s, home_team_rating),
                away_team_rating = COALESCE(%s, away_team_rating)
            WHERE match_id = %s
        """
        update_params = (
            stats.home_xg, stats.away_xg,
            stats.home_possession, stats.away_possession,
            stats.home_shots, stats.away_shots,
            stats.home_shots_on_target, stats.away_shots_on_target,
            stats.home_passes, stats.away_passes,
            stats.home_team_rating, stats.away_team_rating,
            stats.match_id
        )
        cur.execute(update_sql, update_params)

        # 如果没有行被更新，执行 INSERT
        if cur.rowcount == 0:
            insert_sql = """
                INSERT INTO match_features_training (
                    match_id, season, match_date, home_team, away_team,
                    home_xg, away_xg,
                    home_possession, away_possession,
                    home_shots, away_shots,
                    home_shots_on_target, away_shots_on_target,
                    home_passes, away_passes,
                    home_team_rating, away_team_rating
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            insert_params = (
                stats.match_id, season, match_date_obj, stats.home_team, stats.away_team,
                stats.home_xg, stats.away_xg,
                stats.home_possession, stats.away_possession,
                stats.home_shots, stats.away_shots,
                stats.home_shots_on_target, stats.away_shots_on_target,
                stats.home_passes, stats.away_passes,
                stats.home_team_rating, stats.away_team_rating
            )
            cur.execute(insert_sql, insert_params)
        success += 1
    else:
        failed += 1

conn.commit()
cur.close()
conn.close()

logger.info(f"✅ Processed {len(records)} records: {success} successful, {failed} failed")
