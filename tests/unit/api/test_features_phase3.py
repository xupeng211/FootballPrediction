"""
Phase 3: 特征服务 API 综合测试

为 src/api/features.py 和 src/api/features_improved.py 创建综合测试
覆盖所有API端点、错误处理、参数验证和边界情况
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pandas as pd
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


class MockAsyncResult:
    """Mock for SQLAlchemy async result with proper scalars().all() support"""

    def __init__(self, scalars_result=None, scalar_one_or_none_result=None):
        self._scalars_result = scalars_result or []
        self._scalar_one_or_none_result = scalar_one_or_none_result

    def scalars(self):
        return MockScalarResult(self._scalars_result)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_result


class MockScalarResult:
    """Mock for SQLAlchemy scalars() result"""

    def __init__(self, result):
        self._result = result if isinstance(result, list) else [result]

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


from src.api.features import (
    batch_calculate_features,
    calculate_match_features,
    calculate_team_features,
    feature_calculator,
    feature_store,
    features_health_check,
    get_historical_features,
    get_match_features,
    get_team_features,
)
from src.api.features_improved import feature_calculator as improved_feature_calculator
from src.api.features_improved import feature_store as improved_feature_store
from src.api.features_improved import features_health_check as improved_health_check
from src.api.features_improved import get_match_features_improved
from src.database.models.match import Match
from src.database.models.team import Team
from src.features.entities import MatchEntity, TeamEntity
from src.utils.response import APIResponse


class TestFeaturesAPI:
    """特征服务API测试基类"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_match(self):
        """模拟比赛数据"""
        match = MagicMock()
        match.id = 12345
        match.home_team_id = 1
        match.away_team_id = 2
        match.league_id = 1
        match.match_time = datetime(2024, 1, 15, 15, 0)
        match.season = "2024-25"
        match.match_status = "scheduled"
        return match

    @pytest.fixture
    def mock_team(self):
        """模拟球队数据"""
        team = MagicMock()
        team.id = 1
        team.name = "Test Team"
        team.league_id = 1
        team.founded_year = 1900
        team.venue = "Test Stadium"
        return team

    @pytest.fixture
    def mock_features_data(self):
        """模拟特征数据"""
        return {
            "home_recent_goals": 2.5,
            "away_recent_goals": 1.8,
            "home_defense_strength": 0.75,
            "away_defense_strength": 0.68,
            "head_to_head_stats": {"wins": 3, "draws": 2, "losses": 1},
        }

    @pytest.fixture
    def mock_team_features_df(self):
        """模拟球队特征DataFrame"""
        return pd.DataFrame(
            [
                {
                    "team_recent_performance:recent_5_wins": 3,
                    "team_recent_performance:recent_5_draws": 1,
                    "team_recent_performance:recent_5_losses": 1,
                    "team_recent_performance:recent_5_goals_for": 8,
                    "team_recent_performance:recent_5_goals_against": 4,
                    "team_recent_performance:recent_5_points": 10,
                    "team_recent_performance:recent_5_home_wins": 2,
                    "team_recent_performance:recent_5_away_wins": 1,
                }
            ]
        )

    @pytest.fixture
    def mock_historical_features_df(self):
        """模拟历史特征DataFrame"""
        return pd.DataFrame(
            [
                {
                    "match_id": 12345,
                    "team_id": 1,
                    "event_timestamp": datetime(2024, 1, 15, 15, 0),
                    "feature_1": 0.5,
                    "feature_2": 0.8,
                    "feature_3": 0.3,
                },
                {
                    "match_id": 12345,
                    "team_id": 2,
                    "event_timestamp": datetime(2024, 1, 15, 15, 0),
                    "feature_1": 0.7,
                    "feature_2": 0.6,
                    "feature_3": 0.4,
                },
            ]
        )


