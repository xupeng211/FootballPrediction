"""
足球数据适配器测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from src.core.exceptions import AdapterError
# from src.adapters.football import FootballDataAdapter


class TestFootballDataAdapter:
    """足球数据适配器测试"""

    @pytest.fixture
    def mock_api_client(self):
        """模拟API客户端"""
        client = AsyncMock()
        client.get.return_value = {"status": "success"}
        client.post.return_value = {"id": 123}
        return client

    @pytest.fixture
    def adapter(self, mock_api_client):
        """创建适配器实例"""
        config = {
            "api_key": "test_key",
            "base_url": "https://api.football-data.org",
            "timeout": 30,
            "rate_limit": 100,
        }
        adapter = FootballDataAdapter(config)
        adapter.client = mock_api_client
        return adapter

    @pytest.mark.asyncio
    async def test_initialize(self, adapter):
        """测试初始化适配器"""
        await adapter.initialize()
        assert adapter.initialized is True

    @pytest.mark.asyncio
    async def test_get_match_data(self, adapter):
        """测试获取比赛数据"""
        # 模拟API响应
        mock_response = {
            "matches": [
                {
                    "id": 1,
                    "homeTeam": {"name": "Team A"},
                    "awayTeam": {"name": "Team B"},
                    "score": {"fullTime": {"home": 2, "away": 1}},
                    "date": "2024-01-01T15:00:00Z",
                }
            ]
        }
        adapter.client.get.return_value = mock_response

        # 获取比赛数据
        result = await adapter.get_match_data(match_id=1)

        # 验证结果
        assert "matches" in result
        assert len(result["matches"]) == 1
        assert result["matches"][0]["id"] == 1

        # 验证API调用
        adapter.client.get.assert_called_once_with("/matches/1")

    @pytest.mark.asyncio
    async def test_get_team_data(self, adapter):
        """测试获取队伍数据"""
        # 模拟API响应
        mock_response = {
            "id": 456,
            "name": "Test Team",
            "shortName": "TT",
            "crestUrl": "https://example.com/crest.png",
            "address": "123 Stadium St",
            "website": "https://testteam.com",
        }
        adapter.client.get.return_value = mock_response

        # 获取队伍数据
        result = await adapter.get_team_data(team_id=456)

        # 验证结果
        assert result["id"] == 456
        assert result["name"] == "Test Team"

        # 验证API调用
        adapter.client.get.assert_called_once_with("/teams/456")

    @pytest.mark.asyncio
    async def test_get_league_data(self, adapter):
        """测试获取联赛数据"""
        # 模拟API响应
        mock_response = {
            "id": 78,
            "name": "Premier League",
            "area": {"name": "England"},
            "currentSeason": {
                "id": 890,
                "startDate": "2023-08-01",
                "endDate": "2024-05-31",
            },
        }
        adapter.client.get.return_value = mock_response

        # 获取联赛数据
        result = await adapter.get_league_data(league_id=78)

        # 验证结果
        assert result["id"] == 78
        assert result["name"] == "Premier League"

        # 验证API调用
        adapter.client.get.assert_called_once_with("/competitions/78")

    @pytest.mark.asyncio
    async def test_get_player_data(self, adapter):
        """测试获取球员数据"""
        # 模拟API响应
        mock_response = {
            "id": 999,
            "name": "John Doe",
            "position": "Midfielder",
            "dateOfBirth": "1990-01-15",
            "nationality": "England",
            "team": {"id": 456, "name": "Test Team"},
        }
        adapter.client.get.return_value = mock_response

        # 获取球员数据
        result = await adapter.get_player_data(player_id=999)

        # 验证结果
        assert result["id"] == 999
        assert result["name"] == "John Doe"
        assert result["position"] == "Midfielder"

        # 验证API调用
        adapter.client.get.assert_called_once_with("/players/999")

    @pytest.mark.asyncio
    async def test_search_teams(self, adapter):
        """测试搜索队伍"""
        # 模拟API响应
        mock_response = {
            "teams": [
                {"id": 1, "name": "Arsenal FC"},
                {"id": 2, "name": "Aston Villa FC"},
            ]
        }
        adapter.client.get.return_value = mock_response

        # 搜索队伍
        result = await adapter.search_teams(name="Ars")

        # 验证结果
        assert len(result["teams"]) == 2
        assert all("Ars" in team["name"] for team in result["teams"])

        # 验证API调用
        adapter.client.get.assert_called_once_with("/teams?name=Ars")

    @pytest.mark.asyncio
    async def test_get_upcoming_matches(self, adapter):
        """测试获取即将到来的比赛"""
        # 模拟API响应
        mock_response = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2024-01-02T15:00:00Z",
                    "status": "SCHEDULED",
                    "homeTeam": {"name": "Team A"},
                    "awayTeam": {"name": "Team B"},
                },
                {
                    "id": 2,
                    "utcDate": "2024-01-03T18:00:00Z",
                    "status": "SCHEDULED",
                    "homeTeam": {"name": "Team C"},
                    "awayTeam": {"name": "Team D"},
                },
            ]
        }
        adapter.client.get.return_value = mock_response

        # 获取即将到来的比赛
        result = await adapter.get_upcoming_matches(team_id=1)

        # 验证结果
        assert len(result["matches"]) == 2
        assert all(match["status"] == "SCHEDULED" for match in result["matches"])

        # 验证API调用
        adapter.client.get.assert_called_once_with("/teams/1/matches?status=SCHEDULED")

    @pytest.mark.asyncio
    async def test_get_historical_matches(self, adapter):
        """测试获取历史比赛"""
        # 模拟API响应
        mock_response = {
            "matches": [
                {
                    "id": 100,
                    "utcDate": "2023-12-01T15:00:00Z",
                    "status": "FINISHED",
                    "score": {"fullTime": {"home": 3, "away": 1}},
                    "homeTeam": {"name": "Team A"},
                    "awayTeam": {"name": "Team B"},
                }
            ]
        }
        adapter.client.get.return_value = mock_response

        # 获取历史比赛
        result = await adapter.get_historical_matches(team_id=1, limit=10)

        # 验证结果
        assert len(result["matches"]) == 1
        assert result["matches"][0]["status"] == "FINISHED"

        # 验证API调用
        adapter.client.get.assert_called_once_with(
            "/teams/1/matches?status=FINISHED&limit=10"
        )

    @pytest.mark.asyncio
    async def test_get_standings(self, adapter):
        """测试获取积分榜"""
        # 模拟API响应
        mock_response = {
            "standings": [
                {
                    "table": [
                        {"position": 1, "team": {"name": "Team A"}, "points": 45},
                        {"position": 2, "team": {"name": "Team B"}, "points": 42},
                    ]
                }
            ]
        }
        adapter.client.get.return_value = mock_response

        # 获取积分榜
        result = await adapter.get_standings(league_id=78, season=2023)

        # 验证结果
        assert len(result["standings"]) == 1
        assert len(result["standings"][0]["table"]) == 2
        assert result["standings"][0]["table"][0]["position"] == 1

        # 验证API调用
        adapter.client.get.assert_called_once_with(
            "/competitions/78/standings?season=2023"
        )

    @pytest.mark.asyncio
    async def test_get_top_scorers(self, adapter):
        """测试获取射手榜"""
        # 模拟API响应
        mock_response = {
            "scorers": [
                {
                    "player": {"name": "Player A"},
                    "team": {"name": "Team X"},
                    "goals": 15,
                },
                {
                    "player": {"name": "Player B"},
                    "team": {"name": "Team Y"},
                    "goals": 12,
                },
            ]
        }
        adapter.client.get.return_value = mock_response

        # 获取射手榜
        result = await adapter.get_top_scorers(league_id=78, season=2023, limit=10)

        # 验证结果
        assert len(result["scorers"]) == 2
        assert result["scorers"][0]["goals"] == 15

        # 验证API调用
        adapter.client.get.assert_called_once_with(
            "/competitions/78/scorers?season=2023&limit=10"
        )

    @pytest.mark.asyncio
    async def test_api_error_handling(self, adapter):
        """测试API错误处理"""
        # 模拟API错误
        adapter.client.get.side_effect = Exception("API Error")

        # 应该抛出适配器错误
        with pytest.raises(AdapterError, match="Failed to fetch match data"):
            await adapter.get_match_data(match_id=1)

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, adapter):
        """测试速率限制处理"""
        # 模拟速率限制错误
        adapter.client.get.side_effect = Exception("Rate limit exceeded")

        # 应该抛出适配器错误
        with pytest.raises(AdapterError, match="Rate limit exceeded"):
            await adapter.get_match_data(match_id=1)

    @pytest.mark.asyncio
    async def test_data_transformation(self, adapter):
        """测试数据转换"""
        # 模拟原始API响应
        mock_response = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2024-01-01T15:00:00Z",
                    "score": {"fullTime": {"homeTeam": 2, "awayTeam": 1}},
                    "homeTeam": {"name": "Home", "id": 10},
                    "awayTeam": {"name": "Away", "id": 20},
                    "status": "FINISHED",
                }
            ]
        }
        adapter.client.get.return_value = mock_response

        # 获取并转换数据
        result = await adapter.get_match_data(match_id=1)

        # 验证数据转换
        match = result["matches"][0]
        assert "date" in match  # 应该从utcDate转换为date
        assert match["home_score"] == 2  # 应该从嵌套结构提取
        assert match["away_score"] == 1

    @pytest.mark.asyncio
    async def test_batch_request(self, adapter):
        """测试批量请求"""
        # 模拟批量响应
        adapter.client.get.side_effect = [
            {"matches": [{"id": 1}, {"id": 2}]},
            {"matches": [{"id": 3}, {"id": 4}]},
        ]

        # 批量获取比赛
        match_ids = [1, 2, 3, 4]
        results = await adapter.batch_get_matches(match_ids)

        # 验证结果
        assert len(results) == 4
        assert all("matches" in result for result in results)

    def test_configuration_validation(self):
        """测试配置验证"""
        # 测试缺少必要配置
        with pytest.raises(AdapterError, match="api_key is required"):
            FootballDataAdapter({})

        # 测试无效配置
        with pytest.raises(AdapterError, match="timeout must be positive"):
            FootballDataAdapter({"api_key": "test", "timeout": -1})

    @pytest.mark.asyncio
    async def test_cache_integration(self, adapter):
        """测试缓存集成"""
        # 模拟缓存
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = True
        adapter.cache = cache

        # 模拟API响应
        mock_response = {"matches": [{"id": 1}]}
        adapter.client.get.return_value = mock_response

        # 获取数据（应该检查缓存）
        await adapter.get_match_data(match_id=1)

        # 验证缓存调用
        cache.get.assert_called_once_with("match:1")
        cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, adapter):
        """测试关闭适配器"""
        await adapter.initialize()
        assert adapter.initialized is True

        await adapter.close()
        assert adapter.initialized is False
        adapter.client.close.assert_called_once()

    def test_build_url_with_params(self, adapter):
        """测试构建带参数的URL"""
        base_url = "/matches"
        params = {"team": 1, "status": "SCHEDULED", "limit": 10}
        url = adapter._build_url(base_url, params)
        assert "/matches?team=1&status=SCHEDULED&limit=10" in url

    def test_parse_date(self, adapter):
        """测试日期解析"""
        # 测试ISO日期
        iso_date = "2024-01-01T15:00:00Z"
        parsed = adapter._parse_date(iso_date)
        assert isinstance(parsed, datetime)
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 1

    def test_validate_response(self, adapter):
        """测试响应验证"""
        # 测试有效响应
        valid_response = {"status": "success", "data": {}}
        assert adapter._validate_response(valid_response) is True

        # 测试无效响应
        invalid_response = {"error": "Not found"}
        assert adapter._validate_response(invalid_response) is False

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, adapter):
        """测试失败重试"""
        # 前两次失败，第三次成功
        adapter.client.get.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            {"matches": [{"id": 1}]},
        ]

        # 获取数据（应该重试）
        result = await adapter.get_match_data(match_id=1, retries=3)

        # 验证成功
        assert "matches" in result
        assert adapter.client.get.call_count == 3
