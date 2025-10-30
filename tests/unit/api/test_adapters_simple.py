# TODO: Consider creating a fixture for 6 repeated Mock creations

# TODO: Consider creating a fixture for 6 repeated Mock creations


"""
适配器API端点简化测试
Tests for Adapter API Endpoints (Simple Version)

专注于测试API端点的核心功能,使用简化的Mock避免序列化问题。
"""


import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.adapters import router


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.unit
@pytest.mark.api
class TestAdaptersAPI:
    """适配器API测试"""

    # ==================== 适配器注册表管理测试 ====================

    @patch("src.api.adapters.adapter_registry")
    def test_get_registry_status(self, mock_registry, client):
        """测试:获取注册表状态"""
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
        _data = response.json()
        assert "registry" in _data
        assert "metrics" in _data

    @patch("src.api.adapters.adapter_registry")
    def test_initialize_registry(self, mock_registry, client):
        """测试:初始化注册表"""
        # Given
        mock_registry.initialize = AsyncMock()

        # When
        response = client.post("/adapters/registry/initialize")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["message"] == "适配器注册表已初始化"

    @patch("src.api.adapters.adapter_registry")
    def test_shutdown_registry(self, mock_registry, client):
        """测试:关闭注册表"""
        # Given
        mock_registry.shutdown = AsyncMock()

        # When
        response = client.post("/adapters/registry/shutdown")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["message"] == "适配器注册表已关闭"

    # ==================== 适配器配置管理测试 ====================

    @patch("src.api.adapters.adapter_factory")
    def test_get_adapter_configs(self, mock_factory, client):
        """测试:获取适配器配置"""
        # Given
        mock_factory.list_configs.return_value = ["adapter1"]
        mock_factory.get_config.return_value = Mock(
            adapter_type="api-football",
            enabled=True,
            priority=1,
            rate_limits={"rpm": 60},
            cache_config={"ttl": 300},
        )
        mock_factory.list_group_configs.return_value = ["group1"]
        mock_factory.get_group_config.return_value = Mock(
            adapters=["adapter1"],
            primary_adapter="adapter1",
            fallback_strategy="round_robin",
        )

        # When
        response = client.get("/adapters/configs")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert "adapters" in _data
        assert "groups" in _data

    @patch("src.api.adapters.adapter_factory")
    def test_load_adapter_config(self, mock_factory, client):
        """测试:加载适配器配置"""
        # Given
        mock_factory._configs = {}
        config_data = {
            "adapter_name": "test_adapter",
            "adapter_type": "api-football",
        }

        # When
        response = client.post("/adapters/configs/load", json=config_data)

        # Then
        assert response.status_code == 200

    # ==================== 足球数据适配器测试 ====================

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_matches_demo_mode(self, mock_registry, client):
        """测试:演示模式获取足球比赛数据"""
        # Given
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/matches")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["source"] == "demo_adapter"
        assert _data["total_matches"] == 2

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_matches_with_params(self, mock_registry, client):
        """测试:带参数获取比赛数据"""
        # Given
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/matches?league_id=39&team_id=111&live=true")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["filters"]["league_id"] == "39"
        assert _data["filters"]["team_id"] == "111"
        assert _data["filters"]["live"] is True

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_match_demo_mode(self, mock_registry, client):
        """测试:演示模式获取比赛详情"""
        # Given
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/matches/12345")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["source"] == "demo_adapter"
        assert _data["match"]["id"] == "12345"

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_teams_demo_mode(self, mock_registry, client):
        """测试:演示模式获取球队数据"""
        # Given
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/teams")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["source"] == "demo_adapter"
        assert _data["total_teams"] == 2

    @patch("src.api.adapters.adapter_registry")
    def test_get_football_teams_with_search(self, mock_registry, client):
        """测试:搜索球队"""
        # Given
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/teams?search=Manchester")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["filters"]["search"] == "Manchester"

    @patch("src.api.adapters.adapter_registry")
    def test_get_team_players_demo_mode(self, mock_registry, client):
        """测试:演示模式获取球员数据"""
        # Given
        mock_registry.get_adapter.return_value = None

        # When
        response = client.get("/adapters/football/teams/111/players")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert _data["source"] == "demo_adapter"
        assert _data["team_id"] == "111"

    # ==================== 演示功能测试 ====================

    def test_demo_adapter_comparison(self, client):
        """测试:多数据源对比演示"""
        # When
        response = client.get("/adapters/demo/comparison")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert "comparison" in _data
        assert "benefits" in _data

    def test_demo_adapter_fallback(self, client):
        """测试:故障转移演示"""
        # When
        response = client.get("/adapters/demo/fallback")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert "scenario" in _data
        assert "result" in _data
        assert _data["result"]["success"] is True

    def test_demo_data_transformation(self, client):
        """测试:数据转换演示"""
        # When
        response = client.get("/adapters/demo/transformation")

        # Then
        assert response.status_code == 200
        _data = response.json()
        assert "examples" in _data
        assert "benefits" in _data
        assert len(_data["examples"]) == 2

    # ==================== 错误处理测试 ====================

    def test_get_football_matches_invalid_date_format(self, client):
        """测试:无效日期格式"""
        # When
        response = client.get("/adapters/football/matches?date_from=invalid-date")

        # Then - FastAPI会自动验证日期格式
        assert response.status_code == 422

    # ==================== 边界条件测试 ====================

    def test_get_team_players_empty_team_id(self, client):
        """测试:空的球队ID"""
        # When
        response = client.get("/adapters/football/teams//players")

        # Then
        assert response.status_code == 404  # FastAPI路由不匹配
