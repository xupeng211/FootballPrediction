#!/usr/bin/env python3
"""
V50.0 数据采集脚本 - 采集 200 场比赛数据 (Phase 2.2)
=====================================================

功能:
    1. 使用 V50.0 Rich L1 扫描引擎采集比赛数据
    2. 将 L1 数据（比分、状态）写入 matches 表
    3. 将 L2 原始数据写入 raw_match_data 表
    4. 目标：采集 200 场已完成的比赛

Author: Senior Data Engineer
Version: V50.0 (Phase 2.2)
Date: 2025-12-28
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
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
        logging.FileHandler("logs/harvest_200.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据库写入器
# ============================================================================


class MatchDataWriter:
    """比赛数据写入器"""

    def __init__(self, db_config: Any):
        """初始化写入器"""
        self.db_config = db_config
        self.conn_params = {
            "host": db_config.host,
            "port": db_config.port,
            "database": db_config.name,
            "user": db_config.user,
            "password": db_config.password.get_secret_value(),
        }

    def write_matches(self, matches: list[dict]) -> int:
        """
        写入 L1 数据到 matches 表

        Args:
            matches: Rich L1 比赛数据列表

        Returns:
            写入的记录数
        """
        if not matches:
            return 0

        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()

            # 准备数据
            values = []
            for m in matches:
                values.append((
                    m["match_id"],           # external_id
                    m["league_id"],         # league_id
                    m["season_name"],       # season
                    m["match_time_utc"],    # match_time
                    m["status"].upper(),    # status
                    m["home_team"],         # home_team
                    m["away_team"],         # away_team
                    m["home_team_id"],      # home_team_id
                    m["away_team_id"],      # away_team_id
                    m.get("home_score"),    # home_score
                    m.get("away_score"),    # away_score
                    True if m["status"] == "finished" else None,  # is_finished
                    "fotmob_api_v2",        # api_source
                ))

            # 批量写入
            sql = """
                INSERT INTO matches (
                    external_id, league_id, season, match_time, status,
                    home_team, away_team, home_team_id, away_team_id,
                    home_score, away_score, is_finished, api_source
                ) VALUES %s
                ON CONFLICT (external_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    is_finished = EXCLUDED.is_finished,
                    updated_at = CURRENT_TIMESTAMP
            """

            execute_values(cur, sql, values)
            conn.commit()

            logger.info(f"✅ 写入 {cur.rowcount} 条 L1 数据到 matches 表")
            return cur.rowcount

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 写入 L1 数据失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def write_raw_data(self, raw_data_list: list[tuple]) -> int:
        """
        写入 L2 原始数据到 raw_match_data 表

        Args:
            raw_data_list: (external_id, raw_json) 元组列表

        Returns:
            写入的记录数
        """
        if not raw_data_list:
            return 0

        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()

            sql = """
                INSERT INTO raw_match_data (external_id, raw_data, data_version, api_source)
                VALUES %s
                ON CONFLICT (external_id) DO UPDATE SET
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
            """

            execute_values(cur, sql, raw_data_list)
            conn.commit()

            logger.info(f"✅ 写入 {cur.rowcount} 条 L2 数据到 raw_match_data 表")
            return cur.rowcount

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 写入 L2 数据失败: {e}")
            raise
        finally:
            if conn:
                conn.close()


# ============================================================================
# 主采集流程
# ============================================================================


async def harvest_200_matches(
    target_count: int = 200,
    years_back: int = 2,
) -> dict:
    """
    采集 200 场比赛数据

    Args:
        target_count: 目标数量
        years_back: 回溯年数

    Returns:
        采集统计字典
    """
    from src.api.collectors.v50_rich_l1_scanner import RichL1Scanner

    logger.info("=" * 60)
    logger.info("V50.0 数据采集启动")
    logger.info("=" * 60)
    logger.info(f"目标数量: {target_count} 场")
    logger.info(f"回溯年数: {years_back} 年")

    # 初始化写入器
    settings = get_settings()
    writer = MatchDataWriter(settings.database)

    # 初始化扫描器
    scanner = RichL1Scanner()

    # 定义要扫描的联赛（五大联赛）
    league_configs = [
        (87, "La Liga"),           # 西甲
        (135, "Serie A"),          # 意甲
        (54, "Bundesliga"),        # 德甲
        (34, "Premier League"),   # 英超
        (53, "Ligue 1"),           # 法甲
    ]

    # 开始扫描
    all_matches = []
    for league_id, league_name in league_configs:
        matches = await scanner.scan_league_historical(
            league_id, league_name, years_back
        )
        all_matches.extend(matches)

        # 过滤已完成的比赛
        finished_matches = [m for m in matches if m.is_finished()]

        logger.info(f"📊 {league_name}: 总计 {len(matches)} 场, 已完成 {len(finished_matches)} 场")

        if len(all_matches) >= target_count:
            break

    # 只保留已完成的比赛
    finished_matches = [m.to_dict() for m in all_matches if m["status"] == "finished"]

    # 限制数量
    finished_matches = finished_matches[:target_count]

    logger.info(f"")
    logger.info(f"📊 扫描完成: 共 {len(all_matches)} 场, 已完成 {len(finished_matches)} 场")

    if not finished_matches:
        logger.error("❌ 没有可用的已完成比赛")
        return {"success": False, "count": 0}

    # 写入 L1 数据
    l1_count = writer.write_matches(finished_matches)

    # 写入 L2 数据（使用占位符）
    raw_data_list = [(m["match_id"], json.dumps({}), "V50.0", "fotmob_api_v2") for m in finished_matches]
    l2_count = writer.write_raw_data(raw_data_list)

    # 统计
    stats = {
        "success": True,
        "total_scanned": len(all_matches),
        "finished_matches": len(finished_matches),
        "l1_written": l1_count,
        "l2_written": l2_count,
    }

    logger.info(f"")
    logger.info("=" * 60)
    logger.info("采集完成")
    logger.info("=" * 60)
    logger.info(f"扫描总数: {stats['total_scanned']}")
    logger.info(f"已完成: {stats['finished_matches']}")
    logger.info(f"L1 写入: {stats['l1_written']}")
    logger.info(f"L2 写入: {stats['l2_written']}")

    return stats


# ============================================================================
# 命令行入口
# ============================================================================


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V50.0 数据采集 - 采集 200 场比赛数据"
    )
    parser.add_argument("--count", type=int, default=200, help="目标数量")
    parser.add_argument("--years", type=int, default=2, help="回溯年数")

    args = parser.parse_args()

    # 运行采集
    stats = asyncio.run(harvest_200_matches(args.count, args.years))

    return 0 if stats["success"] else 1


if __name__ == "__main__":
    exit(main())