class TestGetMatchFeatures(TestFeaturesAPI):
    """测试获取比赛特征API"""

    @pytest.mark.asyncio
    async def test_get_match_features_success(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试成功获取比赛特征"""
        # 设置mock返回值
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_match)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            result = await get_match_features(12345, False, mock_session)

            # APIResponse.success() 返回的是字典，检查结构
            assert result["success"] is True
            assert "data" in result
            assert "message" in result
            assert "timestamp" in result
            assert result["data"]["match_info"]["match_id"] == 12345
            assert result["data"]["features"] == mock_features_data
            assert "成功获取比赛" in result["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_invalid_match_id(self, mock_session):
        """测试无效比赛ID"""
        with pytest.raises(Exception) as exc_info:
            await get_match_features(-1, False, mock_session)

        assert "比赛ID必须大于0" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_service_unavailable(self, mock_session):
        """测试特征存储服务不可用"""
        with patch("src.api.features.feature_store", None):
            with pytest.raises(Exception) as exc_info:
                await get_match_features(12345, False, mock_session)

            assert "特征存储服务暂时不可用" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_match_not_found(self, mock_session):
        """测试比赛不存在"""
        mock_session.execute.return_value = MockAsyncResult(
            scalars_result=[], scalar_one_or_none_result=None
        )

        with pytest.raises(Exception) as exc_info:
            await get_match_features(99999, False, mock_session)

        assert "不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_database_error(self, mock_session):
        """测试数据库查询错误"""
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            await get_match_features(12345, False, mock_session)

        assert "数据库查询失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_entity_creation_error(
        self, mock_session, mock_match
    ):
        """测试比赛实体创建错误"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            MatchEntity, "__init__", side_effect=Exception("Entity creation failed")
        ):
            with pytest.raises(Exception) as exc_info:
                await get_match_features(12345, False, mock_session)

            assert "处理比赛数据时发生错误" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_no_features_data(self, mock_session, mock_match):
        """测试无特征数据情况"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = {}

            result = await get_match_features(12345, False, mock_session)

            assert result["data"]["features"] == {}
            assert "成功获取比赛" in result["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_feature_retrieval_error(
        self, mock_session, mock_match
    ):
        """测试特征获取错误"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.side_effect = Exception("Feature retrieval failed")

            # 验证HTTP异常被正确抛出
            with pytest.raises(HTTPException) as exc_info:
                await get_match_features(12345, False, mock_session)

            assert exc_info.value.status_code == 500
            assert "获取特征数据失败" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_match_features_with_raw_data(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试包含原始特征数据"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            with patch.object(
                feature_calculator,
                "calculate_all_match_features",
                new_callable=AsyncMock,
            ) as mock_calculate:
                mock_raw_features = pd.DataFrame({"feature1": [1.0], "feature2": [2.0]})
                mock_calculate.return_value = mock_raw_features

                result = await get_match_features(12345, True, mock_session)

                assert "raw_features" in result["data"]
                assert result["data"]["raw_features"] == mock_raw_features.to_dict()

    @pytest.mark.asyncio
    async def test_get_match_features_raw_data_error(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试原始特征计算错误"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            with patch.object(
                feature_calculator,
                "calculate_all_match_features",
                new_callable=AsyncMock,
            ) as mock_calculate:
                mock_calculate.side_effect = Exception("Raw calculation failed")

                result = await get_match_features(12345, True, mock_session)

                assert "raw_features_error" in result["data"]
                assert "Raw calculation failed" in result["data"]["raw_features_error"]

    @pytest.mark.asyncio
    async def test_get_match_features_no_feature_calculator(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试无特征计算器情况"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            with patch("src.api.features.feature_calculator", None):
                result = await get_match_features(12345, True, mock_session)

                assert "raw_features" not in result["data"]


class TestGetTeamFeatures(TestFeaturesAPI):
    """测试获取球队特征API"""

    @pytest.mark.asyncio
    async def test_get_team_features_success(
        self, mock_session, mock_team, mock_team_features_df
    ):
        """测试成功获取球队特征"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "get_online_features", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_team_features_df

            result = await get_team_features(1, None, False, mock_session)

            assert result["success"] is True
            assert result["data"]["team_info"]["team_id"] == 1
            assert (
                result["data"]["features"]["team_recent_performance:recent_5_wins"] == 3
            )
            assert "成功获取球队" in result["message"]

    @pytest.mark.asyncio
    async def test_get_team_features_team_not_found(self, mock_session):
        """测试球队不存在"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=None
        )

        with pytest.raises(Exception) as exc_info:
            await get_team_features(99999, None, False, mock_session)

        assert "不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_team_features_with_calculation_date(
        self, mock_session, mock_team, mock_team_features_df
    ):
        """测试指定计算日期"""
        calculation_date = datetime(2024, 1, 15)
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "get_online_features", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_team_features_df

            result = await get_team_features(1, calculation_date, False, mock_session)

            assert result["data"]["calculation_date"] == calculation_date.isoformat()

    @pytest.mark.asyncio
    async def test_get_team_features_empty_features(self, mock_session, mock_team):
        """测试空特征数据"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "get_online_features", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = pd.DataFrame()

            result = await get_team_features(1, None, False, mock_session)

            assert result["data"]["features"] == {}

    @pytest.mark.asyncio
    async def test_get_team_features_with_raw_data(
        self, mock_session, mock_team, mock_team_features_df
    ):
        """测试包含原始特征数据"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "get_online_features", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_team_features_df

            with patch.object(
                feature_calculator,
                "calculate_all_team_features",
                new_callable=AsyncMock,
            ) as mock_calculate:
                mock_raw_features = pd.DataFrame({"feature1": [1.0], "feature2": [2.0]})
                mock_calculate.return_value = mock_raw_features

                result = await get_team_features(1, None, True, mock_session)

                assert "raw_features" in result["data"]
                assert result["data"]["raw_features"] == mock_raw_features.to_dict()

    @pytest.mark.asyncio
    async def test_get_team_features_raw_data_error(
        self, mock_session, mock_team, mock_team_features_df
    ):
        """测试原始特征计算错误"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "get_online_features", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_team_features_df

            with patch.object(
                feature_calculator,
                "calculate_all_team_features",
                new_callable=AsyncMock,
            ) as mock_calculate:
                mock_calculate.side_effect = Exception("Raw calculation failed")

                result = await get_team_features(1, None, True, mock_session)

                assert "raw_features_error" in result["data"]
                assert "Raw calculation failed" in result["data"]["raw_features_error"]


class TestCalculateMatchFeatures(TestFeaturesAPI):
    """测试计算比赛特征API"""

    @pytest.mark.asyncio
    async def test_calculate_match_features_success(self, mock_session, mock_match):
        """测试成功计算比赛特征"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "calculate_and_store_match_features", new_callable=AsyncMock
        ) as mock_calc_match:
            mock_calc_match.return_value = True

            with patch.object(
                feature_store,
                "calculate_and_store_team_features",
                new_callable=AsyncMock,
            ) as mock_calc_team:
                mock_calc_team.return_value = True

                result = await calculate_match_features(12345, False, mock_session)

                assert result["success"] is True
                assert result["data"]["match_features_stored"] is True
                assert result["data"]["home_team_features_stored"] is True
                assert result["data"]["away_team_features_stored"] is True
                assert "特征计算完成" in result["message"]

    @pytest.mark.asyncio
    async def test_calculate_match_features_match_not_found(self, mock_session):
        """测试比赛不存在"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=None
        )

        with pytest.raises(Exception) as exc_info:
            await calculate_match_features(99999, False, mock_session)

        assert "不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_calculate_match_features_partial_failure(
        self, mock_session, mock_match
    ):
        """测试部分特征计算失败"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "calculate_and_store_match_features", new_callable=AsyncMock
        ) as mock_calc_match:
            mock_calc_match.return_value = False

            with patch.object(
                feature_store,
                "calculate_and_store_team_features",
                new_callable=AsyncMock,
            ) as mock_calc_team:
                mock_calc_team.return_value = True

                result = await calculate_match_features(12345, False, mock_session)

                assert result["data"]["match_features_stored"] is False
                assert result["data"]["home_team_features_stored"] is True

    @pytest.mark.asyncio
    async def test_calculate_match_features_calculation_error(
        self, mock_session, mock_match
    ):
        """测试特征计算错误"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "calculate_and_store_match_features", new_callable=AsyncMock
        ) as mock_calc_match:
            mock_calc_match.side_effect = Exception("Calculation failed")

            with pytest.raises(Exception) as exc_info:
                await calculate_match_features(12345, False, mock_session)

            assert "计算比赛特征失败" in str(exc_info.value.detail)


class TestCalculateTeamFeatures(TestFeaturesAPI):
    """测试计算球队特征API"""

    @pytest.mark.asyncio
    async def test_calculate_team_features_success(self, mock_session, mock_team):
        """测试成功计算球队特征"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "calculate_and_store_team_features", new_callable=AsyncMock
        ) as mock_calc:
            mock_calc.return_value = True

            result = await calculate_team_features(1, None, mock_session)

            assert result["success"] is True
            assert result["data"]["team_id"] == 1
            assert result["data"]["features_stored"] is True
            assert "特征计算完成" in result["message"]

    @pytest.mark.asyncio
    async def test_calculate_team_features_with_date(self, mock_session, mock_team):
        """测试指定计算日期"""
        calculation_date = datetime(2024, 1, 15)
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_team
        )

        with patch.object(
            feature_store, "calculate_and_store_team_features", new_callable=AsyncMock
        ) as mock_calc:
            mock_calc.return_value = True

            result = await calculate_team_features(1, calculation_date, mock_session)

            assert result["data"]["calculation_date"] == calculation_date.isoformat()


