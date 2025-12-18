#!/usr/bin/env python3
"""
FotMob 详情采集器测试脚本
用于在 Docker 容器内直接运行并验证数据采集功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.collectors.fotmob_details_collector import FotmobDetailsCollector


def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/fotmob_test.log')
        ]
    )


async def test_single_match_collection(match_id: str = "4186358"):
    """
    测试单场比赛数据采集

    Args:
        match_id: 比赛ID，默认使用一场典型的英超比赛
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 开始测试比赛 {match_id} 的数据采集")

    collector = FotmobDetailsCollector()

    try:
        # 执行数据采集
        match_details = await collector.collect_match_details(match_id)

        if match_details:
            logger.info("✅ 数据采集成功!")
            print("\n📊 比赛基本信息:")
            print(f"  比赛 ID: {match_details.match_id}")
            print(f"  主队: {match_details.home_team}")
            print(f"  客队: {match_details.away_team}")
            print(f"  比分: {match_details.home_score} - {match_details.away_score}")
            print(f"  比赛时间: {match_details.match_date}")
            print(f"  比赛状态: {match_details.status}")

            if match_details.odds:
                print("\n💰 市场概率数据:")
                print(f"  主胜概率: {match_details.odds.home_win}")
                print(f"  平局概率: {match_details.odds.draw}")
                print(f"  客胜概率: {match_details.odds.away_win}")

                if match_details.odds.providers:
                    print(f"  数据来源: {list(match_details.odds.providers.keys())}")
            else:
                print("\n⚠️ 未获取到市场概率数据")

            return True
        else:
            logger.error("❌ 数据采集失败 - 返回 None")
            return False

    except Exception as e:
        logger.error(f"❌ 数据采集过程中发生异常: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        return False

    finally:
        await collector.close()


async def test_api_only(match_id: str = "4186358"):
    """
    仅测试API数据获取（不使用Playwright）

    Args:
        match_id: 比赛ID
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 测试API数据获取 - 比赛 {match_id}")

    collector = FotmobDetailsCollector()

    try:
        api_data = await collector.get_match_details(match_id)

        if api_data:
            logger.info("✅ API数据获取成功!")
            match_info = api_data.get("match_info", {})

            print("\n📋 API返回的比赛信息:")
            print(f"  主队: {match_info.get('home_team', 'N/A')}")
            print(f"  客队: {match_info.get('away_team', 'N/A')}")
            print(f"  比分: {match_info.get('home_score', 0)} - {match_info.get('away_score', 0)}")
            print(f"  开始时间: {match_info.get('start_time', 'N/A')}")
            print(f"  比赛完成: {match_info.get('finished', 'N/A')}")

            # 显示数据结构概览
            print("\n🔧 API数据结构概览:")
            for key, value in api_data.items():
                if isinstance(value, dict):
                    print(f"  {key}: dict with {len(value)} keys")
                elif isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                else:
                    print(f"  {key}: {type(value).__name__}")

            return True
        else:
            logger.error("❌ API数据获取失败")
            return False

    except Exception as e:
        logger.error(f"❌ API数据获取异常: {e}")
        return False

    finally:
        await collector.close()


async def test_playwright_only(match_id: str = "4186358"):
    """
    仅测试Playwright数据提取（需要页面访问）

    Args:
        match_id: 比赛ID
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🌐 测试Playwright页面数据提取 - 比赛 {match_id}")

    collector = FotmobDetailsCollector()

    try:
        odds_data = await collector._extract_odds_from_page(match_id)

        if odds_data:
            logger.info("✅ Playwright数据提取成功!")
            print("\n💎 页面提取的市场概率:")
            print(f"  主胜概率: {odds_data.get('home_win', 'N/A')}")
            print(f"  平局概率: {odds_data.get('draw', 'N/A')}")
            print(f"  客胜概率: {odds_data.get('away_win', 'N/A')}")
            print(f"  数据来源策略: {odds_data.get('source', 'N/A')}")

            return True
        else:
            logger.warning("⚠️ Playwright未提取到市场概率数据")
            return False

    except Exception as e:
        logger.error(f"❌ Playwright数据提取异常: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        return False


async def main():
    """主测试函数"""
    setup_logging()
    logger = logging.getLogger(__name__)

    print("🎯 FotMob 详情采集器测试开始")
    print("=" * 50)

    # 测试参数
    test_match_id = "4186358"  # 可以替换为其他有效的比赛ID

    test_results = {
        "api_test": False,
        "playwright_test": False,
        "full_integration_test": False
    }

    try:
        # 测试1: API数据获取
        logger.info("\n📡 执行API数据获取测试...")
        test_results["api_test"] = await test_api_only(test_match_id)

        # 测试2: Playwright数据提取
        logger.info("\n🌐 执行Playwright数据提取测试...")
        test_results["playwright_test"] = await test_playwright_only(test_match_id)

        # 测试3: 完整集成测试
        logger.info("\n🔄 执行完整集成测试...")
        test_results["full_integration_test"] = await test_single_match_collection(test_match_id)

    except Exception as e:
        logger.error(f"测试过程中发生全局异常: {e}")

    # 输出测试结果摘要
    print("\n" + "=" * 50)
    print("📊 测试结果摘要:")
    print(f"  API数据获取: {'✅ 通过' if test_results['api_test'] else '❌ 失败'}")
    print(f"  Playwright提取: {'✅ 通过' if test_results['playwright_test'] else '❌ 失败'}")
    print(f"  完整集成测试: {'✅ 通过' if test_results['full_integration_test'] else '❌ 失败'}")

    success_count = sum(test_results.values())
    total_tests = len(test_results)

    if success_count == total_tests:
        print(f"\n🎉 所有测试通过! ({success_count}/{total_tests})")
        return 0
    else:
        print(f"\n⚠️ 部分测试失败 ({success_count}/{total_tests})")
        return 1


if __name__ == "__main__":
    # 直接运行的one-liner命令
    import os

    print("🚀 FotMob L2 详情采集器测试")
    print("使用方法:")
    print("  python scripts/test_fotmob_details_collector.py")
    print("  或者在 Docker 容器内:")
    print("  docker-compose exec app python scripts/test_fotmob_details_collector.py")
    print()

    # 设置事件循环策略（在某些容器环境中需要）
    if sys.platform == 'linux' and os.getenv('DOCKER_ENV'):
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
