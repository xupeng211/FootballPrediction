"""
OddsPortalFetcher 使用示例
OddsPortalFetcher Usage Example

展示如何使用OddsPortalFetcher获取赔率数据。

该示例演示了:
1. 通过工厂创建获取器实例
2. 获取不同市场类型的赔率数据
3. 处理和验证获取到的数据
4. 集成到OddsService中

作者: Data Integration Team
创建时间: 2025-12-07
版本: 1.0.0
"""

import asyncio
import logging
from typing import Any 

from src.fetchers.fetcher_factory import FetcherFactory
from src.fetchers.oddsportal_fetcher import OddsPortalFetcher
from src.collectors.abstract_fetcher import OddsData
from src.services.odds_service import OddsService
from src.services.odds_service import OddsIngestionResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """基本使用示例"""
    logger.info("=== OddsPortalFetcher 基本使用示例 ===")

    try:
        # 1. 通过工厂创建获取器
        fetcher = FetcherFactory.create("oddsportal")

        # 2. 获取指定比赛的赔率数据
        match_id = "premier_league_arsenal_vs_chelsea"
        logger.info(f"获取比赛 {match_id} 的赔率数据...")

        odds_data = await fetcher.fetch_odds(
            match_id=match_id,
            count=10  # 最多10条记录
        )

        logger.info(f"成功获取 {len(odds_data)} 条赔率记录")

        # 3. 显示获取到的数据
        for i, odds in enumerate(odds_data[:3], 1):  # 只显示前3条
            logger.info(f"记录 {i}:")
            logger.info(f"  博彩公司: {odds.bookmaker}")
            logger.info(f"  市场类型: {odds.market_type}")
            logger.info(f"  主胜赔率: {odds.home_win}")
            logger.info(f"  平局赔率: {odds.draw}")
            logger.info(f"  客胜赔率: {odds.away_win}")
            logger.info(f"  更新时间: {odds.last_updated}")
            logger.info("-" * 40)

    except Exception as e:
        logger.error(f"基本使用示例失败: {e}")


async def example_different_markets():
    """不同市场类型示例"""
    logger.info("=== 不同市场类型示例 ===")

    try:
        fetcher = FetcherFactory.create("oddsportal")
        match_id = "champion_league_real_vs_barcelona"

        # 获取不同市场类型的数据
        markets = ["1X2", "Asian Handicap", "Over/Under"]

        for market in markets:
            logger.info(f"\n获取 {market} 市场数据...")
            odds_data = await fetcher.fetch_odds(
                match_id=match_id,
                markets=[market],
                count=3
            )

            if odds_data:
                logger.info(f"找到 {len(odds_data)} 条 {market} 赔率记录")
                for odds in odds_data:
                    if odds.market_type == "1X2":
                        logger.info(f"  {odds.bookmaker}: 主胜={odds.home_win} 平局={odds.draw} 客胜={odds.away_win}")
                    elif odds.market_type == "Asian Handicap":
                        logger.info(f"  {odds.bookmaker}: 让分={odds.asian_handicap_line} 主队={odds.asian_handicap_home} 客队={odds.asian_handicap_away}")
                    elif odds.market_type == "Over/Under":
                        logger.info(f"  {odds.bookmaker}: 线路={odds.over_under_line} 大球={odds.over_odds} 小球={odds.under_odds}")
            else:
                logger.warning(f"未找到 {market} 市场数据")

    except Exception as e:
        logger.error(f"不同市场类型示例失败: {e}")


async def example_custom_bookmakers():
    """自定义博彩公司示例"""
    logger.info("=== 自定义博彩公司示例 ===")

    try:
        fetcher = FetcherFactory.create("oddsportal")
        match_id = "world_cup_brazil_vs_argentina"

        # 指定特定的博彩公司
        custom_bookmakers = ["Bet365", "William Hill", "Betfair"]

        odds_data = await fetcher.fetch_odds(
            match_id=match_id,
            bookmakers=custom_bookmakers,
            count=5
        )

        logger.info(f"从指定博彩公司获取到 {len(odds_data)} 条记录")

        # 按博彩公司分组显示
        bookmaker_groups = {}
        for odds in odds_data:
            bookmaker = odds.bookmaker
            if bookmaker not in bookmaker_groups:
                bookmaker_groups[bookmaker] = []
            bookmaker_groups[bookmaker].append(odds)

        for bookmaker, records in bookmaker_groups.items():
            logger.info(f"\n{bookmaker} 提供的市场:")
            for odds in records:
                logger.info(f"  - {odds.market_type}: {odds.home_win or odds.over_odds or 'N/A'}")

    except Exception as e:
        logger.error(f"自定义博彩公司示例失败: {e}")


