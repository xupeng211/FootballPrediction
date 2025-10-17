"""
测试 fixture 是否正确工作
"""

import pytest


@pytest.mark.unit
class TestFixtures:
    """测试 fixture 基本功能"""

    @pytest.mark.asyncio
    async def test_api_client_fixture(self, api_client):
        """测试 api_client fixture"""
        # 验证 fixture 正确返回 AsyncClient 或 mock
        from httpx import AsyncClient
        from unittest.mock import AsyncMock

        assert api_client is not None
        assert hasattr(api_client, "get")
        assert hasattr(api_client, "post")
        # 检查是 AsyncClient 或 AsyncMock
        assert isinstance(api_client, (AsyncMock, AsyncClient))

    def test_performance_metrics_fixture(self, performance_metrics):
        """测试 performance_metrics fixture"""
        # 测试计时器功能
        performance_metrics.start_timer("test_timer")
        import time

        time.sleep(0.01)
        duration = performance_metrics.end_timer("test_timer")

        assert duration >= 0.01
        assert duration < 0.1

    def test_performance_metrics_counters(self, performance_metrics):
        """测试计数器功能"""
        performance_metrics.increment("test_counter")
        performance_metrics.increment("test_counter")

        assert performance_metrics.counters["test_counter"] == 2

    def test_data_loader_fixture(self, test_data_loader):
        """测试 test_data_loader fixture"""
        # 测试创建团队
        teams = test_data_loader.create_teams()
        assert len(teams) > 0
        assert "id" in teams[0]
        assert "name" in teams[0]

        # 测试创建比赛
        matches = test_data_loader.create_matches()
        assert len(matches) > 0
        assert "home_team_id" in matches[0]
        assert "away_team_id" in matches[0]

        # 测试创建赔率
        odds = test_data_loader.create_odds(1)
        assert "home_odds" in odds
        assert "draw_odds" in odds
        assert "away_odds" in odds
