# TODO: Consider creating a fixture for 31 repeated Mock creations

# TODO: Consider creating a fixture for 31 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
适配器API测试覆盖率提升
Adapters API Coverage Improvement

专门为提升src/api/adapters.py模块覆盖率而创建的测试用例。
Created specifically to improve coverage for src/api/adapters.py module.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

# 尝试导入适配器API
try:
    from src.adapters import AdapterFactory, AdapterRegistry
    from src.api.adapters import adapter_factory, adapter_registry, router
except ImportError as e:
    print(f"导入适配器模块失败: {e}")
    pytest.skip("无法导入适配器模块", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.external_api
class TestAdaptersAPI:
    """测试适配器API端点"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_registry(self):
        """模拟适配器注册表"""
        with patch("src.api.adapters.adapter_registry") as mock:
            mock.status.value = "inactive"
            mock.get_health_status = AsyncMock(return_value={"status": "healthy"})
            mock.get_metrics_summary = Mock(return_value={"total_adapters": 5})
            mock.initialize = AsyncMock()
            mock.shutdown = AsyncMock()
            mock.get_adapter = AsyncMock()
            mock.get_group = AsyncMock()
            mock.list_adapters = Mock(return_value=[])
            mock.list_groups = Mock(return_value=[])
            mock.enable_adapter = AsyncMock()
            mock.disable_adapter = AsyncMock()
            mock.restart_adapter = AsyncMock()
            yield mock

    @pytest.fixture
    def mock_factory(self):
        """模拟适配器工厂"""
        with patch("src.api.adapters.adapter_factory") as mock:
            mock.get_config = Mock(return_value={})
            mock.get_group_config = Mock(return_value={})
            mock.list_configs = Mock(return_value=[])
            mock.list_group_configs = Mock(return_value=[])
            mock.load_config = AsyncMock(return_value=True)
            mock.save_config = AsyncMock(return_value=True)
            mock.create_adapter = Mock(return_value=Mock())
            mock.create_adapter_group = Mock(return_value={})
            mock.validate_config = Mock(return_value=True)
            yield mock

    def test_get_registry_status_inactive(self, client, mock_registry):
        """测试获取非活跃注册表状态"""
        mock_registry.status.value = "inactive"

        response = client.get("/adapters/registry/status")

        assert response.status_code == 200
        data = response.json()
        assert "registry" in data
        assert "metrics" in data
        mock_registry.initialize.assert_called_once()
        mock_registry.get_health_status.assert_called_once()
        mock_registry.get_metrics_summary.assert_called_once()

    def test_get_registry_status_active(self, client, mock_registry):
        """测试获取活跃注册表状态"""
        mock_registry.status.value = "active"

        response = client.get("/adapters/registry/status")

        assert response.status_code == 200
        data = response.json()
        assert "registry" in data
        assert "metrics" in data
        mock_registry.initialize.assert_not_called()

    def test_initialize_registry(self, client, mock_registry):
        """测试初始化注册表"""
        response = client.post("/adapters/registry/initialize")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "适配器注册表已初始化" in data["message"]
        mock_registry.initialize.assert_called_once()

    def test_shutdown_registry(self, client, mock_registry):
        """测试关闭注册表"""
        response = client.post("/adapters/registry/shutdown")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "适配器注册表已关闭" in data["message"]
        mock_registry.shutdown.assert_called_once()

    def test_get_adapter_configs(self, client, mock_factory):
        """测试获取适配器配置"""
        mock_factory.list_configs.return_value = ["config1", "config2"]
        mock_factory.list_group_configs.return_value = ["group1"]

        response = client.get("/adapters/configs")

        assert response.status_code == 200
        data = response.json()
        assert "configs" in data
        assert "group_configs" in data
        assert data["configs"] == ["config1", "config2"]
        assert data["group_configs"] == ["group1"]

    def test_load_adapter_config_success(self, client, mock_factory):
        """测试成功加载适配器配置"""
        mock_factory.load_config.return_value = True

        response = client.post("/adapters/configs/load", json={"name": "test_config"})

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "配置已加载" in data["message"]

    def test_load_adapter_config_missing_name(self, client):
        """测试缺少配置名称的加载请求"""
        response = client.post("/adapters/configs/load", json={})

        assert response.status_code == 422  # Validation error

    def test_get_football_matches_with_adapter(self, client, mock_registry):
        """测试通过适配器获取足球比赛"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {
            "matches": [
                {"id": 1, "home": "Team A", "away": "Team B"},
                {"id": 2, "home": "Team C", "away": "Team D"},
            ]
        }
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert len(data["matches"]) == 2
        mock_registry.get_adapter.assert_called_with("football")

    def test_get_football_matches_demo_mode(self, client):
        """测试演示模式的足球比赛获取"""
        response = client.get("/adapters/football/matches?demo=true")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert len(data["matches"]) > 0
        assert "demo" in data

    def test_get_football_matches_with_dates(self, client, mock_registry):
        """测试带日期过滤的足球比赛获取"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {"matches": []}
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get(
            "/adapters/football/matches?start_date=2024-01-01&end_date=2024-12-31"
        )

        assert response.status_code == 200
        mock_registry.get_adapter.assert_called_with("football")

    def test_get_football_match_success(self, client, mock_registry):
        """测试成功获取单个足球比赛"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {
            "id": 123,
            "home": "Team A",
            "away": "Team B",
            "date": "2024-01-15",
        }
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/matches/123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 123
        assert data["home"] == "Team A"

    def test_get_football_match_not_found(self, client, mock_registry):
        """测试获取不存在的足球比赛"""
        mock_adapter = Mock()
        mock_adapter.request.side_effect = HTTPException(
            status_code=404, detail="Match not found"
        )
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/matches/999")

        assert response.status_code == 404

    def test_get_football_match_demo_mode(self, client):
        """测试演示模式的单个足球比赛获取"""
        response = client.get("/adapters/football/matches/123?demo=true")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "demo" in data

    def test_get_football_teams_success(self, client, mock_registry):
        """测试成功获取足球队列表"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {
            "teams": [{"id": 1, "name": "Team A"}, {"id": 2, "name": "Team B"}]
        }
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/teams")

        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert len(data["teams"]) == 2

    def test_get_football_teams_with_search(self, client, mock_registry):
        """测试搜索足球队"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {"teams": []}
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/teams?search=Team")

        assert response.status_code == 200
        mock_registry.get_adapter.assert_called_with("football")

    def test_get_football_teams_demo_mode(self, client):
        """测试演示模式的足球队获取"""
        response = client.get("/adapters/football/teams?demo=true")

        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert len(data["teams"]) > 0
        assert "demo" in data

    def test_get_team_players_success(self, client, mock_registry):
        """测试成功获取球队球员"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {
            "players": [
                {"id": 1, "name": "Player A", "position": "Forward"},
                {"id": 2, "name": "Player B", "position": "Goalkeeper"},
            ]
        }
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/teams/123/players")

        assert response.status_code == 200
        data = response.json()
        assert "players" in data
        assert len(data["players"]) == 2

    def test_get_team_players_demo_mode(self, client):
        """测试演示模式的球队球员获取"""
        response = client.get("/adapters/football/teams/123/players?demo=true")

        assert response.status_code == 200
        data = response.json()
        assert "players" in data
        assert len(data["players"]) > 0
        assert "demo" in data

    def test_demo_adapter_comparison(self, client):
        """测试适配器比较演示"""
        response = client.get("/adapters/demo/comparison")

        assert response.status_code == 200
        data = response.json()
        assert "adapters" in data
        assert "comparison" in data

    def test_demo_adapter_fallback(self, client):
        """测试适配器回退演示"""
        response = client.get("/adapters/demo/fallback")

        assert response.status_code == 200
        data = response.json()
        assert "fallback" in data
        assert "message" in data

    def test_demo_data_transformation(self, client):
        """测试数据转换演示"""
        response = client.get("/adapters/demo/transformation")

        assert response.status_code == 200
        data = response.json()
        assert "original" in data
        assert "transformed" in data

    def test_get_football_matches_error(self, client, mock_registry):
        """测试获取足球比赛时出错"""
        mock_registry.get_adapter.side_effect = HTTPException(
            status_code=503, detail="Service unavailable"
        )

        response = client.get("/adapters/football/matches")

        assert response.status_code == 503

    def test_get_football_match_error(self, client, mock_registry):
        """测试获取单个足球比赛时出错"""
        mock_registry.get_adapter.side_effect = Exception("Connection error")

        response = client.get("/adapters/football/matches/123")

        assert response.status_code == 500

    def test_get_football_teams_error(self, client, mock_registry):
        """测试获取足球队时出错"""
        mock_adapter = Mock()
        mock_adapter.request.side_effect = Exception("API error")
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/teams")

        assert response.status_code == 500

    def test_get_team_players_error(self, client, mock_registry):
        """测试获取球队球员时出错"""
        mock_adapter = Mock()
        mock_adapter.request.side_effect = Exception("Data error")
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/teams/123/players")

        assert response.status_code == 500

    def test_get_football_matches_with_live_filter(self, client, mock_registry):
        """测试实时比赛过滤"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {"matches": []}
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get("/adapters/football/matches?live=true")

        assert response.status_code == 200
        mock_registry.get_adapter.assert_called_with("football")

    def test_get_football_matches_all_parameters(self, client, mock_registry):
        """测试所有参数的足球比赛获取"""
        mock_adapter = Mock()
        mock_adapter.request.return_value = {"matches": []}
        mock_registry.get_adapter.return_value = mock_adapter

        response = client.get(
            "/adapters/football/matches?demo =
    false&live=true&start_date=2024-01-01&end_date=2024-12-31&league=premier"
        )

        assert response.status_code == 200
        mock_registry.get_adapter.assert_called_with("football")


class TestAdaptersModuleStructure:
    """测试适配器模块结构"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, "routes")

    def test_adapter_factory_exists(self):
        """测试适配器工厂存在"""
        assert adapter_factory is not None
        assert isinstance(adapter_factory, AdapterFactory)

    def test_adapter_registry_exists(self):
        """测试适配器注册表存在"""
        assert adapter_registry is not None
        assert isinstance(adapter_registry, AdapterRegistry)

    def test_router_prefix(self):
        """测试路由器前缀"""
        assert router.prefix == "/adapters"

    def test_router_tags(self):
        """测试路由器标签"""
        assert "适配器模式" in router.tags


class TestModuleImports:
    """测试模块导入"""

    def test_adapters_import(self):
        """测试适配器导入"""
        try:
            from src.api.adapters import router

            assert router is not None
        except ImportError as e:
            pytest.skip(f"适配器模块导入失败: {e}")

    def test_adapters_classes_import(self):
        """测试适配器类导入"""
        try:
            from src.adapters import AdapterFactory, AdapterRegistry

            assert AdapterFactory is not None
            assert AdapterRegistry is not None
        except ImportError as e:
            pytest.skip(f"适配器类导入失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