async def example_quality_validation():
    """数据质量验证示例"""
    logger.info("=== 数据质量验证示例 ===")

    try:
        fetcher = FetcherFactory.create("oddsportal")
        match_id = "test_quality_match"

        odds_data = await fetcher.fetch_odds(
            match_id=match_id,
            markets=["1X2"],
            count=5
        )

        logger.info(f"获取到 {len(odds_data)} 条记录进行质量验证")

        quality_issues = []

        for odds in odds_data:
            # 验证赔率合理性
            if odds.home_win and odds.draw and odds.away_win:
                # 计算隐含概率
                total_probability = (1/odds.home_win) + (1/odds.draw) + (1/odds.away_win)
                if total_probability > 1.3:  # 如果总概率过高，可能数据有问题
                    quality_issues.append(f"{odds.bookmaker}: 隐含概率过高 ({total_probability:.2f})")

                # 验证赔率范围
                if not (1.0 <= odds.home_win <= 10.0):
                    quality_issues.append(f"{odds.bookmaker}: 主胜赔率异常 ({odds.home_win})")

            # 验证数据新鲜度
            if odds.last_updated:
                time_diff = asyncio.get_event_loop().time() - odds.last_updated.timestamp()
                if time_diff > 3600:  # 超过1小时
                    quality_issues.append(f"{odds.bookmaker}: 数据过期 ({time_diff/3600:.1f}小时前)")

        if quality_issues:
            logger.warning("发现数据质量问题:")
            for issue in quality_issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info("数据质量验证通过，未发现问题")

    except Exception as e:
        logger.error(f"数据质量验证示例失败: {e}")


async def example_service_integration():
    """与OddsService集成示例"""
    logger.info("=== OddsService 集成示例 ===")

    try:
        # 注意：这个示例需要模拟的DAO，实际使用时需要真实的DAO
        from unittest.mock import AsyncMock, Mock

        # 模拟DAO
        mock_odds_dao = Mock()
        mock_match_dao = Mock()
        mock_odds_dao.get_by_match_and_bookmaker = AsyncMock(return_value=None)
        mock_odds_dao.create = AsyncMock(return_value=None)
        mock_match_dao.get.return_value = Mock(id=123)

        # 创建OddsService（这里使用模拟的DAO）
        # odds_service = OddsService(odds_dao=mock_odds_dao, match_dao=mock_match_dao)

        # 创建OddsPortalFetcher
        fetcher = FetcherFactory.create("oddsportal")
        match_id = "service_integration_match"

        # 获取赔率数据
        odds_data_list = await fetcher.fetch_odds(match_id, count=5)

        logger.info(f"获取到 {len(odds_data_list)} 条赔率记录")

        # 模拟将数据传递给OddsService
        # result = await odds_service.ingest_odds_data(odds_data_list)
        # logger.info(f"OddsService 处理结果: {result.to_dict()}")

        # 显示数据摘要
        market_types = {odds.market_type for odds in odds_data_list}
        bookmakers = {odds.bookmaker for odds in odds_data_list}

        logger.info("数据摘要:")
        logger.info(f"  - 市场类型: {', '.join(market_types)}")
        logger.info(f"  - 博彩公司: {', '.join(bookmakers)}")
        logger.info("  - 数据已准备就绪，可传递给OddsService处理")

    except Exception as e:
        logger.error(f"OddsService集成示例失败: {e}")


async def example_fetcher_info():
    """获取器信息示例"""
    logger.info("=== 获取器信息示例 ===")

    try:
        # 显示所有可用的获取器
        available_fetchers = FetcherFactory.list_available()
        logger.info(f"可用的获取器: {available_fetchers}")

        # 显示OddsPortal的详细信息
        metadata = FetcherFactory.get_metadata("oddsportal")
        if metadata:
            logger.info("OddsPortal 获取器信息:")
            logger.info(f"  - 描述: {metadata['description']}")
            logger.info(f"  - 版本: {metadata['version']}")
            logger.info(f"  - 支持的市场: {metadata.get('supported_markets', [])}")
            logger.info(f"  - 支持的博彩公司: {metadata.get('supported_bookmakers', [])}")

        # 创建获取器实例并查看其配置
        fetcher = FetcherFactory.create("oddsportal", timeout=15, max_retries=2)
        logger.info("获取器配置:")
        logger.info(f"  - 源名称: {fetcher.source_name}")
        logger.info(f"  - 基础URL: {fetcher.base_url}")
        logger.info(f"  - 超时时间: {fetcher.timeout}秒")
        logger.info(f"  - 最大重试: {fetcher.max_retries}")

        # 显示支持的市场类型和博彩公司
        logger.info(f"支持的市场类型: {fetcher.get_supported_markets()}")
        logger.info(f"支持的博彩公司: {fetcher.get_supported_bookmakers()}")

    except Exception as e:
        logger.error(f"获取器信息示例失败: {e}")


async def main():
    """主函数：运行所有示例"""
    logger.info("开始运行 OddsPortalFetcher 示例")

    try:
        await example_fetcher_info()
        await asyncio.sleep(0.5)

        await example_basic_usage()
        await asyncio.sleep(0.5)

        await example_different_markets()
        await asyncio.sleep(0.5)

        await example_custom_bookmakers()
        await asyncio.sleep(0.5)

        await example_quality_validation()
        await asyncio.sleep(0.5)

        await example_service_integration()
        await asyncio.sleep(0.5)

        logger.info("OddsPortalFetcher 示例运行完成")

    except Exception as e:
        logger.error(f"示例运行过程中发生错误: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
