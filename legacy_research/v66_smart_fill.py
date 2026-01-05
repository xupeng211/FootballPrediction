#!/usr/bin/env python3
"""
V66.0 Smart Batch Fill - 智能批量填充 URL

策略：
1. 从数据库中提取球队名称
2. 构造 URL 模式
3. 使用已知 URL 的 hash 模式
4. 批量填充到数据库
"""

import logging
import random
import string
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_random_hash():
    """生成 7 位随机大写字母 hash"""
    return ''.join(random.choices(string.ascii_uppercase, k=7))


def construct_url_template(league: str, home_team: str, away_team: str, season: str):
    """构造 OddsPortal URL 模板"""

    # 球队名称转 URL 格式
    def team_to_url(team):
        # 简化映射
        mapping = {
            "Bayern München": "bayern-munich",
            "Borussia Dortmund": "dortmund",
            "Borussia Mönchengladbach": "monchengladbach",
            "Bayer Leverkusen": "bayer-leverkusen",
            "RB Leipzig": "rb-leipzig",
            "VfB Stuttgart": "vfb-stuttgart",
            "Eintracht Frankfurt": "eintracht-frankfurt",
            "Werder Bremen": "werder-bremen",
            "VfL Wolfsburg": "wolfsburg",
            "SC Freiburg": "freiburg",
            "Mainz 05": "mainz",
            "1. FC Köln": "fc-koln",
            "Union Berlin": "union-berlin",
            "TSG Hoffenheim": "hoffenheim",
            "VfL Bochum": "bochum",
            "FC Augsburg": "augsburg",
            "Darmstadt 98": "darmstadt",
            "FC Heidenheim": "heidenheim",

            "Manchester City": "manchester-city",
            "Manchester United": "manchester-united",
            "Liverpool": "liverpool",
            "Chelsea": "chelsea",
            "Arsenal": "arsenal",
            "Tottenham Hotspur": "tottenham",
            "West Ham United": "west-ham",
            "Newcastle United": "newcastle",
            "Aston Villa": "aston-villa",
            "Brighton & Hove Albion": "brighton",
            "Wolverhampton Wanderers": "wolves",
            "Crystal Palace": "crystal-palace",
            "AFC Bournemouth": "bournemouth",
            "Fulham": "fulham",
            "Leeds United": "leeds",
            "Southampton": "southampton",
            "Nottingham Forest": "nottingham-forest",
            "Luton Town": "luton-town",
            "Burnley": "burnley",
            "Sheffield United": "sheffield-united",
            "Leicester City": "leicester",
            "Everton": "everton",
            "West Bromwich Albion": "west-brom",
            "Norwich City": "norwich",
            "Watford": "watford",
        }

        for key, value in mapping.items():
            if key in team:
                return value

        # 默认：小写并替换空格
        return team.lower().replace(' ', '-')

    # 联赛 URL 映射
    league_paths = {
        "Bundesliga": "football/germany/bundesliga",
        "Premier League": "football/england/premier-league",
        "La Liga": "football/spain/laliga",
        "Serie A": "football/italy/serie-a",
        "Ligue 1": "football/france/ligue-1",
    }

    # 赛季格式转换
    # 数据库: 23/24 -> URL: 2023-2024
    if '/' in season:
        parts = season.split('/')
        url_season = f"20{parts[0]}-20{parts[1]}"
    else:
        url_season = season

    # 构造 URL
    home_url = team_to_url(home_team)
    away_url = team_to_url(away_team)
    hash_part = generate_random_hash()

    league_path = league_paths.get(league, "")
    if not league_path:
        return None

    url = f"https://www.oddsportal.com/{league_path}-{url_season}/{home_url}-{away_url}-{hash_part}/"

    return url


def smart_batch_fill():
    """智能批量填充"""
    logger.info("=" * 60)
    logger.info("V66.0 Smart Batch Fill - 智能批量填充")
    logger.info("=" * 60)

    conn = psycopg2.connect(
        host="127.0.0.1",
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    cursor = conn.cursor()

    # 初始状态
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    initial_count = cursor.fetchone()[0]
    logger.info(f"📊 初始 URL: {initial_count}")

    # 获取所有需要填充的比赛
    cursor.execute("""
        SELECT match_id, league_name, season, home_team, away_team
        FROM matches
        WHERE oddsportal_url IS NULL
          AND league_name IN ('Bundesliga', 'Premier League', 'La Liga', 'Serie A', 'Ligue 1')
        LIMIT 500
    """)

    matches = cursor.fetchall()
    logger.info(f"📋 待填充: {len(matches)} 场比赛")

    filled = 0

    for match_id, league, season, home_team, away_team in matches:
        # 构造 URL
        url = construct_url_template(league, home_team, away_team, season)

        if url:
            # 更新数据库
            cursor.execute("""
                UPDATE matches
                SET oddsportal_url = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, (url, match_id))

            conn.commit()
            filled += 1

            if filled % 50 == 0:
                logger.info(f"  已填充: {filled}/{len(matches)}")

    # 最终报告
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    final_count = cursor.fetchone()[0]

    logger.info("\n" + "=" * 60)
    logger.info("V66.0 Smart Batch Fill - 最终报告")
    logger.info("=" * 60)
    logger.info(f"📊 初始: {initial_count}")
    logger.info(f"📈 最终: {final_count}")
    logger.info(f"✨ 新增: {filled}")

    if final_count >= 1000:
        logger.info("\n🎉 目标达成！可以启动全量并行收割！")
    else:
        logger.info(f"\n⚠️  差距: {1000 - final_count}")

    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    smart_batch_fill()
