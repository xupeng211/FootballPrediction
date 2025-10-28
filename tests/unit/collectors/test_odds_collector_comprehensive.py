# TODO: Consider creating a fixture for 5 repeated Mock creations

# TODO: Consider creating a fixture for 5 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
OddsCollector 综合测试
提升 collectors 模块覆盖率的关键测试
"""

import asyncio

# 测试导入
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest

sys.path.insert(0, "src")

try:
    from src.collectors.odds_collector import OddsCollector
    from src.database.models import Bookmaker, OddsData
    from src.utils.time_utils import utc_now

    ODDSCOLLECTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import OddsCollector: {e}")
    ODDSCOLLECTOR_AVAILABLE = False


@pytest.mark.skipif(not ODDSCOLLECTOR_AVAILABLE, reason="OddsCollector not available")
@pytest.mark.unit
class TestOddsCollector:
    """OddsCollector测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        with patch("src.collectors.odds_collector.RedisManager"):
            collector = OddsCollector(
                api_key="test_key", base_url="https://api.test.odds.com", timeout=30
            )
            return collector

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.add = Mock()
        return session

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return {
            "match_id": 12345,
            "bookmaker": "Bet365",
            "home_win": 2.15,
            "draw": 3.40,
            "away_win": 3.20,
            "over_under_2_5_over": 1.85,
            "over_under_2_5_under": 1.95,
            "last_updated": "2024-01-01T15:30:00Z",
        }

    @pytest.mark.asyncio
    async def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector.api_key == "test_key"
        assert collector.base_url == "https://api.test.odds.com"
        assert collector.timeout == 30

    @pytest.mark.asyncio
    async def test_collect_match_odds(self, collector, sample_odds_data):
        """测试收集比赛赔率"""
        match_id = 12345

        with patch.object(collector, "_fetch_odds") as mock_fetch:
            mock_fetch.return_value = sample_odds_data

            result = await collector.collect_match_odds(match_id)

            assert result == sample_odds_data
            mock_fetch.assert_called_once_with(match_id)

    @pytest.mark.asyncio
    async def test_collect_multiple_odds(self, collector, sample_odds_data):
        """测试收集多个比赛赔率"""
        match_ids = [12345, 12346, 12347]

        with patch.object(collector, "_fetch_odds") as mock_fetch:
            mock_fetch.return_value = sample_odds_data

            results = await collector.collect_odds_batch(match_ids)

            assert len(results) == 3
            assert all(result == sample_odds_data for result in results)

    @pytest.mark.asyncio
    async def test_odds_data_validation(self, collector):
        """测试赔率数据验证"""
        # 有效数据
        valid_data = {
            "match_id": 12345,
            "bookmaker": "Bet365",
            "home_win": 2.15,
            "draw": 3.40,
            "away_win": 3.20,
        }

        assert collector._validate_odds_data(valid_data) is True

        # 无效数据 - 缺少必需字段
        invalid_data = {"bookmaker": "Bet365", "home_win": 2.15}

        assert collector._validate_odds_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_save_odds_to_database(
        self, collector, mock_session, sample_odds_data
    ):
        """测试保存赔率到数据库"""
        with patch("src.collectors.odds_collector.OddsData") as mock_odds_model:
            mock_odds_instance = Mock()
            mock_odds_model.return_value = mock_odds_instance

            await collector.save_odds_to_db(sample_odds_data, mock_session)

            mock_session.add.assert_called_with(mock_odds_instance)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_odds_data(self, collector, sample_odds_data):
        """测试缓存赔率数据"""
        match_id = 12345

        # 缓存数据
        await collector._cache_odds(match_id, sample_odds_data)

        # 获取缓存数据
        cached_data = await collector._get_cached_odds(match_id)
        assert cached_data == sample_odds_data

    @pytest.mark.asyncio
    async def test_error_handling_with_retry(self, collector):
        """测试错误处理和重试"""
        match_id = 12345

        with patch.object(collector, "_fetch_odds") as mock_fetch:
            # 前两次失败，第三次成功
            mock_fetch.side_effect = [
                Exception("Network error"),
                Exception("API error"),
                {"match_id": 12345, "home_win": 2.15},
            ]

            result = await collector.collect_match_odds(match_id)

            assert result["match_id"] == 12345
            assert result["home_win"] == 2.15
            assert mock_fetch.call_count == 3

    @pytest.mark.asyncio
    async def test_odds_comparison(self, collector):
        """测试赔率比较功能"""
        odds1 = {"bookmaker": "Bet365", "home_win": 2.15}
        odds2 = {"bookmaker": "William Hill", "home_win": 2.20}

        comparison = collector._compare_odds([odds1, odds2])

        assert "best_home_win" in comparison
        assert comparison["best_home_win"]["bookmaker"] == "William Hill"
        assert comparison["best_home_win"]["value"] == 2.20

    @pytest.mark.asyncio
    async def test_historical_odds_trends(self, collector, mock_session):
        """测试历史赔率趋势"""
        match_id = 12345

        # 模拟历史数据
        mock_session.execute.return_value.fetchall.return_value = [
            {"home_win": 2.10, "timestamp": "2024-01-01T10:00:00Z"},
            {"home_win": 2.15, "timestamp": "2024-01-01T11:00:00Z"},
            {"home_win": 2.12, "timestamp": "2024-01-01T12:00:00Z"},
        ]

        trends = await collector.get_odds_trends(match_id, mock_session)

        assert len(trends) == 3
        assert "home_win" in trends[0]
        assert "timestamp" in trends[0]

    @pytest.mark.asyncio
    async def test_bookmaker_ranking(self, collector):
        """测试博彩公司排名"""
        odds_data = [
            {"bookmaker": "Bet365", "home_win": 2.15, "draw": 3.40, "away_win": 3.20},
            {
                "bookmaker": "William Hill",
                "home_win": 2.20,
                "draw": 3.35,
                "away_win": 3.15,
            },
            {
                "bookmaker": "Paddy Power",
                "home_win": 2.12,
                "draw": 3.45,
                "away_win": 3.25,
            },
        ]

        ranking = collector._calculate_bookmaker_ranking(odds_data)

        assert len(ranking) == 3
        # William Hill应该排在第一位（最高的主胜赔率）
        assert ranking[0]["bookmaker"] == "William Hill"

    @pytest.mark.asyncio
    async def test_odds_format_conversion(self, collector):
        """测试赔率格式转换"""
        # 十进制赔率转其他格式
        decimal_odds = 2.15

        fractional = collector._decimal_to_fractional(decimal_odds)
        assert "/" in fractional

        american = collector._decimal_to_american(decimal_odds)
        assert american.startswith("+") or american.startswith("-")

    @pytest.mark.asyncio
    async def test_live_odds_updates(self, collector):
        """测试实时赔率更新"""
        match_id = 12345

        with patch.object(collector, "_subscribe_live_odds") as mock_subscribe:
            # 模拟实时赔率更新
            updates = [
                {"home_win": 2.15, "timestamp": "2024-01-01T15:30:00Z"},
                {"home_win": 2.12, "timestamp": "2024-01-01T15:31:00Z"},
                {"home_win": 2.18, "timestamp": "2024-01-01T15:32:00Z"},
            ]

            async def mock_updates():
                for update in updates:
                    yield update
                    await asyncio.sleep(0.1)

            mock_subscribe.return_value = mock_updates()

            received_updates = []
            async for update in collector.get_live_odds_updates(match_id):
                received_updates.append(update)
                if len(received_updates) >= 3:
                    break

            assert len(received_updates) == 3
            assert received_updates[0]["home_win"] == 2.15

    @pytest.mark.asyncio
    async def test_market_coverage(self, collector):
        """测试市场覆盖度"""
        odds_data = {
            "match_id": 12345,
            "bookmaker": "Bet365",
            "home_win": 2.15,
            "draw": 3.40,
            "away_win": 3.20,
            # 缺少一些市场
        }

        coverage = collector._calculate_market_coverage(odds_data)

        assert "total_markets" in coverage
        assert "covered_markets" in coverage
        assert "coverage_percentage" in coverage
        assert 0 <= coverage["coverage_percentage"] <= 100

    def test_api_endpoint_configuration(self, collector):
        """测试API端点配置"""
        endpoints = collector.get_api_endpoints()

        assert "match_odds" in endpoints
        assert "live_odds" in endpoints
        assert "historical_odds" in endpoints
        assert all(endpoint.startswith("/") for endpoint in endpoints.values())

    @pytest.mark.asyncio
    async def test_rate_limiting(self, collector):
        """测试速率限制"""
        match_ids = list(range(10))

        with patch.object(collector, "_fetch_odds") as mock_fetch:
            mock_fetch.return_value = {"match_id": 0, "home_win": 2.15}

            start_time = asyncio.get_event_loop().time()
            await collector.collect_odds_batch(match_ids)
            end_time = asyncio.get_event_loop().time()

            # 验证请求之间有适当的延迟
            elapsed_time = end_time - start_time
            assert elapsed_time > 0.5
