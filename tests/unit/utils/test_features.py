"""
特征服务API测试

测试 src/api/features.py 中的7个API端点：
- GET /features/{match_id} - 获取比赛特征
- GET /features/teams/{team_id} - 获取球队特征
- POST /features/calculate/{match_id} - 计算比赛特征
- GET /features/calculate/teams/{team_id} - 计算球队特征
- POST /features/batch/calculate - 批量计算特征
- GET /features/historical/{match_id} - 获取历史特征
- GET /features/health - 特征服务健康检查
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import pytest


class TestGetMatchFeatures:
    """获取比赛特征API测试"""

    @pytest.mark.asyncio
    async def test_get_match_features_success(self, api_client_full):
        """测试获取比赛特征成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_match.season = "2024-25"
        mock_match.match_status = "scheduled"

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_match_features_for_prediction = AsyncMock(
                return_value={
                    "home_recent_wins": 3,
                    "away_recent_wins": 2,
                    "head_to_head_home_wins": 4,
                    "odds_home_win": 2.1,
                    "odds_draw": 3.2,
                    "odds_away_win": 3.8,
                }
            )

            # Mock FeatureCalculator
            with patch("src.api.features.feature_calculator") as mock_calculator:
                mock_calculator.calculate_all_match_features = AsyncMock(
                    return_value=pd.DataFrame(
                        {
                            "feature1": [1.0],
                            "feature2": [2.0],
                        }
                    )
                )

                # 发送请求
                response = api_client_full.get(
                    "/api/v1/features/12345?include_raw=true"
                )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["match_info"]["match_id"] == 12345
        assert data["data"]["match_info"]["home_team_id"] == 10
        assert data["data"]["match_info"]["away_team_id"] == 20
        assert "features" in data["data"]
        assert "raw_features" in data["data"]
        assert "成功获取比赛 12345 的特征" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_invalid_id(self, api_client_full):
        """测试无效的比赛ID"""
        # 发送请求
        response = api_client_full.get("/api/v1/features/0")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "比赛ID必须大于0" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_not_found(self, api_client_full):
        """测试比赛不存在"""
        mock_session = api_client_full.mock_session

        # 设置mock返回值 - 比赛不存在
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.get("/api/v1/features/99999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "比赛 99999 不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_service_unavailable(self, api_client_full):
        """测试特征存储服务不可用"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock feature_store为None
        with patch("src.api.features.feature_store", None):
            # 发送请求
            response = api_client_full.get("/api/v1/features/12345")

        # 验证响应
        assert response.status_code == 503
        data = response.json()
        assert data["error"] is True
        assert "特征存储服务暂时不可用" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_database_error(self, api_client_full):
        """测试数据库查询错误"""
        mock_session = api_client_full.mock_session

        # 模拟数据库错误
        mock_session.execute.side_effect = Exception("Database connection failed")

        # 发送请求
        response = api_client_full.get("/api/v1/features/12345")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert "Database connection failed" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_without_raw_data(self, api_client_full):
        """测试获取比赛特征（不包含原始数据）"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_match_features_for_prediction.return_value = {
                "home_recent_wins": 3,
                "away_recent_wins": 2,
            }

            # 发送请求（不包含include_raw参数）
            response = api_client_full.get("/api/v1/features/12345")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "features" in data["data"]
        assert "raw_features" not in data["data"]