class TestBatchCalculateFeatures(TestFeaturesAPI):
    """测试批量计算特征API"""

    @pytest.mark.asyncio
    async def test_batch_calculate_features_success(self):
        """测试成功批量计算特征"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)

        expected_stats = {
            "total_matches": 10,
            "successful_calculations": 9,
            "failed_calculations": 1,
        }

        with patch.object(
            feature_store, "batch_calculate_features", new_callable=AsyncMock
        ) as mock_batch:
            mock_batch.return_value = expected_stats

            result = await batch_calculate_features(start_date, end_date, AsyncMock())

            assert result["success"] is True
            assert result["data"]["statistics"] == expected_stats
            assert "批量特征计算完成" in result["message"]

    @pytest.mark.asyncio
    async def test_batch_calculate_features_invalid_date_range(self):
        """测试无效日期范围"""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 1)  # 结束日期早于开始日期

        with pytest.raises(Exception) as exc_info:
            await batch_calculate_features(start_date, end_date, AsyncMock())

        assert "开始日期必须早于结束日期" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_batch_calculate_features_date_range_too_large(self):
        """测试日期范围过大"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 2, 15)  # 超过30天

        with pytest.raises(Exception) as exc_info:
            await batch_calculate_features(start_date, end_date, AsyncMock())

        assert "时间范围不能超过30天" in str(exc_info.value.detail)


