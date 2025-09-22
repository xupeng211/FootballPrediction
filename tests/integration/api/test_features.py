"""
测试API特征提取模块

覆盖src / api / features.py的主要功能：
- 特征提取API端点
- 特征验证逻辑
- 错误处理机制
- 参数验证

目标：将覆盖率从19%提升到85%+
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.integration


class TestFeatureExtractionAPI:
    """特征提取API测试类"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_match_data(self):
        """样本比赛数据"""
        return {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "match_date": datetime.now() + timedelta(days=1),
            "league_id": 1,
        }

    @pytest.fixture
    def sample_features_data(self):
        """样本特征数据"""
        return {
            "team_form": {
                "home_team": {
                    "wins": 3,
                    "draws": 1,
                    "losses": 1,
                    "goals_for": 8,
                    "goals_against": 4,
                },
                "away_team": {
                    "wins": 2,
                    "draws": 2,
                    "losses": 1,
                    "goals_for": 6,
                    "goals_against": 5,
                },
            },
            "head_to_head": {
                "total_matches": 10,
                "home_wins": 4,
                "away_wins": 3,
                "draws": 3,
            },
            "statistical_features": {
                "home_team_strength": 0.75,
                "away_team_strength": 0.65,
                "form_diff": 0.1,
                "market_confidence": 0.8,
            },
        }

    @pytest.mark.asyncio
    @patch(
        "src.api.features.feature_store.get_match_features_for_prediction",
        new_callable=AsyncMock,
    )
    async def test_get_match_features_success(
        self, mock_get_features, mock_session, sample_match_data, sample_features_data
    ):
        """测试成功获取比赛特征"""
        # 模拟数据库查询返回比赛数据
        mock_match = Mock()
        mock_match.id = sample_match_data["match_id"]
        mock_match.home_team_id = sample_match_data["home_team_id"]
        mock_match.away_team_id = sample_match_data["away_team_id"]
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        # 配置异步mock的返回值
        mock_get_features.return_value = sample_features_data

        from src.api.features import get_match_features

        result = await get_match_features(
            match_id=sample_match_data["match_id"], session=mock_session
        )

        # 验证APIResponse结构
        assert result["success"] is True
        assert "data" in result

        # 验证数据结构
        data = result["data"]
        assert data["match_info"]["match_id"] == sample_match_data["match_id"]
        assert "features" in data

        # 验证特征数据结构（基于sample_features_data的实际结构）
        features = data["features"]
        assert "team_form" in features
        assert features["team_form"]["home_team"]["wins"] == 3
        assert features["statistical_features"]["home_team_strength"] == 0.75

    @pytest.mark.asyncio
    async def test_get_match_features_not_found(self, mock_session):
        """测试比赛不存在的情况"""
        # 模拟比赛不存在
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        from src.api.features import get_match_features

        with pytest.raises(HTTPException) as exc_info:
            await get_match_features(match_id=99999, session=mock_session)

        assert exc_info.value.status_code == 404
        assert "比赛" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_features_invalid_id(self, mock_session):
        """测试无效的比赛ID"""
        from src.api.features import get_match_features

        # 测试负数ID
        with pytest.raises(HTTPException) as exc_info:
            await get_match_features(match_id=-1, session=mock_session)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("src.api.features.feature_store.get_match_features_for_prediction")
    async def test_get_match_features_service_error(
        self, mock_get_features, mock_session, sample_match_data
    ):
        """测试当特征服务异常时，API应返回500错误"""
        # 模拟数据库成功返回比赛信息
        mock_match = Mock()
        mock_match.id = sample_match_data["match_id"]
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        # 模拟特征存储服务在被调用时抛出异常
        mock_get_features.side_effect = RuntimeError("Feature store is down")

        # 验证是否捕获了HTTPException 500
        with pytest.raises(HTTPException) as exc_info:
            from src.api.features import get_match_features

            await get_match_features(
                match_id=sample_match_data["match_id"], session=mock_session
            )

        assert exc_info.value.status_code == 500
        assert "获取特征数据失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_batch_calculate_features_success(self, mock_session):
        """测试批量特征计算成功"""
        from datetime import datetime, timedelta

        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)

        # 模拟批量比赛数据
        mock_matches = []
        for i in range(3):
            mock_match = Mock()
            mock_match.id = i + 1
            mock_match.home_team_id = i + 1
            mock_match.away_team_id = i + 11
            mock_matches.append(mock_match)

        mock_result = Mock()
        mock_result.all.return_value = mock_matches
        mock_session.execute.return_value = mock_result

        # 模拟特征计算
        with patch("src.api.features.feature_calculator") as mock_feature_calculator:
            mock_feature_calculator.calculate_match_features.return_value = {
                "team_form": {"home": 0.8, "away": 0.6}
            }

            from src.api.features import batch_calculate_features

            result = await batch_calculate_features(
                start_date=start_date, end_date=end_date, session=mock_session
            )

            # 验证结果
            assert isinstance(result, dict)
            # 验证基本结构，具体字段根据实际API调整

    @pytest.mark.asyncio
    async def test_batch_extract_features_empty_list(self, mock_session):
        """测试空的比赛ID列表"""
        from datetime import datetime, timedelta

        from src.api.features import batch_calculate_features

        # 测试空的日期范围（开始日期晚于结束日期）
        start_date = datetime.now()
        end_date = start_date - timedelta(days=1)

        with pytest.raises(HTTPException) as exc_info:
            await batch_calculate_features(
                start_date=start_date, end_date=end_date, session=mock_session
            )

        assert exc_info.value.status_code == 400
        assert "开始日期必须早于结束日期" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_batch_calculate_features_date_range_too_large(self, mock_session):
        """测试当日期范围超过30天时，API应返回400错误"""
        from datetime import datetime, timedelta

        from src.api.features import batch_calculate_features

        start_date = datetime.now()
        end_date = start_date + timedelta(days=31)  # 超过30天限制

        with pytest.raises(HTTPException) as exc_info:
            await batch_calculate_features(
                start_date=start_date, end_date=end_date, session=mock_session
            )

        assert exc_info.value.status_code == 400
        assert "时间范围不能超过30天" in str(exc_info.value.detail)


@pytest.mark.integration
class TestFeatureServiceIntegration:
    """特征服务集成测试"""

    @pytest.mark.asyncio
    async def test_feature_extraction_with_real_data(self):
        """使用真实数据测试特征提取（需要测试数据库）"""
        # 这个测试需要真实的数据库连接和测试数据
        # 在CI / CD环境中跳过，或者使用测试数据库
        pytest.skip("需要真实数据库环境")

    @pytest.mark.asyncio
    async def test_feature_caching_behavior(self):
        """测试特征缓存行为"""
        # 测试特征数据的缓存机制
        pytest.skip("缓存测试需要Redis环境")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--cov=src.api.features"])
