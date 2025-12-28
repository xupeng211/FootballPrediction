#!/usr/bin/env python3
"""
模拟数据生成器 - 生成 200 场比赛数据用于测试 (Phase 2.2)
======================================================

功能:
    1. 生成 200 场模拟比赛数据
    2. 写入 matches 表
    3. 写入 raw_match_data 表

Author: Senior Data Engineer
Version: Phase 2.2
Date: 2025-12-28
"""

import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/generate_mock.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 模拟数据生成器
# ============================================================================


class MockMatchGenerator:
    """模拟比赛数据生成器"""

    # 模拟球队
    TEAMS = [
        "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla",
        "Manchester City", "Liverpool", "Arsenal", "Chelsea",
        "Bayern Munich", "Dortmund", "Leverkusen", "RB Leipzig",
        "Inter Milan", "AC Milan", "Juventus", "Napoli",
        "PSG", "Monaco", "Lyon", "Marseille",
    ]

    # 模拟联赛
    LEAGUES = [
        (87, "La Liga"),
        (135, "Serie A"),
        (54, "Bundesliga"),
        (34, "Premier League"),
        (53, "Ligue 1"),
    ]

    def __init__(self, db_config: Any):
        """初始化生成器"""
        self.db_config = db_config
        self.conn_params = {
            "host": db_config.host,
            "port": db_config.port,
            "database": db_config.name,
            "user": db_config.user,
            "password": db_config.password.get_secret_value(),
        }

    def generate_match_data(self, count: int = 200) -> tuple[list[dict], list[tuple]]:
        """
        生成模拟比赛数据

        Args:
            count: 生成数量

        Returns:
            (matches_list, raw_data_list) 元组
        """
        matches = []
        raw_data_list = []

        # 起始时间：90 天前
        start_time = datetime.now() - timedelta(days=90)

        for i in range(count):
            # 随机选择联赛
            league_id, league_name = random.choice(self.LEAGUES)

            # 随机选择球队
            home_team, away_team = random.sample(self.TEAMS, 2)

            # 随机比分
            home_score = random.randint(0, 5)
            away_score = random.randint(0, 5)

            # 随机时间（90 天内）
            match_time = start_time + timedelta(
                days=random.randint(0, 90),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            # 生成 match_id
            match_id = 1000000 + i

            # 模拟 FotMob API 原始数据
            raw_data = {
                "general": {
                    "leagueId": league_id,
                    "leagueName": league_name,
                },
                "header": {
                    "teams": [
                        {"id": 1000 + i * 2, "name": home_team},
                        {"id": 1001 + i * 2, "name": away_team},
                    ]
                },
                "content": {
                    "stats": {
                        "possession": {"home": random.randint(40, 70), "away": random.randint(30, 60)},
                        "shots": {
                            "total": {"home": random.randint(5, 25), "away": random.randint(5, 25)},
                            "onTarget": {"home": random.randint(2, 10), "away": random.randint(2, 10)},
                        },
                        "corners": {"home": random.randint(2, 12), "away": random.randint(2, 12)},
                    }
                }
            }

            # 构建 L1 数据
            match = {
                "match_id": match_id,
                "league_id": league_id,
                "season_name": "2324",
                "match_time_utc": match_time.isoformat(),
                "status": "finished",
                "home_team": home_team,
                "away_team": away_team,
                "home_team_id": 1000 + i * 2,
                "away_team_id": 1001 + i * 2,
                "home_score": home_score,
                "away_score": away_score,
            }

            matches.append(match)
            raw_data_list.append((match_id, json.dumps(raw_data), "V50.0", "fotmob_api_v2"))

        return matches, raw_data_list

    def write_to_database(self, matches: list[dict], raw_data_list: list[tuple]) -> dict:
        """
        写入数据库

        Args:
            matches: L1 比赛数据
            raw_data_list: L2 原始数据

        Returns:
            写入统计
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()

            # 写入 matches 表
            l1_values = []
            for m in matches:
                # 获取联赛名称
                league_name = next((name for lid, name in self.LEAGUES if lid == m["league_id"]), "Unknown")

                l1_values.append((
                    m["match_id"], league_name, m["league_id"], m["season_name"],
                    m["match_time_utc"], m["status"], m["home_team"], m["away_team"],
                    m["home_team_id"], m["away_team_id"],
                    m["home_score"], m["away_score"], True
                ))

            l1_sql = """
                INSERT INTO matches (
                    external_id, league_name, league_id, season, match_time, status,
                    home_team, away_team, home_team_id, away_team_id,
                    home_score, away_score, is_finished
                ) VALUES %s
                ON CONFLICT (external_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    is_finished = EXCLUDED.is_finished,
                    updated_at = CURRENT_TIMESTAMP
            """

            execute_values(cur, l1_sql, l1_values)
            l1_count = cur.rowcount

            # 写入 raw_match_data 表
            # 注意：external_id 没有唯一约束，使用 id 列的约束
            # 这里我们使用简单的 INSERT，如果存在则跳过
            inserted_count = 0
            for external_id, raw_data, data_version, api_source in raw_data_list:
                try:
                    cur.execute("""
                        INSERT INTO raw_match_data (external_id, raw_data, data_version, api_source)
                        VALUES (%s, %s, %s, %s)
                    """, (external_id, raw_data, data_version, api_source))
                    inserted_count += 1
                except psycopg2.IntegrityError:
                    # 记录已存在，跳过
                    pass

            l2_count = inserted_count

            conn.commit()

            return {
                "l1_count": l1_count,
                "l2_count": l2_count,
            }

        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="生成 200 场模拟比赛数据"
    )
    parser.add_argument("--count", type=int, default=200, help="生成数量")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("模拟数据生成器启动")
    logger.info("=" * 60)
    logger.info(f"目标数量: {args.count} 场")

    # 获取配置
    settings = get_settings()

    # 初始化生成器
    generator = MockMatchGenerator(settings.database)

    # 生成数据
    logger.info(f"生成 {args.count} 场模拟比赛...")
    matches, raw_data_list = generator.generate_match_data(args.count)

    # 写入数据库
    logger.info(f"写入数据库...")
    stats = generator.write_to_database(matches, raw_data_list)

    logger.info("")
    logger.info("=" * 60)
    logger.info("生成完成")
    logger.info("=" * 60)
    logger.info(f"L1 数据: {stats['l1_count']} 条")
    logger.info(f"L2 数据: {stats['l2_count']} 条")

    return 0


if __name__ == "__main__":
    exit(main())