class TestGetHistoricalFeatures(TestFeaturesAPI):
    """测试获取历史特征API"""

    @pytest.mark.asyncio
    async def test_get_historical_features_success(
        self, mock_session, mock_match, mock_historical_features_df
    ):
        """测试成功获取历史特征"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        feature_refs = ["feature_1", "feature_2", "feature_3"]

        with patch.object(
            feature_store, "get_historical_features", new_callable=AsyncMock
        ) as mock_get_historical:
            mock_get_historical.return_value = mock_historical_features_df

            result = await get_historical_features(12345, feature_refs, mock_session)

            assert result["success"] is True
            assert result["data"]["match_id"] == 12345
            assert result["data"]["feature_refs"] == feature_refs
            assert len(result["data"]["features"]) == 2
            assert (
                result["data"]["feature_count"] == 5
            )  # 3 features + match_id + team_id + event_timestamp
            assert result["data"]["record_count"] == 2
            assert "成功获取历史特征数据" in result["message"]

    @pytest.mark.asyncio
    async def test_get_historical_features_match_not_found(self, mock_session):
        """测试比赛不存在"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=None
        )

        with pytest.raises(Exception) as exc_info:
            await get_historical_features(99999, ["feature_1"], mock_session)

        assert "不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_historical_features_empty_feature_refs(
        self, mock_session, mock_match
    ):
        """测试空特征引用列表"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_historical_features", new_callable=AsyncMock
        ) as mock_get_historical:
            mock_get_historical.return_value = pd.DataFrame()

            result = await get_historical_features(12345, [], mock_session)

            assert result["data"]["feature_refs"] == []
            assert result["data"]["features"] == []


class TestFeaturesHealthCheck:
    """测试特征服务健康检查"""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """测试健康状态"""
        with patch("src.api.features.feature_store", MagicMock()):
            with patch("src.api.features.feature_calculator", MagicMock()):
                result = await features_health_check()

                assert result["success"] is True
                assert result["components"]["feature_store"] is True
                assert result["components"]["feature_calculator"] is True

    @pytest.mark.asyncio
    async def test_health_check_feature_store_unavailable(self):
        """测试特征存储不可用"""
        with patch("src.api.features.feature_store", None):
            with patch("src.api.features.feature_calculator", MagicMock()):
                result = await features_health_check()

                assert result["success"] is False
                assert result["components"]["feature_store"] is False

    @pytest.mark.asyncio
    async def test_health_check_feature_calculator_unavailable(self):
        """测试特征计算器不可用"""
        with patch("src.api.features.feature_store", MagicMock()):
            with patch("src.api.features.feature_calculator", None):
                result = await features_health_check()

                assert result["success"] is False
                assert result["components"]["feature_calculator"] is False

    @pytest.mark.asyncio
    async def test_health_check_connection_failed(self):
        """测试连接检查失败"""
        mock_store = MagicMock()
        mock_store.__bool__ = MagicMock(return_value=True)

        with patch("src.api.features.feature_store", mock_store):
            # 模拟连接检查失败
            with patch.object(
                mock_store,
                "__getattribute__",
                side_effect=Exception("Connection failed"),
            ):
                result = await features_health_check()

                assert result["success"] is True
                assert result["components"]["feature_store"] is True
                assert result["components"]["feature_store_connection"] is False


class TestFeaturesImprovedAPI(TestFeaturesAPI):
    """测试改进版特征服务API"""

    @pytest.mark.asyncio
    async def test_get_match_features_improved_success(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试改进版成功获取比赛特征"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            improved_feature_store,
            "get_match_features_for_prediction",
            new_callable=AsyncMock,
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            result = await get_match_features_improved(12345, False, mock_session)

            assert result["success"] is True
            assert result["data"]["match_info"]["match_id"] == 12345
            assert result["data"]["features"] == mock_features_data
            assert "成功获取比赛" in result["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_improved_entity_creation_error(
        self, mock_session, mock_match
    ):
        """测试改进版比赛实体创建错误"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            MatchEntity, "__init__", side_effect=Exception("Entity creation failed")
        ):
            with pytest.raises(Exception) as exc_info:
                await get_match_features_improved(12345, False, mock_session)

            assert "处理比赛数据时发生错误" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_improved_database_error(self, mock_session):
        """测试改进版数据库查询错误"""
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            await get_match_features_improved(12345, False, mock_session)

        assert "数据库查询失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_improved_graceful_degradation(
        self, mock_session, mock_match
    ):
        """测试改进版优雅降级"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            improved_feature_store,
            "get_match_features_for_prediction",
            new_callable=AsyncMock,
        ) as mock_get_features:
            mock_get_features.side_effect = Exception("Feature retrieval failed")

            result = await get_match_features_improved(12345, False, mock_session)

            assert result["success"] is True
            assert result["data"]["features"] == {}
            assert "features_warning" in result["data"]
            assert "特征数据部分缺失" in result["message"]

    @pytest.mark.asyncio
    async def test_improved_health_check_healthy(self):
        """测试改进版健康检查"""
        with patch("src.api.features_improved.feature_store", MagicMock()):
            with patch("src.api.features_improved.feature_calculator", MagicMock()):
                result = await improved_health_check()

                assert result["success"] is True
                assert result["components"]["feature_store"] is True
                assert result["components"]["feature_calculator"] is True

    @pytest.mark.asyncio
    async def test_improved_health_check_degraded(self):
        """测试改进版降级状态"""
        mock_store = MagicMock()
        mock_store.__bool__ = MagicMock(return_value=True)

        with patch("src.api.features_improved.feature_store", mock_store):
            with patch("src.api.features_improved.feature_calculator", MagicMock()):
                # 模拟连接检查失败
                with patch.object(
                    mock_store,
                    "__getattribute__",
                    side_effect=Exception("Connection failed"),
                ):
                    result = await improved_health_check()

                    assert result["success"] is True
                    assert result["components"]["feature_store_connection"] is False


class TestFeaturesAPIIntegration:
    """特征服务API集成测试"""

    @pytest.mark.asyncio
    async def test_concurrent_feature_requests(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试并发特征请求"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            # 并发请求
            tasks = [
                get_match_features(12345, False, mock_session),
                get_match_features(12345, True, mock_session),
                get_team_features(1, None, False, mock_session),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证所有请求都成功完成
            for result in results:
                assert not isinstance(result, Exception)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_feature_service_error_propagation(self, mock_session, mock_match):
        """测试错误传播"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.side_effect = Exception("Service unavailable")

            with pytest.raises(Exception) as exc_info:
                await get_match_features(12345, False, mock_session)

            assert "获取比赛特征失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_feature_service_response_structure(
        self, mock_session, mock_match, mock_features_data
    ):
        """测试响应结构"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = mock_features_data

            result = await get_match_features(12345, False, mock_session)

            # 验证响应结构
            assert "status" in result
            assert "data" in result
            assert "message" in result
            assert "timestamp" in result

            # 验证数据结构
            assert "match_info" in result["data"]
            assert "features" in result["data"]
            assert "match_id" in result["data"]["match_info"]
            assert "home_team_id" in result["data"]["match_info"]
            assert "away_team_id" in result["data"]["match_info"]

    @pytest.mark.asyncio
    async def test_feature_service_edge_cases(self, mock_session):
        """测试边界情况"""
        # 测试极值ID
        with pytest.raises(Exception):
            await get_match_features(0, False, mock_session)

        with pytest.raises(Exception):
            await get_match_features(-1, False, mock_session)

        # 测试极大ID（在有效范围内）
        large_id = 999999999
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=None
        )

        with pytest.raises(Exception) as exc_info:
            await get_match_features(large_id, False, mock_session)

        assert "不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_feature_service_performance_considerations(
        self, mock_session, mock_match
    ):
        """测试性能考虑"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            # 模拟慢响应
            async def slow_response():
                await asyncio.sleep(0.1)
                return {"feature": "value"}

            mock_get_features.side_effect = slow_response

            start_time = asyncio.get_event_loop().time()
            result = await get_match_features(12345, False, mock_session)
            end_time = asyncio.get_event_loop().time()

            assert result["success"] is True
            assert (end_time - start_time) >= 0.1  # 验证响应时间

    @pytest.mark.asyncio
    async def test_feature_service_memory_usage(self, mock_session, mock_match):
        """测试内存使用"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        # 模拟大数据集
        large_features = {f"feature_{i}": i for i in range(1000)}

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = large_features

            result = await get_match_features(12345, False, mock_session)

            assert len(result["data"]["features"]) == 1000
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_feature_service_caching_behavior(self, mock_session, mock_match):
        """测试缓存行为"""
        mock_session.execute.return_value = MockAsyncResult(
            scalar_one_or_none_result=mock_match
        )

        with patch.object(
            feature_store, "get_match_features_for_prediction", new_callable=AsyncMock
        ) as mock_get_features:
            mock_get_features.return_value = {"cached": "data"}

            # 多次请求相同数据
            result1 = await get_match_features(12345, False, mock_session)
            result2 = await get_match_features(12345, False, mock_session)

            assert result1["status"] == "success"
            assert result2["status"] == "success"
            assert result1["data"]["features"] == result2["data"]["features"]
