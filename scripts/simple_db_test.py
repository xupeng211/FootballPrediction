#!/usr/bin/env python3
"""
最简单的数据库连接测试
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def simple_database_test():
    """简单数据库连接测试"""
    logger.info("🚀 开始简单数据库连接测试")

    try:
        # 初始化数据库
        from database.async_manager import initialize_database

        initialize_database()
        logger.info("✅ 数据库初始化成功")

        # 检查数据库连接
        from database.async_manager import get_async_db_session
        from sqlalchemy import text

        async for session in get_async_db_session():
            try:
                # 简单查询测试
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.fetchone()
                if test_value and test_value[0] == 1:
                    logger.info("✅ 数据库连接测试成功")
                else:
                    logger.error("❌ 数据库查询结果异常")
                    return False

                # 检查matches表
                result = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name = 'matches'
                """
                    )
                )
                table_exists = result.scalar()
                if table_exists:
                    logger.info("✅ matches表存在")
                else:
                    logger.error("❌ matches表不存在")
                    return False

                # 检查matches表记录数
                result = await session.execute(text("SELECT COUNT(*) FROM matches"))
                match_count = result.scalar()
                logger.info(f"📊 matches表当前有 {match_count} 条记录")

                return True

            finally:
                await session.close()

    except Exception as e:
        logger.error(f"❌ 数据库测试失败: {str(e)}")
        return False


async def test_data_collection_ready():
    """测试数据采集准备状态"""
    logger.info("\n🔍 测试数据采集准备状态")

    try:
        # 检查采集器是否能初始化
        from collectors.fotmob_api_collector import FotMobAPICollector

        FotMobAPICollector()
        logger.info("✅ FotMob采集器初始化成功")

        # 检查环境变量
        import os

        fotmob_token = os.getenv("FOTMOB_TOKEN")
        if fotmob_token:
            logger.info("✅ FOTMOB_TOKEN环境变量已设置")
        else:
            logger.warning("⚠️ FOTMOB_TOKEN环境变量未设置")

        return True

    except Exception as e:
        logger.error(f"❌ 数据采集准备测试失败: {str(e)}")
        return False


async def main():
    """主函数"""
    logger.info("🚀 启动最简单的验证测试")

    # 测试1: 数据库连接
    db_ok = await simple_database_test()

    # 测试2: 数据采集准备
    collection_ready = await test_data_collection_ready()

    logger.info("\n" + "=" * 60)
    logger.info("🏆 验证结果")
    logger.info("=" * 60)
    logger.info(f"数据库连接: {'✅ 成功' if db_ok else '❌ 失败'}")
    logger.info(f"数据采集准备: {'✅ 成功' if collection_ready else '❌ 失败'}")

    if db_ok and collection_ready:
        logger.info("\n🎉 系统基础功能验证成功！")
        logger.info("✅ 数据库连接正常")
        logger.info("✅ 数据采集器初始化正常")
        logger.info("🚀 系统已准备好进行数据采集和保存")
        return True
    else:
        logger.error("\n⚠️ 基础功能验证失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
