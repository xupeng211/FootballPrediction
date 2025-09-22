"""
API预测端到端测试

测试范围: FastAPI预测接口的完整功能
测试重点:
- API端点响应和状态码
- 预测结果的概率分布验证
- 响应格式和数据完整性
- 错误处理和异常情况
- 性能和响应时间
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import pytest

# 项目导入 - 根据实际项目结构调整
try:
    from src.api.main import app
    from src.core.exceptions import PredictionError, ValidationError
    from src.models.prediction import PredictionResponse
except ImportError:
    # 创建Mock类用于测试框架
    class MockApp:
        def __init__(self):
            pass

    app = MockApp()

    class PredictionResponse:  # type: ignore[no-redef]
        pass

    class PredictionError(Exception):  # type: ignore[no-redef]
        pass

    class ValidationError(Exception):  # type: ignore[no-redef]
        pass


@pytest.mark.e2e
@pytest.mark.slow
class TestAPIPredictions:
    """API预测端到端测试类"""

    @pytest.fixture
    def sample_match_ids(self):
        """示例比赛ID列表"""
        return [12345, 67890, 11111, 22222, 33333]

    @pytest.fixture
    def expected_prediction_fields(self):
        """预期的预测响应字段"""
        return {
            "match_id",
            "home_win_probability",
            "draw_probability",
            "away_win_probability",
            "predicted_result",
            "confidence_score",
            "model_version",
            "prediction_timestamp",
            "features_used",
        }

    # ================================
    # 基础API功能测试
    # ================================

    def test_get_prediction_success(
        self, test_api_client, sample_match_ids, expected_prediction_fields
    ):
        """测试成功获取单场比赛预测"""
        match_id = sample_match_ids[0]

        response = test_api_client.get(f"/predictions/{match_id}")

        # 验证HTTP状态码
        assert response.status_code == 200, f"API返回状态码{response.status_code}，期望200"

        # 验证响应格式
        prediction_data = response.json()
        assert isinstance(prediction_data, dict), "预测响应应该是字典格式"

        # 验证必要字段存在
        for field in expected_prediction_fields:
            assert field in prediction_data, f"预测响应缺少字段: {field}"

        # 验证比赛ID匹配
        assert prediction_data["match_id"] == match_id, "返回的比赛ID与请求不匹配"

    def test_probability_distribution_validation(
        self, test_api_client, sample_match_ids
    ):
        """测试预测概率分布的有效性（总和为1）"""
        match_id = sample_match_ids[0]

        response = test_api_client.get(f"/predictions/{match_id}")

        if response.status_code == 200:
            prediction_data = response.json()

            # 提取概率值
            home_prob = prediction_data.get("home_win_probability", 0)
            draw_prob = prediction_data.get("draw_probability", 0)
            away_prob = prediction_data.get("away_win_probability", 0)

            # 验证概率范围
            assert 0 <= home_prob <= 1, f"主队胜率{home_prob}不在[0,1]范围内"
            assert 0 <= draw_prob <= 1, f"平局概率{draw_prob}不在[0,1]范围内"
            assert 0 <= away_prob <= 1, f"客队胜率{away_prob}不在[0,1]范围内"

            # 验证概率总和
            total_probability = home_prob + draw_prob + away_prob
            assert (
                abs(total_probability - 1.0) < 0.01
            ), f"概率总和{total_probability:.3f}不等于1.0"

            # 验证置信度分数
            confidence = prediction_data.get("confidence_score", 0)
            assert 0 <= confidence <= 1, f"置信度分数{confidence}不在[0,1]范围内"

    def test_batch_predictions_endpoint(self, test_api_client, sample_match_ids):
        """测试批量预测端点"""
        batch_request = {
            "match_ids": sample_match_ids[:3],  # 取前3个ID
            "include_features": True,
            "model_version": "latest",
        }

        response = test_api_client.post("/predictions/batch", json=batch_request)

        if response.status_code == 200:
            batch_predictions = response.json()

            # 验证批量响应格式
            assert isinstance(batch_predictions, dict), "批量预测响应应该是字典"
            assert "predictions" in batch_predictions, "批量响应缺少predictions字段"

            predictions_list = batch_predictions["predictions"]
            assert isinstance(predictions_list, list), "predictions应该是列表"
            assert len(predictions_list) == len(
                batch_request["match_ids"]
            ), "预测数量与请求不匹配"

            # 验证每个预测的完整性
            for prediction in predictions_list:
                assert "match_id" in prediction
                assert prediction["match_id"] in sample_match_ids[:3]

                # 验证概率分布
                total_prob = (
                    prediction.get("home_win_probability", 0)
                    + prediction.get("draw_probability", 0)
                    + prediction.get("away_win_probability", 0)
                )
                assert (
                    abs(total_prob - 1.0) < 0.01
                ), f"批量预测中比赛{prediction['match_id']}概率分布无效"

    # ================================
    # 错误处理测试
    # ================================

    def test_invalid_match_id_handling(self, test_api_client):
        """测试无效比赛ID的处理"""
        invalid_match_ids = [-1, 0, 999999999, "invalid", None]

        for invalid_id in invalid_match_ids:
            response = test_api_client.get(f"/predictions/{invalid_id}")

            # 应该返回4xx错误状态码
            assert response.status_code in [
                400,
                404,
                422,
            ], f"无效ID {invalid_id} 应该返回4xx错误，实际返回{response.status_code}"

            # 验证错误响应格式
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data, "错误响应缺少错误信息"

    def test_nonexistent_match_handling(self, test_api_client):
        """测试不存在比赛的处理"""
        nonexistent_match_id = 999999999  # 极大概率不存在的ID

        response = test_api_client.get(f"/predictions/{nonexistent_match_id}")

        # 应该返回404 Not Found
        assert response.status_code == 404, f"不存在的比赛应该返回404，实际返回{response.status_code}"

        # 验证错误消息
        error_data = response.json()
        error_message = error_data.get("detail", "").lower()
        assert "not found" in error_message or "不存在" in error_message, "错误消息应该指明比赛不存在"

    def test_api_rate_limiting(self, test_api_client, sample_match_ids):
        """测试API限流机制"""
        match_id = sample_match_ids[0]

        # 快速发送多个请求
        responses = []
        for i in range(10):
            response = test_api_client.get(f"/predictions/{match_id}")
            responses.append(response)

        # 检查是否有限流响应
        status_codes = [r.status_code for r in responses]
        rate_limit_detected = any(code == 429 for code in status_codes)

        if rate_limit_detected:
            # 验证限流响应格式
            rate_limit_response = next(r for r in responses if r.status_code == 429)
            assert "rate limit" in rate_limit_response.json().get("detail", "").lower()

        # 至少应该有一些成功的响应
        successful_responses = sum(1 for code in status_codes if code == 200)
        assert successful_responses > 0, "应该至少有一些成功的响应"

    # ================================
    # 数据质量测试
    # ================================

    def test_prediction_consistency(self, test_api_client, sample_match_ids):
        """测试预测结果的一致性"""
        match_id = sample_match_ids[0]

        # 多次请求同一比赛的预测
        predictions = []
        for _ in range(3):
            response = test_api_client.get(f"/predictions/{match_id}")
            if response.status_code == 200:
                predictions.append(response.json())
            time.sleep(0.1)  # 短暂延迟

        if len(predictions) >= 2:
            # 验证预测结果一致性（同一时间窗口内应该相同）
            first_prediction = predictions[0]
            for subsequent_prediction in predictions[1:]:
                # 检查关键字段是否一致
                assert subsequent_prediction["match_id"] == first_prediction["match_id"]

                # 如果是同一模型版本，预测应该相同
                if subsequent_prediction.get("model_version") == first_prediction.get(
                    "model_version"
                ):
                    assert (
                        abs(
                            subsequent_prediction["home_win_probability"]
                            - first_prediction["home_win_probability"]
                        )
                        < 0.001
                    ), "同一模型版本的预测结果应该一致"

    def test_features_metadata_completeness(self, test_api_client, sample_match_ids):
        """测试特征元数据的完整性"""
        match_id = sample_match_ids[0]

        # 请求包含特征信息的预测
        response = test_api_client.get(f"/predictions/{match_id}?include_features=true")

        if response.status_code == 200:
            prediction_data = response.json()

            # 验证特征信息存在
            assert "features_used" in prediction_data, "预测响应缺少特征信息"

            features_info = prediction_data["features_used"]
            if isinstance(features_info, dict):
                # 验证特征元数据字段
                expected_feature_fields = [
                    "feature_names",
                    "feature_count",
                    "feature_sources",
                ]
                for field in expected_feature_fields:
                    if field in features_info:
                        assert features_info[field] is not None, f"特征字段{field}不应为空"

            # 验证模型版本信息
            assert "model_version" in prediction_data, "预测响应缺少模型版本信息"
            model_version = prediction_data["model_version"]
            assert (
                isinstance(model_version, str) and len(model_version) > 0
            ), "模型版本应该是非空字符串"

    # ================================
    # 性能测试
    # ================================

    def test_api_response_time(self, test_api_client, sample_match_ids):
        """测试API响应时间"""
        match_id = sample_match_ids[0]
        max_response_time = 2.0  # 2秒最大响应时间

        start_time = time.time()
        response = test_api_client.get(f"/predictions/{match_id}")
        response_time = time.time() - start_time

        # 验证响应时间
        assert (
            response_time < max_response_time
        ), f"API响应时间{response_time:.2f}s超过{max_response_time}s阈值"

        # 如果响应成功，验证数据完整性
        if response.status_code == 200:
            prediction_data = response.json()
            assert "match_id" in prediction_data, "快速响应仍应包含完整数据"

    def test_concurrent_api_requests(self, test_api_client, sample_match_ids):
        """测试并发API请求处理"""

        def make_prediction_request(match_id):
            try:
                response = test_api_client.get(f"/predictions/{match_id}")
                return response.status_code, (
                    response.json() if response.status_code == 200 else None
                )
            except Exception:
                return None, None

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(make_prediction_request, mid)
                for mid in sample_match_ids[:3]
            }
            for future in as_completed(futures):
                results.append(future.result())

        # 验证并发处理结果
        successful_requests = sum(
            1 for result in results if result is not None and result[0] == 200
        )
        assert successful_requests >= len(sample_match_ids[:3]) * 0.8, "并发请求成功率应该至少80%"

        # 验证返回数据的一致性
        valid_results = [
            result for result in results if result is not None and result[1] is not None
        ]
        for status_code, prediction_data in valid_results:
            if prediction_data:
                # 验证每个并发请求的预测质量
                total_prob = (
                    prediction_data.get("home_win_probability", 0)
                    + prediction_data.get("draw_probability", 0)
                    + prediction_data.get("away_win_probability", 0)
                )
                assert abs(total_prob - 1.0) < 0.01, "并发请求中的概率分布应该有效"

    # ================================
    # 安全测试
    # ================================

    def test_sql_injection_prevention(self, test_api_client):
        """测试SQL注入防护"""
        malicious_inputs = [
            "1'; DROP TABLE predictions; --",
            "1 OR 1=1",
            "1 UNION SELECT * FROM users",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
        ]

        for malicious_input in malicious_inputs:
            response = test_api_client.get(f"/predictions/{malicious_input}")

            # 应该返回4xx错误，而不是500内部错误
            assert response.status_code in [
                400,
                404,
                422,
            ], f"恶意输入{malicious_input}应该被安全处理"

            # 响应不应该包含敏感信息
            response_text = response.text.lower()
            dangerous_keywords = ["error", "database", "table", "sql", "exception"]
            sensitive_info_leaked = any(
                keyword in response_text for keyword in dangerous_keywords
            )

            if sensitive_info_leaked:
                # 检查是否是预期的错误信息格式
                response_data = response.json()
                assert "detail" in response_data, "错误响应应该使用标准格式"

    def test_api_authentication_if_required(self, api_base_url):
        """测试API认证（如果需要）"""
        # 如果API需要认证，测试无认证访问
        with httpx.Client() as client:
            response = client.get(f"{api_base_url}/predictions/12345")

            # 如果API需要认证，应该返回401
            if response.status_code == 401:
                assert "unauthorized" in response.json().get("detail", "").lower()
            # 如果不需要认证，应该正常处理
            elif response.status_code in [200, 404]:
                pass  # 正常情况
            else:
                pytest.fail(f"意外的认证响应状态码: {response.status_code}")
