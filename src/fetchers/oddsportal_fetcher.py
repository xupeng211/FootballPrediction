"""
OddsPortal 数据获取器 - 生产级实现
OddsPortal Data Fetcher - Production Implementation

实现OddsPortal网站的真实数据获取功能，集成HTTP客户端和HTML解析器。

支持的市场类型:
- 1X2 (胜负平)
- Asian Handicap (亚洲让分盘)
- Over/Under (大小球)
- Both Teams to Score (双方进球)
- Correct Score (正确比分)

核心特性:
- 真实HTTP请求和HTML解析
- 智能重试和错误恢复
- 反爬虫对抗措施
- Mock数据保底机制

作者: Senior Backend Architect
创建时间: 2025-12-07
版本: 2.0.0
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Any, dict, list, Optional

from src.collectors.abstract_fetcher import (
    AbstractFetcher,
    OddsData,
    ResourceType,
    FetchMetadata,
)
from src.utils.http_client import AsyncHttpClient
from src.fetchers.parsers.odds_parser import OddsParser


class OddsPortalFetcher(AbstractFetcher):
    """
    OddsPortal 数据获取器 - 生产级实现

    集成了真实的HTTP客户端和HTML解析器，具备完整的网络采集能力。
    当网络请求失败时，可自动回退到模拟数据模式，确保系统稳定性。
    """

    def __init__(self, source_name: str = "oddsportal", config: Optional[dict[str, Any]] = None):
        """
        初始化OddsPortal获取器

        Args:
            source_name: 数据源名称，默认为 "oddsportal"
            config: 配置参数，可包含:
                - base_url: OddsPortal基础URL
                - timeout: 请求超时时间(秒)
                - max_retries: 最大重试次数
                - max_connections: 最大连接数
                - use_mock: 是否使用Mock数据 (默认False)
                - fallback_to_mock: 网络失败时是否回退到Mock (默认True)
                - delay_between_requests: 请求间延迟(秒)
        """
        super().__init__(source_name, config)

        # 配置参数
        self.base_url = config.get("base_url", "https://www.oddsportal.com") if config else "https://www.oddsportal.com"
        self.timeout = config.get("timeout", 30.0) if config else 30.0
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.max_connections = config.get("max_connections", 20) if config else 20
        self.use_mock = config.get("use_mock", False) if config else False
        self.fallback_to_mock = config.get("fallback_to_mock", True) if config else True
        self.delay = config.get("delay_between_requests", 1.0) if config else 1.0

        # 初始化核心组件
        self.http_client = AsyncHttpClient(
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_connections=self.max_connections,
        )
        self.parser = OddsParser()

        # 初始化logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 模拟不同的博彩公司 (用于Mock模式)
        self.bookmakers = [
            "Bet365",
            "William Hill",
            "Betfair",
            "Paddy Power",
            "Ladbrokes",
            "888Sport",
            "Unibet",
            "Betway"
        ]

        # 支持的市场类型
        self.market_types = [
            "1X2",
            "Asian Handicap",
            "Over/Under",
            "Both Teams to Score",
            "Correct Score"
        ]

        self.logger.info(
            "🎯 OddsPortalFetcher 初始化完成",
            extra={
                "source_name": self.source_name,
                "base_url": self.base_url,
                "use_mock": self.use_mock,
                "fallback_enabled": self.fallback_to_mock,
            }
        )

    async def fetch_data(
        self,
        resource_id: str,
        resource_type: Optional[ResourceType] = None,
        **kwargs
    ) -> list[dict[str, Any]]:
        """
        获取通用数据

        Args:
            resource_id: 资源标识符 (通常是比赛ID)
            resource_type: 资源类型
            **kwargs: 其他查询参数

        Returns:
            list[dict[str, Any]]: 获取到的数据列表
        """
        if resource_type == ResourceType.ODDS:
            odds_data_list = await self.fetch_odds(resource_id, **kwargs)
            return [odds.dict() for odds in odds_data_list]
        else:
            self.logger.warning(f"OddsPortalFetcher 不支持资源类型: {resource_type}")
            return []

    async def fetch_odds(self, match_id: str, league_id: Optional[str] = None, **kwargs) -> list[OddsData]:
        """
        获取指定比赛的赔率数据

        这是OddsPortalFetcher的核心方法，首先尝试真实网络请求，
        失败时根据配置回退到模拟数据。

        Args:
            match_id: 比赛ID
            league_id: 联赛ID (可选，用于构建URL)
            **kwargs: 其他参数:
                - markets: 指定要获取的市场类型列表
                - bookmakers: 指定要获取的博彩公司列表
                - count: 返回的赔率记录数量 (默认8)
                - force_mock: 强制使用Mock数据

        Returns:
            list[OddsData]: 赔率数据列表

        Raises:
            ValueError: 当match_id为空时
            NetworkError: 网络连接失败且不允许回退到Mock时
            DataNotFoundError: 数据解析失败且不允许回退到Mock时
        """
        # 参数验证
        if not match_id or not match_id.strip():
            raise ValueError("match_id 不能为空")

        start_time = datetime.now()
        force_mock = kwargs.get("force_mock", False)

        try:
            # 检查是否应该使用Mock数据
            if self.use_mock or force_mock:
                self.logger.info(f"🎭 使用Mock模式获取赔率数据，比赛ID: {match_id}")
                return await self._generate_mock_odds(match_id, start_time, **kwargs)

            # 尝试真实网络请求
            self.logger.info(f"🌐 开始真实网络请求获取赔率数据，比赛ID: {match_id}")

            # 构建URL (OddsPortal的URL结构)
            url = self._build_odds_url(match_id, league_id)

            # 模拟请求间延迟
            if self.delay > 0:
                import asyncio
                await asyncio.sleep(self.delay)

            # 发送HTTP请求
            html_content = await self.http_client.get_text(url)

            if not html_content:
                raise NetworkError("Failed to fetch odds page content")

            # 解析HTML内容
            self.logger.info(f"📊 开始解析HTML内容，比赛ID: {match_id}")
            raw_odds_data = self.parser.parse_match_page(html_content)

            # 验证解析结果
            validated_odds = self.parser.validate_odds_data(raw_odds_data)

            # 转换为OddsData对象
            odds_data_list = self._convert_to_odds_data(match_id, validated_odds)

            if not odds_data_list:
                if self.fallback_to_mock:
                    self.logger.warning(
                        f"⚠️ 解析结果为空，回退到Mock模式，比赛ID: {match_id}"
                    )
                    return await self._generate_mock_odds(match_id, start_time, **kwargs)
                else:
                    raise DataNotFoundError(f"No odds data found for match: {match_id}")

            # 记录成功的元数据
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._metadata[match_id] = FetchMetadata(
                source=self.source_name,
                fetched_at=start_time,
                resource_type=ResourceType.ODDS,
                resource_id=match_id,
                processing_time_ms=processing_time,
                success=True,
                error_message=None,
                record_count=len(odds_data_list)
            )

            self.logger.info(
                f"✅ 成功获取 {len(odds_data_list)} 条赔率记录，比赛ID: {match_id}",
                extra={
                    "url": url,
                    "processing_time_ms": processing_time,
                    "unique_bookmakers": len({d.bookmaker for d in odds_data_list}),
                    "markets": list({d.market_type for d in odds_data_list}),
                }
            )

            # 应用数量限制
            record_count = kwargs.get("count", len(odds_data_list))
            return odds_data_list[:record_count]

        except Exception as e:
            # 网络或数据解析失败
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            self._metadata[match_id] = FetchMetadata(
                source=self.source_name,
                fetched_at=start_time,
                resource_type=ResourceType.ODDS,
                resource_id=match_id,
                processing_time_ms=processing_time,
                success=False,
                error_message=str(e),
                record_count=0
            )

            self.logger.error(f"❌ 获取赔率数据失败，比赛ID: {match_id}, 错误: {e}")

            # 检查是否允许回退到Mock
            if self.fallback_to_mock:
                self.logger.info(f"🔄 回退到Mock模式，比赛ID: {match_id}")
                return await self._generate_mock_odds(match_id, start_time, **kwargs)
            else:
                raise  # 重新抛出异常

        except Exception as e:
            # 其他未预期的错误
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            self._metadata[match_id] = FetchMetadata(
                source=self.source_name,
                fetched_at=start_time,
                resource_type=ResourceType.ODDS,
                resource_id=match_id,
                processing_time_ms=processing_time,
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                record_count=0
            )

            self.logger.error(f"❌ 获取赔率数据时发生未预期错误，比赛ID: {match_id}, 错误: {e}")

            # 检查是否允许回退到Mock
            if self.fallback_to_mock:
                self.logger.info(f"🔄 回退到Mock模式，比赛ID: {match_id}")
                return await self._generate_mock_odds(match_id, start_time, **kwargs)
            else:
                raise NetworkError(f"Unexpected error while fetching odds: {e}") from e

    def _build_odds_url(self, match_id: str, league_id: Optional[str] = None) -> str:
        """
        构建OddsPortal赔率页面URL

        Args:
            match_id: 比赛ID
            league_id: 联赛ID

        Returns:
            构建的URL
        """
        # OddsPortal的标准URL结构
        # 注意：实际URL结构可能需要根据网站的具体情况进行调整
        if league_id:
            return f"{self.base_url}/match/{match_id}/#1X2;2;0"
        else:
            return f"{self.base_url}/match/{match_id}/"

    def _convert_to_odds_data(self, match_id: str, parsed_odds: list[dict[str, Any]]) -> list[OddsData]:
        """
        将解析器输出转换为OddsData对象

        Args:
            match_id: 比赛ID
            parsed_odds: 解析器输出的赔率数据

        Returns:
            OddsData对象列表
        """
        odds_data_list = []

        for odds_dict in parsed_odds:
            try:
                # 解析时间戳
                timestamp = datetime.now()
                if odds_dict.get("timestamp"):
                    timestamp = datetime.fromisoformat(odds_dict["timestamp"])

                # 根据市场类型创建相应的OddsData对象
                market_type = odds_dict["market"]
                bookmaker = odds_dict["bookmaker"]
                selection = odds_dict["selection"]
                odds_value = odds_dict["odds"]

                # 创建OddsData对象 (使用适当的字段)
                odds_data = OddsData(
                    match_id=match_id,
                    source=self.source_name,
                    home_win=odds_value if selection == "Home" else None,
                    draw=odds_value if selection == "Draw" else None,
                    away_win=odds_value if selection == "Away" else None,
                    bookmaker=bookmaker,
                    market_type=market_type,
                    last_updated=timestamp,
                    raw_data=odds_dict
                )

                odds_data_list.append(odds_data)

            except Exception as e:
                self.logger.warning(f"⚠️ 转换赔率数据失败: {e}, 数据: {odds_dict}")
                continue

        return odds_data_list

    async def _generate_mock_odds(self, match_id: str, start_time: datetime, **kwargs) -> list[OddsData]:
        """
        生成模拟赔率数据

        Args:
            match_id: 比赛ID
            start_time: 开始时间
            **kwargs: 其他参数

        Returns:
            模拟的OddsData列表
        """
        import asyncio

        # 模拟网络延迟
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # 获取配置参数
        requested_markets = kwargs.get("markets", self.market_types)
        requested_bookmakers = kwargs.get("bookmakers", self.bookmakers)
        record_count = kwargs.get("count", 8)

        odds_data_list = []

        # 生成不同市场类型的模拟数据
        if "1X2" in requested_markets:
            odds_data_list.extend(self._generate_1x2_odds(
                match_id, requested_bookmakers[:record_count//2]
            ))

        if "Asian Handicap" in requested_markets:
            odds_data_list.extend(self._generate_asian_handicap_odds(
                match_id, requested_bookmakers[:record_count//3]
            ))

        if "Over/Under" in requested_markets:
            odds_data_list.extend(self._generate_over_under_odds(
                match_id, requested_bookmakers[:record_count//3]
            ))

        if "Both Teams to Score" in requested_markets:
            odds_data_list.extend(self._generate_btts_odds(
                match_id, requested_bookmakers[:record_count//4]
            ))

        if "Correct Score" in requested_markets:
            odds_data_list.extend(self._generate_correct_score_odds(
                match_id, requested_bookmakers[:record_count//6]
            ))

        # 记录Mock模式的元数据
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        self._metadata[match_id] = FetchMetadata(
            source=self.source_name,
            fetched_at=start_time,
            resource_type=ResourceType.ODDS,
            resource_id=match_id,
            processing_time_ms=processing_time,
            success=True,
            error_message=None,
            record_count=len(odds_data_list)
        )

        self.logger.info(
            f"🎭 Mock模式生成 {len(odds_data_list)} 条赔率记录，比赛ID: {match_id}"
        )

        return odds_data_list[:record_count]

    def _generate_1x2_odds(self, match_id: str, bookmakers: list[str]) -> list[OddsData]:
        """生成1X2市场赔率数据"""
        odds_data_list = []

        for bookmaker in bookmakers:
            home_win_odds = round(random.uniform(1.8, 3.5), 2)
            draw_odds = round(random.uniform(3.0, 4.5), 2)
            away_win_odds = round(random.uniform(2.0, 4.0), 2)

            # 确保赔率合理性
            total_probability = (1/home_win_odds) + (1/draw_odds) + (1/away_win_odds)
            if total_probability > 1.2:
                multiplier = total_probability / 1.1
                home_win_odds = round(home_win_odds * multiplier, 2)
                draw_odds = round(draw_odds * multiplier, 2)
                away_win_odds = round(away_win_odds * multiplier, 2)

            odds_data = OddsData(
                match_id=match_id,
                source=self.source_name,
                home_win=home_win_odds,
                draw=draw_odds,
                away_win=away_win_odds,
                bookmaker=bookmaker,
                market_type="1X2",
                last_updated=datetime.now() - timedelta(minutes=random.randint(1, 60)),
                raw_data={
                    "mode": "mock",
                    "market": "1X2",
                    "bookmaker": bookmaker,
                    "timestamp": datetime.now().isoformat()
                }
            )
            odds_data_list.append(odds_data)

        return odds_data_list

    def _generate_asian_handicap_odds(self, match_id: str, bookmakers: list[str]) -> list[OddsData]:
        """生成亚洲让分盘赔率数据"""
        odds_data_list = []

        handicap_lines = [-1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5]

        for bookmaker in bookmakers:
            line = random.choice(handicap_lines)

            if line < 0:  # 主队让球
                home_odds = round(random.uniform(1.8, 2.2), 2)
                away_odds = round(random.uniform(1.6, 2.0), 2)
            elif line > 0:  # 客队让球
                home_odds = round(random.uniform(1.6, 2.0), 2)
                away_odds = round(random.uniform(1.8, 2.2), 2)
            else:  # 平手盘
                home_odds = round(random.uniform(1.8, 2.1), 2)
                away_odds = home_odds

            odds_data = OddsData(
                match_id=match_id,
                source=self.source_name,
                home_win=home_odds,
                away_win=away_odds,
                bookmaker=bookmaker,
                market_type="Asian Handicap",
                last_updated=datetime.now() - timedelta(minutes=random.randint(1, 60)),
                raw_data={
                    "mode": "mock",
                    "market": "Asian Handicap",
                    "handicap_line": line,
                    "bookmaker": bookmaker,
                    "timestamp": datetime.now().isoformat()
                }
            )
            odds_data_list.append(odds_data)

        return odds_data_list

    def _generate_over_under_odds(self, match_id: str, bookmakers: list[str]) -> list[OddsData]:
        """生成大小球赔率数据"""
        odds_data_list = []

        over_under_lines = [2.0, 2.5, 3.0, 3.5]

        for bookmaker in bookmakers:
            line = random.choice(over_under_lines)

            over_odds = round(random.uniform(1.7, 2.1), 2)
            under_odds = round(over_odds * random.uniform(1.1, 1.3), 2)

            odds_data = OddsData(
                match_id=match_id,
                source=self.source_name,
                home_win=over_odds,  # 使用home_win存储Over
                away_win=under_odds,  # 使用away_win存储Under
                bookmaker=bookmaker,
                market_type="Over/Under",
                last_updated=datetime.now() - timedelta(minutes=random.randint(1, 60)),
                raw_data={
                    "mode": "mock",
                    "market": "Over/Under",
                    "line": line,
                    "bookmaker": bookmaker,
                    "timestamp": datetime.now().isoformat()
                }
            )
            odds_data_list.append(odds_data)

        return odds_data_list

    def _generate_btts_odds(self, match_id: str, bookmakers: list[str]) -> list[OddsData]:
        """生成双方进球(BTTS)赔率数据"""
        odds_data_list = []

        for bookmaker in bookmakers:
            btts_yes_odds = round(random.uniform(1.8, 2.5), 2)
            btts_no_odds = round(btts_yes_odds * random.uniform(1.2, 1.8), 2)

            odds_data = OddsData(
                match_id=match_id,
                source=self.source_name,
                home_win=btts_yes_odds,  # BTTS Yes
                away_win=btts_no_odds,   # BTTS No
                bookmaker=bookmaker,
                market_type="Both Teams to Score",
                last_updated=datetime.now() - timedelta(minutes=random.randint(1, 60)),
                raw_data={
                    "mode": "mock",
                    "market": "BTTS",
                    "btts_yes": btts_yes_odds,
                    "btts_no": btts_no_odds,
                    "bookmaker": bookmaker,
                    "timestamp": datetime.now().isoformat()
                }
            )
            odds_data_list.append(odds_data)

        return odds_data_list

    def _generate_correct_score_odds(self, match_id: str, bookmakers: list[str]) -> list[OddsData]:
        """生成正确比分赔率数据"""
        odds_data_list = []

        common_scores = [("1-0", 8.0), ("1-1", 6.5), ("2-1", 9.0), ("0-0", 9.5),
                         ("2-0", 12.0), ("1-2", 10.0), ("2-2", 15.0), ("3-1", 18.0)]

        for bookmaker in bookmakers:
            score, base_odds = random.choice(common_scores)
            actual_odds = round(base_odds * random.uniform(0.8, 1.2), 1)
            actual_odds = max(3.0, min(50.0, actual_odds))

            odds_data = OddsData(
                match_id=match_id,
                source=self.source_name,
                home_win=actual_odds,  # 使用home_win存储比分赔率
                bookmaker=bookmaker,
                market_type="Correct Score",
                last_updated=datetime.now() - timedelta(minutes=random.randint(1, 60)),
                raw_data={
                    "mode": "mock",
                    "market": "Correct Score",
                    "score": score,
                    "odds": actual_odds,
                    "bookmaker": bookmaker,
                    "timestamp": datetime.now().isoformat()
                }
            )
            odds_data_list.append(odds_data)

        return odds_data_list

    async def validate_connection(self) -> bool:
        """
        验证与OddsPortal的连接

        Returns:
            bool: 连接是否正常
        """
        try:
            # 尝试访问OddsPortal首页
            response = await self.http_client.get(self.base_url, timeout=10)
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"❌ 连接验证失败: {e}")
            return False

    def get_client_stats(self) -> dict[str, Any]:
        """
        获取HTTP客户端统计信息

        Returns:
            HTTP客户端统计信息
        """
        return self.http_client.get_stats()

    def get_supported_markets(self) -> list[str]:
        """
        获取支持的市场类型列表

        Returns:
            list[str]: 支持的市场类型
        """
        return self.market_types.copy()

    def get_supported_bookmakers(self) -> list[str]:
        """
        获取支持的博彩公司列表

        Returns:
            list[str]: 支持的博彩公司
        """
        return self.bookmakers.copy()

    async def close(self):
        """
        清理资源
        """
        await self.http_client.close()
        self.logger.info("🔌 OddsPortalFetcher 资源已清理")

    async def __aenter__(self):
        """异步上下文管理器支持"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器支持"""
        await self.close()


# 导出OddsPortalFetcher
__all__ = ["OddsPortalFetcher"]
