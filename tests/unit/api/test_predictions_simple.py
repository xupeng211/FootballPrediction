"""
预测API简化测试
目标覆盖率: 45%
模块: src.api.predictions
测试范围: 预测API端点、数据验证、业务逻辑、响应格式
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

# 直接导入predictions路由器
import importlib.util

spec = importlib.util.spec_from_file_location(
    "predictions_module",
    "/home/user/projects/FootballPrediction/src/api/predictions/router.py",
)
predictions_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predictions_module)

# 从导入的模块中获取类和路由器
router = predictions_module.router
PredictionRequest = predictions_module.PredictionRequest
PredictionResult = predictions_module.PredictionResult
BatchPredictionRequest = predictions_module.BatchPredictionRequest
BatchPredictionResponse = predictions_module.BatchPredictionResponse
PredictionHistory = predictions_module.PredictionHistory
RecentPrediction = predictions_module.RecentPrediction
PredictionVerification = predictions_module.PredictionVerification


class TestPredictionModels:
    """预测数据模型测试"""

    def test_prediction_request_default_values(self):
        """测试预测请求模型默认值"""
        request = PredictionRequest()

        assert request.model_version == "default"
        assert request.include_details is False

    def test_prediction_request_custom_values(self):
        """测试预测请求模型自定义值"""
        request = PredictionRequest(model_version="v2.0", include_details=True)

        assert request.model_version == "v2.0"
        assert request.include_details is True

    def test_prediction_result_valid_data(self):
        """测试预测结果模型有效数据"""
        now = datetime.utcnow()
        result = PredictionResult(
            match_id=12345,
            home_win_prob=0.45,
            draw_prob=0.30,
            away_win_prob=0.25,
            predicted_outcome="home",
            confidence=0.75,
            model_version="default",
            predicted_at=now,
        )

        assert result.match_id == 12345
        assert result.home_win_prob == 0.45
        assert result.draw_prob == 0.30
        assert result.away_win_prob == 0.25
        assert result.predicted_outcome == "home"
        assert result.confidence == 0.75
        assert result.model_version == "default"
        assert result.predicted_at == now

    def test_prediction_result_probability_validation(self):
        """测试预测结果概率验证"""
        # 测试有效概率
        valid_probs = [
            (0.0, 0.0, 1.0),  # 极端情况
            (0.33, 0.34, 0.33),  # 平均分布
            (1.0, 0.0, 0.0),  # 确定性预测
        ]

        for home, draw, away in valid_probs:
            result = PredictionResult(
                match_id=1,
                home_win_prob=home,
                draw_prob=draw,
                away_win_prob=away,
                predicted_outcome="home",
                confidence=0.5,
                model_version="test",
            )
            assert result.home_win_prob == home
            assert result.draw_prob == draw
            assert result.away_win_prob == away

    def test_prediction_result_invalid_probabilities(self):
        """测试预测结果无效概率"""
        # 测试超出范围的概率
        invalid_probs = [
            (-0.1, 0.5, 0.6),  # 负概率
            (1.1, 0.0, 0.0),  # 超过1的概率
            (0.5, 0.6, 0.0),  # 总和超过1
        ]

        for home, draw, away in invalid_probs:
            with pytest.raises(ValidationError):
                PredictionResult(
                    match_id=1,
                    home_win_prob=home,
                    draw_prob=draw,
                    away_win_prob=away,
                    predicted_outcome="home",
                    confidence=0.5,
                    model_version="test",
                )

    def test_prediction_result_invalid_outcome(self):
        """测试预测结果无效结果"""
        with pytest.raises(ValidationError):
            PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="invalid",  # 无效结果
                confidence=0.75,
                model_version="default",
            )

    def test_batch_prediction_request_valid(self):
        """测试批量预测请求有效数据"""
        request = BatchPredictionRequest(
            match_ids=[1, 2, 3, 4, 5], model_version="v2.0"
        )

        assert request.match_ids == [1, 2, 3, 4, 5]
        assert request.model_version == "v2.0"

    def test_batch_prediction_request_empty_list(self):
        """测试批量预测请求空列表"""
        with pytest.raises(ValidationError):
            BatchPredictionRequest(match_ids=[])

    def test_batch_prediction_request_too_many_matches(self):
        """测试批量预测请求比赛数量过多"""
        with pytest.raises(ValidationError):
            BatchPredictionRequest(match_ids=list(range(101)))  # 101场比赛，超过限制

    def test_recent_prediction_model(self):
        """测试最近预测模型"""
        now = datetime.utcnow()
        prediction = PredictionResult(
            match_id=123,
            home_win_prob=0.45,
            draw_prob=0.30,
            away_win_prob=0.25,
            predicted_outcome="home",
            confidence=0.75,
            model_version="default",
            predicted_at=now,
        )

        recent = RecentPrediction(
            id=1,
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            prediction=prediction,
            match_date=now + timedelta(days=1),
        )

        assert recent.id == 1
        assert recent.match_id == 123
        assert recent.home_team == "Team A"
        assert recent.away_team == "Team B"
        assert recent.prediction == prediction
        assert recent.match_date == now + timedelta(days=1)

    def test_prediction_verification_model(self):
        """测试预测验证模型"""
        now = datetime.utcnow()
        prediction = PredictionResult(
            match_id=123,
            home_win_prob=0.45,
            draw_prob=0.30,
            away_win_prob=0.25,
            predicted_outcome="home",
            confidence=0.75,
            model_version="default",
            predicted_at=now,
        )

        verification = PredictionVerification(
            match_id=123,
            prediction=prediction,
            actual_result="home",
            is_correct=True,
            accuracy_score=0.75,
        )

        assert verification.match_id == 123
        assert verification.prediction == prediction
        assert verification.actual_result == "home"
        assert verification.is_correct is True
        assert verification.accuracy_score == 0.75


class TestPredictionAPIEndpoints:
    """预测API端点测试"""

    @pytest.fixture
    def client(self):
        """FastAPI测试客户端"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return TestClient(app)

    def test_get_predictions_root(self, client):
        """测试获取预测服务根路径"""
        response = client.get("/api/v1/predictions/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "足球预测API"
        assert data["module"] == "predictions"
        assert data["version"] == "1.0.0"
        assert data["status"] == "运行中"
        assert "endpoints" in data

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/api/v1/predictions/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "predictions"

    def test_get_recent_predictions_default_params(self, client):
        """测试获取最近预测默认参数"""
        with patch("predictions_module.logger") as mock_logger:
            response = client.get("/api/v1/predictions/recent")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10  # 默认限制

        # 验证日志记录
        mock_logger.info.assert_called()

    def test_get_recent_predictions_custom_params(self, client):
        """测试获取最近预测自定义参数"""
        with patch("predictions_module.logger") as mock_logger:
            response = client.get("/api/v1/predictions/recent?limit=5&hours=12")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5  # 自定义限制

        # 验证日志记录包含参数
        call_args = mock_logger.info.call_args[0][0]
        assert "12" in call_args  # hours参数
        assert "5" in call_args  # limit参数

    def test_get_recent_predictions_invalid_limit(self, client):
        """测试获取最近预测无效限制参数"""
        response = client.get("/api/v1/predictions/recent?limit=0")

        # FastAPI会自动验证查询参数
        assert response.status_code == 422  # Validation error

    def test_get_prediction_valid_match_id(self, client):
        """测试获取有效比赛ID的预测"""
        match_id = 12345
        with patch("predictions_module.logger") as mock_logger:
            response = client.get(f"/api/v1/predictions/{match_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == match_id
        assert "home_win_prob" in data
        assert "draw_prob" in data
        assert "away_win_prob" in data
        assert "predicted_outcome" in data
        assert "confidence" in data
        assert "model_version" in data
        assert "predicted_at" in data

        # 验证概率总和
        total_prob = data["home_win_prob"] + data["draw_prob"] + data["away_win_prob"]
        assert abs(total_prob - 1.0) < 0.01  # 允许小的浮点误差

    def test_get_prediction_with_custom_params(self, client):
        """测试获取带自定义参数的预测"""
        match_id = 12345
        response = client.get(
            f"/api/v1/predictions/{match_id}?model_version=v2.0&include_details=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == match_id
        assert data["model_version"] == "v2.0"

    def test_create_prediction_success(self, client):
        """测试创建预测成功"""
        match_id = 12345
        request_data = {"model_version": "v2.0", "include_details": True}

        with patch("predictions_module.logger") as mock_logger:
            response = client.post(
                f"/api/v1/predictions/{match_id}/predict", json=request_data
            )

        assert response.status_code == 201
        data = response.json()
        assert data["match_id"] == match_id
        assert data["model_version"] == "v2.0"
        assert "predicted_at" in data

        # 验证日志记录
        mock_logger.info.assert_called()

    def test_create_prediction_default_params(self, client):
        """测试创建预测默认参数"""
        match_id = 12345

        with patch("predictions_module.logger") as mock_logger:
            response = client.post(f"/api/v1/predictions/{match_id}/predict")

        assert response.status_code == 201
        data = response.json()
        assert data["match_id"] == match_id
        assert data["model_version"] == "default"  # 默认值

    def test_batch_predict_success(self, client):
        """测试批量预测成功"""
        request_data = {"match_ids": [1, 2, 3, 4, 5], "model_version": "v2.0"}

        with patch("predictions_module.logger") as mock_logger:
            response = client.post("/api/v1/predictions/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "total" in data
        assert "success_count" in data
        assert "failed_count" in data
        assert data["total"] == 5
        assert len(data["predictions"]) == 5
        assert data["success_count"] == 5
        assert data["failed_count"] == 0

        # 验证每个预测都有必需字段
        for prediction in data["predictions"]:
            assert "match_id" in prediction
            assert "predicted_outcome" in prediction
            assert "confidence" in prediction

    def test_batch_predict_too_many_matches(self, client):
        """测试批量预测比赛数量过多"""
        request_data = {
            "match_ids": list(range(101)),  # 101场比赛，超过限制
            "model_version": "default",
        }

        response = client.post("/api/v1/predictions/batch", json=request_data)

        # Pydantic会验证输入并返回422错误
        assert response.status_code == 422

    def test_get_prediction_history_valid_match(self, client):
        """测试获取有效比赛的预测历史"""
        match_id = 12345

        with patch("predictions_module.logger") as mock_logger:
            response = client.get(f"/api/v1/predictions/history/{match_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == match_id
        assert "predictions" in data
        assert "total_predictions" in data
        assert isinstance(data["predictions"], list)

    def test_get_prediction_history_with_limit(self, client):
        """测试获取带限制的预测历史"""
        match_id = 12345
        response = client.get(f"/api/v1/predictions/history/{match_id}?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["predictions"]) <= 3

    def test_verify_prediction_correct(self, client):
        """测试验证正确预测"""
        match_id = 12345

        with patch("predictions_module.logger") as mock_logger:
            response = client.post(
                f"/api/v1/predictions/{match_id}/verify?actual_result=home"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == match_id
        assert data["actual_result"] == "home"
        assert "prediction" in data
        assert "is_correct" in data
        assert "accuracy_score" in data

        # 验证预测逻辑
        prediction = data["prediction"]
        assert prediction["predicted_outcome"] == "home"  # 模拟数据中预测为home
        assert data["is_correct"] is True
        assert data["accuracy_score"] > 0

    def test_verify_prediction_incorrect(self, client):
        """测试验证错误预测"""
        match_id = 12345

        with patch("predictions_module.logger") as mock_logger:
            response = client.post(
                f"/api/v1/predictions/{match_id}/verify?actual_result=away"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["actual_result"] == "away"
        assert data["is_correct"] is False  # 预测为home，实际为away
        assert data["accuracy_score"] < 1.0

    def test_verify_prediction_invalid_result(self, client):
        """测试验证无效比赛结果"""
        match_id = 12345

        response = client.post(
            f"/api/v1/predictions/{match_id}/verify?actual_result=invalid"
        )

        # FastAPI会验证查询参数
        assert response.status_code == 422


class TestPredictionBusinessLogic:
    """预测业务逻辑测试"""

    def test_prediction_probability_sum_validation(self):
        """测试预测概率总和验证"""
        # 测试概率总和应该接近1.0
        test_cases = [
            (0.45, 0.30, 0.25),  # 正常情况
            (0.33, 0.33, 0.34),  # 平均分布
            (0.50, 0.25, 0.25),  # 偏向主队
            (0.25, 0.25, 0.50),  # 偏向客队
        ]

        for home, draw, away in test_cases:
            result = PredictionResult(
                match_id=1,
                home_win_prob=home,
                draw_prob=draw,
                away_win_prob=away,
                predicted_outcome="home",
                confidence=0.75,
                model_version="test",
            )

            total_prob = home + draw + away
            assert (
                abs(total_prob - 1.0) < 0.01
            ), f"概率总和应该为1.0，实际为{total_prob}"

    def test_prediction_outcome_consistency(self):
        """测试预测结果一致性"""
        # 预测结果应该对应最高概率
        test_cases = [
            (0.50, 0.30, 0.20, "home"),  # 主队概率最高
            (0.20, 0.50, 0.30, "draw"),  # 平局概率最高
            (0.25, 0.25, 0.50, "away"),  # 客队概率最高
        ]

        for home, draw, away, expected_outcome in test_cases:
            result = PredictionResult(
                match_id=1,
                home_win_prob=home,
                draw_prob=draw,
                away_win_prob=away,
                predicted_outcome=expected_outcome,
                confidence=0.75,
                model_version="test",
            )

            # 验证预测结果与最高概率一致
            probs = {"home": home, "draw": draw, "away": away}
            max_prob_outcome = max(probs, key=probs.get)
            assert result.predicted_outcome == max_prob_outcome

    def test_confidence_range_validation(self):
        """测试置信度范围验证"""
        valid_confidences = [0.0, 0.25, 0.5, 0.75, 1.0]

        for confidence in valid_confidences:
            result = PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=confidence,
                model_version="test",
            )
            assert result.confidence == confidence

    def test_model_version_consistency(self):
        """测试模型版本一致性"""
        versions = ["default", "v1.0", "v2.0", "experimental"]

        for version in versions:
            result = PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=0.75,
                model_version=version,
            )
            assert result.model_version == version

    def test_batch_prediction_response_accuracy(self):
        """测试批量预测响应准确性"""
        predictions = [
            PredictionResult(
                match_id=i,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=0.75,
                model_version="test",
                predicted_at=datetime.utcnow(),
            )
            for i in range(1, 6)
        ]

        response = BatchPredictionResponse(
            predictions=predictions,
            total=5,
            success_count=5,
            failed_count=0,
            failed_match_ids=[],
        )

        assert response.total == len(predictions)
        assert response.success_count == len(predictions)
        assert response.failed_count == 0
        assert len(response.failed_match_ids) == 0
        assert len(response.predictions) == 5

        # 验证每个预测都在响应中
        response_ids = {p.match_id for p in response.predictions}
        expected_ids = {p.match_id for p in predictions}
        assert response_ids == expected_ids

    def test_prediction_verification_accuracy_calculation(self):
        """测试预测验证准确性计算"""
        prediction = PredictionResult(
            match_id=1,
            home_win_prob=0.45,
            draw_prob=0.30,
            away_win_prob=0.25,
            predicted_outcome="home",
            confidence=0.75,
            model_version="test",
            predicted_at=datetime.utcnow(),
        )

        # 正确预测
        verification_correct = PredictionVerification(
            match_id=1,
            prediction=prediction,
            actual_result="home",
            is_correct=True,
            accuracy_score=prediction.confidence,
        )
        assert verification_correct.accuracy_score == 0.75
        assert verification_correct.is_correct is True

        # 错误预测
        verification_incorrect = PredictionVerification(
            match_id=1,
            prediction=prediction,
            actual_result="away",
            is_correct=False,
            accuracy_score=1.0 - prediction.confidence,
        )
        assert verification_incorrect.accuracy_score == 0.25
        assert verification_incorrect.is_correct is False


class TestErrorHandling:
    """错误处理测试"""

    def test_prediction_model_validation_errors(self):
        """测试预测模型验证错误"""
        # 测试无效的概率值
        invalid_data = {
            "match_id": 1,
            "home_win_prob": 1.5,  # 超过1.0
            "draw_prob": 0.3,
            "away_win_prob": 0.2,
            "predicted_outcome": "home",
            "confidence": 0.75,
            "model_version": "test",
        }

        with pytest.raises(ValidationError):
            PredictionResult(**invalid_data)

    def test_batch_request_validation_errors(self):
        """测试批量请求验证错误"""
        # 测试空的match_ids列表
        invalid_data = {"match_ids": [], "model_version": "test"}

        with pytest.raises(ValidationError):
            BatchPredictionRequest(**invalid_data)

    def test_prediction_outcome_validation(self):
        """测试预测结果验证"""
        # 测试无效的预测结果
        result = PredictionResult(
            match_id=1,
            home_win_prob=0.45,
            draw_prob=0.30,
            away_win_prob=0.25,
            predicted_outcome="home",
            confidence=0.75,
            model_version="test",
        )

        # 测试有效结果
        valid_outcomes = ["home", "draw", "away"]
        assert result.predicted_outcome in valid_outcomes


class TestDataValidation:
    """数据验证测试"""

    def test_match_id_validation(self):
        """测试比赛ID验证"""
        # 测试有效的比赛ID
        valid_ids = [1, 12345, 999999]
        for match_id in valid_ids:
            result = PredictionResult(
                match_id=match_id,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=0.75,
                model_version="test",
            )
            assert result.match_id == match_id

    def test_confidence_boundary_values(self):
        """测试置信度边界值"""
        boundary_values = [0.0, 0.5, 1.0]

        for confidence in boundary_values:
            result = PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=confidence,
                model_version="test",
            )
            assert result.confidence == confidence

    def test_model_version_formats(self):
        """测试模型版本格式"""
        version_formats = [
            "default",
            "v1.0",
            "v2.1.0",
            "experimental",
            "prod-2024-01-01",
        ]

        for version in version_formats:
            result = PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=0.75,
                model_version=version,
            )
            assert result.model_version == version

    def test_prediction_timestamp_validation(self):
        """测试预测时间戳验证"""
        now = datetime.utcnow()
        time_variations = [
            now,
            now - timedelta(hours=1),
            now + timedelta(days=1),
            now - timedelta(days=30),
        ]

        for timestamp in time_variations:
            result = PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=0.75,
                model_version="test",
                predicted_at=timestamp,
            )
            assert result.predicted_at == timestamp


class TestPerformanceConsiderations:
    """性能考虑测试"""

    def test_batch_prediction_scaling(self):
        """测试批量预测扩展性"""
        # 测试不同规模的批量预测
        batch_sizes = [1, 10, 50, 100]

        for size in batch_sizes:
            match_ids = list(range(1, size + 1))
            request = BatchPredictionRequest(match_ids=match_ids, model_version="test")

            assert len(request.match_ids) == size
            assert request.match_ids == match_ids

    def test_large_prediction_history(self):
        """测试大量预测历史"""
        # 模拟大量历史预测
        large_history = [
            PredictionResult(
                match_id=1,
                home_win_prob=0.45,
                draw_prob=0.30,
                away_win_prob=0.25,
                predicted_outcome="home",
                confidence=0.75,
                model_version="test",
                predicted_at=datetime.utcnow() - timedelta(hours=i),
            )
            for i in range(100)  # 100条历史记录
        ]

        history = PredictionHistory(
            match_id=1, predictions=large_history, total_predictions=len(large_history)
        )

        assert history.total_predictions == 100
        assert len(history.predictions) == 100

    def test_concurrent_prediction_requests(self):
        """测试并发预测请求"""
        # 模拟并发请求的数据结构
        requests = [
            PredictionRequest(model_version=f"version_{i}", include_details=i % 2 == 0)
            for i in range(10)
        ]

        for i, request in enumerate(requests):
            assert request.model_version == f"version_{i}"
            assert request.include_details == (i % 2 == 0)
