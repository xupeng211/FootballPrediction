
"""
预测API路由器测试
Tests for predictions API router

测试预测API的各个端点功能。
"""


import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionHistory,
    PredictionRequest,
    PredictionResult,
    PredictionVerification,
    RecentPrediction,
    router,
)


@pytest.mark.unit
@pytest.mark.api
class TestPredictionsRouter:
    """预测API路由器测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def sample_prediction_result(self):
        """示例预测结果"""
        return {
            "match_id": 12345,
            "home_win_prob": 0.45,
            "draw_prob": 0.30,
            "away_win_prob": 0.25,
            "predicted_outcome": "home",
            "confidence": 0.75,
            "model_version": "default",
            "predicted_at": datetime.utcnow().isoformat(),
        }

    @pytest.fixture
    def sample_batch_request(self):
        """示例批量预测请求"""
        return {
            "match_ids": [12345, 12346, 12347],
            "model_version": "default",
        }

    # ========================================
    # 健康检查端点测试
    # ========================================

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/api/v1/predictions/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "predictions"

    # ========================================
    # 获取预测端点测试
    # ========================================

    def test_get_prediction_success(self, client, sample_prediction_result):
        """测试成功获取预测"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.get("/api/v1/predictions/12345")

            assert response.status_code == 200
            data = response.json()
            assert data["match_id"] == 12345
            assert data["home_win_prob"] == 0.45
            assert data["draw_prob"] == 0.30
            assert data["away_win_prob"] == 0.25
            assert data["predicted_outcome"] == "home"
            assert data["confidence"] == 0.75
            assert data["model_version"] == "default"

    def test_get_prediction_with_custom_model_version(self, client):
        """测试使用自定义模型版本获取预测"""
        response = client.get("/api/v1/predictions/12345?model_version=v2.0")

        assert response.status_code == 200
        data = response.json()
        assert data["model_version"] == "v2.0"

    def test_get_prediction_with_details(self, client):
        """测试获取包含详细信息的预测"""
        response = client.get("/api/v1/predictions/12345?include_details=true")

        assert response.status_code == 200
        # 这个端点目前不返回详细信息，但测试确保参数被正确接收

    @patch("src.api.predictions.router.logger")
    def test_get_prediction_logging(self, mock_logger, client):
        """测试获取预测时的日志记录"""
        client.get("/api/v1/predictions/12345")

        mock_logger.info.assert_any_call("获取比赛 12345 的预测结果")
        mock_logger.info.assert_any_call("成功获取比赛 12345 的预测: home")

    # ========================================
    # 创建预测端点测试
    # ========================================

    def test_create_prediction_success(self, client):
        """测试成功创建预测"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.post("/api/v1/predictions/12345/predict")

            assert response.status_code == 201
            data = response.json()
            assert data["match_id"] == 12345
            assert data["home_win_prob"] == 0.50
            assert data["draw_prob"] == 0.28
            assert data["away_win_prob"] == 0.22
            assert data["predicted_outcome"] == "home"
            assert data["confidence"] == 0.78
            assert data["model_version"] == "default"

    def test_create_prediction_with_request_body(self, client):
        """测试带请求体的预测创建"""
        request_data = {
            "match_id": 12345,
            "model_version": "v2.0",
            "include_details": True,
        }

        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.post(
                "/api/v1/predictions/12345/predict", json=request_data
            )

            assert response.status_code == 201
            data = response.json()
            assert data["model_version"] == "v2.0"

    def test_create_prediction_with_empty_request(self, client):
        """测试空请求体的预测创建"""
        # 发送空的JSON体，应该使用默认值
        response = client.post("/api/v1/predictions/12345/predict", json={})

        assert response.status_code == 201
        data = response.json()
        assert data["model_version"] == "default"

    @patch("src.api.predictions.router.logger")
    def test_create_prediction_logging(self, mock_logger, client):
        """测试创建预测时的日志记录"""
        client.post("/api/v1/predictions/12345/predict")

        mock_logger.info.assert_any_call("开始为比赛 12345 生成预测")
        mock_logger.info.assert_any_call("成功生成比赛 12345 的预测: home")

    # ========================================
    # 批量预测端点测试
    # ========================================

    def test_batch_predict_success(self, client, sample_batch_request):
        """测试成功批量预测"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.post(
                "/api/v1/predictions/batch", json=sample_batch_request
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert data["success_count"] == 3
            assert data["failed_count"] == 0
            assert len(data["predictions"]) == 3
            assert len(data["failed_match_ids"]) == 0

    def test_batch_predict_single_match(self, client):
        """测试单场比赛批量预测"""
        request_data = {
            "match_ids": [12345],
            "model_version": "default",
        }

        response = client.post("/api/v1/predictions/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["success_count"] == 1

    def test_batch_predict_max_matches(self, client):
        """测试最大数量比赛批量预测"""
        request_data = {
            "match_ids": list(range(100)),  # 100场比赛
            "model_version": "default",
        }

        response = client.post("/api/v1/predictions/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100

    def test_batch_predict_too_many_matches(self, client):
        """测试超过限制的比赛数量"""
        request_data = {
            "match_ids": list(range(101)),  # 101场比赛，超过限制
            "model_version": "default",
        }

        response = client.post("/api/v1/predictions/batch", json=request_data)

        # 这应该触发Pydantic验证错误
        assert response.status_code == 422

    def test_batch_predict_empty_matches(self, client):
        """测试空比赛列表"""
        request_data = {
            "match_ids": [],
            "model_version": "default",
        }

        response = client.post("/api/v1/predictions/batch", json=request_data)

        # 这应该触发Pydantic验证错误
        assert response.status_code == 422

    @patch("src.api.predictions.router.logger")
    def test_batch_predict_logging(self, mock_logger, client, sample_batch_request):
        """测试批量预测时的日志记录"""
        client.post("/api/v1/predictions/batch", json=sample_batch_request)

        mock_logger.info.assert_any_call("开始批量预测 3 场比赛")
        mock_logger.info.assert_any_call("批量预测完成: 成功 3, 失败 0")

    # ========================================
    # 预测历史端点测试
    # ========================================

    def test_get_prediction_history_success(self, client):
        """测试成功获取预测历史"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.get("/api/v1/predictions/history/12345")

            assert response.status_code == 200
            data = response.json()
            assert data["match_id"] == 12345
            assert data["total_predictions"] == 5  # 默认返回5条记录
            assert len(data["predictions"]) == 5

    def test_get_prediction_history_custom_limit(self, client):
        """测试自定义限制的预测历史"""
        response = client.get("/api/v1/predictions/history/12345?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total_predictions"] == 3
        assert len(data["predictions"]) == 3

    def test_get_prediction_history_limit_validation(self, client):
        """测试预测历史限制验证"""
        # 测试最小限制
        response = client.get("/api/v1/predictions/history/12345?limit=0")
        assert response.status_code == 422

        # 测试最大限制
        response = client.get("/api/v1/predictions/history/12345?limit=101")
        assert response.status_code == 422

    def test_get_prediction_history_large_limit(self, client):
        """测试大限制的预测历史"""
        response = client.get("/api/v1/predictions/history/12345?limit=100")

        assert response.status_code == 200
        data = response.json()
        assert data["total_predictions"] == 5  # 模拟数据最多返回5条

    @patch("src.api.predictions.router.logger")
    def test_get_prediction_history_logging(self, mock_logger, client):
        """测试获取预测历史时的日志记录"""
        client.get("/api/v1/predictions/history/12345")

        mock_logger.info.assert_any_call("获取比赛 12345 的历史预测记录")
        mock_logger.info.assert_any_call("成功获取 5 条历史记录")

    # ========================================
    # 最近预测端点测试
    # ========================================

    def test_get_recent_predictions_success(self, client):
        """测试成功获取最近预测"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.get("/api/v1/predictions/recent")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 10  # 默认返回10条

    def test_get_recent_predictions_custom_params(self, client):
        """测试自定义参数的最近预测"""
        response = client.get("/api/v1/predictions/recent?limit=5&hours=12")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_recent_predictions_limit_validation(self, client):
        """测试最近预测限制验证"""
        # 测试最小限制
        response = client.get("/api/v1/predictions/recent?limit=0")
        assert response.status_code == 422

        # 测试最大限制
        response = client.get("/api/v1/predictions/recent?limit=101")
        assert response.status_code == 422

    def test_get_recent_predictions_hours_validation(self, client):
        """测试时间范围验证"""
        # 测试最小小时数
        response = client.get("/api/v1/predictions/recent?hours=0")
        assert response.status_code == 422

        # 测试最大小时数
        response = client.get("/api/v1/predictions/recent?hours=169")
        assert response.status_code == 422

    @patch("src.api.predictions.router.logger")
    def test_get_recent_predictions_logging(self, mock_logger, client):
        """测试获取最近预测时的日志记录"""
        client.get("/api/v1/predictions/recent")

        mock_logger.info.assert_any_call("获取最近 24 小时内的 20 条预测")
        mock_logger.info.assert_any_call("成功获取 10 条最近预测")

    # ========================================
    # 预测验证端点测试
    # ========================================

    def test_verify_prediction_success(self, client):
        """测试成功验证预测"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.post(
                "/api/v1/predictions/12345/verify?actual_result=home"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["match_id"] == 12345
            assert data["actual_result"] == "home"
            assert data["is_correct"] is True
            assert data["accuracy_score"] == 0.75

    def test_verify_prediction_wrong_result(self, client):
        """测试验证预测错误结果"""
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

            response = client.post(
                "/api/v1/predictions/12345/verify?actual_result=away"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["actual_result"] == "away"
            assert data["is_correct"] is False
            assert data["accuracy_score"] == 0.25  # 1.0 - 0.75

    def test_verify_prediction_invalid_result(self, client):
        """测试验证预测无效结果"""
        response = client.post("/api/v1/predictions/12345/verify?actual_result=invalid")

        assert response.status_code == 422  # 正则表达式验证失败

    def test_verify_prediction_draw_result(self, client):
        """测试验证预测平局结果"""
        response = client.post("/api/v1/predictions/12345/verify?actual_result=draw")

        assert response.status_code == 200
        data = response.json()
        assert data["actual_result"] == "draw"
        assert data["is_correct"] is False
        assert data["accuracy_score"] == 0.25

    @patch("src.api.predictions.router.logger")
    def test_verify_prediction_logging(self, mock_logger, client):
        """测试验证预测时的日志记录"""
        client.post("/api/v1/predictions/12345/verify?actual_result=home")

        mock_logger.info.assert_any_call("验证比赛 12345 的预测结果，实际结果: home")
        mock_logger.info.assert_any_call("验证完成: 正确, 准确度: 0.75")

    # ========================================
    # 错误处理测试
    # ========================================

    @patch("src.api.predictions.router.logger")
    def test_error_handling_logging(self, mock_logger, client):
        """测试错误处理时的日志记录"""
        # 模拟一个会抛出异常的情况
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.side_effect = Exception("模拟错误")

            response = client.get("/api/v1/predictions/12345")

            assert response.status_code == 500
            mock_logger.error.assert_called()

    # ========================================
    # 数据模型验证测试
    # ========================================

    def test_prediction_request_model(self):
        """测试预测请求模型"""
        # 测试最小请求
        request = PredictionRequest()
        assert request.model_version == "default"
        assert request.include_details is False

        # 测试完整请求
        request = PredictionRequest(model_version="v2.0", include_details=True)
        assert request.model_version == "v2.0"
        assert request.include_details is True

    def test_prediction_result_model_validation(self):
        """测试预测结果模型验证"""
        # 测试有效结果
        result = PredictionResult(
            match_id=12345,
            home_win_prob=0.5,
            draw_prob=0.3,
            away_win_prob=0.2,
            predicted_outcome="home",
            confidence=0.8,
            model_version="default",
        )
        assert result.match_id == 12345
        assert result.predicted_outcome == "home"

        # 测试概率边界
        with pytest.raises(ValueError):
            PredictionResult(
                match_id=12345,
                home_win_prob=1.5,  # 超出范围
                draw_prob=0.3,
                away_win_prob=0.2,
                predicted_outcome="home",
                confidence=0.8,
                model_version="default",
            )

    def test_batch_prediction_request_model(self):
        """测试批量预测请求模型"""
        # 测试有效请求
        request = BatchPredictionRequest(match_ids=[12345, 12346], model_version="v2.0")
        assert len(request.match_ids) == 2
        assert request.model_version == "v2.0"

        # 测试空列表（应该在Pydantic层被拒绝）
        with pytest.raises(ValueError):
            BatchPredictionRequest(match_ids=[])

        # 测试过长列表（应该在Pydantic层被拒绝）
        with pytest.raises(ValueError):
            BatchPredictionRequest(match_ids=list(range(101)))

    # ========================================
    # 边界条件测试
    # ========================================

    def test_large_match_id(self, client):
        """测试大比赛ID"""
        large_id = 2**31 - 1  # 最大的32位整数
        response = client.get(f"/api/v1/predictions/{large_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == large_id

    def test_negative_match_id(self, client):
        """测试负数比赛ID"""
        response = client.get("/api/v1/predictions/-1")
        # FastAPI通常会处理负整数，但我们检查响应
        assert response.status_code in [200, 422]

    def test_zero_match_id(self, client):
        """测试零比赛ID"""
        response = client.get("/api/v1/predictions/0")
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == 0
