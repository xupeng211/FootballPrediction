"""
赔率收集器核心
Odds Collector Core

协调各个组件完成赔率收集任务
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from src.cache.redis_manager import RedisManager
from .time_utils_compat import utc_now

from .analyzer import OddsAnalyzer
from .processor import OddsProcessor
from .sources import OddsSourceManager
from .storage import OddsStorage

logger = logging.getLogger(__name__)


class OddsCollector:
    """
    赔率收集器
    Odds Collector

    从多个博彩公司收集赔率数据，支持实时更新和历史追踪。
    Collects odds data from multiple bookmakers with real-time updates and history tracking.
    """

    def __init__(
        self,
        db_session,
        redis_manager: RedisManager,
        api_key: Optional[str] = None,
        update_interval: int = 300,  # 5分钟
    ):
        """
        初始化赔率收集器

        Args:
            db_session: 数据库会话
            redis_manager: Redis管理器
            api_key: API密钥
            update_interval: 更新间隔（秒）
        """
        self.db_session = db_session
        self.redis_manager = redis_manager
        self.update_interval = update_interval

        # 初始化组件
        self.source_manager = OddsSourceManager(api_key)
        self.processor = OddsProcessor()
        self.analyzer = OddsAnalyzer(redis_manager)
        self.storage = OddsStorage(db_session, redis_manager)

        # 支持的博彩公司
        self.bookmakers = [
            "bet365",
            "william_hill",
            "ladbrokes",
            "betfair",
            "pinnacle",
            "betway",
            "888sport",
            "unibet",
            "betfred",
            "coral",
        ]

        # 支持的市场类型
        self.market_types = [
            "match_winner",
            "over_under",
            "handicap",
            "both_teams_score",
            "correct_score",
        ]

        # 状态管理
        self.running = False
        self.update_task: Optional[asyncio.Task] = None

        # 性能统计
        self.stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "api_calls": 0,
            "unique_matches": 0,
            "average_processing_time": 0.0,
        }

    async def start_collection(self):
        """启动赔率收集"""
        if self.running:
            logger.warning("赔率收集器已在运行")
            return

        self.running = True
        logger.info("启动赔率收集器")

        # 启动定期更新任务
        self.update_task = asyncio.create_task(self._periodic_update())

    async def stop_collection(self):
        """停止赔率收集"""
        self.running = False
        logger.info("停止赔率收集器")

        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

    async def collect_match_odds(
        self,
        match_id: int,
        bookmakers: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        收集指定比赛的赔率数据

        Args:
            match_id: 比赛ID
            bookmakers: 指定博彩公司列表
            markets: 指定市场类型列表
            force: 是否强制更新

        Returns:
            Dict[str, Any]: 赔率数据
        """
        bookmakers = bookmakers or self.bookmakers
        markets = markets or self.market_types

        # 检查缓存
        cached_data = self.storage.check_cache(
            match_id, bookmakers, markets, cache_duration_minutes=5
        )
        if not force and cached_data:
            return cached_data

        try:
            start_time = utc_now()

            # 获取比赛信息
            match = await self.storage.get_match_info(match_id)
            if not match:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 从API获取赔率
            odds_data = await self.source_manager.fetch_odds_from_apis(
                match_id, bookmakers, markets
            )

            # 处理和分析赔率
            processed_data = await self.processor.process_odds_data(
                match_id, odds_data
            )

            if processed_data:
                # 验证数据
                if not self.processor.validate_odds_data(processed_data):
                    logger.warning(f"比赛 {match_id} 的赔率数据验证失败")
                    return {}

                # 更新缓存
                self.storage.update_cache(match_id, bookmakers, markets, processed_data)

                # 保存到数据库
                success = await self.storage.save_odds_data(processed_data)
                if not success:
                    logger.error(f"保存比赛 {match_id} 赔率数据失败")
                    return {}

                # 识别价值投注
                value_bets = await self.analyzer.identify_value_bets(processed_data)
                if value_bets:
                    processed_data["value_bets"] = value_bets

                # 市场效率分析
                market_analysis = self.analyzer.analyze_market_efficiency(processed_data)
                processed_data["market_analysis"].update(market_analysis)

                # 检查套利机会
                arbitrage_opps = self.analyzer.calculate_arbitrage_opportunities(
                    processed_data
                )
                if arbitrage_opps:
                    processed_data["arbitrage_opportunities"] = arbitrage_opps

                # 发布更新通知
                await self.storage.publish_odds_update(processed_data)

                # 更新统计
                self._update_stats(start_time)

                return processed_data

            return {}

        except Exception as e:
            logger.error(f"收集比赛 {match_id} 赔率失败: {e}")
            self.stats["failed_updates"] += 1
            return {}

    async def collect_upcoming_matches_odds(
        self,
        hours_ahead: int = 48,
        max_matches: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        收集即将开始比赛的赔率

        Args:
            hours_ahead: 未来多少小时
            max_matches: 最大比赛数

        Returns:
            List[Dict[str, Any]]: 赔率数据列表
        """
        # 获取即将开始的比赛
        upcoming_matches = await self.storage.get_upcoming_matches(
            hours_ahead, max_matches
        )

        if not upcoming_matches:
            return []

        # 批量收集赔率
        tasks = [
            self.collect_match_odds(match["id"]) for match in upcoming_matches
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        odds_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"收集比赛 {upcoming_matches[i]['id']} 赔率失败: {result}"
                )
            elif result:
                result.update(upcoming_matches[i])
                odds_list.append(result)

        return odds_list

    async def get_odds_history(
        self,
        match_id: int,
        bookmaker: str,
        market: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        获取赔率历史数据

        Args:
            match_id: 比赛ID
            bookmaker: 博彩公司
            market: 市场类型
            hours: 历史时长（小时）

        Returns:
            List[Dict[str, Any]]: 历史赔率数据
        """
        return await self.storage.get_odds_history(
            match_id, bookmaker, market, hours
        )

    async def _periodic_update(self):
        """定期更新赔率"""
        logger.info("启动定期赔率更新")

        while self.running:
            try:
                # 收集即将开始的比赛赔率
                await self.collect_upcoming_matches_odds()
                self.stats["api_calls"] += 1

                # 等待下次更新
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定期更新失败: {e}")
                await asyncio.sleep(60)

    def _update_stats(self, start_time):
        """更新统计信息"""
        self.stats["total_updates"] += 1
        self.stats["successful_updates"] += 1
        self.stats["unique_matches"] = len(self.storage.odds_cache)

        processing_time = (utc_now() - start_time).total_seconds()
        self.stats["average_processing_time"] = (
            self.stats["average_processing_time"]
            * (self.stats["successful_updates"] - 1)
            + processing_time
        ) / self.stats["successful_updates"]

    def get_stats(self) -> Dict[str, Any]:
        """获取收集统计信息"""
        return {
            **self.stats,
            "running": self.running,
            "cached_odds": len(self.storage.odds_cache),
            "success_rate": (
                self.stats["successful_updates"] / self.stats["total_updates"]
                if self.stats["total_updates"] > 0
                else 0.0
            ),
        }