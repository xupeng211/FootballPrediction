"""赔率收集器模块 (Odds Collector).

负责从各种数据源收集足球比赛赔率数据。
Responsible for collecting football match odds data from various data sources.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, List, Dict, Optional

import curl_cffi.requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from src.core.logging import get_logger
from src.database.models import Odds
from src.database.base import AsyncSessionLocal


class CollectionResult:
    """数据收集结果类."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        count: int = 0,
        cached: bool = False,
        response_time: float = 0.0,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.count = count
        self.cached = cached
        self.response_time = response_time
        self.timestamp = datetime.now()


class OddsCollector:
    """赔率收集器类."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.logger = get_logger(__name__)
        self.base_url = "https://api.football-data.org/v4"
        self.cache = {}

    async def collect_match_odds(self, match_id: int) -> CollectionResult:
        """收集指定比赛的赔率数据.

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含赔率数据的收集结果
        """
        start_time = time.time()
        self.logger.info(f"Collecting odds for match {match_id}")

        try:
            # 检查缓存
            cache_key = f"odds_{match_id}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                response_time = time.time() - start_time
                return CollectionResult(
                    success=True,
                    data=cached_data,
                    count=len(cached_data.get("odds", [])),
                    cached=True,
                    response_time=response_time,
                )

            # 模拟API调用
            await asyncio.sleep(0.1)  # 模拟网络延迟

            # 模拟返回数据
            mock_data = {
                "match_id": match_id,
                "odds": [
                    {
                        "bookmaker": "Bet365",
                        "home_win": 2.10,
                        "draw": 3.40,
                        "away_win": 3.20,
                    },
                    {
                        "bookmaker": "William Hill",
                        "home_win": 2.05,
                        "draw": 3.50,
                        "away_win": 3.25,
                    },
                ],
            }

            # 缓存结果
            self.cache[cache_key] = mock_data

            response_time = time.time() - start_time
            return CollectionResult(
                success=True,
                data=mock_data,
                count=len(mock_data.get("odds", [])),
                cached=False,
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error(f"Failed to collect odds for match {match_id}: {e}")
            return CollectionResult(
                success=False, error=str(e), response_time=response_time
            )

    async def collect_league_odds(self, league_id: int) -> CollectionResult:
        """收集指定联赛的赔率数据.

        Args:
            league_id: 联赛ID

        Returns:
            CollectionResult: 包含赔率数据的收集结果
        """
        start_time = time.time()
        self.logger.info(f"Collecting odds for league {league_id}")

        try:
            # 模拟API调用
            await asyncio.sleep(0.2)

            # 模拟返回数据
            mock_data = {
                "league_id": league_id,
                "matches": [
                    {
                        "match_id": 12345,
                        "home_team": "Team A",
                        "away_team": "Team B",
                        "odds": [
                            {
                                "bookmaker": "Bet365",
                                "home_win": 2.10,
                                "draw": 3.40,
                                "away_win": 3.20,
                            }
                        ],
                    }
                ],
            }

            response_time = time.time() - start_time
            return CollectionResult(
                success=True,
                data=mock_data,
                count=len(mock_data.get("matches", [])),
                cached=False,
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error(f"Failed to collect odds for league {league_id}: {e}")
            return CollectionResult(
                success=False, error=str(e), response_time=response_time
            )

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息.

        Returns:
            Dict[str, Any]: 缓存统计数据
        """
        return {"cache_size": len(self.cache), "cache_keys": list(self.cache.keys())}

    def clear_cache(self) -> None:
        """清空缓存."""
        self.cache.clear()
        self.logger.info("Cache cleared")

    async def save_odds_to_database(self, match_id: int, odds_data: List[Dict[str, Any]]) -> int:
        """将赔率数据保存到数据库.

        Args:
            match_id: 比赛ID
            odds_data: 赔率数据列表

        Returns:
            int: 保存的赔率记录数量
        """
        if not odds_data:
            return 0

        saved_count = 0
        async with AsyncSessionLocal() as session:
            try:
                # 检查是否已存在相同的赔率记录
                for odds_item in odds_data:
                    bookmaker = odds_item.get("bookmaker", "Unknown")

                    # 保存主胜赔率
                    if "home_win" in odds_item:
                        home_win_odds = Odds(
                            match_id=match_id,
                            bookmaker=bookmaker,
                            bet_type="home_win",
                            odds_value=Decimal(str(odds_item["home_win"])),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(home_win_odds)
                        saved_count += 1

                    # 保存平局赔率
                    if "draw" in odds_item:
                        draw_odds = Odds(
                            match_id=match_id,
                            bookmaker=bookmaker,
                            bet_type="draw",
                            odds_value=Decimal(str(odds_item["draw"])),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(draw_odds)
                        saved_count += 1

                    # 保存客胜赔率
                    if "away_win" in odds_item:
                        away_win_odds = Odds(
                            match_id=match_id,
                            bookmaker=bookmaker,
                            bet_type="away_win",
                            odds_value=Decimal(str(odds_item["away_win"])),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(away_win_odds)
                        saved_count += 1

                await session.commit()
                self.logger.info(f"✅ 成功保存 {saved_count} 条赔率记录到数据库 (match_id: {match_id})")

            except Exception as e:
                await session.rollback()
                self.logger.error(f"❌ 保存赔率数据失败: {e}")
                raise

        return saved_count

    async def collect_and_save_odds(self, match_id: int) -> CollectionResult:
        """收集并保存指定比赛的赔率数据.

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含处理结果的收集结果
        """
        start_time = time.time()

        try:
            # 收集赔率数据
            collection_result = await self.collect_match_odds(match_id)

            if not collection_result.success:
                return collection_result

            # 保存到数据库
            odds_data = collection_result.data.get("odds", [])
            saved_count = await self.save_odds_to_database(match_id, odds_data)

            response_time = time.time() - start_time
            return CollectionResult(
                success=True,
                data=collection_result.data,
                count=saved_count,
                cached=collection_result.cached,
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error(f"Failed to collect and save odds for match {match_id}: {e}")
            return CollectionResult(
                success=False, error=str(e), response_time=response_time
            )

    async def get_collection_stats(self) -> dict[str, Any]:
        """获取收集统计信息.

        Returns:
            Dict[str, Any]: 统计数据
        """
        # 这里可以实现真实的统计逻辑
        return {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "cache_hit_rate": 0.0,
            "average_response_time": 0.0,
        }
