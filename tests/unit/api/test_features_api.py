"""
特征服务API测试
测试覆盖src/api/features.py中的所有路由
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException
import pandas as pd

from src.api.features import router


@pytest.mark.asyncio
class TestMatchFeatures:
    """测试比赛特征相关端点"""

    @patch('src.api.features.get_async_session')
    @patch('src.api.features.feature_store')
    async def test_get_match_features_success(self, mock_store, mock_get_session):
        """测试获取比赛特征成功"""
        # 模拟数据库会话
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛数据
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 100
        mock_match.match_time = datetime(2024, 1, 15)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_match

        # 模拟特征存储
        mock_store.get_match_features.return_value = {
            "match_id": 1,
            "home_team_features": {"form": 0.8, "goals_scored": 10},
            "away_team_features": {"form": 0.6, "goals_scored": 8},
            "head_to_head": {"home_wins": 5, "away_wins": 3}
        }

        from src.api.features import get_match_features
        result = await get_match_features(1)

        assert result is not None
        assert "data" in result
        assert result["success"] is True

    @patch('src.api.features.get_async_session')
    async def test_get_match_features_invalid_id(self, mock_get_session):
        """测试获取比赛特征时ID无效"""
        from src.api.features import get_match_features

        with pytest.raises(HTTPException) as exc_info:
            await get_match_features(-1)

        assert exc_info.value.status_code == 400
        assert "比赛ID必须大于0" in str(exc_info.value.detail)

    @patch('src.api.features.get_async_session')
    @patch('src.api.features.feature_store', None)
    async def test_get_match_features_service_unavailable(self, mock_get_session):
        """测试特征服务不可用"""
        from src.api.features import get_match_features

        with pytest.raises(HTTPException) as exc_info:
            await get_match_features(1)

        assert exc_info.value.status_code == 503
        assert "特征存储服务暂时不可用" in str(exc_info.value.detail)

    @patch('src.api.features.get_async_session')
    async def test_get_match_features_not_found(self, mock_get_session):
        """测试获取不存在的比赛特征"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛不存在
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        from src.api.features import get_match_features

        with pytest.raises(HTTPException) as exc_info:
            await get_match_features(99999)

        assert exc_info.value.status_code == 404
        assert "比赛 99999 不存在" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestTeamFeatures:
    """测试球队特征相关端点"""

    @patch('src.api.features.get_async_session')
    @patch('src.api.features.feature_store')
    async def test_get_team_features_success(self, mock_store, mock_get_session):
        """测试获取球队特征成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队存在
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.team_name = "Test Team"
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_team

        # 模拟特征存储
        mock_store.get_team_features.return_value = {
            "team_id": 10,
            "recent_form": [1, 0, 1, 1, 0],
            "home_performance": {"wins": 5, "losses": 2},
            "away_performance": {"wins": 3, "losses": 4},
            "goals_stats": {"scored": 20, "conceded": 15}
        }

        from src.api.features import get_team_features
        result = await get_team_features(10)

        assert result is not None
        assert "data" in result
        assert result["success"] is True

    @patch('src.api.features.get_async_session')
    async def test_get_team_features_not_found(self, mock_get_session):
        """测试获取不存在的球队特征"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队不存在
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        from src.api.features import get_team_features

        with pytest.raises(HTTPException) as exc_info:
            await get_team_features(99999)

        assert exc_info.value.status_code == 404
        assert "球队 99999 不存在" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestBatchFeatures:
    """测试批量特征处理端点"""

    @patch('src.api.features.feature_calculator')
    @patch('src.api.features.feature_store')
    async def test_batch_compute_features_success(self, mock_store, mock_calculator):
        """测试批量计算特征成功"""
        # 模拟特征计算器
        mock_calculator.compute_batch_features.return_value = pd.DataFrame({
            'match_id': [1, 2, 3],
            'feature1': [0.1, 0.2, 0.3],
            'feature2': [0.4, 0.5, 0.6]
        })

        # 模拟特征存储
        mock_store.save_features.return_value = True

        from src.api.features import batch_compute_features
        result = await batch_compute_features(
            match_ids=[1, 2, 3],
            feature_types=["basic", "advanced"]
        )

        assert result is not None
        assert result["success"] is True
        assert "processed_count" in result

    @patch('src.api.features.feature_calculator')
    async def test_batch_compute_features_no_matches(self, mock_calculator):
        """测试批量计算时没有比赛"""
        from src.api.features import batch_compute_features
        result = await batch_compute_features(match_ids=[])

        assert result["success"] is False
        assert "没有提供比赛ID" in result["message"]


