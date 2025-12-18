#!/usr/bin/env python3
"""
测试修复后的 backfill_full_history.py 脚本
Test the fixed backfill_full_history.py script
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def test_initialization():
    """测试初始化部分"""
    try:
        # 导入相关模块
        from database.async_manager import initialize_database
        from collectors.fotmob_api_collector import FotMobAPICollector

        logger.info("✅ 模块导入成功")

        # 测试数据库初始化（同步调用）
        logger.info("🔍 测试数据库初始化...")
        try:
            initialize_database()
            logger.info("✅ 数据库初始化成功（同步调用）")
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False

        # 测试采集器初始化（异步调用）
        logger.info("🔍 测试采集器初始化...")
        try:
            collector = FotMobAPICollector(max_concurrent=2, timeout=30)
            await collector.initialize()
            await collector.close()
            logger.info("✅ 采集器初始化成功（异步调用）")
        except Exception as e:
            logger.error(f"❌ 采集器初始化失败: {e}")
            return False

        return True

    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False

async def test_backfill_engine_initialization():
    """测试回填引擎初始化"""
    try:
        logger.info("🔍 测试回填引擎初始化...")

        # 设置环境变量
        if not os.getenv("DATABASE_URL"):
            os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/football_prediction"

        # 导入回填引擎
        from scripts.backfill_full_history import IndustrialBackfillEngine

        # 创建引擎实例
        engine = IndustrialBackfillEngine()

        # 测试初始化
        await engine.initialize()

        # 测试清理
        await engine.cleanup()

        logger.info("✅ 回填引擎初始化测试成功")
        return True

    except Exception as e:
        logger.error(f"❌ 回填引擎初始化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    logger.info("🧪 开始测试修复后的 backfill_full_history.py")

    # 测试1: 基础初始化
    logger.info("\n📋 测试 1: 基础初始化")
    test1_success = await test_initialization()

    # 测试2: 回填引擎初始化
    logger.info("\n📋 测试 2: 回填引擎初始化")
    test2_success = await test_backfill_engine_initialization()

    # 总结
    logger.info("\n📊 测试总结:")
    logger.info(f"  基础初始化: {'✅ 通过' if test1_success else '❌ 失败'}")
    logger.info(f"  回填引擎初始化: {'✅ 通过' if test2_success else '❌ 失败'}")

    if test1_success and test2_success:
        logger.info("\n🎉 所有测试通过！修复成功！")
        return True
    else:
        logger.error("\n❌ 测试失败，仍有问题需要修复")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
