#!/usr/bin/env python3
"""
生产版L2批处理 - 修复数据库列问题
Production L2 Batch - Fixed database column issue
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from sqlalchemy import text

from src.collectors.fotmob_api_collector import FotMobAPICollector
from src.database.async_manager import get_db_session, initialize_database

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


async def process_l2_batch(limit=100):
    """处理L2批次"""
    try:
        logger.info("🚀 开始L2批处理")

        # 初始化数据库
        db_url = os.getenv("ASYNC_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction")
        initialize_database(db_url)
        logger.info("✅ 数据库初始化完成")

        # 获取待处理比赛
        async with get_db_session() as session:
            query = text("""
                SELECT fotmob_id, home_team_id, away_team_id
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND home_xg IS NULL
                LIMIT :limit
            """)

            result = await session.execute(query, {"limit": limit})
            matches = result.fetchall()

            logger.info(f"📊 找到 {len(matches)} 场待处理比赛")

            if not matches:
                logger.info("ℹ️ 没有待处理的比赛")
                return

            # 初始化采集器
            collector = FotMobAPICollector(
                max_concurrent=5, timeout=30, base_delay=1.5, enable_proxy=False, enable_jitter=True
            )

            await collector.initialize()
            logger.info("✅ 采集器初始化完成")

            success_count = 0
            error_count = 0

            # 处理每场比赛
            for i, (fotmob_id, home_team, away_team) in enumerate(matches, 1):
                logger.info(f"🔄 [{i}/{len(matches)}] 处理: {fotmob_id}")

                try:
                    # 采集数据
                    match_data = await collector.collect_match_details(fotmob_id)

                    if match_data:
                        logger.info("✅ 数据采集成功")
                        logger.info(f"   xG: 主队{match_data.xg_home} vs 客队{match_data.xg_away}")
                        logger.info(f"   比分: {match_data.home_score}-{match_data.away_score}")

                        # 更新数据库（只更新存在的列）
                        update_query = text("""
                            UPDATE matches SET
                                home_xg = :home_xg,
                                away_xg = :away_xg,
                                home_score = :home_score,
                                away_score = :away_score,
                                status = :status,
                                venue = :venue,
                                referee = :referee,
                                stats_json = :stats_json,
                                lineups_json = :lineups_json,
                                environment_json = :environment_json,
                                data_completeness = 'complete',
                                updated_at = NOW()
                            WHERE fotmob_id = :fotmob_id
                        """)

                        await session.execute(
                            update_query,
                            {
                                "fotmob_id": fotmob_id,
                                "home_xg": match_data.xg_home,
                                "away_xg": match_data.xg_away,
                                "home_score": match_data.home_score,
                                "away_score": match_data.away_score,
                                "status": match_data.status,
                                "venue": match_data.venue,
                                "referee": match_data.referee,
                                "stats_json": json.dumps(match_data.stats_json) if match_data.stats_json else None,
                                "lineups_json": json.dumps(match_data.lineups_json)
                                if match_data.lineups_json
                                else None,
                                "environment_json": json.dumps(match_data.environment_json)
                                if match_data.environment_json
                                else None,
                            },
                        )

                        await session.commit()
                        logger.info("✅ 数据库更新成功")
                        success_count += 1
                    else:
                        logger.warning("⚠️ 数据采集失败")
                        error_count += 1

                except Exception as e:
                    logger.error(f"❌ 处理失败 {fotmob_id}: {e}")
                    error_count += 1
                    await session.rollback()

                # 智能延迟
                if i < len(matches):
                    delay = 1.5 + (i % 3) * 0.3  # 1.5-2.4秒随机延迟
                    await asyncio.sleep(delay)

            # 显示最终统计
            logger.info("🎉 批处理完成!")
            logger.info(f"✅ 成功: {success_count}")
            logger.info(f"❌ 失败: {error_count}")
            if len(matches) > 0:
                logger.info(f"📈 成功率: {(success_count / len(matches)) * 100:.1f}%")

            # 采集器统计
            stats = collector.get_stats()
            logger.info(f"📊 采集器统计: {stats}")

            await collector.close()
            return success_count > 0

    except Exception as e:
        logger.error(f"❌ 批处理失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="L2批处理作业")
    parser.add_argument("--limit", type=int, default=100, help="处理比赛数量限制")

    args = parser.parse_args()

    success = asyncio.run(process_l2_batch(args.limit))

    if success:
        logger.info("🎉 L2批处理作业成功完成!")
    else:
        logger.error("💥 L2批处理作业失败!")

    sys.exit(0 if success else 1)
