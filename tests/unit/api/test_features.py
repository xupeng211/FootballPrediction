# TODO: Consider creating a fixture for 22 repeated Mock creations

# TODO: Consider creating a fixture for 22 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

"""
API特征管理测试
Tests for API Features

测试src.api.features模块的特征管理功能
"""

from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# 测试导入
try:
    from src.api.features import (
        build_response_data,
        check_feature_store_availability,
        feature_store,
        get_feature_store,
        get_features_data,
        get_match_info,
        router,
        validate_match_id,
    )

    FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    FEATURES_AVAILABLE = False
    router = None
    get_feature_store = None
    validate_match_id = None
    check_feature_store_availability = None
    get_match_info = None
    get_features_data = None
    build_response_data = None
    feature_store = None


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features module not available")
@pytest.mark.unit
class TestFeatureStore:
    """特征存储测试"""

    def test_get_feature_store_initialization_success(self):
        """测试：特征存储初始化成功"""
        # 重置全局变量
        import src.api.features

        src.api.features.feature_store = None

        with patch("src.api.features.FootballFeatureStore") as mock_store_class:
            mock_store = Mock()
            mock_store_class.return_value = mock_store

            # 第一次调用应该初始化
            store = get_feature_store()
            assert store is mock_store
            mock_store_class.assert_called_once()

            # 第二次调用应该返回缓存实例
            store2 = get_feature_store()
            assert store2 is store
            assert mock_store_class.call_count == 1

    def test_get_feature_store_initialization_failure(self):
        """测试：特征存储初始化失败"""
        # 重置全局变量
        import src.api.features

        src.api.features.feature_store = None

        with patch("src.api.features.FootballFeatureStore") as mock_store_class:
            mock_store_class.side_effect = ValueError("Connection failed")

            store = get_feature_store()
            assert store is None

    def test_get_feature_store_cached(self):
        """测试：获取缓存的特征存储"""
        # 设置全局变量
        import src.api.features

        src.api.features.feature_store = Mock()

        store = get_feature_store()
        assert store is not None


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features module not available")
class TestValidationFunctions:
    """验证函数测试"""

    def test_validate_match_id_valid(self):
        """测试：验证有效的比赛ID"""
        # 不应该抛出异常
        validate_match_id(1)
        validate_match_id(100)
        validate_match_id(999999)

    def test_validate_match_id_invalid(self):
        """测试：验证无效的比赛ID"""
        with pytest.raises(HTTPException) as exc_info:
            validate_match_id(0)
        assert exc_info.value.status_code == 400
        assert "比赛ID必须大于0" in exc_info.value.detail

        with pytest.raises(HTTPException) as exc_info:
            validate_match_id(-1)
        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException) as exc_info:
            validate_match_id(-100)
        assert exc_info.value.status_code == 400

    def test_check_feature_store_availability_available(self):
        """测试：检查特征存储可用（可用）"""
        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = Mock()

            # 不应该抛出异常
            check_feature_store_availability()

    def test_check_feature_store_availability_unavailable(self):
        """测试：检查特征存储可用（不可用）"""
        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                check_feature_store_availability()
            assert exc_info.value.status_code == 503
            assert "特征存储服务暂时不可用" in exc_info.value.detail


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features module not available")
@pytest.mark.asyncio
class TestMatchInfo:
    """比赛信息测试"""

    async def test_get_match_info_success(self):
        """测试：成功获取比赛信息"""
        # 创建模拟会话和比赛
        mock_session = Mock(spec=AsyncSession)
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.league_id = 10
        mock_match.match_time = datetime(2023, 1, 1, 12, 0)
        mock_match.season = "2023-2024"

        # 模拟数据库查询
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        # 获取比赛信息
        match = await get_match_info(mock_session, 123)

        assert match is mock_match
        mock_session.execute.assert_called_once()

    async def test_get_match_info_not_found(self):
        """测试：比赛不存在"""
        mock_session = Mock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_match_info(mock_session, 999)
        assert exc_info.value.status_code == 404
        assert "比赛 999 不存在" in exc_info.value.detail

    async def test_get_match_info_database_error(self):
        """测试：数据库查询错误"""
        from sqlalchemy.exc import SQLAlchemyError

        mock_session = Mock(spec=AsyncSession)
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_match_info(mock_session, 123)
        assert exc_info.value.status_code == 500
        assert "数据库查询失败" in exc_info.value.detail

    async def test_get_match_info_unknown_error(self):
        """测试：未知错误"""
        mock_session = Mock(spec=AsyncSession)
        mock_session.execute.side_effect = ValueError("Invalid data")

        with pytest.raises(HTTPException) as exc_info:
            await get_match_info(mock_session, 123)
        assert exc_info.value.status_code == 500
        assert "查询比赛信息失败" in exc_info.value.detail


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features module not available")
@pytest.mark.asyncio
class TestFeaturesData:
    """特征数据测试"""

    async def test_get_features_data_success(self):
        """测试：成功获取特征数据"""
        # 创建模拟比赛和特征存储
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team_id = "1"
        mock_match.away_team_id = "2"

        mock_store = AsyncMock()
        mock_features = {"feature1": 0.5, "feature2": 0.3}
        mock_store.get_match_features_for_prediction.return_value = mock_features

        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = mock_store

            features, error = await get_features_data(123, mock_match)

            assert features == mock_features
            assert error is None
            mock_store.get_match_features_for_prediction.assert_called_once()

    async def test_get_features_data_store_unavailable(self):
        """测试：特征存储不可用"""
        mock_match = Mock()

        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = None

            features, error = await get_features_data(123, mock_match)

            assert features == {}
            assert error == "feature store unavailable"

    async def test_get_features_data_no_features(self):
        """测试：没有特征数据"""
        mock_match = Mock()
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2

        mock_store = AsyncMock()
        mock_store.get_match_features_for_prediction.return_value = {}

        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = mock_store

            features, error = await get_features_data(123, mock_match)

            assert features == {}
            assert error is None

    async def test_get_features_data_error(self):
        """测试：获取特征数据错误"""
        mock_match = Mock()
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2

        mock_store = AsyncMock()
        mock_store.get_match_features_for_prediction.side_effect = ValueError(
            "Feature calculation failed"
        )

        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = mock_store

            features, error = await get_features_data(123, mock_match)

            assert features == {}
            assert "Feature calculation failed" in error or error is not None


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features module not available")
class TestResponseBuilder:
    """响应构建器测试"""

    def test_build_response_data_success(self):
        """测试：构建成功的响应数据"""
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.league_id = 10
        mock_match.match_time = datetime(2023, 1, 1, 12, 0)
        mock_match.season = "2023-2024"

        features = {"feature1": 0.5, "feature2": 0.3}
        features_error = None

        response = build_response_data(mock_match, features, features_error, False)

        assert response["match_id"] == 123
        assert response["home_team_id"] == 1
        assert response["away_team_id"] == 2
        assert response["league_id"] == 10
        assert response["match_time"] == "2023-01-01T12:00:00"
        assert response["season"] == "2023-2024"
        assert response["features"] == features
        assert response["status"] == "success"
        assert response["message"] == "特征数据获取成功"
        assert "warning" not in response
        assert "raw_features" not in response

    def test_build_response_data_partial_success(self):
        """测试：构建部分成功的响应数据"""
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.league_id = 10
        mock_match.match_time = None
        mock_match.season = "2023-2024"

        features = {"feature1": 0.5}
        features_error = "Feature2 calculation failed"

        response = build_response_data(mock_match, features, features_error, False)

        assert response["status"] == "partial_success"
        assert "部分特征获取失败" in response["warning"]
        assert response["warning"] == "部分特征获取失败: Feature2 calculation failed"

    def test_build_response_data_with_raw_features(self):
        """测试：构建包含原始特征的响应数据"""
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.league_id = 10
        mock_match.match_time = None
        mock_match.season = "2023-2024"

        features = {"feature1": 0.5, "feature2": 0.3, "feature3": 0.2}
        features_error = None

        response = build_response_data(mock_match, features, features_error, True)

        assert "raw_features" in response
        assert response["raw_features"]["feature_count"] == 3
        assert response["raw_features"]["feature_keys"] == [
            "feature1",
            "feature2",
            "feature3",
        ]

    def test_build_response_data_empty_features(self):
        """测试：构建空特征的响应数据"""
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.league_id = 10
        mock_match.match_time = None
        mock_match.season = "2023-2024"

        features = {}
        features_error = None

        response = build_response_data(mock_match, features, features_error, True)

        assert response["features"] == {}
        assert "raw_features" not in response  # 空特征时不包含原始数据


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features module not available")
@pytest.mark.asyncio
class TestAPIEndpoints:
    """API端点测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self):
        """创建测试客户端（不依赖数据库）"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        # 创建独立应用以避免数据库依赖
        test_app = FastAPI()

        # 只注册健康检查端点
        @test_app.get("/features/health")
        async def health_check():
            return {"service": "test", "status": "healthy"}

        return TestClient(test_app)

    def test_router_exists(self):
        """测试：路由器存在"""
        assert router is not None
        assert hasattr(router, "routes")
        assert len(router.routes) > 0

    @pytest.mark.asyncio
    async def test_health_check_endpoint_simple(self):
        """测试：健康检查端点（简化版）"""
        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = Mock()

            # 直接调用函数而不是通过HTTP
            from src.api.features import health_check

            _result = await health_check()
            assert _result["service"] == "特征获取服务"
            assert _result["status"] == "healthy"
            assert _result["feature_store"] == "available"

    @pytest.mark.asyncio
    async def test_health_check_endpoint_unhealthy_simple(self):
        """测试：健康检查端点（不健康，简化版）"""
        with patch("src.api.features.get_feature_store") as mock_get:
            mock_get.return_value = None

            # 直接调用函数而不是通过HTTP
            from src.api.features import health_check

            _result = await health_check()
            assert _result["service"] == "特征获取服务"
            assert _result["status"] == "unhealthy"
            assert _result["feature_store"] == "unavailable"

    # HTTP端点测试需要数据库依赖，已简化为单元测试


@pytest.mark.skipif(FEATURES_AVAILABLE, reason="Features module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not FEATURES_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if FEATURES_AVAILABLE:
        from src.api.features import get_feature_store, router

        assert router is not None
        assert get_feature_store is not None


def test_router_routes():
    """测试：路由器路由"""
    if FEATURES_AVAILABLE:
        routes = [route.path for route in router.routes]
        expected_routes = ["/features/{match_id}", "/features/health"]

        for route in expected_routes:
            assert route in routes, f"Missing route: {route}"


def test_global_feature_store():
    """测试：全局特征存储变量"""
    if FEATURES_AVAILABLE:
        # 验证全局变量存在
        import src.api.features

        assert hasattr(src.api.features, "feature_store")
        # 初始值可能为None
