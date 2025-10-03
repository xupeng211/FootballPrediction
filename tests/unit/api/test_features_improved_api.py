"""
改进特征API测试
测试覆盖src/api/features_improved.py中的所有路由
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from src.api.features_improved import router


@pytest.mark.asyncio
class TestImprovedFeatures:
    """测试改进的特征API端点"""

    @patch('src.api.features_improved.get_async_session')
    @patch('src.api.features_improved.feature_store')
    async def test_get_improved_match_features(self, mock_store, mock_get_session):
        """测试获取改进的比赛特征"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛存在
        mock_match = MagicMock()
        mock_match.id = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_match

        # 模拟特征存储
        mock_store.get_match_features.return_value = {
            "match_id": 1,
            "features": {
                "home_form": 0.8,
                "away_form": 0.6,
                "head_to_head": {"home_wins": 5}
            }
        }

        from src.api.features_improved import get_match_features
        result = await get_match_features(1)

        assert result is not None
        assert "data" in result
        assert result["success"] is True

    @patch('src.api.features_improved.feature_store')
    async def test_get_improved_team_features(self, mock_store):
        """测试获取改进的球队特征"""
        mock_store.get_team_features.return_value = {
            "team_id": 10,
            "features": {
                "recent_form": [1, 0, 1],
                "performance_metrics": {"avg_goals": 1.5}
            }
        }

        from src.api.features_improved import get_team_features
        result = await get_team_features(10)

        assert result is not None
        assert "data" in result
        assert result["success"] is True

    @patch('src.api.features_improved.feature_calculator')
    async def test_calculate_advanced_features(self, mock_calculator):
        """测试计算高级特征"""
        mock_calculator.calculate_advanced.return_value = {
            "feature1": 0.5,
            "feature2": 0.7,
            "confidence": 0.85
        }

        from src.api.features_improved import calculate_advanced_features
        result = await calculate_advanced_features(
            match_id=1,
            feature_types=["pattern", "trend"]
        )

        assert result is not None
        assert "data" in result
        assert result["success"] is True


class TestRouterConfiguration:
    """测试路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_tags(self):
        """测试路由标签"""
        assert "features" in router.tags

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])