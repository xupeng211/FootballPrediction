#!/usr/bin/env python3
"""
杯赛补全脚本
数据工程主管专用工具

Purpose: 补全豪门球队的杯赛数据（欧冠、欧联、足总杯等）
使用FBrefTeamCollector采集所有赛事数据
"""

import asyncio
import logging
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_team_collector import FBrefTeamScheduleCollector

# 数据库连接
db_url = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)
engine = create_engine(db_url)

# 豪门球队列表（从数据库查询得到的前20支）
BIG_TEAMS = [
    "Liverpool",
    "Manchester City",
    "Aston Villa",
    "Newcastle Utd",
    "Bournemouth",
    "Brighton",
    "Fulham",
    "Chelsea",
    "Crystal Palace",
    "Nott'ham Forest",
    "Manchester Utd",
    "Leeds United",
    "West Ham",
    "Tottenham",
    "Wolves",
    "Brentford",
    "Burnley",
    "Sunderland",
    "Arsenal",
    "Everton",
]

# 额外的重要球队（未在前20中但很重要）- 暂时跳过避免事务错误
EXTRA_TEAMS = []

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cup_backfill.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def backfill_team_cups(team_name: str, season: str = "2023-2024") -> dict:
    """
    为单个球队补全杯赛数据

    Args:
        team_name: 球队名称
        season: 赛季

    Returns:
        采集统计信息
    """
    collector = FBrefTeamScheduleCollector(db_url)

    logger.info(f"开始采集 {team_name} 的所有赛事数据...")
    logger.info("=" * 80)

    try:
        # 采集所有比赛
        matches = await collector.collect_team_schedule(team_name, season)

        if matches:
            # 保存到数据库
            saved_count = await collector.save_matches_to_database(matches)

            result = {
                "team": team_name,
                "collected": len(matches),
                "saved": saved_count,
                "status": "success",
            }

            logger.info(f"✅ {team_name} 采集完成:")
            logger.info(f"   采集比赛: {len(matches)} 场")
            logger.info(f"   保存比赛: {saved_count} 场")
            logger.info("=" * 80)

        else:
            result = {
                "team": team_name,
                "collected": 0,
                "saved": 0,
                "status": "no_data",
            }
            logger.warning(f"⚠️ {team_name} 未采集到数据")

        # 添加延迟避免被封
        await asyncio.sleep(3)

    except Exception as e:
        logger.error(f"❌ {team_name} 采集失败: {e}")
        result = {
            "team": team_name,
            "collected": 0,
            "saved": 0,
            "status": "error",
            "error": str(e),
        }

    return result


async def backfill_all_teams_concurrent(teams: list, max_concurrent: int = 3):
    """
    并发采集多个球队数据

    Args:
        teams: 球队名称列表
        max_concurrent: 最大并发数
    """
    logger.info(f"🚀 开始杯赛补全计划")
    logger.info(f"📋 计划采集 {len(teams)} 支球队")
    logger.info(f"🔧 最大并发数: {max_concurrent}")
    logger.info("=" * 80)

    # 创建信号量限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_team(team):
        async with semaphore:
            return await backfill_team_cups(team)

    # 并发执行
    results = await asyncio.gather(*[process_team(team) for team in teams])

    # 统计结果
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    no_data = [r for r in results if r["status"] == "no_data"]

    total_collected = sum(r["collected"] for r in results)
    total_saved = sum(r["saved"] for r in results)

    logger.info("\n" + "=" * 80)
    logger.info("📊 杯赛补全完成统计")
    logger.info("=" * 80)

    logger.info(f"\n✅ 成功球队: {len(successful)}")
    logger.info(f"❌ 失败球队: {len(failed)}")
    logger.info(f"⚠️ 无数据球队: {len(no_data)}")

    logger.info(f"\n📈 总计统计:")
    logger.info(f"   采集比赛: {total_collected}")
    logger.info(f"   保存比赛: {total_saved}")

    # 列出成功的球队
    if successful:
        logger.info(f"\n✅ 成功球队列表:")
        for r in successful:
            logger.info(f"   • {r['team']:25s}: {r['saved']:3d} 场比赛")

    # 列出失败的球队
    if failed:
        logger.info(f"\n❌ 失败球队列表:")
        for r in failed:
            logger.info(f"   • {r['team']:25s}: {r['error']}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 杯赛补全计划执行完成")
    logger.info("=" * 80)

    return results


def verify_cup_data():
    """
    验证杯赛数据是否成功入库
    """
    logger.info("\n🔍 验证杯赛数据入库...")

    with engine.connect() as conn:
        # 查询是否有杯赛数据
        result = conn.execute(
            text(
                """
            SELECT DISTINCT l.name as league_name, COUNT(*) as match_count
            FROM matches m
            JOIN leagues l ON m.league_id = l.id
            WHERE l.name IS NOT NULL
              AND l.name NOT LIKE '%Premier League%'
              AND l.name NOT LIKE '%Championship%'
              AND l.name NOT LIKE '%League One%'
              AND l.name NOT LIKE '%League Two%'
            GROUP BY l.name
            ORDER BY match_count DESC
        """
            )
        )

        cup_matches = result.fetchall()

        if cup_matches:
            logger.info("✅ 发现杯赛数据:")
            for league_name, match_count in cup_matches:
                logger.info(f"   🏆 {league_name}: {match_count} 场比赛")
        else:
            logger.warning("⚠️ 未发现杯赛数据")

        # 查询是否有欧冠、足总杯等关键词
        result = conn.execute(
            text(
                """
            SELECT DISTINCT data_source
            FROM matches
            WHERE data_source LIKE '%cup%'
               OR data_source LIKE '%champion%'
               OR data_source LIKE '%europa%'
        """
            )
        )

        source_matches = result.fetchall()

        if source_matches:
            logger.info(f"\n📊 发现相关数据源:")
            for (source,) in source_matches:
                logger.info(f"   • {source}")

    logger.info("✅ 验证完成")


async def main():
    """主函数"""
    logger.info("🏆 杯赛补全计划启动")
    logger.info(f"时间: {asyncio.get_event_loop().time()}")

    # Step 1: 采集BIG_TEAMS
    logger.info("\n📋 Phase 1: 采集英超前20球队")
    results1 = await backfill_all_teams_concurrent(BIG_TEAMS, max_concurrent=1)

    # Step 2: 验证数据
    logger.info("\n📋 Phase 2: 验证数据")
    verify_cup_data()

    logger.info("\n🎉 杯赛补全计划完成！")

    return 0


if __name__ == "__main__":
    # 运行主程序
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ 程序异常退出: {e}", exc_info=True)
        sys.exit(1)