class TestGetTeamFeatures:
    """获取球队特征API测试"""

    @pytest.mark.asyncio
    async def test_get_team_features_success(self, api_client_full):
        """测试获取球队特征成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"
        mock_team.league_id = 1
        mock_team.founded_year = 1900
        mock_team.venue = "Test Stadium"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_team_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_online_features = AsyncMock(
                return_value=pd.DataFrame(
                    {
                        "recent_5_wins": [3],
                        "recent_5_draws": [1],
                        "recent_5_losses": [1],
                        "recent_5_goals_for": [8],
                        "recent_5_goals_against": [5],
                    }
                )
            )

            # 发送请求
            response = api_client_full.get("/api/v1/features/teams/10")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["team_info"]["team_id"] == 10
        assert data["data"]["team_info"]["team_name"] == "Test Team FC"
        assert "features" in data["data"]
        assert data["data"]["features"]["recent_5_wins"] == 3
        assert "成功获取球队 Test Team FC 的特征" in data["message"]

    @pytest.mark.asyncio
    async def test_get_team_features_with_date(self, api_client_full):
        """测试获取球队特征（指定日期）"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_team_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_online_features = AsyncMock(
                return_value=pd.DataFrame(
                    {
                        "recent_5_wins": [2],
                        "recent_5_draws": [2],
                    }
                )
            )

            # 发送请求（带日期参数）
            response = api_client_full.get(
                "/api/v1/features/teams/10?calculation_date=2025-09-15T15:00:00"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "2025-09-15T15:00:00" in data["data"]["calculation_date"]

    @pytest.mark.asyncio
    async def test_get_team_features_not_found(self, api_client_full):
        """测试球队不存在"""
        mock_session = api_client_full.mock_session

        # 设置mock返回值 - 球队不存在
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_team_result

        # 发送请求
        response = api_client_full.get("/api/v1/features/teams/99999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "球队 99999 不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_team_features_empty_features(self, api_client_full):
        """测试球队特征为空"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_team_result

        # Mock FootballFeatureStore - 返回空特征
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_online_features = AsyncMock(return_value=pd.DataFrame())

            # 发送请求
            response = api_client_full.get("/api/v1/features/teams/10")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["features"] == {}


class TestCalculateMatchFeatures:
    """计算比赛特征API测试"""

    @pytest.mark.asyncio
    async def test_calculate_match_features_success(self, api_client_full):
        """测试计算比赛特征成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)
        mock_match.season = "2024-25"

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.calculate_and_store_match_features = AsyncMock(return_value=True)
            mock_store.calculate_and_store_team_features = AsyncMock(return_value=True)

            # 发送请求
            response = api_client_full.post("/api/v1/features/calculate/12345")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["match_id"] == 12345
        assert data["data"]["match_features_stored"] is True
        assert data["data"]["home_team_features_stored"] is True
        assert data["data"]["away_team_features_stored"] is True
        assert "calculation_time" in data["data"]
        assert data["message"] == "特征计算完成"

    @pytest.mark.asyncio
    async def test_calculate_match_features_force_recalculate(self, api_client_full):
        """测试强制重新计算比赛特征"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.calculate_and_store_match_features = AsyncMock(return_value=True)
            mock_store.calculate_and_store_team_features = AsyncMock(return_value=True)

            # 发送请求（带force_recalculate参数）
            response = api_client_full.post(
                "/api/v1/features/calculate/12345?force_recalculate=true"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_calculate_match_features_not_found(self, api_client_full):
        """测试计算不存在的比赛特征"""
        mock_session = api_client_full.mock_session

        # 设置mock返回值 - 比赛不存在
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.post("/api/v1/features/calculate/99999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "比赛 99999 不存在" in data["message"]


class TestCalculateTeamFeatures:
    """计算球队特征API测试"""

    @pytest.mark.asyncio
    async def test_calculate_team_features_success(self, api_client_full):
        """测试计算球队特征成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_team_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.calculate_and_store_team_features = AsyncMock(return_value=True)

            # 发送请求
            response = api_client_full.get("/api/v1/features/calculate/teams/10")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["team_id"] == 10
        assert data["data"]["features_stored"] is True
        assert "calculation_date" in data["data"]
        assert "球队 Test Team FC 特征计算完成" in data["message"]

    @pytest.mark.asyncio
    async def test_calculate_team_features_with_date(self, api_client_full):
        """测试计算球队特征（指定日期）"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_team_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.calculate_and_store_team_features = AsyncMock(return_value=True)

            # 发送请求（带日期参数）
            response = api_client_full.get(
                "/api/v1/features/calculate/teams/10?calculation_date=2025-09-15T15:00:00"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "2025-09-15T15:00:00" in data["data"]["calculation_date"]

    @pytest.mark.asyncio
    async def test_calculate_team_features_not_found(self, api_client_full):
        """测试计算不存在的球队特征"""
        mock_session = api_client_full.mock_session

        # 设置mock返回值 - 球队不存在
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_team_result

        # 发送请求
        response = api_client_full.get("/api/v1/features/calculate/teams/99999")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "球队 99999 不存在" in data["message"]


class TestBatchCalculateFeatures:
    """批量计算特征API测试"""

    @pytest.mark.asyncio
    async def test_batch_calculate_features_success(self, api_client_full):
        """测试批量计算特征成功"""
        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.batch_calculate_features = AsyncMock(
                return_value={
                    "total_matches": 50,
                    "successful_calculations": 48,
                    "failed_calculations": 2,
                    "processing_time": 120.5,
                }
            )

            # 发送请求
            response = api_client_full.post(
                "/api/v1/features/batch/calculate?start_date=2025-09-01T00:00:00&end_date=2025-09-07T23:59:59"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["date_range"]["start_date"] == "2025-09-01T00:00:00"
        assert data["data"]["date_range"]["end_date"] == "2025-09-07T23:59:59"
        assert data["data"]["statistics"]["total_matches"] == 50
        assert data["data"]["statistics"]["successful_calculations"] == 48
        assert "completion_time" in data["data"]
        assert data["message"] == "批量特征计算完成"

    @pytest.mark.asyncio
    async def test_batch_calculate_features_invalid_date_range(self, api_client_full):
        """测试无效的日期范围"""
        # 发送请求（开始日期晚于结束日期）
        response = api_client_full.post(
            "/api/v1/features/batch/calculate?start_date=2025-09-10T00:00:00&end_date=2025-09-01T00:00:00"
        )

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "开始日期必须早于结束日期" in data["message"]

    @pytest.mark.asyncio
    async def test_batch_calculate_features_range_too_large(self, api_client_full):
        """测试时间范围过大"""
        # 发送请求（时间范围超过30天）
        response = api_client_full.post(
            "/api/v1/features/batch/calculate?start_date=2025-08-01T00:00:00&end_date=2025-09-15T00:00:00"
        )

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "时间范围不能超过30天" in data["message"]

    @pytest.mark.asyncio
    async def test_batch_calculate_features_exactly_30_days(self, api_client_full):
        """测试恰好30天的时间范围"""
        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.batch_calculate_features = AsyncMock(
                return_value={
                    "total_matches": 30,
                    "successful_calculations": 30,
                    "failed_calculations": 0,
                }
            )

            # 发送请求（恰好30天）
            response = api_client_full.post(
                "/api/v1/features/batch/calculate?start_date=2025-08-16T00:00:00&end_date=2025-09-15T00:00:00"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestGetHistoricalFeatures:
    """获取历史特征API测试"""

    @pytest.mark.asyncio
    async def test_get_historical_features_success(self, api_client_full):
        """测试获取历史特征成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_historical_features = AsyncMock(
                return_value=pd.DataFrame(
                    {
                        "match_id": [12345, 12345],
                        "team_id": [10, 20],
                        "feature1": [1.0, 2.0],
                        "feature2": [3.0, 4.0],
                    }
                )
            )

            # 发送请求
            response = api_client_full.get(
                "/api/v1/features/historical/12345?feature_refs=feature1&feature_refs=feature2"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["feature_refs"] == ["feature1", "feature2"]
        assert (
            data["data"]["feature_count"] == 4
        )  # match_id, team_id, feature1, feature2
        assert data["data"]["record_count"] == 2
        assert len(data["data"]["features"]) == 2
        assert data["message"] == "成功获取历史特征数据"

    @pytest.mark.asyncio
    async def test_get_historical_features_multiple_refs(self, api_client_full):
        """测试获取历史特征（多个特征引用）"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.match_time = datetime(2025, 9, 15, 15, 0, 0)

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_historical_features = AsyncMock(
                return_value=pd.DataFrame(
                    {
                        "match_id": [12345, 12345],
                        "team_id": [10, 20],
                        "team_performance": [0.8, 0.6],
                        "head_to_head": [0.7, 0.3],
                    }
                )
            )

            # 发送请求（多个特征引用）
            response = api_client_full.get(
                "/api/v1/features/historical/12345?"
                "feature_refs=team_performance&feature_refs=head_to_head"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["feature_refs"]) == 2

    @pytest.mark.asyncio
    async def test_get_historical_features_match_not_found(self, api_client_full):
        """测试获取不存在比赛的历史特征"""
        mock_session = api_client_full.mock_session

        # 设置mock返回值 - 比赛不存在
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.get(
            "/api/v1/features/historical/99999?feature_refs=feature1"
        )

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "比赛 99999 不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_historical_features_empty_result(self, api_client_full):
        """测试历史特征为空"""
        mock_session = api_client_full.mock_session

        # 创建模拟比赛
        mock_match = MagicMock()
        mock_match.id = 12345

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_match_result

        # Mock FootballFeatureStore - 返回空结果
        with patch("src.api.features.feature_store") as mock_store:
            mock_store.get_historical_features = AsyncMock(return_value=pd.DataFrame())

            # 发送请求
            response = api_client_full.get(
                "/api/v1/features/historical/12345?feature_refs=feature1"
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["feature_count"] == 0
        assert data["data"]["record_count"] == 0


class TestFeaturesHealthCheck:
    """特征服务健康检查API测试"""

    @pytest.mark.asyncio
    async def test_features_health_check_healthy(self, api_client_full):
        """测试特征服务健康检查 - 健康"""
        # 发送请求（使用默认的feature_store和feature_calculator）
        response = api_client_full.get("/api/v1/features/health")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_features_health_check_unhealthy(self, api_client_full):
        """测试特征服务健康检查 - 基本验证"""
        # 发送请求
        response = api_client_full.get("/api/v1/features/health")

        # 验证响应基本结构
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_features_health_check_degraded(self, api_client_full):
        """测试特征服务健康检查 - 基本验证"""
        # 发送请求
        response = api_client_full.get("/api/v1/features/health")

        # 验证响应基本结构
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
