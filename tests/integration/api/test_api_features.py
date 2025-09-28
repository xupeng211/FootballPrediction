"""
特征API测试

测试特征相关的FastAPI端点：
- GET /features/{match_id}
- GET /features/teams/{team_id}
- POST /features/calculate/{match_id}
- POST /features/batch/calculate
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.main import app


def pytest_db_available():
    """检查数据库是否可用以及表结构是否存在"""
    try:
        import sqlalchemy as sa

        from src.database.connection import get_database_manager

        # 检查数据库连接
        db_manager = get_database_manager()

        # 检查关键表是否存在
        with db_manager.get_session() as session:
            result = session.execute(
                sa.text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'matches')"
                )
            )
            matches_exists = result.scalar()

            result = session.execute(
                sa.text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'teams')"
                )
            )
            teams_exists = result.scalar()

            return matches_exists and teams_exists

    except Exception:
        return False


# 跳过需要数据库的测试，如果数据库不可用
pytestmark = pytest.mark.skipif(
    not pytest_db_available(), reason="Database connection not available"
)


@pytest.fixture
def client():
    """创建测试客户端"""
    # 初始化多用户数据库管理器以避免运行时错误
    from src.database.connection import initialize_multi_user_database

    try:
        initialize_multi_user_database()
    except Exception:
        # 如果初始化失败，使用模拟的数据库会话
        pass
    return TestClient(app)


@pytest.fixture
def mock_match():
    """模拟比赛数据"""
    return Mock(
        id=1,
        home_team_id=1,
        away_team_id=2,
        league_id=1,
        match_time=datetime(2025, 9, 15, 15, 0),
        season="2024-25",
        match_status="scheduled",
    )


@pytest.fixture
def mock_team():
    """模拟球队数据"""
    return Mock(id=1, name="测试球队", league_id=1, founded_year=2000, venue="测试球场")


class TestFeaturesAPI:
    """特征API测试类"""

    @pytest.fixture(autouse=True)
    def setup_database_mocks(self):
        """自动设置数据库模拟"""
        with patch("src.database.connection.get_async_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session
            yield mock_session

    @pytest.mark.asyncio
    async def test_get_match_features_success(self, client, mock_match):
        """测试获取比赛特征成功"""
        # 🔧 FIXED: 移除对select的patch，只patch特征存储
        with patch("src.api.features.feature_store") as mock_feature_store:
            # 模拟特征存储返回结果
            mock_features = {
                "team_features": [
                    {"team_id": 1, "recent_5_wins": 3, "recent_5_goals_for": 8},
                    {"team_id": 2, "recent_5_wins": 2, "recent_5_goals_for": 6},
                ],
                "h2h_features": {"h2h_total_matches": 5, "h2h_home_wins": 2},
                "odds_features": {"home_implied_probability": 0.45},
            }

            mock_feature_store.get_match_features_for_prediction.return_value = (
                mock_features
            )

            # 🔧 FIXED: 正确配置数据库会话Mock
            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                # 🔧 FIXED: 创建AsyncMock的结果对象
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = AsyncMock(return_value=mock_match)
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                # 发送请求
                response = client.get("_api/v1/features/1")

                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "match_info" in data["data"]
                assert "features" in data["data"]

                # 验证比赛信息
                match_info = data["data"]["match_info"]
                assert match_info["match_id"] == 1
                assert match_info["home_team_id"] == 1
                assert match_info["away_team_id"] == 2

                # 验证特征数据
                features = data["data"]["features"]
                assert "team_features" in features
                assert "h2h_features" in features
                assert "odds_features" in features

    @pytest.mark.asyncio
    async def test_get_match_features_not_found(self, client):
        """测试获取不存在比赛的特征"""
        with patch("src.api.features.select"):
            # 模拟数据库查询返回None
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=None)

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.get("_api/v1/features/999")

                assert response.status_code == 404
                data = response.json()
                assert "比赛 999 不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_team_features_success(self, client, mock_team):
        """测试获取球队特征成功"""
        with patch("src.api.features.select"), patch(
            "src.api.features.feature_store"
        ) as mock_feature_store:
            # 模拟数据库查询结果
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_team)

            # 模拟特征存储返回结果
            mock_features_df = pd.DataFrame(
                {
                    "team_id": [1],
                    "recent_5_wins": [3],
                    "recent_5_goals_for": [8],
                    "recent_5_points": [9],
                }
            )

            mock_feature_store.get_online_features.return_value = mock_features_df

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.get("_api/v1/features/teams/1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # 验证球队信息
        team_info = data["data"]["team_info"]
        assert team_info["team_id"] == 1
        assert team_info["team_name"] == "测试球队"

    # 验证特征数据
        features = data["data"]["features"]
        assert features["recent_5_wins"] == 3
        assert features["recent_5_goals_for"] == 8

    @pytest.mark.asyncio
    async def test_get_team_features_with_raw_data(self, client, mock_team):
        """测试获取球队特征包含原始数据"""
        with patch("src.api.features.select"), patch(
            "src.api.features.feature_store"
        ) as mock_feature_store, patch(
            "src.api.features.feature_calculator"
        ) as mock_calculator:
            # 模拟数据库查询结果
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_team)

            # 模拟特征存储返回空结果
            mock_feature_store.get_online_features.return_value = pd.DataFrame()

            # 模拟原始特征计算
            mock_raw_features = Mock()
            mock_raw_features.to_dict.return_value = {
                "team_entity": {"team_id": 1, "team_name": "测试球队"},
                "recent_performance": {"recent_5_wins": 3, "recent_5_goals_for": 8},
            }
            mock_calculator.calculate_all_team_features.return_value = mock_raw_features

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.get("_api/v1/features/teams/1?include_raw=true")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "raw_features" in data["data"]

    @pytest.mark.asyncio
    async def test_calculate_match_features_success(self, client, mock_match):
        """测试计算比赛特征成功"""
        with patch("src.api.features.select"), patch(
            "src.api.features.feature_store"
        ) as mock_feature_store:
            # 模拟数据库查询结果
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_match)

            # 模拟特征计算和存储成功
            mock_feature_store.calculate_and_store_match_features.return_value = True
            mock_feature_store.calculate_and_store_team_features.return_value = True

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.post("_api/v1/features/calculate/1")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

                result_data = data["data"]
                assert result_data["match_id"] == 1
                assert result_data["match_features_stored"] is True
                assert result_data["home_team_features_stored"] is True
                assert result_data["away_team_features_stored"] is True
                assert "calculation_time" in result_data

    @pytest.mark.asyncio
    async def test_calculate_team_features_success(self, client, mock_team):
        """测试计算球队特征成功"""
        with patch("src.api.features.select"), patch(
            "src.api.features.feature_store"
        ) as mock_feature_store:
            # 模拟数据库查询结果
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_team)

            # 模拟特征计算和存储成功
            mock_feature_store.calculate_and_store_team_features.return_value = True

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.post("_api/v1/features/calculate/teams/1")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

                result_data = data["data"]
                assert result_data["team_id"] == 1
                assert result_data["team_name"] == "测试球队"
                assert result_data["features_stored"] is True
                assert "calculation_date" in result_data

    @pytest.mark.asyncio
    async def test_batch_calculate_features_success(self, client):
        """测试批量计算特征成功"""
        with patch("src.api.features.feature_store") as mock_feature_store:
            # 模拟批量计算统计结果
            mock_stats = {
                "matches_processed": 10,
                "teams_processed": 20,
                "features_stored": 30,
                "errors": 0,
            }
            mock_feature_store.batch_calculate_features.return_value = mock_stats

            # 发送请求
            response = client.post(
                "_api/v1/features/batch/calculate",
                params={
                    "start_date": "2025-09-10T00:00:00",
                    "end_date": "2025-09-17T00:00:00",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            result_data = data["data"]
            assert "date_range" in result_data
            assert result_data["date_range"]["start_date"] == "2025-09-10T00:00:00"
            assert result_data["date_range"]["end_date"] == "2025-09-17T00:00:00"
            assert result_data["statistics"] == mock_stats
            assert "completion_time" in result_data

    @pytest.mark.asyncio
    async def test_batch_calculate_features_invalid_dates(self, client):
        """测试批量计算特征日期无效"""
        response = client.post(
            "_api/v1/features/batch/calculate",
            params={
                "start_date": "2025-09-17T00:00:00",
                "end_date": "2025-09-10T00:00:00",  # 结束日期早于开始日期
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "开始日期必须早于结束日期" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_historical_features_success(self, client, mock_match):
        """测试获取历史特征成功"""
        with patch("src.api.features.select"), patch(
            "src.api.features.feature_store"
        ) as mock_feature_store:
            # 模拟数据库查询结果
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_match)

            # 模拟历史特征查询结果
            mock_historical_df = pd.DataFrame(
                {
                    "match_id": [1, 1],
                    "team_id": [1, 2],
                    "recent_5_wins": [3, 2],
                    "recent_5_goals_for": [8, 6],
                    "event_timestamp": [datetime(2025, 9, 15), datetime(2025, 9, 15)],
                }
            )
            mock_feature_store.get_historical_features.return_value = mock_historical_df

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.get(
                    "_api/v1/features/historical/1",
                    params={"feature_refs": ["team_recent_performance:recent_5_wins"]},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

                result_data = data["data"]
                assert result_data["match_id"] == 1
                assert result_data["feature_count"] == 5  # DataFrame列数
                assert result_data["record_count"] == 2  # DataFrame行数
                assert len(result_data["features"]) == 2  # 转换为records的长度

    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """测试API错误处理"""
        # 测试数据库连接错误
        with patch(
            "src.api.features.get_async_session",
            side_effect=Exception("数据库连接错误"),
        ):
            response = client.get("_api/v1/features/1")
        assert response.status_code == 500

    # 测试特征存储错误
        with patch("src.api.features.select"), patch(
                "src.api.features.feature_store"
            ) as mock_feature_store:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(
                return_value=Mock(id=1, home_team_id=1, away_team_id=2)
            )

            mock_feature_store.get_match_features_for_prediction.side_effect = (
                Exception("特征存储错误")
            )

            with patch("src.api.features.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_get_session.return_value.__aenter__.return_value = mock_session

                response = client.get("/api/v1/features/1")
                assert response.status_code == 500

    def test_api_route_registration(self, client):
        """测试API路由注册"""
        # 测试特征相关路由是否正确注册
        response = client.get("_api/v1/features/1")
        # 即使返回错误，也说明路由已注册（不是404）
        assert response.status_code != 404

        response = client.get("/api/v1/features/teams/1")
        assert response.status_code != 404

        response = client.post("/api/v1/features/calculate/1")
        assert response.status_code != 404

        response = client.post(
            "/api/v1/features/batch/calculate?start_date=2025-09-10T00:00:00&end_date=2025-09-17T00:00:00"
        )
        assert response.status_code != 404
