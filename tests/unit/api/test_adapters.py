"""
适配器API端点测试
Tests for Adapter API Endpoints

测试适配器模式的所有API端点，包括：
- 适配器注册表管理
- 配置管理
- 足球数据获取
- 演示功能
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.adapters import router
from src.adapters import AdapterFactory, AdapterRegistry


class MockAdapter:
    """模拟适配器"""

    def __init__(self, name="mock_adapter"):
        self.name = name
        self.initialized = False

    async def initialize(self):
        """初始化适配器"""
        self.initialized = True

    def get_metrics(self):
        """获取指标"""
        return {
            "requests_count": 10,
            "success_count": 9,
            "error_count": 1,
            "average_response_time": 150.0,
        }

    async def get_matches(self, date, league_id=None, team_id=None, live=False):
        """获取比赛数据"""
        return [
            Mock(
                id="123",
                home_team="Team A",
                away_team="Team B",
                home_team_id="1",
                away_team_id="2",
                competition="Premier League",
                competition_id="39",
                match_date=datetime.now(),
                status=Mock(value="SCHEDULED"),
                home_score=None,
                away_score=None,
                venue="Stadium",
                weather={"temperature": "20°C", "condition": "Sunny"},
            )
        ]

    async def get_match(self, match_id):
        """获取单个比赛"""
        if match_id == "999":
            return None
        return Mock(
            id=match_id,
            home_team="Team A",
            away_team="Team B",
            home_team_id="1",
            away_team_id="2",
            competition="Premier League",
            competition_id="39",
            match_date=datetime.now(),
            status=Mock(value="SCHEDULED"),
            home_score=None,
            away_score=None,
            venue="Stadium",
            weather={"temperature": "20°C", "condition": "Sunny"},
        )

    async def get_teams(self, league_id=None):
        """获取球队数据"""
        return [
            Mock(
                id="111",
                name="Manchester United",
                short_name="MUFC",
                country="England",
                founded=1878,
                stadium="Old Trafford",
                logo_url="https://example.com/logo.png",
            )
        ]

    async def get_players(self, team_id, season=None):
        """获取球员数据"""
        return [
            Mock(
                id="1001",
                name="Bruno Fernandes",
                team_id=team_id,
                position="Midfielder",
                age=28,
                nationality="Portugal",
                height="1.79m",
                weight="69kg",
                photo_url="https://example.com/photo.jpg",
            )
        ]


class TestAdaptersAPI:
    """适配器API测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_factory(self):
        """模拟适配器工厂"""
        factory = Mock(spec=AdapterFactory)
        factory._configs = {}
        factory.list_configs.return_value = ["test_adapter"]
        factory.get_config.return_value = Mock(
            adapter_type="api-football",
            enabled=True,
            priority=1,
            rate_limits={"requests_per_minute": 60},
            cache_config={"ttl": 300},
        )
        factory.list_group_configs.return_value = ["test_group"]
        factory.get_group_config.return_value = Mock(
            adapters=["adapter1", "adapter2"],
            primary_adapter="adapter1",
            fallback_strategy="round_robin",
        )
        return factory

    @pytest.fixture
    def mock_registry(self):
        """模拟适配器注册表"""
        registry = Mock(spec=AdapterRegistry)
        registry.status = Mock(value="inactive")
        registry.initialize = AsyncMock()
        registry.shutdown = AsyncMock()
        registry.get_health_status = AsyncMock(
            return_value={
                "status": "active",
                "total_adapters": 5,
                "active_adapters": 4,
            }
        )
        registry.get_metrics_summary = Mock(
            return_value={
                "total_requests": 1000,
                "success_rate": 0.95,
            }
        )
        registry.get_adapter = Mock(return_value=MockAdapter())
        return registry

    def setup_mocks(self, mock_factory, mock_registry):
        """设置模拟对象"""
        import src.api.adapters

        src.api.adapters.adapter_factory = mock_factory
        src.api.adapters.adapter_registry = mock_registry

    # ==================== 适配器注册表管理测试 ====================

    @patch("src.api.adapters.adapter_registry")
    def test_get_registry_status_inactive(self, mock_registry, client):
        """测试：获取未初始化的注册表状态"""
        # Given
        mock_registry.status.value = "inactive"
        mock_registry.initialize = AsyncMock()
        mock_registry.get_health_status = AsyncMock(
            return_value={
                "status": "active",
                "total_adapters": 5,
            }
        )
        mock_registry.get_metrics_summary = Mock(
            return_value={
                "total_requests": 1000,
            }
        )

        # When
        response = client.get("/adapters/registry/status")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "registry" in data
        assert "metrics" in data
        mock_registry.initialize.assert_called_once()

    @patch("src.api.adapters.adapter_registry")
    def test_get_registry_status_active(self, mock_registry, client):
        """测试：获取已初始化的注册表状态"""
        # Given
        mock_registry.status.value = "active"
        mock_registry.get_health_status = AsyncMock(
            return_value={
                "status": "active",
                "total_adapters": 5,
                "active_adapters": 4,
            }
        )
        mock_registry.get_metrics_summary = Mock(
            return_value={
                "total_requests": 1000,
                "success_rate": 0.95,
            }
        )

        # When
        response = client.get("/adapters/registry/status")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["registry"]["status"] == "active"
        assert data["registry"]["total_adapters"] == 5
        assert data["metrics"]["total_requests"] == 1000
        mock_registry.initialize.assert_not_called()

    @patch("src.api.adapters.adapter_registry")
    def test_initialize_registry(self, mock_registry, client):
        """测试：初始化注册表"""
        # Given
        mock_registry.initialize = AsyncMock()

        # When
        response = client.post("/adapters/registry/initialize")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "适配器注册表已初始化"

    @patch("src.api.adapters.adapter_registry")
    def test_shutdown_registry(self, mock_registry, client):
        """测试：关闭注册表"""
        # Given
        mock_registry.shutdown = AsyncMock()

        # When
        response = client.post("/adapters/registry/shutdown")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "适配器注册表已关闭"

    # ==================== 适配器配置管理测试 ====================

    @patch("src.api.adapters.adapter_factory")
    def test_get_adapter_configs(self, mock_factory, client):
        """测试：获取适配器配置"""
        # Given
        mock_factory.list_configs.return_value = ["adapter1", "adapter2"]
        mock_factory.get_config.side_effect = [
            Mock(
                adapter_type="api-football",
                enabled=True,
                priority=1,
                rate_limits={"rpm": 60},
                cache_config={"ttl": 300},
            ),
            Mock(
                adapter_type="opta",
                enabled=False,
                priority=2,
                rate_limits={"rpm": 30},
                cache_config={"ttl": 600},
            ),
        ]
        mock_factory.list_group_configs.return_value = ["group1"]
        mock_factory.get_group_config.return_value = Mock(
            adapters=["adapter1", "adapter2"],
            primary_adapter="adapter1",
            fallback_strategy="round_robin",
        )

        # When
        response = client.get("/adapters/configs")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "adapters" in data
        assert "groups" in data
        assert len(data["adapters"]) == 2
        assert data["adapters"]["adapter1"]["adapter_type"] == "api-football"
        assert data["adapters"]["adapter1"]["enabled"] is True
        assert data["groups"]["group1"]["primary_adapter"] == "adapter1"

    @patch("src.api.adapters.adapter_factory")
    def test_load_adapter_config_success(self, mock_factory, client):
        """测试：成功加载适配器配置"""
        # Given
        mock_factory._configs = {}
        config_data = {
            "adapter_name": "test_adapter",
            "adapter_type": "api-football",
            "enabled": True,
            "parameters": {"api_key": "test_key"},
        }

        # When
        response = client.post("/adapters/configs/load", json=config_data)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "test_adapter" in data["message"]

    @patch("src.api.adapters.adapter_factory")
    def test_load_adapter_config_missing_name(self, mock_factory, client):
        """测试：加载配置缺少适配器名称"""
        # Given
        config_data = {
            "adapter_type": "api-football",
            "enabled": True,
        }

        # When
        response = client.post("/adapters/configs/load", json=config_data)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    # ==================== 足球数据适配器测试 ====================

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_matches_with_adapter(self, mock_registry, client):
        """测试：使用适配器获取足球比赛数据"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/matches?league_id=39&team_id=111")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "mock_adapter"
        assert data["total_matches"] == 1
        assert len(data["matches"]) == 1
        assert data["matches"][0]["home_team"] == "Team A"
        assert data["filters"]["league_id"] == "39"
        assert data["filters"]["team_id"] == "111"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_matches_demo_mode(self, mock_registry, client):
        """测试：演示模式获取足球比赛数据"""
        # Given
        mock_registry.status.value = "active"
        mock_registry.get_adapter.return_value = None  # 没有可用适配器

        # When
        response = client.get("/adapters/football/matches")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "demo_adapter"
        assert data["total_matches"] == 2
        assert len(data["matches"]) == 2
        assert data["matches"][0]["home_team"] == "Manchester United"
        assert data["message"] == "使用演示适配器返回模拟数据"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_matches_with_dates(self, mock_registry, client):
        """测试：使用日期范围获取比赛数据"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        date_from = date(2023, 12, 1)
        date_to = date(2023, 12, 7)

        # When
        response = client.get(
            f"/adapters/football/matches?date_from={date_from}&date_to={date_to}"
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["date_from"] == "2023-12-01"
        assert data["filters"]["date_to"] == "2023-12-07"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_match_success(self, mock_registry, client):
        """测试：成功获取单个比赛详情"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/matches/123")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "mock_adapter"
        assert data["match"]["id"] == "123"
        assert data["match"]["home_team"] == "Team A"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_match_not_found(self, mock_registry, client):
        """测试：比赛不存在"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/matches/999")

        # Then
        assert response.status_code == 404

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_match_demo_mode(self, mock_registry, client):
        """测试：演示模式获取比赛详情"""
        # Given
        mock_registry.status.value = "active"
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/matches/12345")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "demo_adapter"
        assert data["match"]["id"] == "12345"
        assert data["match"]["home_team"] == "Manchester United"
        assert data["match"]["venue"] == "Old Trafford"
        assert data["message"] == "使用演示适配器返回模拟数据"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_teams_success(self, mock_registry, client):
        """测试：成功获取球队数据"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/teams?league_id=39")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "mock_adapter"
        assert data["total_teams"] == 1
        assert data["teams"][0]["name"] == "Manchester United"
        assert data["filters"]["league_id"] == "39"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_teams_with_search(self, mock_registry, client):
        """测试：搜索球队"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/teams?search=Manchester")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["search"] == "Manchester"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_teams_demo_mode(self, mock_registry, client):
        """测试：演示模式获取球队数据"""
        # Given
        mock_registry.status.value = "active"
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/teams")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "demo_adapter"
        assert data["total_teams"] == 2
        assert data["teams"][0]["name"] == "Manchester United"
        assert data["message"] == "使用演示适配器返回模拟数据"

    @patch("src.api.adapters.adapter_registry")
    def test_get_team_players_success(self, mock_registry, client):
        """测试：成功获取球队球员"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = MockAdapter()
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/teams/111/players?season=2023")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "mock_adapter"
        assert data["team_id"] == "111"
        assert data["season"] == "2023"
        assert data["total_players"] == 1
        assert data["players"][0]["name"] == "Bruno Fernandes"
        assert data["players"][0]["position"] == "Midfielder"

    @patch("src.api.adapters.adapter_registry")
    def test_get_team_players_demo_mode(self, mock_registry, client):
        """测试：演示模式获取球员数据"""
        # Given
        mock_registry.status.value = "active"
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/teams/111/players")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "demo_adapter"
        assert data["team_id"] == "111"
        assert data["total_players"] == 2
        assert data["players"][0]["name"] == "Bruno Fernandes"
        assert data["message"] == "使用演示适配器返回模拟数据"

    # ==================== 演示功能测试 ====================

    def test_demo_adapter_comparison(self, client):
        """测试：多数据源对比演示"""
        # When
        response = client.get("/adapters/demo/comparison?match_id=12345")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert "unified_format" in data
        assert "benefits" in data
        assert "api_football" in data["comparison"]
        assert "opta" in data["comparison"]
        assert data["unified_format"]["id"] == "12345"
        assert len(data["benefits"]) > 0

    def test_demo_adapter_fallback(self, client):
        """测试：故障转移演示"""
        # When
        response = client.get("/adapters/demo/fallback")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "scenario" in data
        assert "adapters" in data
        assert "timeline" in data
        assert "result" in data
        assert "features" in data
        assert data["result"]["success"] is True
        assert data["result"]["data_source"] == "tertiary"
        assert len(data["timeline"]) == 3

    def test_demo_data_transformation(self, client):
        """测试：数据转换演示"""
        # When
        response = client.get("/adapters/demo/transformation")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert "benefits" in data
        assert len(data["examples"]) == 2
        assert "API-Football" in data["examples"][0]["source"]
        assert "transformations" in data["examples"][0]
        assert "input" in data["examples"][0]
        assert "output" in data["examples"][0]

    # ==================== 错误处理测试 ====================

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_matches_error(self, mock_registry, client):
        """测试：获取比赛数据时的错误处理"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = Mock()
        mock_adapter.get_matches = AsyncMock(side_effect=ValueError("API Error"))
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/matches")

        # Then
        assert response.status_code == 500
        assert "获取比赛数据失败" in response.json()["detail"]

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_match_error(self, mock_registry, client):
        """测试：获取比赛详情时的错误处理"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = Mock()
        mock_adapter.get_match = AsyncMock(side_effect=KeyError("Missing data"))
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/matches/123")

        # Then
        assert response.status_code == 500
        assert "获取比赛详情失败" in response.json()["detail"]

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_teams_error(self, mock_registry, client):
        """测试：获取球队数据时的错误处理"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = Mock()
        mock_adapter.get_teams = AsyncMock(
            side_effect=AttributeError("Invalid attribute")
        )
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/teams")

        # Then
        assert response.status_code == 500
        assert "获取球队数据失败" in response.json()["detail"]

    @patch("src.api.adapters.adapter_registry")
    def test_get_team_players_error(self, mock_registry, client):
        """测试：获取球员数据时的错误处理"""
        # Given
        mock_registry.status.value = "active"
        mock_adapter = Mock()
        from requests.exceptions import HTTPError

        mock_adapter.get_players = AsyncMock(side_effect=HTTPError("HTTP error"))
        mock_registry.get_adapter.return_value = mock_adapter

        # When
        response = client.get("/adapters/football/teams/111/players")

        # Then
        assert response.status_code == 500
        assert "获取球员数据失败" in response.json()["detail"]

    # ==================== 参数验证测试 ====================

    def test_get_football_matches_with_live_filter(self, client):
        """测试：使用live过滤器获取比赛"""
        # When
        response = client.get("/adapters/football/matches?live=true")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["live"] is True

    def test_get_football_matches_all_parameters(self, client):
        """测试：使用所有参数获取比赛"""
        # Given
        params = {
            "date_from": "2023-12-01",
            "date_to": "2023-12-07",
            "league_id": "39",
            "team_id": "111",
            "live": "true",
        }

        # When
        response = client.get("/adapters/football/matches", params=params)

        # Then
        assert response.status_code == 200
        data = response.json()
        filters = data["filters"]
        assert filters["date_from"] == "2023-12-01"
        assert filters["date_to"] == "2023-12-07"
        assert filters["league_id"] == "39"
        assert filters["team_id"] == "111"
        assert filters["live"] is True
