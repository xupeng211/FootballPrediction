"""
赔率数据采集器

实现足球赔率数据的采集逻辑。
包含高频采集、时间窗口去重、赔率变化检测等功能。

采集策略：
- 每5分钟高频采集
- 基于时间戳窗口去重
- 只保存有变化的赔率
- 多博彩公司数据聚合

基于 DATA_DESIGN.md 第1.1节设计。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import asyncio
import logging

from .base_collector import DataCollector, CollectionResult


class OddsCollector(DataCollector):
    """
    赔率数据采集器

    负责从多个博彩公司API采集赔率数据，
    实现高频更新和变化检测机制。
    """

    def __init__(
        self,
        data_source: str = "odds_api",
        api_key: Optional[str] = None,
        base_url: str = "https://api.the-odds-api.com/v4",
        time_window_minutes: int = 5,
        **kwargs,
    ):
        """
        初始化赔率采集器

        Args:
            data_source: 数据源名称
            api_key: API密钥
            base_url: API基础URL
            time_window_minutes: 去重时间窗口（分钟）
        """
        super().__init__(data_source, **kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.time_window_minutes = time_window_minutes

        # 赔率去重：记录最近采集的赔率键值
        self._recent_odds_keys: Set[str] = set()  # type: ignore
        # 赔率变化：记录上次赔率值
        self._last_odds_values: Dict[str, Dict[str, Decimal]] = {}  # type: ignore

    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """赔率采集器不处理赛程数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="fixtures",
            records_collected=0,
            success_count=0,
            error_count=0,
            status="skipped",
        )

    async def collect_odds(
        self,
        match_ids: Optional[List[str]] = None,
        bookmakers: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
        **kwargs,
    ) -> CollectionResult:
        """
        采集赔率数据

        去重策略：
        - 基于 match_id + bookmaker + market + timestamp 生成唯一键
        - 时间窗口内的重复数据跳过
        - 只保存有变化的赔率值

        Args:
            match_ids: 需要采集的比赛ID列表
            bookmakers: 博彩公司列表
            markets: 市场类型列表（1x2、over_under等）

        Returns:
            CollectionResult: 采集结果
        """
        collected_data = []
        success_count = 0
        error_count = 0
        error_messages = []

        try:
            # 设置默认参数
            if not bookmakers:
                bookmakers = await self._get_active_bookmakers()
            if not markets:
                markets = ["h2h", "spreads", "totals"]  # 1x2、让球、大小球
            if not match_ids:
                match_ids = await self._get_upcoming_matches()

            self.logger.info(
                f"Starting odds collection for {len(match_ids)} matches, "
                f"{len(bookmakers)} bookmakers, {len(markets)} markets"
            )

            # 清理过期的去重缓存
            await self._clean_expired_odds_cache()

            # 按比赛采集赔率数据
            for match_id in match_ids:
                try:
                    match_odds = await self._collect_match_odds(
                        match_id, bookmakers, markets
                    )

                    # 处理每个赔率数据
                    for odds_data in match_odds:
                        try:
                            # 时间窗口去重检查
                            odds_key = self._generate_odds_key(odds_data)
                            if odds_key in self._recent_odds_keys:
                                self.logger.debug(
                                    f"Skipping duplicate odds: {odds_key}"
                                )
                                continue

                            # 赔率变化检测
                            if await self._has_odds_changed(odds_data):
                                # 数据清洗和标准化
                                cleaned_odds = await self._clean_odds_data(odds_data)
                                if cleaned_odds:
                                    collected_data.append(cleaned_odds)
                                    self._recent_odds_keys.add(odds_key)
                                    success_count += 1
                                else:
                                    error_count += 1
                                    error_messages.append(
                                        f"Invalid odds data: {odds_data}"
                                    )
                            else:
                                self.logger.debug(f"No odds change for: {odds_key}")

                        except Exception as e:
                            error_count += 1
                            error_messages.append(f"Error processing odds: {str(e)}")
                            self.logger.error(f"Error processing odds: {str(e)}")

                except Exception as e:
                    error_count += 1
                    error_messages.append(
                        f"Error collecting match {match_id}: {str(e)}"
                    )
                    self.logger.error(f"Error collecting match {match_id}: {str(e)}")

            # 保存到Bronze层原始数据表
            if collected_data:
                await self._save_to_bronze_layer("raw_odds_data", collected_data)

            # 确定最终状态
            total_collected = len(collected_data)
            if error_count == 0:
                status = "success"
            elif success_count > 0:
                status = "partial"
            else:
                status = "failed"

            result = CollectionResult(
                data_source=self.data_source,
                collection_type="odds",
                records_collected=total_collected,
                success_count=success_count,
                error_count=error_count,
                status=status,
                error_message="; ".join(error_messages[:5]) if error_messages else None,
                collected_data=collected_data,
            )

            self.logger.info(
                f"Odds collection completed: "
                f"collected={total_collected}, success={success_count}, errors={error_count}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Odds collection failed: {str(e)}")
            return CollectionResult(
                data_source=self.data_source,
                collection_type="odds",
                records_collected=0,
                success_count=0,
                error_count=1,
                status="failed",
                error_message=str(e),
            )

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """赔率采集器不处理实时比分数据"""
        return CollectionResult(
            data_source=self.data_source,
            collection_type="live_scores",
            records_collected=0,
            success_count=0,
            error_count=0,
            status="skipped",
        )

    async def _get_active_bookmakers(self) -> List[str]:
        """
        获取活跃的博彩公司列表

        Returns:
            List[str]: 博彩公司代码列表
        """
        try:
            # TODO: 从数据库或配置获取博彩公司列表
            # 目前返回主要博彩公司作为示例
            return [
                "bet365",
                "pinnacle",
                "williamhill",
                "betfair",
                "unibet",
                "marathonbet",
            ]
        except Exception as e:
            self.logger.error(f"Failed to get active bookmakers: {str(e)}")
            return ["bet365", "pinnacle"]  # 默认返回主要的两家

    async def _get_upcoming_matches(self) -> List[str]:
        """
        获取即将开始的比赛列表

        Returns:
            List[str]: 比赛ID列表
        """
        try:
            # TODO: 从数据库查询未来24小时内的比赛
            # 目前返回空列表作为占位符
            return []
        except Exception as e:
            self.logger.error(f"Failed to get upcoming matches: {str(e)}")
            return []

    async def _clean_expired_odds_cache(self) -> None:
        """清理过期的赔率缓存"""
        try:
            # TODO: 实现基于时间窗口的缓存清理
            # 清理超过time_window_minutes的缓存条目
            pass
        except Exception as e:
            self.logger.error(f"Failed to clean odds cache: {str(e)}")

    async def _collect_match_odds(
        self, match_id: str, bookmakers: List[str], markets: List[str]
    ) -> List[Dict[str, Any]]:
        """
        采集指定比赛的赔率数据

        Args:
            match_id: 比赛ID
            bookmakers: 博彩公司列表
            markets: 市场类型列表

        Returns:
            List[Dict]: 赔率数据列表
        """
        all_odds = []

        try:
            for market in markets:
                url = f"{self.base_url}/sports/soccer/odds"
                params = {
                    "apiKey": self.api_key,
                    "markets": market,
                    "bookmakers": ",".join(bookmakers),
                    "eventIds": match_id,
                }

                response = await self._make_request(url=url, params=params)

                # 处理响应数据
                for event in response:
                    for bookmaker in event.get(str("bookmakers"), []):  # type: ignore
                        for market_data in bookmaker.get(str("markets"), []):
                            odds_data = {
                                "match_id": match_id,
                                "bookmaker": bookmaker.get("key"),
                                "market_type": market_data.get("key"),
                                "outcomes": market_data.get(str("outcomes"), []),
                                "last_update": market_data.get("last_update"),
                                "event_data": event,
                            }
                            all_odds.append(odds_data)

        except Exception as e:
            self.logger.error(f"Failed to collect odds for match {match_id}: {str(e)}")

        return all_odds

    def _generate_odds_key(self, odds_data: Dict[str, Any]) -> str:
        """
        生成赔率唯一键（时间窗口去重）

        Args:
            odds_data: 赔率原始数据

        Returns:
            str: 赔率唯一键
        """
        # 基于比赛、博彩公司、市场类型、时间窗口生成键
        timestamp = datetime.now()
        time_window = timestamp.replace(
            minute=(timestamp.minute // self.time_window_minutes)
            * self.time_window_minutes,
            second=0,
            microsecond=0,
        )

        key_components = [
            str(odds_data.get(str("match_id"), "")),
            str(odds_data.get(str("bookmaker"), "")),
            str(odds_data.get(str("market_type"), "")),
            time_window.isoformat(),
        ]

        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()  # type: ignore

    async def _has_odds_changed(self, odds_data: Dict[str, Any]) -> bool:
        """
        检查赔率是否发生变化

        Args:
            odds_data: 新的赔率数据

        Returns:
            bool: 是否有变化
        """
        try:
            odds_id = f"{odds_data.get('match_id')}:{odds_data.get('bookmaker')}:{odds_data.get('market_type')}"

            # 提取当前赔率值
            current_odds = {}
            for outcome in odds_data.get(str("outcomes"), []):
                current_odds[outcome.get(str("name"), "")] = Decimal(  # type: ignore
                    str(outcome.get(str("price"), 0))
                )

            # 与上次记录的值比较
            if odds_id in self._last_odds_values:
                last_odds = self._last_odds_values[odds_id]
                # 检查是否有任何赔率发生变化
                for name, value in current_odds.items():
                    if name not in last_odds or abs(last_odds[name] - value) > Decimal(  # type: ignore
                        "0.01"
                    ):
                        self._last_odds_values[odds_id] = current_odds
                        return True
                return False
            else:
                # 首次记录，视为有变化
                self._last_odds_values[odds_id] = current_odds
                return True

        except Exception as e:
            self.logger.error(f"Failed to check odds change: {str(e)}")
            return True  # 出错时默认认为有变化

    async def _clean_odds_data(
        self, raw_odds: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        清洗和标准化赔率数据

        Args:
            raw_odds: 原始赔率数据

        Returns:
            Optional[Dict]: 清洗后的数据，无效则返回None
        """
        try:
            # 基础字段验证
            required_fields = ["match_id", "bookmaker", "market_type", "outcomes"]
            if not all(field in raw_odds for field in required_fields):
                return None

            # 赔率值验证和标准化
            cleaned_outcomes = []
            for outcome in raw_odds.get(str("outcomes"), []):
                price = outcome.get("price")
                if price and float(price) > 1.0:  # 赔率必须大于1
                    cleaned_outcomes.append(
                        {
                            "name": outcome.get("name"),
                            "price": round(float(price), 3),  # 保留3位小数
                        }
                    )

            if not cleaned_outcomes:
                return None

            cleaned_data = {
                "external_match_id": str(raw_odds["match_id"]),
                "bookmaker": str(raw_odds["bookmaker"]),
                "market_type": str(raw_odds["market_type"]),
                "outcomes": cleaned_outcomes,
                "last_update": raw_odds.get("last_update"),
                "raw_data": raw_odds,
                "collected_at": datetime.now().isoformat(),
                "processed": False,
            }

            return cleaned_data

        except Exception as e:
            self.logger.error(f"Failed to clean odds data: {str(e)}")
            return None
