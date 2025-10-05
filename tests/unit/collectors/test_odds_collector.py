"""
数据收集器测试 - 赔率数据收集器
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.collectors.odds_collector import OddsCollector


@pytest.mark.unit
class TestOddsCollector:
    """OddsCollector测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        collector = OddsCollector()
        collector.logger = MagicMock()
        return collector

    @pytest.fixture
    def mock_odds_data(self):
        """Mock赔率数据"""
        return {
            "match_id": 12345,
            "bookmakers": [
                {
                    "id": 1,
                    "name": "Bet365",
                    "bets": [
                        {
                            "id": 1,
                            "name": "Match Winner",
                            "values": [
                                {"value": "Home", "odd": 2.10},
                                {"value": "Draw", "odd": 3.40},
                                {"value": "Away", "odd": 3.20},
                            ],
                        }
                    ],
                }
            ],
        }

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert collector.logger is not None
        assert hasattr(collector, "bookmakers")
        assert hasattr(collector, "api_key")

    @pytest.mark.asyncio
    async def test_collect_odds_for_match(self, collector, mock_odds_data):
        """测试收集单场比赛赔率"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = mock_odds_data

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            result = await collector.collect_odds_for_match(match_id=12345)

            assert result is not None
            assert result["match_id"] == 12345
            assert len(result["bookmakers"]) == 1
            assert result["bookmakers"][0]["name"] == "Bet365"

    @pytest.mark.asyncio
    async def test_collect_odds_batch(self, collector, mock_odds_data):
        """测试批量收集赔率"""
        match_ids = [12345, 12346, 12347]
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = mock_odds_data

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            results = await collector.collect_odds_batch(match_ids)

            assert len(results) == 3
            assert all("match_id" in result for result in results)
            assert mock_http_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_parse_odds_data(self, collector, mock_odds_data):
        """测试解析赔率数据"""
        parsed = await collector._parse_odds_data(mock_odds_data)

        assert parsed["match_id"] == 12345
        assert "home_win_odds" in parsed
        assert "draw_odds" in parsed
        assert "away_win_odds" in parsed

    @pytest.mark.asyncio
    async def test_collect_odds_error_handling(self, collector):
        """测试错误处理"""
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = Exception("API error")

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            result = await collector.collect_odds_for_match(match_id=12345)

            assert result is None
            collector.logger.error.assert_called()

    def test_parse_decimal_odds(self, collector):
        """测试解析小数赔率"""
        # 测试有效赔率
        odds = collector._parse_decimal_odds("2.10")
        assert odds == 2.10

        # 测试无效赔率
        odds = collector._parse_decimal_odds("invalid")
        assert odds is None

    def test_calculate_implied_probability(self, collector):
        """测试计算隐含概率"""
        # 小数赔率转隐含概率
        probability = collector._calculate_implied_probability(2.0)
        assert probability == 0.5  # 1/2.0

        probability = collector._calculate_implied_probability(3.0)
        assert pytest.approx(probability, 0.01) == 0.333  # 1/3.0

    def test_calculate_bookmaker_margin(self, collector):
        """测试计算庄家利润率"""
        odds = [2.10, 3.40, 3.20]
        margin = collector._calculate_bookmaker_margin(odds)

        # 计算公式: margin = (1/2.1 + 1/3.4 + 1/3.2) - 1
        expected = (1 / 2.1 + 1 / 3.4 + 1 / 3.2) - 1
        assert pytest.approx(margin, 0.01) == expected

    @pytest.mark.asyncio
    async def test_cache_odds_data(self, collector, mock_odds_data):
        """测试缓存赔率数据"""
        mock_cache = MagicMock()
        mock_cache.set.return_value = True

        with patch.object(collector, "get_cache_manager", return_value=mock_cache):
            result = await collector._cache_odds_data(mock_odds_data)

            assert result is True
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_odds(self, collector):
        """测试获取缓存的赔率数据"""
        mock_cache = MagicMock()
        cached_data = {
            "match_id": 12345,
            "home_win_odds": 2.10,
            "updated_at": datetime.now().isoformat(),
        }
        mock_cache.get.return_value = cached_data

        with patch.object(collector, "get_cache_manager", return_value=mock_cache):
            result = await collector.get_cached_odds(match_id=12345)

            assert result == cached_data
            mock_cache.get.assert_called_once()

    def test_filter_odds_by_bookmaker(self, collector, mock_odds_data):
        """测试按庄家过滤赔率"""
        filtered = collector._filter_odds_by_bookmaker(mock_odds_data, bookmakers=["Bet365"])

        assert len(filtered["bookmakers"]) == 1
        assert filtered["bookmakers"][0]["name"] == "Bet365"

    def test_detect_odds_changes(self, collector):
        """测试检测赔率变化"""
        old_odds = {"home_win": 2.10, "draw": 3.40, "away_win": 3.20}
        new_odds = {"home_win": 2.05, "draw": 3.40, "away_win": 3.30}  # 变化  # 变化

        changes = collector._detect_odds_changes(old_odds, new_odds)

        assert len(changes) == 2
        assert "home_win" in changes
        assert "away_win" in changes
        assert changes["home_win"]["old"] == 2.10
        assert changes["home_win"]["new"] == 2.05

    @pytest.mark.asyncio
    async def test_collect_historical_odds(self, collector):
        """测试收集历史赔率"""
        # Mock历史赔率API
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "odds_history": [
                {
                    "date": "2025-10-01",
                    "home_win": 2.10,
                    "draw": 3.40,
                    "away_win": 3.20,
                },
                {
                    "date": "2025-10-02",
                    "home_win": 2.05,
                    "draw": 3.45,
                    "away_win": 3.25,
                },
            ]
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            result = await collector.collect_historical_odds(
                match_id=12345, start_date="2025-10-01", end_date="2025-10-02"
            )

            assert result is not None
            assert len(result["odds_history"]) == 2

    def test_validate_odds_data(self, collector):
        """测试验证赔率数据"""
        # 有效数据
        valid_data = {
            "match_id": 12345,
            "bookmakers": [{"name": "Bet365", "odds": {"home": 2.0}}],
        }
        assert collector._validate_odds_data(valid_data) is True

        # 无效数据 - 缺少match_id
        invalid_data = {"bookmakers": [{"name": "Bet365"}]}
        assert collector._validate_odds_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_collect_live_odds(self, collector):
        """测试收集实时赔率"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "match_id": 12345,
            "status": "live",
            "minute": 65,
            "current_odds": {"home_win": 1.80, "draw": 3.60, "away_win": 4.20},
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            result = await collector.collect_live_odds(match_id=12345)

            assert result is not None
            assert result["status"] == "live"
            assert "current_odds" in result

    def test_format_odds_for_model(self, collector):
        """测试格式化赔率用于模型"""
        raw_odds = {
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.20,
            "bookmakers": ["Bet365", "William Hill"],
        }

        formatted = collector._format_odds_for_model(raw_odds)

        assert "home_win_implied_prob" in formatted
        assert "draw_implied_prob" in formatted
        assert "away_win_implied_prob" in formatted
        assert "bookmaker_count" in formatted
        assert formatted["bookmaker_count"] == 2

    @pytest.mark.asyncio
    async def test_track_odds_movements(self, collector):
        """测试跟踪赔率变动"""
        movements = []

        # 模拟赔率变动
        odds_updates = [
            {"timestamp": "2025-10-05T10:00:00Z", "home_win": 2.10},
            {"timestamp": "2025-10-05T11:00:00Z", "home_win": 2.05},
            {"timestamp": "2025-10-05T12:00:00Z", "home_win": 2.00},
        ]

        for update in odds_updates:
            movement = collector._track_odds_change(
                match_id=12345,
                old_odds=None if len(movements) == 0 else movements[-1],
                new_odds=update,
            )
            movements.append(movement)

        assert len(movements) == 3
        assert movements[2]["change"] == -0.10  # 从2.10到2.00

    def test_identify_value_bets(self, collector):
        """测试识别价值投注"""
        # 模型预测概率 vs 市场赔率
        model_prob = {"home_win": 0.55, "draw": 0.25, "away_win": 0.20}
        market_odds = {"home_win": 2.0, "draw": 3.5, "away_win": 4.0}

        value_bets = collector._identify_value_bets(model_prob, market_odds)

        # 主队有价值（模型概率55% > 隐含概率50%）
        assert "home_win" in value_bets
        assert value_bets["home_win"]["edge"] > 0

    @pytest.mark.asyncio
    async def test_aggregate_bookmaker_odds(self, collector):
        """测试聚合庄家赔率"""
        multiple_bookmakers = {
            "Bet365": {"home_win": 2.10, "draw": 3.40, "away_win": 3.20},
            "William Hill": {"home_win": 2.05, "draw": 3.50, "away_win": 3.30},
            "Betfair": {"home_win": 2.15, "draw": 3.35, "away_win": 3.25},
        }

        aggregated = await collector._aggregate_bookmaker_odds(multiple_bookmakers)

        assert "average_odds" in aggregated
        assert "best_odds" in aggregated
        assert aggregated["best_odds"]["home_win"] == 2.15  # 最高赔率
        assert aggregated["best_odds"]["draw"] == 3.50  # 最高赔率

    def test_calculate_over_round(self, collector):
        """测试计算返还率"""
        odds = [2.10, 3.40, 3.20]
        over_round = collector._calculate_over_round(odds)

        # over_round = 1 / (1/2.1 + 1/3.4 + 1/3.2)
        expected = 1 / (1 / 2.1 + 1 / 3.4 + 1 / 3.2)
        assert pytest.approx(over_round, 0.01) == expected

    @pytest.mark.asyncio
    async def test_collect_asian_handicap_odds(self, collector):
        """测试收集亚洲盘口赔率"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "match_id": 12345,
            "asian_handicap": [
                {"handicap": -1.5, "home_odds": 1.90, "away_odds": 1.90},
                {"handicap": -1.0, "home_odds": 1.95, "away_odds": 1.85},
                {"handicap": -0.5, "home_odds": 1.80, "away_odds": 2.00},
            ],
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            result = await collector.collect_asian_handicap_odds(match_id=12345)

            assert result is not None
            assert "asian_handicap" in result
            assert len(result["asian_handicap"]) == 3

    @pytest.mark.asyncio
    async def test_collect_over_under_odds(self, collector):
        """测试收集大小球赔率"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "match_id": 12345,
            "over_under": [
                {"line": 2.0, "over_odds": 1.85, "under_odds": 1.95},
                {"line": 2.5, "over_odds": 1.90, "under_odds": 1.90},
                {"line": 3.0, "over_odds": 2.10, "under_odds": 1.75},
            ],
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            result = await collector.collect_over_under_odds(match_id=12345)

            assert result is not None
            assert "over_under" in result
            assert len(result["over_under"]) == 3

    @pytest.mark.asyncio
    async def test_rate_limiting(self, collector):
        """测试API限流"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 429
        mock_http_client.get.return_value.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "60",
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            with patch("asyncio.sleep") as mock_sleep:
                result = await collector.collect_odds_for_match(match_id=12345)

                mock_sleep.assert_called_once_with(60)
                assert result is None
