"""
数据采集器测试
Data Collectors Tests

测试数据采集系统的核心功能。
Tests core functionality of data collection system.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.data.collectors import (
    BaseCollector,
    FixturesCollector,
    OddsCollector,
    ScoresCollector,
)
from src.data.collectors.streaming_collector import StreamingCollector


class TestBaseCollector:
    """基础采集器测试类"""

    @pytest.fixture
    def collector(self):
        """基础采集器实例"""
        return BaseCollector("test_collector")

    def test_base_collector_initialization(self, collector):
        """测试基础采集器初始化"""
        assert collector is not None
        assert collector.name == "test_collector"
        assert hasattr(collector, "logger")
        assert hasattr(collector, "session")
        assert hasattr(collector, "cache")

    @pytest.mark.asyncio
    async def test_base_collector_abstract_methods(self, collector):
        """测试基础采集器抽象方法"""
        # BaseCollector应该可以实例化但collect_data需要子类实现
        try:
            await collector.collect_data()
        except (NotImplementedError, AttributeError):
            # 这是预期的行为
            pass

    @pytest.mark.asyncio
    async def test_base_collector_http_request(self, collector):
        """测试HTTP请求功能"""
        with patch.object(collector.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_get.return_value = mock_response

            result = await collector._make_request("https://api.test.com/data")

            assert result == {"data": "test"}
            mock_get.assert_called_once_with("https://api.test.com/data")

    @pytest.mark.asyncio
    async def test_base_collector_error_handling(self, collector):
        """测试错误处理"""
        with patch.object(collector.session, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            with pytest.raises(Exception):
                await collector._make_request("https://api.test.com/data")


class TestFixturesCollector:
    """赛程采集器测试类"""

    @pytest.fixture
    def fixtures_collector(self):
        """赛程采集器实例"""
        return FixturesCollector()

    def test_fixtures_collector_initialization(self, fixtures_collector):
        """测试赛程采集器初始化"""
        assert fixtures_collector is not None
        assert fixtures_collector.name == "fixtures_collector"
        assert hasattr(fixtures_collector, "processed_matches")
        assert hasattr(fixtures_collector, "leagues")

    @pytest.mark.asyncio
    async def test_collect_fixtures_success(self, fixtures_collector):
        """测试成功采集赛程数据"""
        mock_api_response = {
            "matches": [
                {
                    "id": 12345,
                    "home_team": {"id": 1, "name": "Team A"},
                    "away_team": {"id": 2, "name": "Team B"},
                    "league": {"id": 39, "name": "Premier League"},
                    "date": "2024-01-15T15:00:00Z",
                    "status": "NS",
                }
            ]
        }

        with patch.object(fixtures_collector, "_make_request") as mock_request:
            mock_request.return_value = mock_api_response

            result = await fixtures_collector.collect_data()

            assert len(result) > 0
            assert "matches" in result
            assert result["matches"][0]["id"] == 12345

    @pytest.mark.asyncio
    async def test_collect_fixtures_empty_response(self, fixtures_collector):
        """测试空响应处理"""
        with patch.object(fixtures_collector, "_make_request") as mock_request:
            mock_request.return_value = {"matches": []}

            result = await fixtures_collector.collect_data()

            assert result == {"matches": []}

    @pytest.mark.asyncio
    async def test_deduplicate_matches(self, fixtures_collector):
        """比赛去重测试"""
        match1 = {
            "id": 12345,
            "league_id": 39,
            "home_team": "Team A",
            "away_team": "Team B",
        }
        match2 = {
            "id": 12345,
            "league_id": 39,
            "home_team": "Team A",
            "away_team": "Team B",
        }
        match3 = {
            "id": 67890,
            "league_id": 39,
            "home_team": "Team C",
            "away_team": "Team D",
        }

        # 添加重复比赛
        fixtures_collector.processed_matches.add("12345_39")
        unique_matches = fixtures_collector._deduplicate_matches(
            [match1, match2, match3]
        )

        assert len(unique_matches) == 2
        assert unique_matches[0]["id"] == 67890  # 新比赛应该保留
        assert unique_matches[1]["id"] == 12345  # 已处理比赛应该去重

    def test_validate_match_data(self, fixtures_collector):
        """测试比赛数据验证"""
        valid_match = {
            "id": 12345,
            "home_team": {"id": 1, "name": "Team A"},
            "away_team": {"id": 2, "name": "Team B"},
            "league": {"id": 39, "name": "Premier League"},
            "date": "2024-01-15T15:00:00Z",
        }

        invalid_match = {
            "id": None,  # 无效ID
            "home_team": None,  # 缺少主队
            "away_team": {"id": 2, "name": "Team B"},
            "league": {"id": 39, "name": "Premier League"},
            "date": "invalid_date",  # 无效日期
        }

        assert fixtures_collector._validate_match(valid_match) is True
        assert fixtures_collector._validate_match(invalid_match) is False

    @pytest.mark.asyncio
    async def test_process_league_data(self, fixtures_collector):
        """测试联赛数据处理"""
        league_data = [
            {"id": 39, "name": "Premier League", "country": "England"},
            {"id": 140, "name": "La Liga", "country": "Spain"},
        ]

        processed_leagues = fixtures_collector._process_league_data(league_data)

        assert len(processed_leagues) == 2
        assert processed_leagues[0]["id"] == 39
        assert processed_leagues[0]["name"] == "Premier League"
        assert processed_leagues[1]["id"] == 140
        assert processed_leagues[1]["name"] == "La Liga"


class TestOddsCollector:
    """赔率采集器测试类"""

    @pytest.fixture
    def odds_collector(self):
        """赔率采集器实例"""
        return OddsCollector()

    def test_odds_collector_initialization(self, odds_collector):
        """测试赔率采集器初始化"""
        assert odds_collector is not None
        assert odds_collector.name == "odds_collector"
        assert hasattr(odds_collector, "bookmakers")
        assert hasattr(odds_collector, "odds_history")

    @pytest.mark.asyncio
    async def test_collect_odds_success(self, odds_collector):
        """测试成功采集赔率数据"""
        mock_odds_response = {
            "odds": [
                {
                    "match_id": 12345,
                    "bookmaker": "Bet365",
                    "home_win": 2.10,
                    "draw": 3.40,
                    "away_win": 3.20,
                    "timestamp": "2024-01-15T10:00:00Z",
                },
                {
                    "match_id": 12345,
                    "bookmaker": "William Hill",
                    "home_win": 2.15,
                    "draw": 3.35,
                    "away_win": 3.25,
                    "timestamp": "2024-01-15T10:00:00Z",
                },
            ]
        }

        with patch.object(odds_collector, "_make_request") as mock_request:
            mock_request.return_value = mock_odds_response

            result = await odds_collector.collect_data()

            assert len(result["odds"]) == 2
            assert result["odds"][0]["match_id"] == 12345

    @pytest.mark.asyncio
    async def test_calculate_average_odds(self, odds_collector):
        """测试计算平均赔率"""
        odds_data = [
            {"home_win": 2.10, "draw": 3.40, "away_win": 3.20},
            {"home_win": 2.15, "draw": 3.35, "away_win": 3.25},
            {"home_win": 2.05, "draw": 3.45, "away_win": 3.30},
        ]

        avg_odds = odds_collector._calculate_average_odds(odds_data)

        assert abs(avg_odds["home_win"] - 2.10) < 0.01
        assert abs(avg_odds["draw"] - 3.40) < 0.01
        assert abs(avg_odds["away_win"] - 3.25) < 0.01

    @pytest.mark.asyncio
    async def test_detect_odds_anomalies(self, odds_collector):
        """测试赔率异常检测"""
        normal_odds = [
            {"home_win": 2.10, "timestamp": "2024-01-15T10:00:00Z"},
            {"home_win": 2.15, "timestamp": "2024-01-15T11:00:00Z"},
            {"home_win": 2.12, "timestamp": "2024-01-15T12:00:00Z"},
        ]

        anomalous_odds = [
            {"home_win": 2.10, "timestamp": "2024-01-15T10:00:00Z"},
            {"home_win": 2.15, "timestamp": "2024-01-15T11:00:00Z"},
            {"home_win": 4.50, "timestamp": "2024-01-15T12:00:00Z"},  # 异常跳跃
        ]

        normal_anomalies = odds_collector._detect_odds_anomalies(normal_odds)
        anomalous_anomalies = odds_collector._detect_odds_anomalies(anomalous_odds)

        assert len(normal_anomalies) == 0
        assert len(anomalous_anomalies) > 0
        assert anomalous_anomalies[0]["type"] == "price_jump"

    def test_calculate_implied_probability(self, odds_collector):
        """测试计算隐含概率"""
        odds = {"home_win": 2.10, "draw": 3.40, "away_win": 3.20}

        probabilities = odds_collector._calculate_implied_probability(odds)

        assert abs(probabilities["home_win"] - (1 / 2.10)) < 0.01
        assert abs(probabilities["draw"] - (1 / 3.40)) < 0.01
        assert abs(probabilities["away_win"] - (1 / 3.20)) < 0.01

        # 验证概率总和（考虑庄家优势）
        total_prob = sum(probabilities.values())
        assert total_prob > 1.0  # 应该大于1，包含庄家优势


class TestScoresCollector:
    """比分采集器测试类"""

    @pytest.fixture
    def scores_collector(self):
        """比分采集器实例"""
        return ScoresCollector()

    def test_scores_collector_initialization(self, scores_collector):
        """测试比分采集器初始化"""
        assert scores_collector is not None
        assert scores_collector.name == "scores_collector"
        assert hasattr(scores_collector, "live_matches")

    @pytest.mark.asyncio
    async def test_collect_live_scores(self, scores_collector):
        """测试采集实时比分"""
        mock_scores_response = {
            "matches": [
                {
                    "id": 12345,
                    "status": "LIVE",
                    "minute": 65,
                    "score": {"home": 2, "away": 1},
                    "events": [
                        {"type": "goal", "minute": 23, "team": "home"},
                        {"type": "goal", "minute": 45, "team": "away"},
                        {"type": "goal", "minute": 65, "team": "home"},
                    ],
                }
            ]
        }

        with patch.object(scores_collector, "_make_request") as mock_request:
            mock_request.return_value = mock_scores_response

            result = await scores_collector.collect_data()

            assert len(result["matches"]) == 1
            assert result["matches"][0]["status"] == "LIVE"
            assert result["matches"][0]["score"]["home"] == 2
            assert result["matches"][0]["score"]["away"] == 1

    @pytest.mark.asyncio
    async def test_process_match_events(self, scores_collector):
        """测试处理比赛事件"""
        events = [
            {"type": "goal", "minute": 23, "team": "home", "player": "Player A"},
            {"type": "yellow_card", "minute": 45, "team": "away", "player": "Player B"},
            {"type": "red_card", "minute": 67, "team": "home", "player": "Player C"},
            {
                "type": "substitution",
                "minute": 78,
                "team": "away",
                "player_in": "Player D",
                "player_out": "Player E",
            },
        ]

        processed_events = scores_collector._process_events(events)

        assert len(processed_events) == 4
        assert processed_events[0]["type"] == "goal"
        assert processed_events[1]["type"] == "yellow_card"
        assert processed_events[2]["type"] == "red_card"
        assert processed_events[3]["type"] == "substitution"

    def test_validate_score_data(self, scores_collector):
        """测试比分数据验证"""
        valid_score = {
            "match_id": 12345,
            "status": "FT",
            "score": {"home": 2, "away": 1},
            "events": [],
        }

        invalid_score = {
            "match_id": None,  # 无效ID
            "status": "INVALID_STATUS",  # 无效状态
            "score": {"home": -1, "away": 1},  # 无效比分
            "events": None,
        }

        assert scores_collector._validate_score(valid_score) is True
        assert scores_collector._validate_score(invalid_score) is False


class TestStreamingCollector:
    """流数据采集器测试类"""

    @pytest.fixture
    def streaming_collector(self):
        """流数据采集器实例"""
        return StreamingCollector()

    def test_streaming_collector_initialization(self, streaming_collector):
        """测试流数据采集器初始化"""
        assert streaming_collector is not None
        assert streaming_collector.name == "streaming_collector"
        assert hasattr(streaming_collector, "websocket")
        assert hasattr(streaming_collector, "is_streaming")

    @pytest.mark.asyncio
    async def test_start_streaming(self, streaming_collector):
        """测试开始流数据采集"""
        with patch.object(streaming_collector, "_connect_websocket") as mock_connect:
            mock_connect.return_value = AsyncMock()

            await streaming_collector.start_streaming()

            assert streaming_collector.is_streaming is True
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_streaming(self, streaming_collector):
        """测试停止流数据采集"""
        streaming_collector.is_streaming = True

        with patch.object(
            streaming_collector, "_disconnect_websocket"
        ) as mock_disconnect:
            await streaming_collector.stop_streaming()

            assert streaming_collector.is_streaming is False
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_streaming_data(self, streaming_collector):
        """测试处理流数据"""
        streaming_data = {
            "type": "score_update",
            "match_id": 12345,
            "data": {
                "score": {"home": 1, "away": 0},
                "minute": 35,
                "event": {"type": "goal", "team": "home"},
            },
        }

        processed_data = await streaming_collector._process_streaming_data(
            streaming_data
        )

        assert processed_data["match_id"] == 12345
        assert processed_data["score"]["home"] == 1
        assert processed_data["event"]["type"] == "goal"

    @pytest.mark.asyncio
    async def test_handle_streaming_errors(self, streaming_collector):
        """测试流数据处理错误"""
        invalid_data = {"invalid": "data"}

        with patch.object(streaming_collector.logger, "error") as mock_logger:
            result = await streaming_collector._process_streaming_data(invalid_data)

            assert result is None
            mock_logger.assert_called()


class TestDataCollectorsIntegration:
    """数据采集器集成测试类"""

    @pytest.mark.asyncio
    async def test_collectors_workflow(self):
        """测试完整的采集器工作流"""
        fixtures_collector = FixturesCollector()
        odds_collector = OddsCollector()
        scores_collector = ScoresCollector()

        # 模拟采集赛程数据
        with patch.object(fixtures_collector, "_make_request") as mock_fixtures:
            mock_fixtures.return_value = {
                "matches": [
                    {
                        "id": 12345,
                        "home_team": {"name": "Team A"},
                        "away_team": {"name": "Team B"},
                    }
                ]
            }

            fixtures_data = await fixtures_collector.collect_data()
            assert len(fixtures_data["matches"]) > 0

        # 模拟采集赔率数据
        with patch.object(odds_collector, "_make_request") as mock_odds:
            mock_odds.return_value = {
                "odds": [
                    {
                        "match_id": 12345,
                        "home_win": 2.10,
                        "draw": 3.40,
                        "away_win": 3.20,
                    }
                ]
            }

            odds_data = await odds_collector.collect_data()
            assert len(odds_data["odds"]) > 0

        # 模拟采集比分数据
        with patch.object(scores_collector, "_make_request") as mock_scores:
            mock_scores.return_value = {
                "matches": [
                    {"id": 12345, "status": "LIVE", "score": {"home": 1, "away": 0}}
                ]
            }

            scores_data = await scores_collector.collect_data()
            assert len(scores_data["matches"]) > 0

        # 验证数据一致性
        assert fixtures_data["matches"][0]["id"] == odds_data["odds"][0]["match_id"]
        assert odds_data["odds"][0]["match_id"] == scores_data["matches"][0]["id"]

    @pytest.mark.asyncio
    async def test_collectors_error_recovery(self):
        """测试采集器错误恢复"""
        collector = FixturesCollector()

        # 模拟网络错误，然后恢复
        with patch.object(collector, "_make_request") as mock_request:
            mock_request.side_effect = [
                Exception("Network error"),  # 第一次失败
                {"matches": []},  # 第二次成功
            ]

            # 第一次调用应该失败
            with pytest.raises(Exception):
                await collector.collect_data()

            # 第二次调用应该成功
            result = await collector.collect_data()
            assert result == {"matches": []}

    @pytest.mark.asyncio
    async def test_collectors_performance(self):
        """测试采集器性能"""
        import time

        collector = OddsCollector()

        with patch.object(collector, "_make_request") as mock_request:
            mock_request.return_value = {
                "odds": [{"match_id": i, "home_win": 2.0 + i * 0.1} for i in range(100)]
            }

            start_time = time.time()
            result = await collector.collect_data()
            end_time = time.time()

            # 验证性能指标
            assert len(result["odds"]) == 100
            assert (end_time - start_time) < 5.0  # 应该在5秒内完成

    def test_data_quality_validation(self):
        """测试数据质量验证"""
        collector = FixturesCollector()

        # 测试有效数据
        valid_match = {
            "id": 12345,
            "home_team": {"id": 1, "name": "Team A"},
            "away_team": {"id": 2, "name": "Team B"},
            "league": {"id": 39, "name": "Premier League"},
            "date": "2024-01-15T15:00:00Z",
            "status": "NS",
        }

        # 测试无效数据
        invalid_matches = [
            {},  # 空数据
            {"id": None},  # 缺少ID
            {"id": 12345, "home_team": None},  # 缺少主队
            {
                "id": 12345,
                "home_team": {"name": "Team A"},
                "away_team": None,
            },  # 缺少客队
        ]

        assert collector._validate_match(valid_match) is True

        for invalid_match in invalid_matches:
            assert collector._validate_match(invalid_match) is False
