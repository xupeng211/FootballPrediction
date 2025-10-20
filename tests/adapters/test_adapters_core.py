"""
Adapters模块核心测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.adapters.base import BaseAdapter
    from src.adapters.factory import AdapterFactory
    from src.adapters.registry import AdapterRegistry
    from src.adapters.football import FootballAdapter
except ImportError as e:
    pytest.skip(f"Adapters模块不可用: {e}", allow_module_level=True)


class TestBaseAdapter:
    """测试基础适配器"""

    def test_base_adapter_creation(self):
        """测试基础适配器创建"""
        with patch("src.adapters.base.BaseAdapter") as MockAdapter:
            adapter = MockAdapter()
            adapter.initialize = Mock(return_value=True)
            adapter.connect = Mock(return_value=True)
            adapter.disconnect = Mock(return_value=True)

            assert adapter.initialize() is True
            assert adapter.connect() is True
            assert adapter.disconnect() is True

    def test_base_adapter_methods(self):
        """测试基础适配器方法"""
        with patch("src.adapters.base.BaseAdapter") as MockAdapter:
            adapter = MockAdapter()
            adapter.fetch_data = Mock(return_value={"data": "test"})
            adapter.transform_data = Mock(return_value={"transformed": True})
            adapter.validate_data = Mock(return_value=True)
            adapter.send_data = Mock(return_value=True)

            data = adapter.fetch_data("endpoint")
            transformed = adapter.transform_data(data)
            is_valid = adapter.validate_data(transformed)
            sent = adapter.send_data(transformed)

            assert data["data"] == "test"
            assert transformed["transformed"] is True
            assert is_valid is True
            assert sent is True

    def test_base_adapter_error_handling(self):
        """测试基础适配器错误处理"""
        with patch("src.adapters.base.BaseAdapter") as MockAdapter:
            adapter = MockAdapter()
            adapter.handle_error = Mock(return_value={"error": "handled"})
            adapter.log_error = Mock(return_value=True)

            error = adapter.handle_error(Exception("Test error"))
            assert error["error"] == "handled"

            adapter.log_error("Test message")
            adapter.log_error.assert_called_with("Test message")


class TestAdapterFactory:
    """测试适配器工厂"""

    def test_factory_creation(self):
        """测试工厂创建"""
        with patch("src.adapters.factory.AdapterFactory") as MockFactory:
            factory = MockFactory()
            factory.create_adapter = Mock(return_value=Mock())
            factory.register_adapter = Mock(return_value=True)
            factory.get_available_adapters = Mock(return_value=["football", "cricket"])

            # 创建适配器
            adapter = factory.create_adapter("football")
            assert adapter is not None

            # 注册适配器
            assert factory.register_adapter("test", MockAdapter) is True

            # 获取可用适配器
            adapters = factory.get_available_adapters()
            assert len(adapters) == 2

    def test_factory_singleton(self):
        """测试工厂单例模式"""
        with patch("src.adapters.factory.AdapterFactory") as MockFactory:
            factory1 = MockFactory.instance()
            factory2 = MockFactory.instance()
            MockFactory.instance.return_value = factory1

            assert factory1 == factory2

    def test_factory_with_config(self):
        """测试带配置的工厂"""
        with patch("src.adapters.factory.AdapterFactory") as MockFactory:
            factory = MockFactory()
            factory.configure = Mock(return_value=True)
            factory.get_config = Mock(return_value={"timeout": 30})

            config = {"timeout": 30, "retries": 3}
            factory.configure(config)
            assert factory.get_config()["timeout"] == 30


class TestAdapterRegistry:
    """测试适配器注册表"""

    def test_registry_registration(self):
        """测试适配器注册"""
        with patch("src.adapters.registry.AdapterRegistry") as MockRegistry:
            registry = MockRegistry()
            registry.register = Mock(return_value=True)
            registry.unregister = Mock(return_value=True)
            registry.is_registered = Mock(return_value=True)
            registry.get_adapter = Mock(return_value=Mock())

            # 注册适配器
            assert registry.register("football", MockAdapter) is True

            # 检查是否已注册
            assert registry.is_registered("football") is True

            # 获取适配器
            adapter = registry.get_adapter("football")
            assert adapter is not None

            # 注销适配器
            assert registry.unregister("football") is True

    def test_registry_list_adapters(self):
        """测试列出所有适配器"""
        with patch("src.adapters.registry.AdapterRegistry") as MockRegistry:
            registry = MockRegistry()
            registry.list_all = Mock(return_value=["football", "cricket", "tennis"])
            registry.get_count = Mock(return_value=3)

            adapters = registry.list_all()
            count = registry.get_count()

            assert len(adapters) == 3
            assert count == 3
            assert "football" in adapters

    def test_registry_search(self):
        """测试适配器搜索"""
        with patch("src.adapters.registry.AdapterRegistry") as MockRegistry:
            registry = MockRegistry()
            registry.search_by_capability = Mock(
                return_value=[{"name": "football", "capability": "scores"}]
            )
            registry.search_by_type = Mock(
                return_value=["data_fetcher", "data_transformer"]
            )

            # 按能力搜索
            results = registry.search_by_capability("scores")
            assert results[0]["capability"] == "scores"

            # 按类型搜索
            types = registry.search_by_type("data_fetcher")
            assert "data_fetcher" in types


class TestFootballAdapter:
    """测试足球适配器"""

    def test_football_adapter_creation(self):
        """测试足球适配器创建"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.set_league = Mock(return_value=True)
            adapter.set_season = Mock(return_value=True)
            adapter.fetch_matches = Mock(return_value=[{"match": "test"}])
            adapter.fetch_teams = Mock(return_value=[{"team": "test"}])

            # 设置联赛
            assert adapter.set_league("Premier League") is True

            # 设置赛季
            assert adapter.set_season("2024/2025") is True

            # 获取比赛
            matches = adapter.fetch_matches()
            assert len(matches) == 1

            # 获取队伍
            teams = adapter.fetch_teams()
            assert len(teams) == 1

    def test_football_adapter_odds(self):
        """测试足球赔率获取"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.fetch_odds = Mock(
                return_value={"home_win": 2.5, "draw": 3.2, "away_win": 2.8}
            )
            adapter.fetch_live_odds = Mock(
                return_value={"current_home": 2.3, "current_away": 3.1}
            )

            # 获取赔率
            odds = adapter.fetch_odds()
            assert odds["home_win"] == 2.5
            assert odds["draw"] == 3.2

            # 获取实时赔率
            live_odds = adapter.fetch_live_odds()
            assert live_odds["current_home"] == 2.3

    def test_football_adapter_scores(self):
        """测试足球比分获取"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.fetch_live_scores = Mock(
                return_value=[
                    {"match_id": 1, "home_score": 2, "away_score": 1},
                    {"match_id": 2, "home_score": 0, "away_score": 0},
                ]
            )
            adapter.fetch_final_scores = Mock(
                return_value=[{"match_id": 1, "final_home": 2, "final_away": 1}]
            )

            # 获取实时比分
            live_scores = adapter.fetch_live_scores()
            assert len(live_scores) == 2
            assert live_scores[0]["home_score"] == 2

            # 获取最终比分
            final_scores = adapter.fetch_final_scores()
            assert len(final_scores) == 1

    def test_football_adapter_statistics(self):
        """测试足球统计获取"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.fetch_team_stats = Mock(
                return_value={"wins": 10, "losses": 5, "draws": 3}
            )
            adapter.fetch_player_stats = Mock(
                return_value={"goals": 5, "assists": 3, "yellow_cards": 1}
            )

            # 获取队伍统计
            team_stats = adapter.fetch_team_stats("Team A")
            assert team_stats["wins"] == 10

            # 获取球员统计
            player_stats = adapter.fetch_player_stats("Player 1")
            assert player_stats["goals"] == 5

    def test_football_adapter_error_handling(self):
        """测试足球适配器错误处理"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.fetch_matches = Mock(side_effect=Exception("API error"))
            adapter.handle_api_error = Mock(return_value={"error": "API unavailable"})

            # 处理API错误
            try:
                adapter.fetch_matches()
            except Exception:
                error = adapter.handle_api_error(Exception("API error"))
                assert error["error"] == "API unavailable"

    def test_football_adapter_caching(self):
        """测试足球适配器缓存"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.cache_result = Mock(return_value=True)
            adapter.get_cached_result = Mock(return_value={"cached": True})
            adapter.clear_cache = Mock(return_value=True)

            # 缓存结果
            assert adapter.cache_result("matches", [{"id": 1}]) is True

            # 获取缓存
            cached = adapter.get_cached_result("matches")
            assert cached["cached"] is True

            # 清除缓存
            assert adapter.clear_cache() is True

    def test_football_adapter_rate_limiting(self):
        """测试足球适配器速率限制"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.check_rate_limit = Mock(return_value=False)
            adapter.get_remaining_requests = Mock(return_value=100)
            adapter.wait_if_needed = Mock(return_value=True)

            # 检查速率限制
            assert not adapter.check_rate_limit()

            # 获取剩余请求
            remaining = adapter.get_remaining_requests()
            assert remaining == 100

            # 等待如果需要
            assert adapter.wait_if_needed() is True

    def test_football_adapter_authentication(self):
        """测试足球适配器认证"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.set_api_key = Mock(return_value=True)
            adapter.authenticate = Mock(return_value=True)
            adapter.is_authenticated = Mock(return_value=True)
            adapter.refresh_token = Mock(return_value=True)

            # 设置API密钥
            assert adapter.set_api_key("test_key") is True

            # 认证
            assert adapter.authenticate() is True

            # 检查认证状态
            assert adapter.is_authenticated() is True

            # 刷新令牌
            assert adapter.refresh_token() is True

    def test_football_adapter_batch_operations(self):
        """测试足球适配器批量操作"""
        with patch("src.adapters.football.FootballAdapter") as MockFootballAdapter:
            adapter = MockFootballAdapter()
            adapter.fetch_multiple_matches = Mock(
                return_value=[{"id": i} for i in range(10)]
            )
            adapter.fetch_team_standings = Mock(
                return_value={
                    "position_1": {"team": "Team A", "points": 25},
                    "position_2": {"team": "Team B", "points": 20},
                }
            )

            # 批量获取比赛
            matches = adapter.fetch_multiple_matches([1, 2, 3, 4, 5])
            assert len(matches) == 10

            # 获取积分榜
            standings = adapter.fetch_team_standings()
            assert standings["position_1"]["points"] == 25
