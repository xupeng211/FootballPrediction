"""
Phase 3：预测API接口综合测试
目标：全面提升predictions.py模块覆盖率到20%+
重点：测试所有预测API端点、缓存机制、批量预测和验证功能
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


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


from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.predictions import (
    batch_predict_matches,
    get_match_prediction,
    get_match_prediction_history,
    get_recent_predictions,
    predict_match,
    verify_prediction,
)


class TestPredictionsAPIGetMatchPrediction:
    """预测API获取比赛预测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_get_match_prediction_success_cached(self):
        """测试成功获取缓存的预测结果"""
        # Mock match
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now() + timedelta(days=1)
        mock_match.match_status = "scheduled"
        mock_match.season = "2024-25"

        # Mock prediction
        mock_prediction = Mock()
        mock_prediction.id = 100
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = "football_baseline_model"
        mock_prediction.home_win_probability = 0.45
        mock_prediction.draw_probability = 0.30
        mock_prediction.away_win_probability = 0.25
        mock_prediction.predicted_result = "home"
        mock_prediction.confidence_score = 0.45
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = None
        mock_prediction.actual_result = None

        async def mock_execute(query):
            result = AsyncMock()
            if "Match" in str(query):
                result.scalar_one_or_none.return_value = mock_match
            else:
                result.scalar_one_or_none.return_value = mock_prediction
            return result

        self.mock_session.execute = mock_execute

        result = await get_match_prediction(
            match_id=1, force_predict=False, session=self.mock_session
        )

        assert result["success"] is True
        assert result["data"]["match_id"] == 1
        assert "match_info" in result["data"]
        assert "prediction" in result["data"]
        assert result["data"]["source"] == "cached"
        assert result["data"]["prediction"]["model_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_match_prediction_match_not_found(self):
        """测试比赛不存在"""

        async def mock_execute(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = None
            return result

        self.mock_session.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(
                match_id=999, force_predict=False, session=self.mock_session
            )

        assert exc_info.value.status_code == 404
        assert "比赛 999 不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_match_prediction_finished_match(self):
        """测试已结束比赛的预测"""
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now() - timedelta(days=1)
        mock_match.match_status = "finished"
        mock_match.season = "2024-25"

        async def mock_execute(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = mock_match
            return result

        self.mock_session.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(
                match_id=1, force_predict=True, session=self.mock_session
            )

        assert exc_info.value.status_code == 400
        assert "比赛 1 已结束，无法生成预测" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_match_prediction_database_error(self):
        """测试数据库错误"""
        self.mock_session.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(
                match_id=1, force_predict=False, session=self.mock_session
            )

        assert exc_info.value.status_code == 500
        assert "获取预测结果失败" in exc_info.value.detail


class TestPredictionsAPIPredictMatch:
    """预测API实时预测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_predict_match_success(self):
        """测试成功预测比赛"""
        mock_match = Mock()
        mock_match.id = 1

        async def mock_execute(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = mock_match
            return result

        self.mock_session.execute = mock_execute

        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_prediction_result = Mock()
            mock_prediction_result.to_dict.return_value = {
                "model_version": "1.0",
                "home_win_probability": 0.45,
                "draw_probability": 0.30,
                "away_win_probability": 0.25,
                "predicted_result": "home",
                "confidence_score": 0.45,
            }

            mock_service.predict_match = AsyncMock(return_value=mock_prediction_result)

            result = await predict_match(match_id=1, session=self.mock_session)

            assert result["success"] is True
            assert result["data"]["model_version"] == "1.0"
            assert "比赛 1 预测完成" in result["message"]

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self):
        """测试比赛不存在"""

        async def mock_execute(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = None
            return result

        self.mock_session.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await predict_match(match_id=999, session=self.mock_session)

        assert exc_info.value.status_code == 404
        assert "比赛 999 不存在" in exc_info.value.detail


class TestPredictionsAPIBatchPredict:
    """预测API批量预测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(self):
        """测试成功批量预测"""
        match_ids = [1, 2, 3]

        async def mock_execute(query):
            result = AsyncMock()
            # Mock valid match IDs
            mock_matches = [Mock(id=1), Mock(id=2), Mock(id=3)]
            result.all.return_value = mock_matches
            return result

        self.mock_session.execute = mock_execute

        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_prediction_result = Mock()
            mock_prediction_result.to_dict.return_value = {
                "model_version": "1.0",
                "home_win_probability": 0.45,
                "draw_probability": 0.30,
                "away_win_probability": 0.25,
                "predicted_result": "home",
                "confidence_score": 0.45,
            }

            mock_service.batch_predict_matches = AsyncMock(
                return_value=[
                    mock_prediction_result,
                    mock_prediction_result,
                    mock_prediction_result,
                ]
            )

            result = await batch_predict_matches(
                match_ids=match_ids, session=self.mock_session
            )

            assert result["success"] is True
            assert result["data"]["total_requested"] == 3
            assert result["data"]["valid_matches"] == 3
            assert result["data"]["successful_predictions"] == 3
            assert len(result["data"]["predictions"]) == 3
            assert result["data"]["invalid_match_ids"] == []

    @pytest.mark.asyncio
    async def test_batch_predict_matches_too_many(self):
        """测试批量预测超过限制"""
        match_ids = list(range(51))  # 51 matches

        with pytest.raises(HTTPException) as exc_info:
            await batch_predict_matches(match_ids=match_ids, session=self.mock_session)

        assert exc_info.value.status_code == 400
        assert "批量预测最多支持50场比赛" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_batch_predict_matches_database_error(self):
        """测试数据库错误"""
        self.mock_session.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await batch_predict_matches(match_ids=[1, 2, 3], session=self.mock_session)

        assert exc_info.value.status_code == 500
        assert "批量预测失败" in exc_info.value.detail


class TestPredictionsAPIHistory:
    """预测API历史记录测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_success(self):
        """测试成功获取预测历史"""
        mock_match = Mock()
        mock_match.id = 1

        mock_prediction = Mock()
        mock_prediction.id = 100
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = "football_baseline_model"
        mock_prediction.home_win_probability = 0.45
        mock_prediction.draw_probability = 0.30
        mock_prediction.away_win_probability = 0.25
        mock_prediction.predicted_result = "home"
        mock_prediction.confidence_score = 0.45
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = None
        mock_prediction.actual_result = None
        mock_prediction.verified_at = None

        async def mock_execute(query):
            result = AsyncMock()
            if "Match" in str(query):
                result.scalar_one_or_none.return_value = mock_match
            else:
                result.scalars.return_value.all.return_value = [mock_prediction]
            return result

        self.mock_session.execute = mock_execute

        result = await get_match_prediction_history(
            match_id=1, limit=10, session=self.mock_session
        )

        assert result["success"] is True
        assert result["data"]["match_id"] == 1
        assert result["data"]["total_predictions"] == 1
        assert len(result["data"]["predictions"]) == 1

        prediction = result["data"]["predictions"][0]
        assert prediction["model_version"] == "1.0"
        assert prediction["predicted_result"] == "home"

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_match_not_found(self):
        """测试比赛不存在"""

        async def mock_execute(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = None
            return result

        self.mock_session.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction_history(
                match_id=999, limit=10, session=self.mock_session
            )

        assert exc_info.value.status_code == 404
        assert "比赛 999 不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_database_error(self):
        """测试数据库错误"""
        self.mock_session.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction_history(
                match_id=1, limit=10, session=self.mock_session
            )

        assert exc_info.value.status_code == 500
        assert "获取历史预测失败" in exc_info.value.detail


class TestPredictionsAPIRecent:
    """预测API最近预测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_get_recent_predictions_success(self):
        """测试成功获取最近预测"""
        mock_prediction = Mock()
        mock_prediction.id = 100
        mock_prediction.match_id = 1
        mock_prediction.model_version = "1.0"
        mock_prediction.model_name = "football_baseline_model"
        mock_prediction.predicted_result = "home"
        mock_prediction.confidence_score = 0.45
        mock_prediction.created_at = datetime.now()
        mock_prediction.is_correct = None
        mock_prediction.home_team_id = 10
        mock_prediction.away_team_id = 20
        mock_prediction.match_time = datetime.now() + timedelta(days=1)
        mock_prediction.match_status = "scheduled"

        async def mock_execute(query):
            result = AsyncMock()
            result.fetchall.return_value = [mock_prediction]
            return result

        self.mock_session.execute = mock_execute

        result = await get_recent_predictions(
            hours=24, limit=50, session=self.mock_session
        )

        assert result["success"] is True
        assert result["data"]["time_range_hours"] == 24
        assert result["data"]["total_predictions"] == 1
        assert len(result["data"]["predictions"]) == 1

        prediction = result["data"]["predictions"][0]
        assert prediction["model_version"] == "1.0"
        assert prediction["predicted_result"] == "home"
        assert "match_info" in prediction

    @pytest.mark.asyncio
    async def test_get_recent_predictions_database_error(self):
        """测试数据库错误"""
        self.mock_session.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_recent_predictions(hours=24, limit=50, session=self.mock_session)

        assert exc_info.value.status_code == 500
        assert "获取最近预测失败" in exc_info.value.detail


class TestPredictionsAPIVerify:
    """预测API验证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self):
        """测试成功验证预测"""
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=True)

            result = await verify_prediction(match_id=1, session=self.mock_session)

            assert result["success"] is True
            assert result["data"]["match_id"] == 1
            assert result["data"]["verified"] is True
            assert "预测结果验证完成" in result["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_failure(self):
        """测试验证失败"""
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=False)

            result = await verify_prediction(match_id=1, session=self.mock_session)

            assert result["success"] is False
            assert result["data"]["match_id"] == 1
            assert result["data"]["verified"] is False
            assert "预测结果验证失败" in result["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_service_error(self):
        """测试验证服务错误"""
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(
                side_effect=Exception("Verification failed")
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_prediction(match_id=1, session=self.mock_session)

            assert exc_info.value.status_code == 500
            assert "验证预测结果失败" in exc_info.value.detail


class TestPredictionsAPIIntegration:
    """预测API集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_response_structure_consistency(self):
        """测试响应结构一致性"""
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now() + timedelta(days=1)
        mock_match.match_status = "scheduled"
        mock_match.season = "2024-25"

        async def mock_execute(query):
            result = AsyncMock()
            if "Match" in str(query):
                result.scalar_one_or_none.return_value = mock_match
            else:
                result.scalar_one_or_none.return_value = None
            return result

        self.mock_session.execute = mock_execute

        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_prediction_result = Mock()
            mock_prediction_result.to_dict.return_value = {
                "model_version": "1.0",
                "home_win_probability": 0.45,
                "draw_probability": 0.30,
                "away_win_probability": 0.25,
                "predicted_result": "home",
                "confidence_score": 0.45,
            }

            mock_service.predict_match = AsyncMock(return_value=mock_prediction_result)

            result = await get_match_prediction(
                match_id=1, force_predict=True, session=self.mock_session
            )

            # Check response structure
            assert "success" in result
            assert "data" in result
            assert "message" in result
            assert "match_id" in result["data"]
            assert "match_info" in result["data"]
            assert "prediction" in result["data"]

    @pytest.mark.asyncio
    async def test_error_response_consistency(self):
        """测试错误响应一致性"""

        async def mock_execute(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = None
            return result

        self.mock_session.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(
                match_id=999, force_predict=False, session=self.mock_session
            )

        # Check error response format
        assert isinstance(exc_info.value.detail, str)
        assert "比赛 999 不存在" in exc_info.value.detail
