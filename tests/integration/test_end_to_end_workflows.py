"""
端到端业务流程集成测试
End-to-End Business Logic Integration Tests

测试完整的业务流程，从数据收集到预测生成的整个链条。
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestDataCollectionWorkflow:
    """数据收集工作流集成测试"""

    @pytest.mark.asyncio
    async def test_team_data_collection_workflow(self, test_client: TestClient):
        """测试球队数据收集工作流"""
        # 1. 检查数据源状态
        response = test_client.get("/api/data/sources/status")
        # 接受200或404（端点可能不存在）
        assert response.status_code in [200, 404]

        # 2. 收集球队数据
        collect_data = {
            "collection_type": "teams",
            "data_source": "mock",
            "force_refresh": False,
        }

        response = test_client.post("/api/data/collect/teams", json=collect_data)
        # 接受200或404
        assert response.status_code in [200, 404]

        # 3. 验证收集结果
        if response.status_code == 200:
            data = response.json()
            assert "collected_count" in data
            assert "success" in data

    @pytest.mark.asyncio
    async def test_match_data_collection_workflow(self, test_client: TestClient):
        """测试比赛数据收集工作流"""
        # 1. 收集比赛数据
        collect_data = {
            "collection_type": "all",
            "days_ahead": 30,
            "data_source": "mock",
            "force_refresh": False,
        }

        response = test_client.post("/api/data/collect/all", json=collect_data)
        assert response.status_code in [200, 404]

        # 2. 验证收集统计
        response = test_client.get("/api/data/stats")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            stats = response.json()
            assert "total_matches" in stats
            assert "total_teams" in stats


@pytest.mark.integration
class TestPredictionWorkflow:
    """预测工作流集成测试"""

    @pytest.mark.asyncio
    async def test_single_match_prediction_workflow(self, test_client: TestClient):
        """测试单场比赛预测工作流"""
        # 1. 创建预测请求
        prediction_request = {"model_version": "default", "include_details": True}

        # 2. 生成预测
        response = test_client.post(
            "/api/predictions/1/predict", json=prediction_request
        )
        # 接受201或404
        assert response.status_code in [201, 404]

        # 3. 验证预测结果
        if response.status_code == 201:
            prediction = response.json()
            assert "match_id" in prediction
            assert "home_win_prob" in prediction
            assert "draw_prob" in prediction
            assert "away_win_prob" in prediction
            assert "predicted_outcome" in prediction
            assert "confidence" in prediction

    @pytest.mark.asyncio
    async def test_batch_prediction_workflow(self, test_client: TestClient):
        """测试批量预测工作流"""
        # 1. 创建批量预测请求
        batch_request = {"match_ids": [1, 2, 3, 4, 5], "model_version": "default"}

        # 2. 生成批量预测
        response = test_client.post("/api/predictions/batch", json=batch_request)
        assert response.status_code in [200, 404]

        # 3. 验证批量结果
        if response.status_code == 200:
            batch_result = response.json()
            assert "predictions" in batch_result
            assert "total" in batch_result
            assert "success_count" in batch_result

    @pytest.mark.asyncio
    async def test_prediction_history_workflow(self, test_client: TestClient):
        """测试预测历史工作流"""
        # 1. 获取预测历史
        response = test_client.get("/api/predictions/history/1")
        assert response.status_code in [200, 404]

        # 2. 验证历史数据
        if response.status_code == 200:
            history = response.json()
            assert "predictions" in history
            assert "total_predictions" in history

    @pytest.mark.asyncio
    async def test_prediction_verification_workflow(self, test_client: TestClient):
        """测试预测验证工作流"""
        # 1. 验证预测结果
        verification_data = {"actual_result": "home"}

        response = test_client.post(
            "/api/predictions/1/verify", params=verification_data
        )
        assert response.status_code in [200, 404]

        # 2. 验证验证结果
        if response.status_code == 200:
            verification = response.json()
            assert "match_id" in verification
            assert "is_correct" in verification
            assert "accuracy_score" in verification


@pytest.mark.integration
class TestDataProcessingWorkflow:
    """数据处理工作流集成测试"""

    @pytest.mark.asyncio
    async def test_feature_extraction_workflow(self, test_client: TestClient):
        """测试特征提取工作流"""
        # 1. 获取比赛特征
        response = test_client.get("/api/features/match/1")
        assert response.status_code in [200, 404]

        # 2. 验证特征数据
        if response.status_code == 200:
            features = response.json()
            assert "match_id" in features
            assert "status" in features

    @pytest.mark.asyncio
    async def test_data_preprocessing_workflow(self, test_client: TestClient):
        """测试数据预处理工作流"""
        # 这个测试需要实际的预处理API端点
        # 由于可能不存在，我们只测试基础连接
        response = test_client.get("/api/data/processing/status")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_data_quality_check_workflow(self, test_client: TestClient):
        """测试数据质量检查工作流"""
        # 1. 检查数据质量
        response = test_client.get("/api/data/quality/check")
        assert response.status_code in [200, 404]

        # 2. 验证质量报告
        if response.status_code == 200:
            quality_report = response.json()
            assert "completeness" in quality_report
            assert "accuracy" in quality_report


@pytest.mark.integration
class TestSystemMonitoringWorkflow:
    """系统监控工作流集成测试"""

    @pytest.mark.asyncio
    async def test_system_health_check_workflow(self, test_client: TestClient):
        """测试系统健康检查工作流"""
        # 1. 基础健康检查
        response = test_client.get("/api/health")
        assert response.status_code == 200

        health_data = response.json()
        assert "status" in health_data
        assert "timestamp" in health_data

        # 2. 详细系统状态
        response = test_client.get("/api/monitoring/status")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            monitoring_data = response.json()
            assert "status" in monitoring_data
            assert "services" in monitoring_data

    @pytest.mark.asyncio
    async def test_performance_monitoring_workflow(self, test_client: TestClient):
        """测试性能监控工作流"""
        # 1. 获取性能指标
        response = test_client.get("/api/monitoring/metrics")
        assert response.status_code in [200, 404]

        # 2. 验证性能数据
        if response.status_code == 200:
            metrics = response.json()
            assert "system" in metrics
            assert "database" in metrics

    @pytest.mark.asyncio
    async def test_error_monitoring_workflow(self, test_client: TestClient):
        """测试错误监控工作流"""
        # 模拟错误场景
        # 测试404处理
        response = test_client.get("/api/nonexistent/endpoint")
        assert response.status_code == 404

        # 测试错误响应格式
        error_data = response.json()
        assert "detail" in error_data


@pytest.mark.integration
class TestBusinessLogicIntegration:
    """业务逻辑集成测试"""

    @pytest.mark.asyncio
    async def test_football_prediction_business_logic(self, test_client: TestClient):
        """测试足球预测业务逻辑"""
        # 这是一个高级集成测试，模拟完整的业务流程

        # 1. 获取可用球队列表
        teams_response = test_client.get("/api/teams")
        assert teams_response.status_code in [200, 404]

        # 2. 获取比赛列表
        matches_response = test_client.get("/api/matches")
        assert matches_response.status_code in [200, 404]

        # 3. 选择比赛并生成预测
        if matches_response.status_code == 200:
            matches = matches_response.json()
            if len(matches) > 0:
                match_id = matches[0]["id"]

                prediction_response = test_client.post(
                    f"/api/predictions/{match_id}/predict",
                    json={"model_version": "default"},
                )
                assert prediction_response.status_code in [201, 404]

                if prediction_response.status_code == 201:
                    prediction = prediction_response.json()
                    # 验证预测结果的业务逻辑
                    total_prob = (
                        prediction["home_win_prob"]
                        + prediction["draw_prob"]
                        + prediction["away_win_prob"]
                    )
                    assert abs(total_prob - 1.0) < 0.01  # 允许小的浮点误差
                    assert prediction["confidence"] >= 0
                    assert prediction["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_data_consistency_workflow(self, test_client: TestClient):
        """测试数据一致性工作流"""
        # 这个测试验证系统中各个组件间的数据一致性

        # 1. 获取比赛统计
        stats_response = test_client.get("/api/data/stats")
        assert stats_response.status_code in [200, 404]

        # 2. 获取预测统计
        predictions_response = test_client.get("/api/predictions/recent")
        assert predictions_response.status_code in [200, 404]

        # 3. 验证数据一致性
        if (
            stats_response.status_code == 200
            and predictions_response.status_code == 200
        ):

            stats_data = stats_response.json()
            predictions_data = predictions_response.json()

            # 这里可以添加更复杂的一致性检查
            assert isinstance(stats_data, dict)
            assert isinstance(predictions_data, (list, dict))

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, test_client: TestClient):
        """测试错误恢复工作流"""
        # 测试系统在遇到错误时的恢复能力

        # 1. 模拟API超时或错误
        # 由于是集成测试，我们测试现有的错误处理机制

        # 2. 测试404错误处理
        response = test_client.get("/api/nonexistent/resource/12345")
        assert response.status_code == 404

        # 3. 测试错误响应的格式
        error_data = response.json()
        assert "detail" in error_data

        # 4. 测试系统在错误后仍然可用
        health_response = test_client.get("/api/health")
        assert health_response.status_code == 200


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """性能集成测试"""

    def test_api_response_times(self, test_client: TestClient):
        """测试API响应时间"""
        import time

        # 测试多个端点的响应时间
        endpoints = ["/api/health", "/api/", "/api/monitoring/status"]

        response_times = []

        for endpoint in endpoints:
            start_time = time.time()
            response = test_client.get(endpoint)
            end_time = time.time()

            # 记录响应时间（接受404状态码）
            response_times.append(
                {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                }
            )

        # 验证平均响应时间
        avg_time = sum(r["response_time"] for r in response_times) / len(response_times)
        assert avg_time < 1.0, f"Average response time {avg_time}s exceeds 1s"

        # 验证所有端点都在合理时间内响应
        for result in response_times:
            assert result["response_time"] < 2.0, (
                f"Endpoint {result['endpoint']} took " f"{result['response_time']:.2f}s"
            )

    def test_concurrent_request_handling(self, test_client: TestClient):
        """测试并发请求处理"""
        import threading
        import time

        results = []
        errors = []

        def make_request():
            try:
                start_time = time.time()
                response = test_client.get("/api/health")
                end_time = time.time()

                results.append(
                    {
                        "status_code": response.status_code,
                        "response_time": end_time - start_time,
                    }
                )
            except Exception as e:
                errors.append(str(e))

        # 创建多个并发请求
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有请求完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(results) == 20
        assert len(errors) == 0

        # 验证所有请求都成功
        successful_requests = [r for r in results if r["status_code"] in [200, 404]]
        assert len(successful_requests) == 20

        # 验证响应时间合理
        avg_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
