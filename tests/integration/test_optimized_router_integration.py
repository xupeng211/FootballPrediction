from typing import Optional

"""
optimized_router.py 黑盒集成测试
Optimized Router Black Box Integration Tests

【SDET安全网测试】为P0风险文件 optimized_router.py 创建第一层安全网测试

测试原则:
- 🚫 绝对不Mock目标文件的内部函数
- ✅ 只关注HTTP输入和HTTP输出
- ✅ 使用TestClient进行真实的HTTP请求
- ✅ 构造简单的请求，验证关键响应字段

风险等级: P0 (1576行代码，0%覆盖率)
测试策略: 黑盒集成测试 - Happy Path + Unhappy Path
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestOptimizedRouterSafetyNet:
    """
    optimized_router.py 安全网测试

    核心目标：为这个1576行的P0风险文件创建最基本的"安全网"
    未来重构时，这些测试能保证基本功能不被破坏
    """

    @pytest.fixture(scope="class")
    def client(self):
        """创建TestClient - 使用真实的应用实例"""
        # 创建FastAPI应用并导入目标路由
        app = FastAPI(title="Football Prediction API Test")

        # 添加简单的认证绕过 - 为了集成测试目的
        from fastapi import Request
        from src.core.dependencies import get_current_user_optional

        # 创建Mock用户用于测试
        class MockUser:
            def __init__(self):
                self.id = 1
                self.is_admin = True

        async def mock_get_current_user_optional(request: Request = None):
            """Mock认证依赖，返回可选用户"""
            return MockUser()

        # 导入并注册目标路由 - 覆盖认证依赖
        from src.api.predictions.optimized_router import router

        app.include_router(router, prefix="/api/v1")

        # 覆盖认证依赖
        app.dependency_overrides[get_current_user_optional] = (
            mock_get_current_user_optional
        )

        return TestClient(app)

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.critical
    def test_health_check_happy_path(self, client):
        """
        P0测试: 健康检查端点 Happy Path

        测试目标: GET /api/v1/predictions/health
        预期结果: 200 OK + 基本健康状态字段
        业务重要性: 系统监控的核心入口点
        """
        response = client.get("/api/v1/predictions/health")

        # 断言HTTP状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # 验证核心字段存在（不验证具体值，避免Mock）
        assert "status" in data, "Response should contain 'status' field"
        assert "timestamp" in data, "Response should contain 'timestamp' field"
        assert "cache_stats" in data, "Response should contain 'cache_stats' field"
        assert "system_metrics" in data, (
            "Response should contain 'system_metrics' field"
        )

        # 验证数据结构合理性
        assert isinstance(data["status"], str), "Status should be a string"
        assert isinstance(data["timestamp"], str), "Timestamp should be a string"

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.critical
    def test_predictions_list_happy_path(self, client):
        """
        P0测试: 获取预测列表 Happy Path

        测试目标: GET /api/v1/predictions/
        预期结果: 200 OK + 预测列表结构
        业务重要性: 用户查看预测的核心功能
        """
        response = client.get("/api/v1/predictions/")

        # 断言HTTP状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # 验证响应结构（基于文档中的示例）
        assert "predictions" in data, "Response should contain 'predictions' field"
        assert "total" in data, "Response should contain 'total' field"
        assert "limit" in data, "Response should contain 'limit' field"
        assert "offset" in data, "Response should contain 'offset' field"

        # 验证数据类型
        assert isinstance(data["predictions"], list), "Predictions should be a list"
        assert isinstance(data["total"], int), "Total should be an integer"
        assert isinstance(data["limit"], int), "Limit should be an integer"
        assert isinstance(data["offset"], int), "Offset should be an integer"

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.critical
    def test_create_prediction_happy_path(self, client):
        """
        P0测试: 创建预测 Happy Path

        测试目标: POST /api/v1/predictions/
        预期结果: 201 Created + 预测创建响应
        业务重要性: 核心业务功能 - 创建新预测
        """
        # 构造最简单的有效请求
        request_payload = {
            "match_id": 12345,
            "features": {"test_feature": "test_value"},
            "priority": "normal",
        }

        response = client.post("/api/v1/predictions/", json=request_payload)

        # 断言HTTP状态码
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data = response.json()

        # 验证创建响应的核心字段
        assert "id" in data, "Response should contain 'id' field"
        assert "status" in data, "Response should contain 'status' field"
        assert "match_id" in data, "Response should contain 'match_id' field"
        assert "created_at" in data, "Response should contain 'created_at' field"
        assert "estimated_completion" in data, (
            "Response should contain 'estimated_completion' field"
        )

        # 验证数据合理性
        assert data["status"] == "pending", (
            "New prediction should have 'pending' status"
        )
        assert data["match_id"] == request_payload["match_id"], (
            "Match ID should match request"
        )
        assert isinstance(data["id"], str), "Prediction ID should be a string"
        assert data["id"].startswith("pred_"), "Prediction ID should start with 'pred_'"

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.critical
    def test_get_match_prediction_happy_path(self, client):
        """
        P0测试: 获取比赛预测结果 Happy Path (核心业务API)

        测试目标: GET /api/v1/predictions/matches/{match_id}/prediction
        预期结果: 200 OK + 预测结果数据
        业务重要性: 系统核心价值 - 提供AI预测结果
        """
        match_id = 12345

        response = client.get(f"/api/v1/predictions/matches/{match_id}/prediction")

        # 断言HTTP状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # 验证预测响应的核心结构
        assert "status" in data, "Response should contain 'status' field"
        assert "data" in data, "Response should contain 'data' field"
        assert "cached" in data, "Response should contain 'cached' field"
        assert "execution_time_ms" in data, (
            "Response should contain 'execution_time_ms' field"
        )

        # 验证预测数据结构
        prediction_data = data["data"]
        assert "match_id" in prediction_data, (
            "Prediction data should contain 'match_id'"
        )
        assert "prediction_id" in prediction_data, (
            "Prediction data should contain 'prediction_id'"
        )
        assert "predicted_outcome" in prediction_data, (
            "Prediction data should contain 'predicted_outcome'"
        )
        assert "confidence_score" in prediction_data, (
            "Prediction data should contain 'confidence_score'"
        )
        assert "probabilities" in prediction_data, (
            "Prediction data should contain 'probabilities'"
        )
        assert "created_at" in prediction_data, (
            "Prediction data should contain 'created_at'"
        )

        # 验证数据合理性
        assert data["status"] == "success", "Response status should be 'success'"
        assert prediction_data["match_id"] == match_id, "Match ID should match request"
        assert isinstance(prediction_data["confidence_score"], (int, float)), (
            "Confidence should be numeric"
        )
        assert 0 <= prediction_data["confidence_score"] <= 1, (
            "Confidence should be between 0 and 1"
        )

        # 验证概率结构
        probs = prediction_data["probabilities"]
        assert "home_win" in probs, "Probabilities should contain 'home_win'"
        assert "draw" in probs, "Probabilities should contain 'draw'"
        assert "away_win" in probs, "Probabilities should contain 'away_win'"
        assert isinstance(probs["home_win"], (int, float)), (
            "Home win probability should be numeric"
        )
        assert isinstance(probs["draw"], (int, float)), (
            "Draw probability should be numeric"
        )
        assert isinstance(probs["away_win"], (int, float)), (
            "Away win probability should be numeric"
        )

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.critical
    def test_popular_predictions_happy_path(self, client):
        """
        P0测试: 获取热门预测 Happy Path

        测试目标: GET /api/v1/predictions/popular
        预期结果: 200 OK + 热门预测列表
        业务重要性: 用户发现热门内容的重要功能
        """
        response = client.get("/api/v1/predictions/popular")

        # 断言HTTP状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # 验证响应结构
        assert "status" in data, "Response should contain 'status' field"
        assert "data" in data, "Response should contain 'data' field"
        assert "time_range" in data, "Response should contain 'time_range' field"
        assert "limit" in data, "Response should contain 'limit' field"

        # 验证数据合理性
        assert data["status"] == "success", "Response status should be 'success'"
        assert isinstance(data["data"], list), "Popular predictions should be a list"
        assert isinstance(data["limit"], int), "Limit should be an integer"

        # 验证热门预测数据结构（如果有数据）
        if data["data"]:
            prediction = data["data"][0]  # 检查第一个预测的结构
            assert "prediction_id" in prediction, (
                "Popular prediction should contain 'prediction_id'"
            )
            assert "match_id" in prediction, (
                "Popular prediction should contain 'match_id'"
            )
            assert "predicted_outcome" in prediction, (
                "Popular prediction should contain 'predicted_outcome'"
            )
            assert "confidence_score" in prediction, (
                "Popular prediction should contain 'confidence_score'"
            )
            assert "popularity_score" in prediction, (
                "Popular prediction should contain 'popularity_score'"
            )

    @pytest.mark.integration
    @pytest.mark.api
    def test_create_prediction_unhappy_path_missing_fields(self, client):
        """
        P1测试: 创建预测 Unhappy Path - 缺少必需字段

        测试目标: POST /api/v1/predictions/
        错误构造: 缺少match_id字段
        预期结果: 422 Validation Error
        """
        # 构造缺少必需字段的请求
        invalid_payload = {
            "features": {"test_feature": "test_value"},
            "priority": "normal",
            # 缺少 match_id
        }

        response = client.post("/api/v1/predictions/", json=invalid_payload)

        # 断言HTTP状态码
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

        # 验证错误响应结构
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"

    @pytest.mark.integration
    @pytest.mark.api
    def test_create_prediction_unhappy_path_invalid_data(self, client):
        """
        P1测试: 创建预测 Unhappy Path - 无效数据类型

        测试目标: POST /api/v1/predictions/
        错误构造: match_id为字符串而非整数
        预期结果: 422 Validation Error
        """
        # 构造数据类型错误的请求
        invalid_payload = {
            "match_id": "not_a_number",  # 应该是整数
            "features": {"test_feature": "test_value"},
            "priority": "normal",
        }

        response = client.post("/api/v1/predictions/", json=invalid_payload)

        # 断言HTTP状态码
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_match_prediction_unhappy_path_invalid_id(self, client):
        """
        P1测试: 获取比赛预测 Unhappy Path - 无效ID

        测试目标: GET /api/v1/predictions/matches/{match_id}/prediction
        错误构造: 使用负数match_id
        预期结果: 400 或 422 Validation Error
        """
        # 使用负数ID（通常无效）
        invalid_match_id = -1

        response = client.get(
            f"/api/v1/predictions/matches/{invalid_match_id}/prediction"
        )

        # 断言HTTP状态码（可能是400或422，取决于验证逻辑）
        assert response.status_code in [400, 422], (
            f"Expected 400 or 422, got {response.status_code}"
        )

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_match_prediction_unhappy_path_zero_id(self, client):
        """
        P1测试: 获取比赛预测 Unhappy Path - 零值ID

        测试目标: GET /api/v1/predictions/matches/{match_id}/prediction
        错误构造: 使用0作为match_id
        预期结果: 400 或 422 Validation Error
        """
        # 使用零作为ID（通常无效）
        invalid_match_id = 0

        response = client.get(
            f"/api/v1/predictions/matches/{invalid_match_id}/prediction"
        )

        # 断言HTTP状态码
        assert response.status_code in [400, 404, 422], (
            f"Expected 400, 404 or 422, got {response.status_code}"
        )

    @pytest.mark.integration
    @pytest.mark.api
    def test_predictions_list_unhappy_path_invalid_pagination(self, client):
        """
        P1测试: 获取预测列表 Unhappy Path - 无效分页参数

        测试目标: GET /api/v1/predictions/
        错误构造: 使用负数作为limit参数
        预期结果: 422 Validation Error
        """
        # 使用无效的分页参数
        response = client.get("/api/v1/predictions/?limit=-5&offset=0")

        # 断言HTTP状态码
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

        # 验证错误响应包含验证信息
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"

    @pytest.mark.integration
    @pytest.mark.api
    def test_predictions_list_unhappy_path_oversized_limit(self, client):
        """
        P1测试: 获取预测列表 Unhappy Path - 超大limit值

        测试目标: GET /api/v1/predictions/
        错误构造: 使用超过限制的limit值（根据文档，最大为100）
        预期结果: 422 Validation Error
        """
        # 使用超过限制的limit值
        response = client.get("/api/v1/predictions/?limit=1000&offset=0")

        # 断言HTTP状态码
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @pytest.mark.integration
    @pytest.mark.api
    def test_popular_predictions_unhappy_path_invalid_time_range(self, client):
        """
        P1测试: 获取热门预测 Unhappy Path - 无效时间范围

        测试目标: GET /api/v1/predictions/popular
        错误构造: 使用不支持的时间范围参数
        预期结果: 422 Validation Error
        """
        # 根据文档，支持的时间范围: '1h', '24h', '7d'
        invalid_time_range = "invalid_time"

        response = client.get(
            f"/api/v1/predictions/popular?time_range={invalid_time_range}"
        )

        # 断言HTTP状态码
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @pytest.mark.integration
    @pytest.mark.api
    def test_popular_predictions_unhappy_path_invalid_limit(self, client):
        """
        P1测试: 获取热门预测 Unhappy Path - 无效limit参数

        测试目标: GET /api/v1/predictions/popular
        错误构造: 使用超过限制的limit值（根据文档，最大为50）
        预期结果: 422 Validation Error
        """
        # 使用超过限制的limit值
        response = client.get("/api/v1/predictions/popular?limit=100")

        # 断言HTTP状态码
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @pytest.mark.integration
    @pytest.mark.api
    def test_endpoint_not_found(self, client):
        """
        P1测试: 不存在的端点 Unhappy Path

        测试目标: GET /api/v1/predictions/nonexistent
        错误构造: 访问不存在的端点
        预期结果: 404 Not Found
        """
        response = client.get("/api/v1/predictions/nonexistent")

        # 断言HTTP状态码
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    @pytest.mark.integration
    @pytest.mark.api
    def test_invalid_method(self, client):
        """
        P1测试: 无效HTTP方法 Unhappy Path

        测试目标: DELETE /api/v1/predictions/
        错误构造: 对只支持GET/POST的端点使用DELETE方法
        预期结果: 405 Method Not Allowed
        """
        response = client.delete("/api/v1/predictions/")

        # 断言HTTP状态码
        assert response.status_code == 405, f"Expected 405, got {response.status_code}"
