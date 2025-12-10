#!/usr/bin/env python3
"""
手动L2数据采集 - 直接使用已验证的采集器
Manual L2 Data Collection - Direct approach
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from src.collectors.fotmob_api_collector import FotMobAPICollector, MatchDetailData
from src.database.async_manager import AsyncDatabaseManager
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    try:
        logger.info("🚀 手动L2数据采集开始")

        # 手动初始化数据库管理器
        db_url = os.getenv("ASYNC_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction")
        db_manager = AsyncDatabaseManager(db_url)
        await db_manager.initialize()

        # 使用数据库管理器创建session
        async with db_manager.get_session() as session:
            # 查询待处理比赛
            query = text("""
                SELECT fotmob_id, home_team_name, away_team_name
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND data_completeness = 'partial'
                LIMIT 5
            """)

            result = await session.execute(query)
            matches = result.fetchall()

            logger.info(f"📊 找到 {len(matches)} 场待处理比赛")

            if not matches:
                logger.info("ℹ️ 没有待处理的比赛")
                return

            # 初始化采集器
            collector = FotMobAPICollector(
                max_concurrent=3,
                timeout=30,
                base_delay=2.0,
                enable_proxy=False,
                enable_jitter=True
            )

            await collector.initialize()
            logger.info("✅ 采集器初始化完成")

            # 处理每场比赛
            for i, (fotmob_id, home_team, away_team) in enumerate(matches, 1):
                logger.info(f"🔄 处理 {i}/{len(matches)}: {fotmob_id} ({home_team} vs {away_team})")

                try:
                    # 采集数据
                    match_data = await collector.collect_match_details(fotmob_id)

                    if match_data:
                        logger.info("✅ 数据采集成功")
                        logger.info(f"   xG: 主队{match_data.xg_home} vs 客队{match_data.xg_away}")
                        logger.info(f"   比分: {match_data.home_score}-{match_data.away_score}")
                        logger.info(f"   状态: {match_data.status}")

                        # 检查JSON数据
                        if match_data.stats_json:
                            logger.info(f"   技术统计: {len(match_data.stats_json)} 个字段")

                        if match_data.lineups_json:
                            logger.info(f"   阵容数据: {len(match_data.lineups_json)} 个部分")

                        # 更新数据库
                        update_query = text("""
                            UPDATE matches SET
                                home_xg = :home_xg,
                                away_xg = :away_xg,
                                home_score = :home_score,
                                away_score = :away_score,
                                status = :status,
                                stats_json = :stats_json,
                                lineups_json = :lineups_json,
                                environment_json = :environment_json,
                                data_completeness = 'complete',
                                updated_at = NOW()
                            WHERE fotmob_id = :fotmob_id
                        """)

                        await session.execute(update_query, {
                            "fotmob_id": fotmob_id,
                            "home_xg": match_data.xg_home,
                            "away_xg": match_data.xg_away,
                            "home_score": match_data.home_score,
                            "away_score": match_data.away_score,
                            "status": match_data.status,
                            "stats_json": json.dumps(match_data.stats_json) if match_data.stats_json else None,
                            "lineups_json": json.dumps(match_data.lineups_json) if match_data.lineups_json else None,
                            "environment_json": json.dumps(match_data.environment_json) if match_data.environment_json else None
                        })

                        await session.commit()
                        logger.info("✅ 数据库更新成功")
                    else:
                        logger.warning("⚠️ 数据采集失败")

                except Exception as e:
                    logger.error(f"❌ 处理失败 {fotmob_id}: {e}")
                    await session.rollback()

                # 延迟
                if i < len(matches):
                    logger.info("⏳ 等待 3 秒...")
                    await asyncio.sleep(3.0)

            # 显示最终统计
            stats = collector.get_stats()
            logger.info("🎉 采集完成!")
            logger.info(f"📊 采集器统计: {stats}")

            await collector.close()
            await db_manager.close()

    except Exception as e:
        logger.error(f"❌ 主程序失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
