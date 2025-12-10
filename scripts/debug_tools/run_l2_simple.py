#!/usr/bin/env python3
"""
L2简化批处理作业
L2 Simple Batch Job
直接使用现有的L2作业进行测试
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from src.collectors.fotmob_api_collector import FotMobAPICollector, MatchDetailData
from src.database.async_manager import get_db_session
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def simple_batch_test():
    """简化的批处理测试"""
    try:
        logger.info("🚀 启动简化L2批处理测试")

        # 直接初始化API采集器
        collector = FotMobAPICollector(
            max_concurrent=5,
            timeout=30,
            base_delay=2.0,
            enable_proxy=False,
            enable_jitter=True
        )

        await collector.initialize()
        logger.info("✅ 采集器初始化完成")

        # 获取待处理比赛ID
        async with get_db_session() as session:
            query = text("""
                SELECT fotmob_id
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND data_completeness = 'partial'
                LIMIT 10
            """)

            result = await session.execute(query)
            match_ids = [row[0] for row in result.fetchall()]

            logger.info(f"📊 找到 {len(match_ids)} 场测试比赛")

        # 处理比赛
        success_count = 0
        for i, match_id in enumerate(match_ids, 1):
            logger.info(f"🔄 处理比赛 {i}/{len(match_ids)}: {match_id}")

            try:
                # 采集数据
                match_data = await collector.collect_match_details(match_id)

                if match_data:
                    # 更新数据库
                    async with get_db_session() as session:
                        update_query = text("""
                            UPDATE matches SET
                                home_xg = :home_xg,
                                away_xg = :away_xg,
                                stats_json = :stats_json,
                                data_completeness = 'complete',
                                updated_at = NOW()
                            WHERE fotmob_id = :fotmob_id
                        """)

                        await session.execute(update_query, {
                            "fotmob_id": match_id,
                            "home_xg": match_data.xg_home,
                            "away_xg": match_data.xg_away,
                            "stats_json": match_data.stats_json
                        })
                        await session.commit()

                        logger.info(f"✅ 成功更新: {match_id}, xG: {match_data.xg_home}-{match_data.xg_away}")
                        success_count += 1
                else:
                    logger.warning(f"⚠️ 采集失败: {match_id}")

                # 延迟
                if i < len(match_ids):
                    await asyncio.sleep(2.0)

            except Exception as e:
                logger.error(f"❌ 处理失败 {match_id}: {e}")

        # 统计结果
        logger.info(f"🎉 测试完成!")
        logger.info(f"✅ 成功: {success_count}/{len(match_ids)}")

        # 显示采集器统计
        stats = collector.get_stats()
        logger.info(f"📊 采集器统计: {stats}")

        await collector.close()
        return success_count > 0

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_batch_test())
    sys.exit(0 if success else 1)