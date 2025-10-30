# TODO: Consider creating a fixture for 30 repeated Mock creations

# TODO: Consider creating a fixture for 30 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, patch

"""预测API单元测试"""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import status

from src.database.models import PredictedResult
from src.models.prediction_service import PredictionService


@pytest.mark.unit
class TestGetMatchPrediction:
    """获取比赛预测API测试"""

    @pytest.mark.asyncio
    async def test_get_match_prediction_cached_success(
        self, api_client_full, sample_match, sample_prediction
    ):
        """测试获取缓存的预测结果成功"""
        # 获取mock session
        mock_session = api_client_full.mock_session

        # 模拟数据库查询
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = sample_prediction

        mock_session.execute.side_effect = [
            mock_match_result,  # 第一次查询：match
            mock_prediction_result,  # 第二次查询:prediction
        ]

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/12345")

        # 验证响应
        assert response.status_code == status.HTTP_200_OK
        _data = response.json()
        assert _data["success"] is True
        assert _data["data"]["match_id"] == 12345
        assert _data["data"]["source"] == "cached"
        assert "prediction" in _data["data"]
        assert _data["data"]["prediction"]["id"] == 1
        assert _data["data"]["prediction"]["model_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_match_prediction_real_time_success(self, api_client_full, sample_match):
        """测试实时生成预测成功"""
        # 模拟数据库查询 - 没有缓存预测
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = None

        api_client_full.mock_session.execute.side_effect = [
            mock_match_result,  # 第一次查询：match
            mock_prediction_result,  # 第二次查询:prediction (None)
        ]

        # 模拟预测服务
        mock_prediction_data = MagicMock()
        mock_prediction_data.to_dict.return_value = {
            "id": 2,
            "model_version": "2.0",
            "model_name": "neural_network",
            "predicted_result": "home_win",
            "home_win_probability": 0.65,
            "draw_probability": 0.25,
            "away_win_probability": 0.10,
            "confidence_score": 0.85,
        }

        with patch.object(
            PredictionService, "predict_match", new_callable=AsyncMock
        ) as mock_predict:
            mock_predict.return_value = mock_prediction_data

            # 发送请求
            response = api_client_full.get("/api/v1/predictions/12345?force_predict=true")

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["success"] is True
            assert _data["data"]["source"] == "real_time"
            assert _data["data"]["prediction"]["model_version"] == "2.0"

    @pytest.mark.asyncio
    async def test_get_match_prediction_match_not_found(self, api_client_full):
        """测试比赛不存在"""
        # 设置mock - 比赛不存在
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        api_client_full.mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/99999")

        # 验证响应
        assert response.status_code == status.HTTP_404_NOT_FOUND
        _data = response.json()
        # Check if error message is in detail or message field
        error_msg = data.get("detail", data.get("message", ""))
        assert "比赛 99999 不存在" in error_msg

    @pytest.mark.asyncio
    async def test_get_match_prediction_finished_match(
        self, api_client_full, sample_match_finished
    ):
        """测试已结束的比赛不允许预测"""
        # 模拟数据库查询 - 比赛已结束
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match_finished
        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = None

        api_client_full.mock_session.execute.side_effect = [
            mock_match_result,  # 第一次查询：match
            mock_prediction_result,  # 第二次查询:prediction (None)
        ]

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/12346?force_predict=true")

        # 验证响应
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        _data = response.json()
        # Check if error message is in detail or message field
        error_msg = data.get("detail", data.get("message", ""))
        assert "已结束,无法生成预测" in error_msg

    @pytest.mark.asyncio
    async def test_get_match_prediction_server_error(self, api_client_full):
        """测试服务器内部错误"""
        # 模拟数据库异常
        api_client_full.mock_session.execute.side_effect = Exception("Database connection failed")

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/12345")

        # 验证响应
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        _data = response.json()
        # Check if error message is in detail or message field
        error_msg = data.get("detail", data.get("message", ""))
        assert "获取预测结果失败" in error_msg

    @pytest.mark.parametrize("match_id", [12345, 99999, 1])
    @pytest.mark.asyncio
    async def test_get_match_prediction_different_ids(
        self, api_client_full, sample_match, match_id
    ):
        """测试不同的比赛ID"""
        # 修改sample_match的ID
        sample_match.id = match_id

        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = None

        api_client_full.mock_session.execute.side_effect = [
            mock_match_result,
            mock_prediction_result,
        ]

        # 模拟预测服务
        mock_prediction_data = MagicMock()
        mock_prediction_data.to_dict.return_value = {"id": match_id}

        with patch.object(
            PredictionService, "predict_match", new_callable=AsyncMock
        ) as mock_predict:
            mock_predict.return_value = mock_prediction_data

            # 发送请求
            response = api_client_full.get(f"/api/v1/predictions/{match_id}?force_predict=true")

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["data"]["match_id"] == match_id


class TestPredictMatch:
    """实时预测比赛API测试"""

    @pytest.mark.asyncio
    async def test_predict_match_success(self, api_client_full, sample_match):
        """测试预测比赛成功"""
        # 模拟数据库查询
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        api_client_full.mock_session.execute.return_value = mock_match_result

        # 模拟预测服务
        mock_prediction_data = MagicMock()
        mock_prediction_data.to_dict.return_value = {
            "model_version": "1.0",
            "predicted_result": "home_win",
            "confidence_score": 0.75,
        }

        with patch.object(
            PredictionService, "predict_match", new_callable=AsyncMock
        ) as mock_predict:
            mock_predict.return_value = mock_prediction_data

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/predict")

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["success"] is True
            assert "比赛 12345 预测完成" in _data["message"]
            assert _data["data"]["model_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self, api_client_full):
        """测试预测不存在的比赛"""
        # 模拟数据库查询 - 没有找到比赛
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        api_client_full.mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.post("/api/v1/predictions/99999/predict")

        # 验证响应
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_predict_match_service_error(self, api_client_full, sample_match):
        """测试预测服务错误"""
        # 模拟数据库查询
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        api_client_full.mock_session.execute.return_value = mock_match_result

        # 模拟预测服务抛出异常
        with patch.object(
            PredictionService, "predict_match", new_callable=AsyncMock
        ) as mock_predict:
            mock_predict.side_effect = Exception("Prediction service failed")

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/predict")

            # 验证响应
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestBatchPredictMatches:
    """批量预测比赛API测试"""

    @pytest.mark.asyncio
    async def test_batch_predict_success(self, api_client_full):
        """测试批量预测成功"""
        match_ids = [1, 2, 3]

        # 模拟数据库查询 - 找到所有比赛
        mock_valid_matches = MagicMock()
        mock_valid_matches.__iter__ = lambda self: iter(
            [MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)]
        )

        api_client_full.mock_session.execute.return_value = mock_valid_matches

        # 模拟预测服务
        mock_results = []
        for match_id in match_ids:
            _result = MagicMock()
            result.to_dict.return_value = {
                "match_id": match_id,
                "predicted_result": "home_win",
            }
            mock_results.append(result)

        with patch.object(
            PredictionService, "batch_predict_matches", new_callable=AsyncMock
        ) as mock_batch_predict:
            mock_batch_predict.return_value = mock_results

            # 发送请求
            response = api_client_full.post(
                "/api/v1/predictions/batch",
                json=match_ids,
            )

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["success"] is True
            assert _data["data"]["total_requested"] == 3
            assert _data["data"]["valid_matches"] == 3
            assert _data["data"]["successful_predictions"] == 3
            assert len(_data["data"]["predictions"]) == 3

    @pytest.mark.asyncio
    async def test_batch_predict_too_many_matches(self, api_client_full):
        """测试批量预测比赛数量超过限制"""
        # 创建51个比赛ID（超过50的限制）
        match_ids = list(range(1, 52))

        # 发送请求
        response = api_client_full.post(
            "/api/v1/predictions/batch",
            json=match_ids,
        )

        # 验证响应
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        _data = response.json()
        # Check if error message is in detail, message or error field
        error_msg = data.get("detail", data.get("message", data.get("error", "")))
        assert "批量预测最多支持50场比赛" in error_msg

    @pytest.mark.asyncio
    async def test_batch_predict_partial_invalid(self, api_client_full):
        """测试批量预测包含无效ID"""
        match_ids = [1, 2, 999, 3]

        # 模拟数据库查询 - 只找到部分比赛
        mock_valid_matches = MagicMock()
        mock_valid_matches.__iter__ = lambda self: iter(
            [MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)]
        )

        api_client_full.mock_session.execute.return_value = mock_valid_matches

        # 模拟预测服务
        mock_results = []
        for match_id in [1, 2, 3]:
            _result = MagicMock()
            result.to_dict.return_value = {"match_id": match_id}
            mock_results.append(result)

        with patch.object(
            PredictionService, "batch_predict_matches", new_callable=AsyncMock
        ) as mock_batch_predict:
            mock_batch_predict.return_value = mock_results

            # 发送请求
            response = api_client_full.post(
                "/api/v1/predictions/batch",
                json=match_ids,
            )

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["data"]["total_requested"] == 4
            assert _data["data"]["valid_matches"] == 3
            assert 999 in _data["data"]["invalid_match_ids"]


