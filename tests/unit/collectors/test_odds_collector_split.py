"""
测试拆分后的赔率收集器模块
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.collectors.odds.sources import OddsSourceManager
from src.collectors.odds.processor import OddsProcessor
from src.collectors.odds.analyzer import OddsAnalyzer
from src.collectors.odds.storage import OddsStorage
from src.collectors.odds.collector import OddsCollector
from src.collectors.odds.manager import OddsCollectorManager, get_odds_manager


class TestOddsSourceManager:
    """测试赔率数据源管理器"""

    @pytest.fixture
    def source_manager(self):
        return OddsSourceManager(api_key="test_key")

    @pytest.mark.asyncio
    async def test_init(self, source_manager):
        """测试初始化"""
        assert source_manager.api_key == "test_key"
        assert "odds_api" in source_manager.api_endpoints
        assert len(source_manager.bookmakers) > 0

    @pytest.mark.asyncio
    async def test_transform_odds_api_data(self, source_manager):
        """测试数据转换"""
        mock_data = {
            "id": 123,
            "sport_key": "soccer",
            "commence_time": "2024-01-01T12:00:00Z",
            "bookmakers": [
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Home", "price": 2.0},
                                {"name": "Draw", "price": 3.2},
                                {"name": "Away", "price": 3.8},
                            ],
                        }
                    ],
                }
            ],
        }

        result = source_manager._transform_odds_api_data(mock_data)

        assert result["match_id"] == 123
        assert len(result["bookmakers"]) == 1
        assert result["bookmakers"][0]["markets"]["match_winner"]["home_win"] == 2.0


class TestOddsProcessor:
    """测试赔率处理器"""

    @pytest.fixture
    def processor(self):
        return OddsProcessor()

    @pytest.mark.asyncio
    async def test_process_odds_data(self, processor):
        """测试赔率数据处理"""
        raw_data = {
            "source1": {
                "bookmakers": [
                    {
                        "key": "bet365",
                        "markets": {
                            "match_winner": {
                                "home_win": 2.0,
                                "draw": 3.2,
                                "away_win": 3.8,
                            }
                        },
                    }
                ]
            }
        }

        result = await processor.process_odds_data(123, raw_data)

        assert result["match_id"] == 123
        assert "average_odds" in result
        assert "best_odds" in result
        assert "implied_probabilities" in result
        assert len(result["bookmakers"]) == 1

    def test_validate_odds_data(self, processor):
        """测试赔率数据验证"""
        valid_data = {
            "match_id": 123,
            "bookmakers": [
                {"name": "bet365", "home_win": 2.0, "draw": 3.2, "away_win": 3.8}
            ],
        }

        assert processor.validate_odds_data(valid_data) is True

        invalid_data = {"match_id": 123}
        assert processor.validate_odds_data(invalid_data) is False

    def test_calculate_odds_movement(self, processor):
        """测试赔率变化计算"""
        current = {"home_win": 2.1, "draw": 3.1, "away_win": 3.7}
        previous = {"home_win": 2.0, "draw": 3.2, "away_win": 3.8}

        movement = processor.calculate_odds_movement(current, previous)

        assert "home_win" in movement
        assert movement["home_win"]["direction"] == "up"
        assert abs(movement["home_win"]["percent_change"] - 5.0) < 0.0001


class TestOddsAnalyzer:
    """测试赔率分析器"""

    @pytest.fixture
    def analyzer(self):
        mock_redis = AsyncMock()
        return OddsAnalyzer(redis_manager=mock_redis)

    @pytest.mark.asyncio
    async def test_identify_value_bets_no_prediction(self, analyzer):
        """测试无模型预测时的价值投注识别"""
        odds_data = {
            "match_id": 123,
            "bookmakers": [
                {"name": "bet365", "home_win": 2.0, "draw": 3.2, "away_win": 3.8}
            ],
        }

        with patch.object(analyzer, "_get_model_prediction", return_value=None):
            value_bets = await analyzer.identify_value_bets(odds_data)
            assert value_bets == []

    @pytest.mark.asyncio
    async def test_identify_value_bets_with_prediction(self, analyzer):
        """测试有模型预测时的价值投注识别"""
        odds_data = {
            "match_id": 123,
            "bookmakers": [
                {"name": "bet365", "home_win": 2.5, "draw": 3.2, "away_win": 3.0}
            ],
        }

        mock_prediction = {"home": 0.5, "draw": 0.3, "away": 0.2}

        with patch.object(
            analyzer, "_get_model_prediction", return_value=mock_prediction
        ):
            value_bets = await analyzer.identify_value_bets(odds_data)
            assert len(value_bets) > 0
            assert value_bets[0]["bookmaker"] == "bet365"

    def test_analyze_market_efficiency(self, analyzer):
        """测试市场效率分析"""
        odds_data = {
            "bookmakers": [
                {"home_win": 2.0, "draw": 3.2, "away_win": 3.8},
                {"home_win": 2.1, "draw": 3.1, "away_win": 3.7},
            ],
            "best_odds": {"home_win": 2.1, "draw": 3.2, "away_win": 3.8},
            "average_odds": {"home_win": 2.05, "draw": 3.15, "away_win": 3.75},
        }

        analysis = analyzer.analyze_market_efficiency(odds_data)

        assert "margin_analysis" in analysis
        assert "price_discrepancy" in analysis
        assert analysis["bookmaker_count"] == 2

    def test_calculate_arbitrage_opportunities(self, analyzer):
        """测试套利机会计算"""
        odds_data = {
            "bookmakers": [
                {"name": "bet365", "home_win": 2.1, "draw": 3.3, "away_win": 3.9},
                {
                    "name": "william_hill",
                    "home_win": 2.05,
                    "draw": 3.4,
                    "away_win": 3.8,
                },
            ]
        }

        opportunities = analyzer.calculate_arbitrage_opportunities(odds_data)

        # 通常不会有套利机会，但测试函数运行
        assert isinstance(opportunities, list)


class TestOddsStorage:
    """测试赔率存储"""

    @pytest.fixture
    def storage(self):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        return OddsStorage(mock_db, mock_redis)

    def test_check_cache_hit(self, storage):
        """测试缓存命中"""
        cache_key = "odds:123:bet365:match_winner"
        storage.odds_cache[cache_key] = {"data": "test"}
        storage.last_update_cache[cache_key] = datetime.now()

        result = storage.check_cache(123, ["bet365"], ["match_winner"])
        assert result is not None

    def test_check_cache_miss(self, storage):
        """测试缓存未命中"""
        result = storage.check_cache(123, ["bet365"], ["match_winner"])
        assert result is None

    def test_update_cache(self, storage):
        """测试更新缓存"""
        test_data = {"data": "test"}
        storage.update_cache(123, ["bet365"], ["match_winner"], test_data)

        cache_key = "odds:123:bet365:match_winner"
        assert cache_key in storage.odds_cache
        assert storage.odds_cache[cache_key] == test_data

    def test_clear_cache(self, storage):
        """测试清空缓存"""
        storage.odds_cache["test"] = "data"
        storage.last_update_cache["test"] = datetime.now()

        storage.clear_cache()
        assert len(storage.odds_cache) == 0
        assert len(storage.last_update_cache) == 0


class TestOddsCollector:
    """测试赔率收集器"""

    @pytest.fixture
    def collector(self):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        return OddsCollector(mock_db, mock_redis, api_key="test_key")

    @pytest.mark.asyncio
    async def test_start_stop_collection(self, collector):
        """测试启动和停止收集"""
        assert collector.running is False

        await collector.start_collection()
        assert collector.running is True

        await collector.stop_collection()
        assert collector.running is False

    @pytest.mark.asyncio
    async def test_collect_match_odds_cached(self, collector):
        """测试从缓存获取赔率"""
        # 模拟缓存命中
        collector.storage.check_cache = MagicMock(return_value={"cached": "data"})

        result = await collector.collect_match_odds(123)
        assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_get_stats(self, collector):
        """测试获取统计信息"""
        stats = collector.get_stats()
        assert "running" in stats
        assert "total_updates" in stats
        assert "success_rate" in stats


class TestOddsCollectorManager:
    """测试赔率收集器管理器"""

    @pytest.fixture
    def manager(self):
        return OddsCollectorManager()

    @pytest.mark.asyncio
    async def test_get_collector(self, manager):
        """测试获取收集器"""
        with patch("src.collectors.odds.manager.get_async_session"):
            collector = await manager.get_collector(1)
            assert isinstance(collector, OddsCollector)
            assert 1 in manager.collectors

    def test_remove_collector(self, manager):
        """测试移除收集器"""
        manager.collectors[1] = MagicMock()
        manager.remove_collector(1)
        assert 1 not in manager.collectors

    def test_get_odds_manager_singleton(self):
        """测试全局管理器单例"""
        manager1 = get_odds_manager()
        manager2 = get_odds_manager()
        assert manager1 is manager2
