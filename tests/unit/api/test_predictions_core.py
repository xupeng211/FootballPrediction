"""
API预测模块的单元测试

测试覆盖：
- 预测生成功能
- 批量预测处理
- 错误处理和异常情况
- API响应格式验证
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.predictions import (
    batch_predict_matches,
    get_match_prediction,
    get_match_prediction_history,
    router,
)
from src.models.prediction_service import PredictionResult


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock(spec=AsyncSession)
    return session


class TestPredictionsAPI:
    """测试预测API的所有功能"""

    @pytest.fixture
    def mock_match_data(self):
        """模拟比赛数据"""
        return {
            "id": 1,
            "home_team_id": 10,
            "away_team_id": 20,
            "match_date": datetime.now() + timedelta(days=1),
            "league_id": 1,
            "status": "scheduled",
        }

    @pytest.fixture
    def mock_prediction_data(self):
        """模拟预测数据"""
        return PredictionResult(
            match_id=1,
            model_version="v3.0",
            model_name="test_model",
            home_win_probability=0.55,
            draw_probability=0.25,
            away_win_probability=0.20,
            predicted_result="home",
            confidence_score=0.83,
            features_used=["team_form", "head_to_head", "home_advantage"],
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_get_match_prediction_success(
        self, mock_session, mock_match_data, mock_prediction_data
    ):
        """测试成功获取比赛预测"""
        # Mock数据库查询
        mock_match = MagicMock()
        mock_match.id = mock_match_data["id"]
        mock_match.home_team_id = mock_match_data["home_team_id"]
        mock_match.away_team_id = mock_match_data["away_team_id"]
        mock_match.match_date = mock_match_data["match_date"]
        mock_match.match_status = mock_match_data["status"]

        # 正确设置AsyncMock的返回值
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.predict_match = AsyncMock(return_value=mock_prediction_data)

            # 执行测试
            result = await get_match_prediction(match_id=1, session=mock_session)

            # 验证结果
            assert "success" in result
            assert result["success"] is True
            assert "data" in result
            assert result["data"]["match_id"] == 1
            assert "home_win_probability" in result["data"]["prediction"]
            assert "confidence_score" in result["data"]["prediction"]
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_match_prediction_match_not_found(self, mock_session):
        """测试比赛不存在的情况"""
        # 正确设置AsyncMock的返回值 - None表示找不到比赛
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(match_id=999, session=mock_session)

        assert exc_info.value.status_code == 404
        assert "比赛 999 不存在" == str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_prediction_finished_match(
        self, mock_session, mock_match_data
    ):
        """测试已结束比赛的预测请求"""
        # Mock已结束的比赛
        mock_match = MagicMock()
        mock_match.id = mock_match_data["id"]
        mock_match.match_status = "finished"
        mock_match.match_date = datetime.now() - timedelta(days=1)

        # 正确设置AsyncMock的返回值
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute = AsyncMock(return_value=mock_result)

        # 使用patch模拟prediction_service
        with patch("src.api.predictions.prediction_service") as mock_prediction_service:
            # 执行测试并验证异常
            with pytest.raises(HTTPException) as exc_info:
                await get_match_prediction(match_id=1, session=mock_session)

            # 确保prediction_service未被调用
            mock_prediction_service.predict_match.assert_not_called()

        assert exc_info.value.status_code == 400
        assert "已结束，无法生成预测" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_match_prediction_service_error(
        self, mock_session, mock_match_data
    ):
        """测试预测服务异常"""
        # Mock正常比赛数据
        mock_match = MagicMock()
        mock_match.id = mock_match_data["id"]
        mock_match.match_status = "scheduled"
        mock_match.match_date = datetime.now() + timedelta(days=1)

        # 正确设置AsyncMock的返回值
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            # Mock预测服务失败
            mock_service.predict_match.side_effect = Exception(
                "Prediction service failed"
            )

            # 执行测试并验证异常
            with pytest.raises(HTTPException) as exc_info:
                await get_match_prediction(match_id=1, session=mock_session)

            assert exc_info.value.status_code == 500
            assert "Prediction service failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(
        self, mock_session, mock_prediction_data
    ):
        """测试批量预测成功"""
        match_ids = [1, 2, 3]

        # Mock多个比赛数据
        mock_matches = []
        for match_id in match_ids:
            mock_match = MagicMock()
            mock_match.id = match_id
            mock_match.match_status = "scheduled"
            mock_match.match_date = datetime.now() + timedelta(days=1)
            mock_matches.append(mock_match)

        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_matches
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            # Mock批量预测
            mock_predictions = []
            for match_id in match_ids:
                prediction_data = mock_prediction_data.to_dict()
                prediction_data["match_id"] = match_id
                # 创建一个模拟对象，它有一个 to_dict 方法
                mock_result = MagicMock()
                mock_result.to_dict.return_value = prediction_data
                mock_predictions.append(mock_result)

            mock_service.batch_predict_matches = AsyncMock(
                return_value=mock_predictions
            )

            # 执行测试
            result = await batch_predict_matches(
                match_ids=match_ids, session=mock_session
            )

            # 验证结果
            assert "success" in result
            assert result["success"] is True
            assert "data" in result
            assert "predictions" in result["data"]
            assert len(result["data"]["predictions"]) == len(match_ids)
            assert all(
                pred["match_id"] in match_ids for pred in result["data"]["predictions"]
            )

    @pytest.mark.asyncio
    async def test_batch_predict_matches_partial_failure(self, mock_session):
        """测试批量预测部分失败"""
        match_ids = [1, 2, 3]

        # Mock只返回部分比赛数据
        mock_matches = []
        for match_id in [1, 2]:  # 缺少match_id=3
            mock_match = MagicMock()
            mock_match.id = match_id
            mock_match.match_status = "scheduled"
            mock_match.match_date = datetime.now() + timedelta(days=1)
            mock_matches.append(mock_match)

        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_matches
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            prediction_result = PredictionResult(
                match_id=1,
                model_version="v1.0",
                model_name="test_model",
                home_win_probability=0.5,
                draw_probability=0.3,
                away_win_probability=0.2,
                predicted_result="home",
                confidence_score=0.75,
                created_at=datetime.now(),
            )
            mock_service.predict_match = AsyncMock(return_value=prediction_result)
            mock_service.batch_predict_matches = AsyncMock(return_value=[])

            # 执行测试
            result = await batch_predict_matches(
                match_ids=match_ids, session=mock_session
            )

            # 验证结果包含成功和失败信息
            assert "success" in result
            assert "data" in result
            assert "predictions" in result["data"]
            assert len(result["data"]["predictions"]) == 0  # 没有成功的预测
            assert "invalid_match_ids" in result["data"]
            assert len(result["data"]["invalid_match_ids"]) == 3  # 3个无效ID

    @pytest.mark.asyncio
    async def test_batch_predict_matches_empty_list(self, mock_session):
        """测试空列表批量预测"""
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.batch_predict_matches = AsyncMock(return_value=[])

            result = await batch_predict_matches(match_ids=[], session=mock_session)

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["predictions"] == []

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_success(self, mock_session):
        """测试获取预测历史成功"""
        match_id = 1

        # Mock历史预测数据 - 使用Mock对象而不是字典
        mock_prediction1 = MagicMock()
        mock_prediction1.id = 1
        mock_prediction1.match_id = match_id
        mock_prediction1.home_win_probability = 0.55
        mock_prediction1.created_at = datetime.now() - timedelta(hours=2)
        mock_prediction1.model_version = "v2.0"
        mock_prediction1.predicted_result = "home"
        mock_prediction1.confidence_score = 0.75

        mock_prediction2 = MagicMock()
        mock_prediction2.id = 2
        mock_prediction2.match_id = match_id
        mock_prediction2.home_win_probability = 0.53
        mock_prediction2.created_at = datetime.now() - timedelta(hours=1)
        mock_prediction2.model_version = "v3.0"
        mock_prediction2.predicted_result = "draw"
        mock_prediction2.confidence_score = 0.65

        mock_history = [mock_prediction1, mock_prediction2]

        # Mock数据库执行 - 正确设置AsyncMock返回值
        mock_history_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_history
        mock_history_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_history_result)

        # 执行测试
        result = await get_match_prediction_history(
            match_id=match_id, limit=10, session=mock_session
        )

        # 验证结果
        assert "success" in result
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["match_id"] == match_id
        assert result["data"]["total_predictions"] == len(mock_history)
        assert len(result["data"]["predictions"]) == len(mock_history)
        assert result["data"]["predictions"][0]["id"] == 1
        assert result["data"]["predictions"][1]["id"] == 2

    @pytest.mark.asyncio
    async def test_get_match_prediction_history_no_history(self, mock_session):
        """测试无预测历史的情况"""
        match_id = 999

        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await get_match_prediction_history(
            match_id=match_id, limit=10, session=mock_session
        )

        # 验证结果
        assert result["success"] is True
        assert result["data"]["match_id"] == match_id
        assert result["data"]["total_predictions"] == 0
        assert result["data"]["predictions"] == []

    # TODO: 实现 update_prediction_feedback 功能后再添加相关测试
    # 目前该函数尚未实现，暂时注释掉相关测试避免 linting 错误

    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_session):
        """测试数据库连接异常"""
        # 模拟数据库连接错误，使用中文错误消息保持一致
        mock_session.execute.side_effect = SQLAlchemyError("数据库连接失败")

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(match_id=1, session=mock_session)

        assert exc_info.value.status_code == 500
        assert "获取预测结果失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_concurrent_prediction_requests(
        self, mock_session, mock_match_data, mock_prediction_data
    ):
        """测试并发预测请求"""
        match_ids = [1, 2, 3, 4, 5]

        # Mock比赛数据
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.match_status = "scheduled"
        mock_match.match_date = datetime.now() + timedelta(days=1)

        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match  # 直接返回对象，不是协程
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.predict_match = AsyncMock(return_value=mock_prediction_data)

            # 创建并发任务
            tasks = []
            for match_id in match_ids:
                task = get_match_prediction(match_id=match_id, session=mock_session)
                tasks.append(task)

            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证所有请求都成功
            assert len(results) == len(match_ids)
            for result in results:
                assert not isinstance(result, Exception)
                assert result["success"] is True

    def test_router_configuration(self):
        """测试路由器配置"""
        assert router.prefix == "/predictions"
        assert "predictions" in router.tags

        # 验证主要路由存在 - 修正：使用实际的路由路径
        routes = [route.path for route in router.routes]
        expected_routes = [
            "/predictions/{match_id}",  # 修正：实际路径包含完整前缀
            "/predictions/{match_id}/predict",
            "/predictions/batch",
            "/predictions/history/{match_id}",
            "/predictions/recent",
            "/predictions/{match_id}/verify",
        ]
        for expected_route in expected_routes:
            assert expected_route in routes, f"路由 {expected_route} 不存在于 {routes}"

        # 验证路由数量
        assert len(routes) == len(expected_routes)

    @pytest.mark.asyncio
    async def test_prediction_caching_behavior(
        self, mock_session, mock_match_data, mock_prediction_data
    ):
        """测试预测缓存行为"""
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.match_status = "scheduled"
        mock_match.match_date = datetime.now() + timedelta(days=1)

        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.predict_match = AsyncMock(return_value=mock_prediction_data)

            # 第一次调用
            result1 = await get_match_prediction(match_id=1, session=mock_session)

            # 第二次调用
            result2 = await get_match_prediction(match_id=1, session=mock_session)

            # 验证结果一致性
            assert result1["success"] is True
            assert result2["success"] is True
            assert result1["data"]["match_id"] == result2["data"]["match_id"]

    @pytest.mark.asyncio
    async def test_prediction_confidence_validation(
        self, mock_session, mock_match_data
    ):
        """测试预测置信度验证"""
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.match_status = "scheduled"
        mock_match.match_date = datetime.now() + timedelta(days=1)

        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            # Mock低置信度预测
            low_confidence_prediction = PredictionResult(
                match_id=1,
                model_version="v1.0",
                model_name="test_model",
                home_win_probability=0.35,
                draw_probability=0.33,
                away_win_probability=0.32,
                predicted_result="draw",
                confidence_score=0.25,  # 低置信度
                created_at=datetime.now(),
            )
            mock_service.predict_match = AsyncMock(
                return_value=low_confidence_prediction
            )

            # 执行测试
            result = await get_match_prediction(match_id=1, session=mock_session)

            # 验证系统处理低置信度预测
            assert result["success"] is True
            assert "data" in result
            assert result["data"]["prediction"]["confidence_score"] == 0.25


class TestAPIResponseFormats:
    """测试API响应格式"""

    @pytest.mark.asyncio
    async def test_prediction_response_structure(self, mock_session):
        """测试预测响应结构"""
        # 创建完整的mock比赛对象
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.match_status = "scheduled"
        mock_match.match_time = datetime.now() + timedelta(days=1)
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.season = "2023-24"

        # 模拟数据库查询结果 - 正确配置AsyncMock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.api.predictions.prediction_service") as mock_service:
            # 创建mock预测结果对象
            mock_prediction_result = MagicMock()
            mock_prediction_result.to_dict.return_value = {
                "match_id": 1,
                "home_win_probability": 0.55,
                "draw_probability": 0.25,
                "away_win_probability": 0.20,
                "predicted_result": "home",
                "confidence_score": 0.85,
            }
            mock_service.predict_match = AsyncMock(return_value=mock_prediction_result)

            # 执行测试
            result = await get_match_prediction(match_id=1, session=mock_session)

            # 验证响应结构
            required_fields = ["success", "data", "timestamp"]
            for field in required_fields:
                assert field in result

            assert isinstance(result["success"], bool)
            assert isinstance(result["data"], dict)
            assert "match_id" in result["data"]

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)  # 添加5秒超时限制
    async def test_batch_prediction_response_structure(self, mock_session):
        """测试批量预测响应结构"""
        # 修复：模拟底层的服务调用以避免网络请求和超时
        with patch(
            "src.api.predictions.prediction_service.batch_predict_matches",
            new_callable=AsyncMock,
        ) as mock_batch_predict:
            # Mock返回预期的批量预测结果结构 - 修正：使用正确的字段
            mock_batch_predict.return_value = []  # 返回空的预测结果列表

            # 执行测试
            result = await batch_predict_matches(match_ids=[], session=mock_session)

            # 验证批量响应结构
            assert result["success"] is True
            assert "data" in result
            assert isinstance(result["data"], dict)
            assert "predictions" in result["data"]
            assert isinstance(result["data"]["predictions"], list)
            assert result["data"]["valid_matches"] == 0

    @pytest.mark.asyncio
    async def test_error_response_structure(self, mock_session):
        """测试错误响应结构"""
        # ✅ 修复：正确配置AsyncMock for session.execute
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试并捕获异常
        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(match_id=999, session=mock_session)

        # 验证错误响应结构
        assert exc_info.value.status_code == 404
        assert isinstance(exc_info.value.detail, str)
        assert len(exc_info.value.detail) > 0
