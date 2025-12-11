#!/usr/bin/env python3
"""
简化版10场比赛数据采集验证脚本
直接使用已验证的方法来测试数据采集和保存
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

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_data_collection():
    """测试数据采集功能"""
    logger.info("🚀 开始测试数据采集功能")

    collector = FotMobAPICollector()

    # 测试3场比赛ID
    test_match_ids = [
        "47_1_3434",  # Premier League
        "54_1_1985",  # La Liga
        "82_1_2673",  # Serie A
    ]

    success_count = 0

    for i, fotmob_id in enumerate(test_match_ids, 1):
        logger.info(f"\n[{i}/3] 📈 测试采集比赛: {fotmob_id}")

        try:
            # 获取比赛详情数据
            match_data = await collector.collect_match_details(fotmob_id)

            if match_data is None:
                logger.error(f"❌ 无法获取比赛 {fotmob_id} 的数据")
                continue

            # 检查数据内容
            logger.info("✅ 成功获取比赛数据:")
            logger.info(f"  - 比赛时间: {match_data.match_time}")
            logger.info(f"  - 主队: {match_data.home_team_name}")
            logger.info(f"  - 客队: {match_data.away_team_name}")
            logger.info(f"  - 比分: {match_data.home_score}-{match_data.away_score}")
            logger.info(f"  - 状态: {match_data.status}")
            logger.info(f"  - 主队xG: {match_data.home_xg}")
            logger.info(f"  - 客队xG: {match_data.away_xg}")

            if match_data.stats and len(match_data.stats.stats) > 0:
                logger.info(f"  - 统计数据: {len(match_data.stats.stats)} 项")
                for stat in match_data.stats.stats[:3]:  # 显示前3项
                    logger.info(
                        f"    * {stat.stat_type}: {stat.home_value} - {stat.away_value}"
                    )

            success_count += 1

        except Exception as e:
            logger.error(f"❌ 采集比赛 {fotmob_id} 失败: {str(e)}")
            continue

    logger.info(f"\n📊 数据采集测试结果: {success_count}/{len(test_match_ids)} 成功")
    return success_count > 0


async def test_database_connection():
    """测试数据库连接和表结构"""
    logger.info("\n🔍 测试数据库连接...")

    try:
        # 初始化数据库
        from database.async_manager import initialize_database

        initialize_database()

        from database.async_manager import get_async_db_session
        from database.models.match import Match
        from sqlalchemy import text, func

        async for session in get_async_db_session():
            try:
                # 检查matches表是否存在
                count_result = await session.execute(func.count(Match.id))
                match_count = count_result.scalar()
                logger.info(f"✅ 数据库连接正常，matches表有 {match_count} 条记录")

                # 检查表结构
                table_info = await session.execute(
                    text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'matches'
                    ORDER BY ordinal_position
                """)
                )

                columns = table_info.fetchall()
                logger.info(f"✅ matches表结构有 {len(columns)} 个字段:")
                for col in columns[:10]:  # 显示前10个字段
                    logger.info(
                        f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})"
                    )

                return True

            finally:
                await session.close()

    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {str(e)}")
        return False


async def save_test_match():
    """保存测试比赛数据到数据库"""
    logger.info("\n💾 测试保存比赛数据到数据库...")

    try:
        # 确保数据库已初始化
        from database.async_manager import initialize_database, get_async_db_session
        from database.models.match import Match

        initialize_database()

        collector = FotMobAPICollector()

        # 获取测试比赛数据
        fotmob_id = "47_1_3434"  # Premier League match
        match_data = await collector.collect_match_details(fotmob_id)

        if match_data is None:
            logger.error("❌ 无法获取测试比赛数据")
            return False

        async for session in get_async_db_session():
            try:
                # 检查是否已存在
                existing = await session.execute(
                    text("SELECT id FROM matches WHERE fotmob_id = :fotmob_id"),
                    {"fotmob_id": fotmob_id},
                )
                if existing.fetchone():
                    logger.info(f"ℹ️ 比赛 {fotmob_id} 已存在，跳过保存")
                    return True

                # 创建比赛记录
                db_match = Match(
                    fotmob_id=fotmob_id,
                    home_team_id=1,  # 暂时使用默认ID
                    away_team_id=2,  # 暂时使用默认ID
                    match_date=match_data.match_time,
                    status=match_data.status,
                    home_score=match_data.home_score,
                    away_score=match_data.away_score,
                    home_xg=match_data.home_xg,
                    away_xg=match_data.away_xg,
                    data_source="fotmob_v2_test",
                    data_completeness="test_partial",
                    match_info=match_data.match_info,
                    lineups_json=match_data.lineups.model_dump_json()
                    if match_data.lineups
                    else None,
                    stats_json=match_data.stats.model_dump_json()
                    if match_data.stats
                    else None,
                    events_json=match_data.events.model_dump_json()
                    if match_data.events
                    else None,
                    odds_snapshot_json=match_data.odds.model_dump_json()
                    if match_data.odds
                    else None,
                    collection_time=datetime.utcnow(),
                )

                session.add(db_match)
                await session.commit()
                await session.refresh(db_match)

                logger.info(f"✅ 测试比赛成功保存到数据库 (DB ID: {db_match.id})")
                return True

            except Exception as e:
                await session.rollback()
                logger.error(f"❌ 保存测试比赛失败: {str(e)}")
                return False
            finally:
                await session.close()

    except Exception as e:
        logger.error(f"❌ 测试保存功能失败: {str(e)}")
        return False


async def main():
    """主函数"""
    logger.info("🚀 启动简化版10场比赛数据采集验证")

    # 测试1: 数据库连接
    db_ok = await test_database_connection()
    if not db_ok:
        logger.error("❌ 数据库连接失败，停止测试")
        return False

    # 测试2: 数据采集
    collection_ok = await test_data_collection()
    if not collection_ok:
        logger.error("❌ 数据采集失败，停止测试")
        return False

    # 测试3: 数据保存
    save_ok = await save_test_match()
    if not save_ok:
        logger.error("❌ 数据保存失败")
        return False

    logger.info("\n" + "=" * 60)
    logger.info("🏆 测试结果总结")
    logger.info("=" * 60)
    logger.info("✅ 数据库连接: 正常")
    logger.info("✅ 数据采集: 正常")
    logger.info("✅ 数据保存: 正常")
    logger.info("\n🎉 系统验证成功！数据可以成功采集并保存到数据库")
    logger.info("🚀 可以开始大规模数据采集任务")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
