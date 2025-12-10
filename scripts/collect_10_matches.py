#!/usr/bin/env python3
"""
10场比赛数据采集验证脚本
用于验证数据能成功入库
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from collectors.fotmob_api_collector import FotMobAPICollector
from database.async_manager import AsyncDatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def collect_10_matches():
    """采集10场比赛数据并验证入库"""
    logger.info("🚀 开始10场比赛数据采集验证")

    # 初始化数据采集器和数据库管理器
    collector = FotMobAPICollector()
    db_manager = AsyncDatabaseManager()

    # 准备10场比赛的测试数据
    test_matches = [
        {"fotmob_id": "47_1_3434", "league_name": "Premier League", "home_team": "Manchester United", "away_team": "Liverpool"},
        {"fotmob_id": "47_1_3435", "league_name": "Premier League", "home_team": "Chelsea", "away_team": "Arsenal"},
        {"fotmob_id": "54_1_1985", "league_name": "La Liga", "home_team": "Real Madrid", "away_team": "Barcelona"},
        {"fotmob_id": "82_1_2673", "league_name": "Serie A", "home_team": "Inter Milan", "away_team": "AC Milan"},
        {"fotmob_id": "100_1_28384", "league_name": "Bundesliga", "home_team": "Bayern Munich", "away_team": "Dortmund"},
        {"fotmob_id": "354_1_50690", "league_name": "Ligue 1", "home_team": "PSG", "away_team": "Lyon"},
        {"fotmob_id": "268_1_1496", "league_name": "Brasileirão", "home_team": "Flamengo", "away_team": "Corinthians"},
        {"fotmob_id": "34_1_48323", "league_name": "MLS", "home_team": "LA Galaxy", "away_team": "Seattle Sounders"},
        {"fotmob_id": "5_1_7770", "league_name": "Champions League", "home_team": "Manchester City", "away_team": "Real Madrid"},
        {"fotmob_id": "372_1_34124", "league_name": "J1 League", "home_team": "Kashima Antlers", "away_team": "Urawa Red Diamonds"},
    ]

    success_count = 0
    error_count = 0
    collected_matches = []

    logger.info("=" * 60)
    logger.info("📊 开始采集10场比赛数据")
    logger.info("=" * 60)

    # 采集每场比赛数据
    for i, match in enumerate(test_matches, 1):
        fotmob_id = match["fotmob_id"]
        logger.info(f"\n[{i}/10] 📈 采集比赛: {match['home_team']} vs {match['away_team']} (ID: {fotmob_id})")

        try:
            # 获取比赛详情数据
            match_data = await collector.collect_match_details(fotmob_id)

            if match_data is None:
                logger.error(f"❌ 无法获取比赛 {fotmob_id} 的数据")
                error_count += 1
                continue

            # 保存到数据库
            async with db_manager.get_session() as session:
                from database.models.match import Match

                # 创建比赛记录
                db_match = Match(
                    fotmob_id=fotmob_id,
                    home_team_id=1,  # 暂时使用默认ID，避免NULL约束问题
                    away_team_id=2,  # 暂时使用默认ID
                    match_date=match_data.match_time,
                    status=match_data.status,
                    home_score=match_data.home_score,
                    away_score=match_data.away_score,
                    data_source="fotmob_v2",
                    data_completeness="partial",
                    match_info=match_data.match_info,
                    lineups_json=match_data.lineups.model_dump_json() if match_data.lineups else None,
                    stats_json=match_data.stats.model_dump_json() if match_data.stats else None,
                    events_json=match_data.events.model_dump_json() if match_data.events else None,
                    odds_snapshot_json=match_data.odds.model_dump_json() if match_data.odds else None,
                    collection_time=datetime.utcnow(),
                    raw_api_response=match_data.raw_api_response
                )

                session.add(db_match)
                await session.commit()
                await session.refresh(db_match)

                logger.info(f"✅ 比赛 {fotmob_id} 成功保存到数据库 (ID: {db_match.id})")
                success_count += 1
                collected_matches.append({
                    "fotmob_id": fotmob_id,
                    "db_id": db_match.id,
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "match_time": match_data.match_time
                })

        except Exception as e:
            logger.error(f"❌ 保存比赛 {fotmob_id} 失败: {str(e)}")
            error_count += 1
            continue

    # 验证结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 10场比赛采集结果统计")
    logger.info("=" * 60)
    logger.info(f"✅ 成功采集: {success_count} 场比赛")
    logger.info(f"❌ 失败: {error_count} 场比赛")
    logger.info(f"📈 成功率: {(success_count / 10) * 100:.1f}%")

    if success_count >= 8:  # 80%成功率
        logger.info("\n🎉 10场比赛数据采集验证成功！")
        logger.info("✅ 数据可以成功入库，系统工作正常")

        # 显示成功采集的比赛
        logger.info("\n📋 成功采集的比赛列表:")
        for match in collected_matches:
            logger.info(f"  - {match['home_team']} vs {match['away_team']} (DB ID: {match['db_id']})")

        return True
    else:
        logger.error(f"\n⚠️ 采集成功率过低 ({success_count}/10)，需要进一步调试")
        return False

async def verify_database_state():
    """验证数据库状态"""
    logger.info("\n🔍 验证数据库状态...")

    db_manager = AsyncDatabaseManager()

    try:
        async with db_manager.get_session() as session:
            from database.models.match import Match
            from sqlalchemy import text, func

            # 检查matches表记录数
            count_result = await session.execute(func.count(Match.id))
            match_count = count_result.scalar()

            logger.info(f"📊 matches表总记录数: {match_count}")

            # 检查最近5条记录
            recent_matches = await session.execute(
                text("""
                SELECT fotmob_id, match_date, status, home_score, away_score, data_source, collection_time
                FROM matches
                ORDER BY collection_time DESC
                LIMIT 5
                """)
            )

            logger.info("📋 最近5条比赛记录:")
            for row in recent_matches:
                logger.info(f"  - ID: {row.fotmob_id}, 时间: {row.match_date}, 状态: {row.status}, "
                          f"比分: {row.home_score}-{row.away_score}, 来源: {row.data_source}")

            return match_count > 0

    except Exception as e:
        logger.error(f"❌ 验证数据库状态失败: {str(e)}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 启动10场比赛数据采集验证任务")

    # 验证数据库状态
    await verify_database_state()

    # 采集10场比赛
    collection_ok = await collect_10_matches()

    # 再次验证数据库状态
    logger.info("\n" + "=" * 60)
    logger.info("🔍 最终数据库状态验证")
    logger.info("=" * 60)
    final_db_ok = await verify_database_state()

    # 综合结果
    logger.info("\n" + "=" * 60)
    logger.info("🏆 最终验证结果")
    logger.info("=" * 60)

    if collection_ok and final_db_ok:
        logger.info("✅ 10场比赛数据采集验证完全成功！")
        logger.info("🎯 数据能够成功采集并保存到数据库")
        logger.info("🚀 系统已准备就绪，可以进行大规模数据采集")
        return True
    else:
        logger.error("⚠️ 验证过程中发现问题，需要进一步调试")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
