#!/usr/bin/env python3
"""
V54.1 URL 构造器 - 简化版本
=========================

功能:
1. 从数据库读取缺失赔率的比赛
2. 使用 team_name_mapping 构造 OddsPortal URL
3. 直接更新 prematch_features.source_url
4. 支持断点续传

Author: Senior Data Engineer
Version: V54.1-Simple
Date: 2026-01-01
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_oddsportal_url(home_team: str, away_team: str, league_path: str) -> str:
    """
    构造 OddsPortal 比赛详情页 URL

    URL 格式: /football/{league_path}/{home_team}-{away_team}/
    """
    # 标准化球队名
    home = home_team.lower().replace(" ", "-").replace("&", "and")
    away = away_team.lower().replace(" ", "-").replace("&", "and")

    return f"/football/{league_path}/{home}-{away}/"


def main():
    """主函数"""
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )

    cursor = conn.cursor()

    # 联赛路径映射
    league_paths = {
        "Premier League": "england/premier-league",
        "La Liga": "spain/la-liga",
        "Bundesliga": "germany/bundesliga",
        "Serie A": "italy/serie-a",
        "Ligue 1": "france/ligue-1",
    }

    logger.info("=" * 60)
    logger.info("【V54.1 URL 构造器】")
    logger.info("=" * 60)
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # 查询缺失赔率的比赛（使用 oddsportal_name）
    cursor.execute("""
        SELECT
            pf.match_id,
            m.home_team,
            m.away_team,
            m.league_name,
            tmh.oddsportal_name as home_op_name,
            tma.oddsportal_name as away_op_name
        FROM prematch_features pf
        JOIN matches m ON pf.match_id = m.match_id
        LEFT JOIN team_name_mapping tmh ON tmh.fotmob_name = m.home_team AND tmh.fotmob_league = m.league_name
        LEFT JOIN team_name_mapping tma ON tma.fotmob_name = m.away_team AND tma.fotmob_league = m.league_name
        WHERE pf.source_url IS NULL
          AND pf.closing_home_odds IS NULL
          AND m.league_name IN %s
          AND m.match_date >= '2020-01-01'
        ORDER BY m.match_date DESC
    """, (tuple(league_paths.keys()),))

    matches = cursor.fetchall()

    logger.info(f"发现 {len(matches)} 场缺失赔率的比赛")
    logger.info("")

    # 批量更新
    updated = 0
    skipped = 0

    for match in matches:
        league_path = league_paths.get(match["league_name"])
        home_op = match["home_op_name"]
        away_op = match["away_op_name"]

        if not league_path or not home_op or not away_op:
            skipped += 1
            continue

        # 构造 URL
        url = build_oddsportal_url(home_op, away_op, league_path)

        # 更新数据库
        cursor.execute("""
            UPDATE prematch_features
            SET source_url = %s,
                url_discovered_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """, (url, match["match_id"]))

        updated += 1

        if updated % 100 == 0:
            logger.info(f"  已处理: {updated}/{len(matches)}")

    conn.commit()

    # 输出报告
    print()
    print("=" * 60)
    print("【V54.1 URL 构造报告】")
    print("=" * 60)
    print()
    print(f"总缺失场次: {len(matches)}")
    print(f"成功构造 URL: {updated}")
    print(f"跳过（无映射）: {skipped}")
    print()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
