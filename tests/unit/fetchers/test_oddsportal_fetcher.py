"""
OddsPortal获取器单元测试
OddsPortal Fetcher Unit Tests

测试OddsPortalFetcher的功能，包括：
1. 赔率数据获取
2. 不同市场类型的数据生成
3. 配置参数处理
4. 异常处理

作者: Quality Assurance Team
创建时间: 2025-12-07
版本: 1.0.0
"""

import pytest
from datetime import datetime
from typing import List

from src.fetchers.oddsportal_fetcher import OddsPortalFetcher
from src.collectors.abstract_fetcher import OddsData, ResourceType
from src.fetchers.fetcher_factory import FetcherFactory


class TestOddsPortalFetcher:
    """OddsPortal获取器测试类"""

    @pytest.fixture
    def fetcher(self) -> OddsPortalFetcher:
        """创建OddsPortalFetcher实例"""
        config = {
            "timeout": 10,
            "max_retries": 2,
            "delay_between_requests": 0.1
        }
        return OddsPortalFetcher(source_name="oddsportal_test", config=config)

    @pytest.fixture
    def sample_match_id(self) -> str:
        """示例比赛ID"""
        return "test_match_123"

    @pytest.mark.asyncio
    async def test_fetch_odds_success(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试成功获取赔率数据"""
        result = await fetcher.fetch_odds(sample_match_id, count=5)

        # 验证返回结果
        assert isinstance(result, list)
        assert len(result) > 0
        assert len(result) <= 5  # 不应超过请求的数量

        # 验证每条记录的结构
        for odds_data in result:
            assert isinstance(odds_data, OddsData)
            assert odds_data.match_id == sample_match_id
            assert odds_data.source == "oddsportal_test"
            assert odds_data.bookmaker is not None
            assert odds_data.market_type is not None
            assert odds_data.timestamp is not None

    @pytest.mark.asyncio
    async def test_fetch_odds_different_markets(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试获取不同市场类型的赔率数据"""
        markets = ["1X2", "Asian Handicap", "Over/Under"]
        result = await fetcher.fetch_odds(
            sample_match_id,
            markets=markets,
            count=6
        )

        # 验证返回了不同市场类型的数据
        market_types = {odds.market_type for odds in result}
        assert len(market_types) > 1  # 应该有多种市场类型

        # 验证1X2市场数据
        odds_1x2 = [odds for odds in result if odds.market_type == "1X2"]
        if odds_1x2:
            odds = odds_1x2[0]
            assert odds.home_win is not None
            assert odds.draw is not None
            assert odds.away_win is not None

        # 验证亚洲让分盘数据
        odds_handicap = [odds for odds in result if odds.market_type == "Asian Handicap"]
        if odds_handicap:
            odds = odds_handicap[0]
            assert odds.asian_handicap_home is not None
            assert odds.asian_handicap_away is not None
            assert odds.asian_handicap_line is not None

        # 验证大小球数据
        odds_ou = [odds for odds in result if odds.market_type == "Over/Under"]
        if odds_ou:
            odds = odds_ou[0]
            assert odds.over_under_line is not None
            assert odds.over_odds is not None
            assert odds.under_odds is not None

    @pytest.mark.asyncio
    async def test_fetch_odds_custom_bookmakers(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试获取指定博彩公司的赔率数据"""
        custom_bookmakers = ["Bet365", "William Hill"]
        result = await fetcher.fetch_odds(
            sample_match_id,
            bookmakers=custom_bookmakers,
            count=4
        )

        # 验证只返回指定博彩公司的数据
        bookmakers_in_result = {odds.bookmaker for odds in result}
        assert bookmakers_in_result.issubset(set(custom_bookmakers))

    @pytest.mark.asyncio
    async def test_fetch_odds_empty_match_id(self, fetcher: OddsPortalFetcher):
        """测试空比赛ID的异常处理"""
        with pytest.raises(ValueError, match="match_id 不能为空"):
            await fetcher.fetch_odds("")

        with pytest.raises(ValueError, match="match_id 不能为空"):
            await fetcher.fetch_odds("   ")

    @pytest.mark.asyncio
    async def test_fetch_general_data(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试获取通用数据接口"""
        # 测试获取赔率数据
        result = await fetcher.fetch_data(
            sample_match_id,
            resource_type=ResourceType.ODDS,
            count=3
        )

        assert isinstance(result, list)
        assert len(result) <= 3
        if result:
            assert isinstance(result[0], dict)
            assert "match_id" in result[0]
            assert "source" in result[0]

        # 测试不支持的资源类型
        result_empty = await fetcher.fetch_data(
            sample_match_id,
            resource_type=ResourceType.FIXTURES
        )

        assert result_empty == []

    def test_initialization_default_config(self):
        """测试默认配置初始化"""
        fetcher = OddsPortalFetcher()

        assert fetcher.source_name == "oddsportal"
        assert fetcher.base_url == "https://www.oddsportal.com"
        assert fetcher.timeout == 30
        assert fetcher.max_retries == 3
        assert fetcher.delay == 1.0
        assert isinstance(fetcher.bookmakers, list)
        assert isinstance(fetcher.market_types, list)

    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "base_url": "https://custom.oddsportal.com",
            "timeout": 15,
            "max_retries": 5,
            "delay_between_requests": 0.5
        }

        fetcher = OddsPortalFetcher(source_name="custom", config=config)

        assert fetcher.source_name == "custom"
        assert fetcher.base_url == "https://custom.oddsportal.com"
        assert fetcher.timeout == 15
        assert fetcher.max_retries == 5
        assert fetcher.delay == 0.5

    @pytest.mark.asyncio
    async def test_validate_connection(self, fetcher: OddsPortalFetcher):
        """测试连接验证"""
        # 连接验证主要是模拟，所以返回值是随机的
        # 只测试方法能正常调用
        result = await fetcher.validate_connection()
        assert isinstance(result, bool)

    def test_get_supported_markets(self, fetcher: OddsPortalFetcher):
        """测试获取支持的市场类型"""
        markets = fetcher.get_supported_markets()

        assert isinstance(markets, list)
        assert len(markets) > 0
        assert "1X2" in markets
        assert "Asian Handicap" in markets
        assert "Over/Under" in markets

    def test_get_supported_bookmakers(self, fetcher: OddsPortalFetcher):
        """测试获取支持的博彩公司"""
        bookmakers = fetcher.get_supported_bookmakers()

        assert isinstance(bookmakers, list)
        assert len(bookmakers) > 0
        assert "Bet365" in bookmakers
        assert "William Hill" in bookmakers

    @pytest.mark.asyncio
    async def test_metadata_tracking(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试元数据跟踪功能"""
        # 获取数据
        await fetcher.fetch_odds(sample_match_id, count=2)

        # 检查元数据是否被记录
        metadata = fetcher.get_metadata(sample_match_id)
        assert metadata is not None
        assert metadata.source == "oddsportal_test"
        assert metadata.resource_id == sample_match_id
        assert metadata.success is True
        assert metadata.error_message is None
        assert metadata.record_count >= 0
        assert metadata.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_data_quality_and_consistency(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试数据质量和一致性"""
        result = await fetcher.fetch_odds(sample_match_id, markets=["1X2"], count=5)

        # 验证数据质量
        for odds in result:
            # 赔率值应该在合理范围内
            if odds.home_win is not None:
                assert 1.0 <= odds.home_win <= 10.0
            if odds.draw is not None:
                assert 1.0 <= odds.draw <= 10.0
            if odds.away_win is not None:
                assert 1.0 <= odds.away_win <= 10.0

            # 时间戳应该是最近的时间
            if odds.last_updated:
                time_diff = datetime.now() - odds.last_updated
                assert time_diff.total_seconds() < 3600  # 不超过1小时前

    @pytest.mark.asyncio
    async def test_market_specific_data_structure(self, fetcher: OddsPortalFetcher, sample_match_id: str):
        """测试市场特定的数据结构"""
        # 测试1X2市场
        odds_1x2 = await fetcher.fetch_odds(
            sample_match_id,
            markets=["1X2"],
            count=1
        )

        if odds_1x2:
            odds = odds_1x2[0]
            assert odds.market_type == "1X2"
            assert odds.home_win is not None
            assert odds.draw is not None
            assert odds.away_win is not None

        # 测试亚洲让分盘
        odds_handicap = await fetcher.fetch_odds(
            sample_match_id,
            markets=["Asian Handicap"],
            count=1
        )

        if odds_handicap:
            odds = odds_handicap[0]
            assert odds.market_type == "Asian Handicap"
            assert odds.asian_handicap_home is not None
            assert odds.asian_handicap_away is not None
            assert odds.asian_handicap_line is not None

        # 测试大小球
        odds_ou = await fetcher.fetch_odds(
            sample_match_id,
            markets=["Over/Under"],
            count=1
        )

        if odds_ou:
            odds = odds_ou[0]
            assert odds.market_type == "Over/Under"
            assert odds.over_under_line is not None
            assert odds.over_odds is not None
            assert odds.under_odds is not None


class TestFetcherFactory:
    """获取器工厂测试类"""

    def test_oddsportal_registration(self):
        """测试OddsPortalFetcher的注册"""
        # 验证获取器已注册
        assert FetcherFactory.is_registered("oddsportal")

        # 获取元数据
        metadata = FetcherFactory.get_metadata("oddsportal")
        assert metadata is not None
        assert metadata["name"] == "oddsportal"
        assert metadata["class_name"] == "OddsPortalFetcher"
        assert metadata["description"] is not None
        assert metadata["version"] == "1.0.0"

    def test_create_oddsportal_fetcher(self):
        """测试创建OddsPortalFetcher实例"""
        fetcher = FetcherFactory.create("oddsportal")

        assert isinstance(fetcher, OddsPortalFetcher)
        assert fetcher.source_name == "oddsportal"

    def test_create_oddsportal_fetcher_with_config(self):
        """测试带配置创建OddsPortalFetcher实例"""
        config = {
            "timeout": 20,
            "max_retries": 5
        }

        fetcher = FetcherFactory.create("oddsportal", config=config)

        assert isinstance(fetcher, OddsPortalFetcher)
        assert fetcher.timeout == 20
        assert fetcher.max_retries == 5

    @pytest.mark.asyncio
    async def test_factory_integration(self):
        """测试工厂集成功能"""
        # 通过工厂创建获取器
        fetcher = FetcherFactory.create("oddsportal")

        # 使用获取器获取数据，指定数量
        result = await fetcher.fetch_odds("integration_test_match", count=3)

        assert isinstance(result, list)
        assert len(result) <= 3
        if result:
            assert result[0].source == "oddsportal"

    def test_list_available_fetchers(self):
        """测试列出可用获取器"""
        available = FetcherFactory.list_available()

        assert isinstance(available, list)
        assert "oddsportal" in available

    def test_registry_info(self):
        """测试注册表信息"""
        info = FetcherFactory.get_registry_info()

        assert isinstance(info, dict)
        assert "total_registered" in info
        assert "available_fetchers" in info
        assert "registry" in info
        assert "metadata" in info
        assert info["total_registered"] >= 1


# 导出测试类
__all__ = [
    "TestOddsPortalFetcher",
    "TestFetcherFactory"
]
