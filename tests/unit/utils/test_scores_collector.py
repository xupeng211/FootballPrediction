import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.data.collectors.scores_collector import ScoresCollector

"""
数据收集器测试 - 比分数据收集器
"""


@pytest.mark.unit
class TestScoresCollector:
    """ScoresCollector测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        collector = ScoresCollector()
        collector.logger = MagicMock()
        return collector

    @pytest.fixture
    def mock_live_score_data(self):
        """Mock实时比分数据"""
        return {
            "match_id": 12345,
            "status": "LIVE",
            "minute": 65,
            "score": {
                "home_team": 2,
                "away_team": 1,
                "half_time": {"home_team": 1, "away_team": 0},
            },
            "events": [
                {"minute": 23, "type": "goal", "team": "home", "player": "Player A"},
                {"minute": 45, "type": "goal", "team": "away", "player": "Player B"},
                {"minute": 67, "type": "goal", "team": "home", "player": "Player C"},
            ],
            "statistics": {
                "possession": {"home": 55, "away": 45},
                "shots": {"home": 12, "away": 8},
                "corners": {"home": 6, "away": 3},
            },
        }

    @pytest.fixture
    def mock_finished_score_data(self):
        """Mock完场比分数据"""
        return {
            "match_id": 12346,
            "status": "FINISHED",
            "final_score": {"home_team": 2, "away_team": 1},
            "minute": 90,
            "goals": [
                {"minute": 15, "scorer": "Home Player 1", "type": "regular"},
                {"minute": 30, "scorer": "Away Player 1", "type": "regular"},
                {"minute": 78, "scorer": "Home Player 2", "type": "penalty"},
            ],
            "cards": [
                {"minute": 35, "player": "Home Player", "type": "yellow"},
                {"minute": 80, "player": "Away Player", "type": "red"},
            ],
        }

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert collector.logger is not None
        assert hasattr(collector, "api_endpoint")
        assert hasattr(collector, "update_interval")

    @pytest.mark.asyncio
    async def test_collect_live_scores(self, collector, mock_live_score_data):
        """测试收集实时比分"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "matches": [mock_live_score_data]
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_live_matches()

            assert result is not None
            assert len(result) == 1
            assert result[0]["match_id"] == 12345
            assert result[0]["status"] == "LIVE"

    @pytest.mark.asyncio
    async def test_collect_match_score(self, collector, mock_live_score_data):
        """测试收集单场比赛比分"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = mock_live_score_data

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_match_score(match_id=12345)

            assert result is not None
            assert result["match_id"] == 12345
            assert result["score"]["home_team"] == 2
            assert result["score"]["away_team"] == 1

    @pytest.mark.asyncio
    async def test_collect_finished_scores(self, collector, mock_finished_score_data):
        """测试收集完场比分"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "matches": [mock_finished_score_data]
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_finished_matches(date="2025-10-05")

            assert result is not None
            assert len(result) == 1
            assert result[0]["status"] == "FINISHED"

    @pytest.mark.asyncio
    async def test_parse_score_events(self, collector, mock_live_score_data):
        """测试解析比分事件"""
        events = await collector._parse_score_events(mock_live_score_data)

        assert len(events) == 3
        assert events[0]["minute"] == 23
        assert events[0]["type"] == "goal"
        assert events[0]["team"] == "home"

    @pytest.mark.asyncio
    async def test_track_score_changes(self, collector):
        """测试跟踪比分变化"""
        old_score = {"home_team": 1, "away_team": 0}
        new_score = {"home_team": 2, "away_team": 1}

        changes = collector._track_score_changes(
            match_id=12345, old_score=old_score, new_score=new_score, minute=65
        )

        assert changes["home_scored"] == 1
        assert changes["away_scored"] == 1
        assert changes["minute"] == 65

    @pytest.mark.asyncio
    async def test_collect_match_statistics(self, collector, mock_live_score_data):
        """测试收集比赛统计数据"""
        _stats = await collector._collect_match_statistics(mock_live_score_data)

        assert stats is not None
        assert "possession" in stats
        assert "shots" in stats
        assert "corners" in stats
        assert stats["possession"]["home"] == 55

    @pytest.mark.asyncio
    async def test_collect_fixtures_scores(self, collector):
        """测试收集即将开始的比赛"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "fixtures": [
                {
                    "match_id": 12347,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "kickoff_time": "2025-10-05T20:00:00Z",
                    "status": "SCHEDULED",
                }
            ]
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_fixtures(date="2025-10-05")

            assert result is not None
            assert len(result) == 1
            assert result[0]["status"] == "SCHEDULED"

    @pytest.mark.asyncio
    async def test_collect_historical_scores(self, collector):
        """测试收集历史比分"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "results": [
                {
                    "match_id": 12348,
                    "date": "2025-09-28",
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "full_time_score": {"home": 2, "away": 1},
                    "half_time_score": {"home": 1, "away": 0},
                }
            ]
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_historical_scores(
                team_id=10, start_date="2025-09-01", end_date="2025-09-30"
            )

            assert result is not None
            assert len(result) == 1
            assert result[0]["full_time_score"]["home"] == 2

    @pytest.mark.asyncio
    async def test_subscribe_live_updates(self, collector):
        """测试订阅实时更新"""
        mock_websocket = AsyncMock()
        mock_websocket.connect = AsyncMock()
        mock_websocket.recv.return_value = json.dumps(
            {
                "type": "score_update",
                "match_id": 12345,
                "score": {"home": 1, "away": 0},
                "minute": 25,
            }
        )

        with patch.object(
            collector, "_get_websocket_client", return_value=mock_websocket
        ):
            updates = []
            async for update in collector.subscribe_live_updates(match_id=12345):
                updates.append(update)
                if len(updates) >= 1:
                    break

            assert len(updates) == 1
            assert updates[0]["match_id"] == 12345

    @pytest.mark.asyncio
    async def test_detect_match_events(self, collector, mock_live_score_data):
        """测试检测比赛事件"""
        events = await collector._detect_match_events(mock_live_score_data)

        assert events is not None
        assert "goals" in events
        assert "cards" in events
        assert "substitutions" in events
        assert len(events["goals"]) == 3

    def test_format_score_for_display(self, collector):
        """测试格式化比分显示"""
        score = {"home_team": 2, "away_team": 1}
        formatted = collector._format_score_for_display(score)

        assert formatted == "2-1"

    def test_calculate_goal_timing(self, collector):
        """测试计算进球时间分布"""
        goals = [
            {"minute": 15, "team": "home"},
            {"minute": 30, "team": "away"},
            {"minute": 67, "team": "home"},
            {"minute": 89, "team": "away"},
        ]

        timing = collector._calculate_goal_timing(goals)

        assert timing["first_half_goals"] == 2
        assert timing["second_half_goals"] == 2
        assert timing["home_goals"] == 2
        assert timing["away_goals"] == 2

    @pytest.mark.asyncio
    async def test_collect_lineup(self, collector):
        """测试收集阵容信息"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "match_id": 12345,
            "home_team": {
                "formation": "4-3-3",
                "starting_xi": [
                    {"name": "Player 1", "position": "GK", "number": 1},
                    {"name": "Player 2", "position": "DEF", "number": 2},
                ],
                "substitutes": [{"name": "Player 12", "position": "DEF", "number": 12}],
            },
            "away_team": {
                "formation": "4-4-2",
                "starting_xi": [
                    {"name": "Player 1", "position": "GK", "number": 1},
                    {"name": "Player 2", "position": "DEF", "number": 2},
                ],
                "substitutes": [{"name": "Player 12", "position": "DEF", "number": 12}],
            },
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_lineup(match_id=12345)

            assert result is not None
            assert result["home_team"]["formation"] == "4-3-3"
            assert len(result["home_team"]["starting_xi"]) == 2

    @pytest.mark.asyncio
    async def test_collect_head_to_head(self, collector):
        """测试收集历史交锋"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "head_to_head": {
                "home_team_wins": 5,
                "away_team_wins": 3,
                "draws": 2,
                "total_matches": 10,
                "recent_matches": [
                    {
                        "date": "2024-05-01",
                        "home_team": 10,
                        "away_team": 20,
                        "result": "home_win",
                        "score": "2-1",
                    }
                ],
            }
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_head_to_head(
                home_team_id=10, away_team_id=20
            )

            assert result is not None
            assert result["home_team_wins"] == 5
            assert result["total_matches"] == 10

    @pytest.mark.asyncio
    async def test_cache_score_data(self, collector, mock_live_score_data):
        """测试缓存比分数据"""
        mock_cache = MagicMock()
        mock_cache.set.return_value = True

        with patch.object(collector, "get_cache_manager", return_value=mock_cache):
            _result = await collector._cache_score_data(mock_live_score_data)

            assert result is True
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_score(self, collector):
        """测试获取缓存的比分"""
        mock_cache = MagicMock()
        cached_data = {
            "match_id": 12345,
            "score": {"home_team": 2, "away_team": 1},
            "updated_at": datetime.now().isoformat(),
        }
        mock_cache.get.return_value = cached_data

        with patch.object(collector, "get_cache_manager", return_value=mock_cache):
            _result = await collector.get_cached_score(match_id=12345)

            assert _result == cached_data
            mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_score_errors(self, collector):
        """测试处理比分错误"""
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = Exception("API error")

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_match_score(match_id=12345)

            assert result is None
            collector.logger.error.assert_called()

    def test_validate_score_data(self, collector, mock_live_score_data):
        """测试验证比分数据"""
        assert collector._validate_score_data(mock_live_score_data) is True

        invalid_data = {"match_id": 12345}  # 缺少score字段
        assert collector._validate_score_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_collect_player_stats(self, collector):
        """测试收集球员统计"""
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = MagicMock()
        mock_http_client.get.return_value.status_code = 200
        mock_http_client.get.return_value.json.return_value = {
            "player_stats": [
                {
                    "player_id": 100,
                    "player_name": "John Doe",
                    "team_id": 10,
                    "position": "Forward",
                    "goals": 1,
                    "assists": 1,
                    "shots": 3,
                    "passes": 25,
                    "pass_accuracy": 88,
                    "rating": 7.8,
                }
            ]
        }

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_player_stats(match_id=12345)

            assert result is not None
            assert len(result["player_stats"]) == 1
            assert result["player_stats"][0]["goals"] == 1

    @pytest.mark.asyncio
    async def test_track_match_momentum(self, collector):
        """测试跟踪比赛势头"""
        events = [
            {"minute": 10, "type": "goal", "team": "home"},
            {"minute": 25, "type": "yellow_card", "team": "away"},
            {"minute": 35, "type": "goal", "team": "home"},
            {"minute": 55, "type": "substitution", "team": "away"},
            {"minute": 70, "type": "goal", "team": "away"},
        ]

        momentum = collector._track_match_momentum(events)

        assert momentum is not None
        assert "home_momentum" in momentum
        assert "away_momentum" in momentum
        assert momentum["home_momentum"][0]["minute"] == 10

    @pytest.mark.asyncio
    async def test_predict_final_score(self, collector, mock_live_score_data):
        """测试预测最终比分"""
        current_score = {"home_team": 2, "away_team": 1}
        minute = 65
        home_advantage = 0.2

        _prediction = collector._predict_final_score(
            current_score=current_score, minute=minute, home_advantage=home_advantage
        )

        assert prediction is not None
        assert "predicted_home_score" in prediction
        assert "predicted_away_score" in prediction
        assert "confidence" in prediction
