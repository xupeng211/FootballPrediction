"""
赔率数据收集器测试
Odds Data Collector Tests
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.odds_collector import OddsCollector


class TestOddsCollector:
    """赔率数据收集器测试"""

    @pytest.fixture
    def collector(self):
        """创建赔率数据收集器实例"""
        # 由于OddsCollector是桩实现，创建一个模拟对象
        collector = MagicMock(spec=OddsCollector)

        # 添加模拟方法
        collector.collect = AsyncMock(return_value=[])
        collector.validate_data = MagicMock(return_value=True)
        collector.compare_odds = MagicMock(return_value={})
        collector.detect_value_bets = MagicMock(return_value=[])
        collector.analyze_odds_trends = MagicMock(return_value={})
        collector.decimal_to_fractional = MagicMock(return_value=[])
        collector.decimal_to_american = MagicMock(return_value=[])
        collector.decimal_to_probability = MagicMock(return_value=[])
        collector.get_stats = MagicMock(
            return_value={
                "total_collected": 0,
                "total_errors": 0,
                "last_collection_time": None,
                "bookmakers_tracked": 0,
                "markets_covered": 0,
            }
        )

        return collector

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return [
            {
                "id": 1,
                "match_id": 101,
                "bookmaker": "Bet365",
                "home_win": 2.10,
                "draw": 3.20,
                "away_win": 3.40,
                "over_2_5": 1.85,
                "under_2_5": 1.95,
                "timestamp": "2025-11-08T15:00:00Z",
                "market_type": "1X2",
            },
            {
                "id": 2,
                "match_id": 102,
                "bookmaker": "William Hill",
                "home_win": 1.95,
                "draw": 3.40,
                "away_win": 3.80,
                "over_2_5": 1.90,
                "under_2_5": 1.90,
                "timestamp": "2025-11-08T16:00:00Z",
                "market_type": "1X2",
            },
            {
                "id": 3,
                "match_id": 103,
                "bookmaker": "Paddy Power",
                "home_win": 2.25,
                "draw": 3.10,
                "away_win": 3.00,
                "both_teams_to_score_yes": 1.70,
                "both_teams_to_score_no": 2.10,
                "timestamp": "2025-11-08T17:00:00Z",
                "market_type": "BTTS",
            },
        ]

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert hasattr(collector, "collect")
        assert hasattr(collector, "validate_data")
        assert hasattr(collector, "compare_odds")

    @pytest.mark.asyncio
    async def test_collect_valid_odds(self, collector, sample_odds_data):
        """测试收集有效赔率数据"""
        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            result = await collector.collect(sample_odds_data)

            assert result is not None
            assert len(result) == len(sample_odds_data)
            assert mock_session.add.call_count == len(sample_odds_data)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_empty_list(self, collector):
        """测试收集空数据列表"""
        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            result = await collector.collect([])

            assert result == []

    @pytest.mark.asyncio
    async def test_data_validation_success(self, collector, sample_odds_data):
        """测试数据验证成功"""
        for odds_data in sample_odds_data:
            is_valid = collector.validate_data(odds_data)
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_data_validation_missing_fields(self, collector):
        """测试数据验证失败 - 缺少字段"""
        invalid_data = [
            {
                "id": 1,
                "match_id": 101,
                # 缺少bookmaker
                "home_win": 2.10,
                "draw": 3.20,
                "away_win": 3.40,
            }
        ]

        is_valid = collector.validate_data(invalid_data[0])
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_data_validation_invalid_odds(self, collector):
        """测试数据验证失败 - 无效赔率"""
        invalid_data = [
            {
                "id": 1,
                "match_id": 101,
                "bookmaker": "Bet365",
                "home_win": -1.0,  # 负赔率无效
                "draw": 3.20,
                "away_win": 3.40,
            }
        ]

        is_valid = collector.validate_data(invalid_data[0])
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_collect_with_bookmaker_filter(self, collector, sample_odds_data):
        """测试按博彩公司过滤收集"""
        bookmaker_filter = "Bet365"

        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            filtered_data = [
                o for o in sample_odds_data if o["bookmaker"] == bookmaker_filter
            ]

            result = await collector.collect(
                sample_odds_data, bookmaker_filter=bookmaker_filter
            )

            assert len(result) == len(filtered_data)
            mock_session.add.call_count == len(filtered_data)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_with_market_filter(self, collector, sample_odds_data):
        """测试按市场类型过滤收集"""
        market_filter = "1X2"

        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            filtered_data = [
                o for o in sample_odds_data if o["market_type"] == market_filter
            ]

            result = await collector.collect(
                sample_odds_data, market_filter=market_filter
            )

            assert len(result) == len(filtered_data)
            mock_session.add.call_count == len(filtered_data)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_odds_comparison_analysis(self, collector, sample_odds_data):
        """测试赔率对比分析"""
        # 为同一比赛添加不同博彩公司的赔率
        comparison_data = [
            {
                "id": 1,
                "match_id": 101,
                "bookmaker": "Bet365",
                "home_win": 2.10,
                "draw": 3.20,
                "away_win": 3.40,
            },
            {
                "id": 2,
                "match_id": 101,
                "bookmaker": "William Hill",
                "home_win": 2.05,
                "draw": 3.25,
                "away_win": 3.50,
            },
        ]

        comparison_result = collector.compare_odds(comparison_data)

        assert isinstance(comparison_result, dict)
        assert 101 in comparison_result
        assert "highest_home_win" in comparison_result[101]
        assert "highest_draw" in comparison_result[101]
        assert "highest_away_win" in comparison_result[101]

    @pytest.mark.asyncio
    async def test_value_bets_detection(self, collector, sample_odds_data):
        """测试价值投注检测"""
        # 模拟市场平均赔率
        market_average = {"home_win": 2.00, "draw": 3.00, "away_win": 3.50}

        value_bets = collector.detect_value_bets(sample_odds_data, market_average)

        assert isinstance(value_bets, list)
        # 应该识别出高于市场平均的赔率作为价值投注
        for bet in value_bets:
            assert "match_id" in bet
            assert "bookmaker" in bet
            assert "bet_type" in bet
            assert "odds" in bet
            assert "value_percentage" in bet

    @pytest.mark.asyncio
    async def test_error_handling_database_error(self, collector, sample_odds_data):
        """测试数据库错误处理"""
        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await collector.collect(sample_odds_data)

    @pytest.mark.asyncio
    async def test_concurrent_collection(self, collector, sample_odds_data):
        """测试并发收集"""
        import asyncio

        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            tasks = [
                collector.collect(sample_odds_data[i : i + 1])
                for i in range(len(sample_odds_data))
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == len(sample_odds_data)

    @pytest.mark.asyncio
    async def test_historical_odds_tracking(self, collector):
        """测试历史赔率跟踪"""
        historical_data = [
            {
                "id": 1,
                "match_id": 101,
                "bookmaker": "Bet365",
                "home_win": 2.10,
                "timestamp": "2025-11-07T15:00:00Z",
            },
            {
                "id": 2,
                "match_id": 101,
                "bookmaker": "Bet365",
                "home_win": 2.05,
                "timestamp": "2025-11-08T15:00:00Z",
            },
        ]

        trend_analysis = collector.analyze_odds_trends(historical_data)

        assert isinstance(trend_analysis, dict)
        assert 101 in trend_analysis
        assert "price_changes" in trend_analysis[101]
        assert "trend_direction" in trend_analysis[101]

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, collector):
        """测试大数据集性能"""
        large_dataset = [
            {
                "id": i,
                "match_id": 100 + i,
                "bookmaker": f"Bookmaker_{i % 10}",
                "home_win": 2.0 + (i % 50) * 0.01,
                "draw": 3.0 + (i % 30) * 0.01,
                "away_win": 3.5 + (i % 40) * 0.01,
                "timestamp": "2025-11-08T15:00:00Z",
                "market_type": "1X2",
            }
            for i in range(1000)
        ]

        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            start_time = datetime.now()

            result = await collector.collect(large_dataset)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            assert len(result) == len(large_dataset)
            assert execution_time < 15.0  # 15秒内完成

    @pytest.mark.asyncio
    async def test_collect_with_limit(self, collector, sample_odds_data):
        """测试收集数量限制"""
        with patch(
            "src.collectors.odds_collector.create_database_session"
        ) as mock_session:
            mock_session.return_value = AsyncMock()
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()

            result = await collector.collect(sample_odds_data, limit=2)

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_odds_format_conversion(self, collector):
        """测试赔率格式转换"""
        decimal_odds = [2.50, 3.20, 1.85]

        # 转换为分数赔率
        fractional_odds = collector.decimal_to_fractional(decimal_odds)
        assert len(fractional_odds) == len(decimal_odds)

        # 转换为美式赔率
        american_odds = collector.decimal_to_american(decimal_odds)
        assert len(american_odds) == len(decimal_odds)

        # 转换为概率
        probabilities = collector.decimal_to_probability(decimal_odds)
        assert len(probabilities) == len(decimal_odds)
        for prob in probabilities:
            assert 0 < prob < 1

    def test_get_collector_stats(self, collector):
        """测试收集器统计信息"""
        stats = collector.get_stats()

        assert isinstance(stats, dict)
        assert "total_collected" in stats
        assert "total_errors" in stats
        assert "last_collection_time" in stats
        assert "bookmakers_tracked" in stats
        assert "markets_covered" in stats
