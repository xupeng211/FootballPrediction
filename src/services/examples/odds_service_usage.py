"""
OddsService 使用示例
OddsService Usage Examples

展示如何使用OddsService进行赔率数据的获取、处理和保存。

作者: Business Logic Team
创建时间: 2025-12-07
版本: 1.0.0
"""

import asyncio
import logging
from typing import List

from src.collectors.abstract_fetcher import OddsData, FetcherFactory
from src.collectors.examples.example_fetcher import ExampleFetcher
from src.services.odds_service import OddsService
from src.database.dao.odds_dao import OddsDAO
from src.database.dao.match_dao import MatchDAO
from src.database.async_manager import get_db_session
from src.database.dao.exceptions import DatabaseConnectionError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_odds_service() -> OddsService:
    """
    设置OddsService实例

    Returns:
        OddsService: 配置好的服务实例
    """
    # 获取数据库会话
    async with get_db_session() as session:
        # 创建DAO实例
        odds_dao = OddsDAO(session=session)
        match_dao = MatchDAO(session=session)

        # 创建服务实例
        odds_service = OddsService(odds_dao=odds_dao, match_dao=match_dao)

        return odds_service


async def example_ingest_odds_data():
    """
    示例1: 直接摄取赔率数据
    """
    logger.info("=== 示例1: 直接摄取赔率数据 ===")

    try:
        # 设置服务
        odds_service = await setup_odds_service()

        # 创建示例赔率数据
        sample_odds_data = [
            OddsData(
                match_id="12345",
                source="example_source",
                home_win=2.45,
                draw=3.20,
                away_win=2.80,
                bookmaker="Example Bookmaker",
                market_type="1X2",
                raw_data={"source": "example_api", "timestamp": "2025-12-07T10:00:00Z"}
            ),
            OddsData(
                match_id="12346",
                source="example_source",
                asian_handicap_home=1.95,
                asian_handicap_away=1.85,
                asian_handicap_line=-0.5,
                bookmaker="Example Bookmaker",
                market_type="Asian Handicap"
            ),
            OddsData(
                match_id="12347",
                source="another_source",
                home_win=1.90,
                draw=3.60,
                away_win=4.20,
                bookmaker="Another Bookmaker",
                market_type="1X2"
            )
        ]

        # 摄取数据
        result = await odds_service.ingest_odds_data(sample_odds_data)

        # 输出结果
        logger.info(f"数据摄取完成: {result.to_dict()}")

    except DatabaseConnectionError as e:
        logger.error(f"数据库连接错误: {e}")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")


async def example_fetch_and_save_odds():
    """
    示例2: 从数据源获取并保存赔率数据
    """
    logger.info("=== 示例2: 从数据源获取并保存赔率数据 ===")

    try:
        # 注册示例获取器
        FetcherFactory.register("example", ExampleFetcher)

        # 设置服务
        odds_service = await setup_odds_service()

        # 从数据源获取并保存赔率数据
        result = await odds_service.fetch_and_save_odds("example", "12348")

        # 输出结果
        logger.info(f"获取并保存完成: {result.to_dict()}")

    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")


async def example_batch_processing():
    """
    示例3: 批量处理多个数据源
    """
    logger.info("=== 示例3: 批量处理多个数据源 ===")

    try:
        # 注册多个示例获取器
        FetcherFactory.register("source1", ExampleFetcher)
        FetcherFactory.register("source2", ExampleFetcher)

        # 设置服务
        odds_service = await setup_odds_service()

        # 要处理的比赛ID列表
        match_ids = ["12349", "12350", "12351"]
        sources = ["source1", "source2"]

        total_results = {}

        # 批量处理
        for source in sources:
            for match_id in match_ids:
                try:
                    logger.info(f"处理: source={source}, match_id={match_id}")

                    result = await odds_service.fetch_and_save_odds(source, match_id)
                    total_results[f"{source}_{match_id}"] = result.to_dict()

                except Exception as e:
                    logger.error(f"处理失败: source={source}, match_id={match_id}, error={e}")
                    total_results[f"{source}_{match_id}"] = {"error": str(e)}

        # 统计总体结果
        total_processed = sum(r.get("total_processed", 0) for r in total_results.values() if isinstance(r, dict))
        total_successful = sum(r.get("successful_inserts", 0) + r.get("successful_updates", 0)
                              for r in total_results.values() if isinstance(r, dict))

        logger.info("批量处理完成:")
        logger.info(f"  - 总处理记录数: {total_processed}")
        logger.info(f"  - 总成功记录数: {total_successful}")
        logger.info(f"  - 成功率: {(total_successful / max(total_processed, 1)) * 100:.2f}%")

    except Exception as e:
        logger.error(f"批量处理过程中发生错误: {e}")


async def example_error_handling():
    """
    示例4: 错误处理和异常情况
    """
    logger.info("=== 示例4: 错误处理和异常情况 ===")

    try:
        # 设置服务
        odds_service = await setup_odds_service()

        # 创建包含错误数据的示例
        invalid_odds_data = [
            OddsData(
                match_id="",  # 无效的空match_id
                source="test_source",
                home_win=2.45,
                bookmaker="Test Bookmaker"
            ),
            OddsData(
                match_id="12352",
                source="test_source",
                home_win=0.5,  # 无效的赔率值（小于1.0）
                bookmaker="Test Bookmaker"
            ),
            OddsData(
                match_id="12353",
                source="test_source",
                # 没有任何赔率值
                bookmaker="Test Bookmaker"
            ),
            # 一条有效数据
            OddsData(
                match_id="12354",
                source="test_source",
                home_win=2.10,
                draw=3.40,
                away_win=3.20,
                bookmaker="Test Bookmaker"
            )
        ]

        # 处理包含错误的数据
        result = await odds_service.ingest_odds_data(invalid_odds_data)

        logger.info(f"错误处理测试完成: {result.to_dict()}")

        # 尝试从不存在的数据源获取数据
        try:
            await odds_service.fetch_and_save_odds("nonexistent_source", "12355")
        except Exception as e:
            logger.info(f"预期的错误（不存在的数据源）: {e}")

    except Exception as e:
        logger.error(f"错误处理测试中发生意外错误: {e}")


async def main():
    """
    主函数：运行所有示例
    """
    logger.info("开始运行OddsService示例")

    try:
        # 运行所有示例
        await example_ingest_odds_data()
        await asyncio.sleep(1)  # 短暂延迟

        await example_fetch_and_save_odds()
        await asyncio.sleep(1)

        await example_batch_processing()
        await asyncio.sleep(1)

        await example_error_handling()

    except Exception as e:
        logger.error(f"示例运行过程中发生错误: {e}")

    logger.info("OddsService示例运行完成")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
