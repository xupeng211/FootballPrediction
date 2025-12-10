#!/usr/bin/env python3
"""
快速验证数据采集和保存功能
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from database.async_manager import initialize_database, get_async_db_session
from database.models.match import Match

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def test_basic_database_operation():
    """测试基本的数据库操作"""
    logger.info("🚀 开始基本数据库操作测试")

    # 初始化数据库
    initialize_database()
    logger.info("✅ 数据库初始化成功")

    async with get_async_db_session() as session:
        try:
            # 检查matches表
            from sqlalchemy import text, func

            count_result = await session.execute(func.count(Match.id))
            match_count = count_result.scalar()
            logger.info(f"📊 当前数据库中有 {match_count} 场比赛")

            # 插入一条测试记录
            test_match = Match(
                fotmob_id="test_123",
                home_team_id=1,
                away_team_id=2,
                match_date=datetime.utcnow(),
                status="Test",
                home_score=0,
                away_score=0,
                data_source="test_script",
                data_completeness="test",
                collection_time=datetime.utcnow()
            )

            session.add(test_match)
            await session.commit()
            await session.refresh(test_match)

            logger.info(f"✅ 测试比赛成功插入，ID: {test_match.id}")

            # 再次检查记录数
            count_result = await session.execute(func.count(Match.id))
            new_match_count = count_result.scalar()
            logger.info(f"📊 插入后数据库中有 {new_match_count} 场比赛")

            return True

        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {str(e)}")
            await session.rollback()
            return False

async def verify_data_with_api():
    """验证API数据采集"""
    logger.info("\n🌐 开始API数据采集验证")

    try:
        from collectors.fotmob_api_collector import FotMobAPICollector

        collector = FotMobAPICollector()

        # 尝试获取一个简单的比赛ID
        test_id = "47_1_3434"  # Premier League match
        logger.info(f"📡 尝试获取比赛数据: {test_id}")

        match_data = await collector.collect_match_details(test_id)

        if match_data:
            logger.info("✅ API数据采集成功!")
            logger.info(f"  - 比赛: {match_data.home_team_name} vs {match_data.away_team_name}")
            logger.info(f"  - 时间: {match_data.match_time}")
            logger.info(f"  - 比分: {match_data.home_score}-{match_data.away_score}")
            logger.info(f"  - xG: {match_data.home_xg}-{match_data.away_xg}")
            return True
        else:
            logger.error("❌ API数据采集失败")
            return False

    except Exception as e:
        logger.error(f"❌ API测试失败: {str(e)}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 启动快速验证测试")

    # 测试1: 基本数据库操作
    db_test = await test_basic_database_operation()

    # 测试2: API数据采集
    api_test = await verify_data_with_api()

    logger.info("\n" + "=" * 60)
    logger.info("🏆 快速验证结果")
    logger.info("=" * 60)
    logger.info(f"数据库操作: {'✅ 成功' if db_test else '❌ 失败'}")
    logger.info(f"API数据采集: {'✅ 成功' if api_test else '❌ 失败'}")

    if db_test and api_test:
        logger.info("\n🎉 核心功能验证成功！")
        logger.info("✅ 数据库读写功能正常")
        logger.info("✅ API数据采集功能正常")
        logger.info("🚀 系统已准备好进行数据采集")
        return True
    else:
        logger.error("\n⚠️ 部分功能验证失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