class TestGetMatchPredictionHistory:
    """获取比赛历史预测API测试"""

    @pytest.mark.asyncio
    async def test_get_prediction_history_success(self, api_client_full, sample_match):
        """测试获取历史预测成功"""
        # 创建模拟的预测历史
        predictions = []
        for i in range(3):
            pred = MagicMock()
            pred.id = i + 1
            pred.model_version = f"1.{i}"
            pred.model_name = "test_model"
            pred.predicted_result = PredictedResult.HOME_WIN
            pred.home_win_probability = Decimal("0.5")
            pred.draw_probability = Decimal("0.3")
            pred.away_win_probability = Decimal("0.2")
            pred.confidence_score = Decimal("0.7")
            pred.created_at = datetime.now()
            pred.is_correct = None
            pred.actual_result = None
            pred.verified_at = None
            predictions.append(pred)

        # 模拟数据库查询
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        mock_history_result = MagicMock()
        mock_history_result.scalars.return_value.all.return_value = predictions

        api_client_full.mock_session.execute.side_effect = [
            mock_match_result,  # 第一次查询：match
            mock_history_result,  # 第二次查询:history
        ]

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/history/12345?limit=3")

        # 验证响应
        assert response.status_code == status.HTTP_200_OK
        _data = response.json()
        assert _data["success"] is True
        assert _data["data"]["match_id"] == 12345
        assert _data["data"]["total_predictions"] == 3
        assert len(_data["data"]["predictions"]) == 3
        assert _data["data"]["predictions"][0]["model_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_prediction_history_match_not_found(self, api_client_full):
        """测试获取不存在比赛的历史预测"""
        # 模拟数据库查询 - 没有找到比赛
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        api_client_full.mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/history/99999")

        # 验证响应
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("limit", [1, 10, 50, 100])
    @pytest.mark.asyncio
    async def test_get_prediction_history_different_limits(
        self, api_client_full, sample_match, limit
    ):
        """测试不同的限制数量"""
        # 模拟数据库查询
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        mock_history_result = MagicMock()
        mock_history_result.scalars.return_value.all.return_value = []

        api_client_full.mock_session.execute.side_effect = [
            mock_match_result,
            mock_history_result,
        ]

        # 发送请求
        response = api_client_full.get(f"/api/v1/predictions/history/12345?limit={limit}")

        # 验证响应
        assert response.status_code == status.HTTP_200_OK


class TestGetRecentPredictions:
    """获取最近预测API测试"""

    @pytest.mark.asyncio
    async def test_get_recent_predictions_success(self, api_client_full):
        """测试获取最近预测成功"""
        # 创建模拟的最近预测 - 模拟JOIN查询返回的Row对象
        predictions = []
        now = datetime.now()
        for i in range(5):
            # 创建类似 Row 对象的 MagicMock
            pred = MagicMock()
            pred.id = i + 1
            pred.match_id = 100 + i
            pred.model_version = "1.0"
            pred.model_name = "test_model"
            pred.predicted_result = "home_win"
            pred.confidence_score = Decimal("0.7")
            pred.created_at = now
            pred.is_correct = None
            pred.home_team_id = 1
            pred.away_team_id = 2
            pred.match_time = now
            pred.match_status = "scheduled"  # 字符串格式而不是枚举
            predictions.append(pred)

        # 模拟数据库查询
        mock_result = MagicMock()
        mock_result.fetchall.return_value = predictions
        api_client_full.mock_session.execute.return_value = mock_result

        # 发送请求
        response = api_client_full.get("/api/v1/predictions/recent?hours=24&limit=5")

        # 验证响应
        assert response.status_code == status.HTTP_200_OK
        _data = response.json()
        assert _data["success"] is True
        assert _data["data"]["time_range_hours"] == 24
        assert _data["data"]["total_predictions"] == 5
        assert len(_data["data"]["predictions"]) == 5
        assert "match_info" in _data["data"]["predictions"][0]

    @pytest.mark.parametrize("hours,limit", [(1, 10), (24, 50), (168, 100)])
    @pytest.mark.asyncio
    async def test_get_recent_predictions_different_params(self, api_client_full, hours, limit):
        """测试不同的时间范围和限制"""
        # 模拟数据库查询返回空结果
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        api_client_full.mock_session.execute.return_value = mock_result

        # 发送请求
        response = api_client_full.get(f"/api/v1/predictions/recent?hours={hours}&limit={limit}")

        # 验证响应
        assert response.status_code == status.HTTP_200_OK
        _data = response.json()
        assert _data["success"] is True
        assert _data["data"]["time_range_hours"] == hours


class TestVerifyPrediction:
    """验证预测结果API测试"""

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, api_client_full):
        """测试验证预测成功"""
        # 模拟预测服务
        with patch.object(
            PredictionService, "verify_prediction", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["success"] is True
            assert _data["data"]["match_id"] == 12345
            assert _data["data"]["verified"] is True
            assert "预测结果验证完成" in _data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_failure(self, api_client_full):
        """测试验证预测失败"""
        # 模拟预测服务
        with patch.object(
            PredictionService, "verify_prediction", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = False

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # 验证响应
            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["success"] is False
            assert _data["data"]["verified"] is False
            assert "验证失败" in _data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_service_error(self, api_client_full):
        """测试验证预测服务错误"""
        # 模拟预测服务抛出异常
        with patch.object(
            PredictionService, "verify_prediction", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.side_effect = Exception("Verification failed")

            # 发送请求
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # 验证响应
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