@pytest.mark.asyncio
class TestFeatureManagement:
    """测试特征管理端点"""

    @patch('src.api.features.feature_store')
    async def test_prefresh_features_success(self, mock_store):
        """测试预刷新特征成功"""
        mock_store.prefresh_features.return_value = {
            "success": True,
            "refreshed_count": 10
        }

        from src.api.features import prefresh_features
        result = await prefresh_features(
            match_ids=[1, 2, 3, 4, 5],
            force_refresh=True
        )

        assert result is not None
        assert result["success"] is True

    @patch('src.api.features.feature_store')
    async def test_clear_cache_success(self, mock_store):
        """测试清除缓存成功"""
        mock_store.clear_cache.return_value = True

        from src.api.features import clear_cache
        result = await clear_cache()

        assert result is not None
        assert result["success"] is True
        assert "缓存清除成功" in result["message"]

    @patch('src.api.features.feature_store')
    async def test_get_feature_stats(self, mock_store):
        """测试获取特征统计信息"""
        mock_store.get_stats.return_value = {
            "total_features": 1000,
            "cached_features": 800,
            "cache_hit_rate": 0.8,
            "last_updated": datetime.now()
        }

        from src.api.features import get_feature_stats
        result = await get_feature_stats()

        assert result is not None
        assert "data" in result
        assert result["success"] is True


@pytest.mark.asyncio
class TestFeatureValidation:
    """测试特征验证端点"""

    @patch('src.api.features.feature_store')
    async def test_validate_features_valid(self, mock_store):
        """测试特征验证 - 有效特征"""
        mock_store.validate_features.return_value = {
            "valid": True,
            "issues": []
        }

        from src.api.features import validate_features
        result = await validate_features(
            feature_data={
                "match_id": 1,
                "home_team_form": 0.8,
                "away_team_form": 0.6
            }
        )

        assert result is not None
        assert result["success"] is True
        assert result["data"]["valid"] is True

    @patch('src.api.features.feature_store')
    async def test_validate_features_invalid(self, mock_store):
        """测试特征验证 - 无效特征"""
        mock_store.validate_features.return_value = {
            "valid": False,
            "issues": ["Missing required field: match_id", "Invalid value for home_team_form"]
        }

        from src.api.features import validate_features
        result = await validate_features(
            feature_data={
                "invalid_field": "value"
            }
        )

        assert result is not None
        assert result["success"] is True
        assert result["data"]["valid"] is False
        assert len(result["data"]["issues"]) > 0


@pytest.mark.asyncio
class TestFeatureHealth:
    """测试特征服务健康检查"""

    @patch('src.api.features.feature_store')
    @patch('src.api.features.feature_calculator')
    async def test_health_check_all_healthy(self, mock_calculator, mock_store):
        """测试健康检查 - 所有服务正常"""
        mock_store.health_check.return_value = {"status": "healthy"}
        mock_calculator.health_check.return_value = {"status": "healthy"}

        from src.api.features import health_check
        result = await health_check()

        assert result is not None
        assert result["status"] == "healthy"
        assert result["services"]["feature_store"]["status"] == "healthy"
        assert result["services"]["feature_calculator"]["status"] == "healthy"

    @patch('src.api.features.feature_store')
    @patch('src.api.features.feature_calculator')
    async def test_health_check_store_unhealthy(self, mock_calculator, mock_store):
        """测试健康检查 - 特征存储不健康"""
        mock_store.health_check.return_value = {"status": "unhealthy", "error": "Redis connection failed"}
        mock_calculator.health_check.return_value = {"status": "healthy"}

        from src.api.features import health_check
        result = await health_check()

        assert result is not None
        assert result["status"] == "degraded"
        assert result["services"]["feature_store"]["status"] == "unhealthy"


class TestRouterConfiguration:
    """测试路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/features"

    def test_router_tags(self):
        """测试路由标签"""
        assert router.tags == ["features"]

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0

        # 检查关键路径存在
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/{match_id}",
            "/teams/{team_id}/features",
            "/batch/compute",
            "/batch/prefresh",
            "/cache/clear",
            "/validate",
            "/stats",
            "/health"
        ]

        for path in expected_paths:
            assert any(path in route_path for route_path in route_paths), f"路径 {path} 不存在"


class TestInitialization:
    """测试模块初始化"""

    def test_feature_store_initialization(self):
        """测试特征存储初始化"""
        # 这个测试验证模块导入时特征存储的初始化
        from src.api.features import feature_store

        # feature_store可能是None（如果初始化失败）或一个实例
        # 主要是确保模块可以正常导入
        assert True  # 如果能导入到这里，说明初始化没有崩溃

    def test_feature_calculator_initialization(self):
        """测试特征计算器初始化"""
        from src.api.features import feature_calculator

        # 同上，确保模块可以正常导入
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])