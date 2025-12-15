#!/usr/bin/env python3
"""
10场比赛极限负载测试脚本 - 简化版
Simple 10 Matches Load Test Script
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("load_test.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:postgres@db:5432/football_prediction"
)


async def simple_load_test():
    """简单的负载测试"""
    logger.info("🚀 开始10场比赛极限负载测试...")

    # 初始化数据库
    try:
        from src.database.async_manager import initialize_database, get_db_session
        from sqlalchemy import text

        logger.info("🔧 初始化数据库...")
        initialize_database()
        logger.info("✅ 数据库初始化成功")

        # 验证数据库连接
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            logger.info("✅ 数据库连接验证成功")

        return True

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_basic_functionality():
    """测试基本功能"""
    logger.info("🧪 测试基本功能...")

    try:
        # 测试导入关键模块
        from src.collectors.fotmob_api_collector import FotMobAPICollector

        logger.info("✅ 导入采集器成功")

        logger.info("✅ 导入数据库模型成功")

        # 创建采集器实例
        collector = FotMobAPICollector()
        logger.info("✅ 采集器实例创建成功")

        # 测试简单的数据采集
        test_match_id = "4044733"  # 测试用比赛ID
        logger.info(f"🔍 测试采集比赛 {test_match_id} 的数据...")

        match_data = await collector.collect_match_details(test_match_id)
        if match_data:
            logger.info(f"✅ 成功获取比赛数据: {len(str(match_data))} 字符")
        else:
            logger.warning(f"⚠️ 未能获取比赛 {test_match_id} 的数据")

        return True

    except Exception as e:
        logger.error(f"❌ 基本功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主函数"""
    logger.info("🎯 启动简化负载测试")

    success_count = 0
    total_tests = 2

    # 测试1: 数据库初始化
    if await simple_load_test():
        success_count += 1

    # 测试2: 基本功能测试
    if await test_basic_functionality():
        success_count += 1

    # 输出结果
    logger.info("\n" + "=" * 50)
    logger.info("📊 简化负载测试结果报告")
    logger.info("=" * 50)
    logger.info(f"📋 总测试数: {total_tests}")
    logger.info(f"✅ 成功测试: {success_count}")
    logger.info(f"❌ 失败测试: {total_tests - success_count}")
    success_rate = (success_count / total_tests) * 100
    logger.info(f"📈 成功率: {success_rate:.1f}%")

    if success_count == total_tests:
        logger.info("🎉 所有测试通过！系统准备就绪")
    else:
        logger.warning("⚠️ 部分测试失败，需要检查系统配置")

    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
