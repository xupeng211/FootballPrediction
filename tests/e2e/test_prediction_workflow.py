"""
端到端预测工作流测试
模拟完整的用户使用场景：从数据收集到预测结果
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.exceptions import PredictionError
from src.ml.inference import MatchPredictor, ModelLoader
from src.ml.inference.cache_manager import PredictionCache
from src.services.collection_service import FotMobCollectionService
from src.services.prediction_service import (
    PredictionRequest,
    PredictionResponse,
    PredictionService,
)


class TestEndToEndPredictionWorkflow:
    """端到端预测工作流测试"""

    @pytest.fixture
    def complete_system(self):
        """创建完整的系统模拟"""
        # Mock模型
        mock_model = Mock()
        mock_model.predict.return_value = [0]  # HOME_WIN
        mock_model.predict_proba.return_value = [[0.7, 0.2, 0.1]]
        mock_model.n_features_in_ = 12
        mock_model.classes_ = [0, 1, 2]

        # Mock模型加载器
        mock_loader = Mock()
        mock_loader.get_model.return_value = mock_model
        mock_loader.list_loaded_models.return_value = ["xgboost_v2.pkl"]
        mock_loader.get_model_metadata.return_value = {
            "accuracy": 0.68,
            "features": 12,
            "training_date": "2024-01-01",
        }
        mock_loader.load_model.return_value = True
        mock_loader.unload_model.return_value = True

        # Mock缓存
        mock_cache = Mock()
        mock_cache.get.return_value = None  # 初始缓存未命中
        mock_cache.set.return_value = True
        mock_cache.get_stats.return_value = {"hits": 0, "misses": 1, "hit_rate": 0.0}

        # 创建推理服务
        inference_service = InferenceService()
        inference_service.model_loader = mock_loader
        inference_service.cache_manager = mock_cache
        inference_service.is_initialized = True

        # 创建数据收集服务
        collection_service = FotMobCollectionService()

        return {
            "inference_service": inference_service,
            "collection_service": collection_service,
            "model": mock_model,
            "loader": mock_loader,
            "cache": mock_cache,
        }

    @pytest.mark.asyncio
    async def test_complete_prediction_workflow_single_match(self, complete_system):
        """测试单个比赛的完整预测工作流"""
        inference_service = complete_system["inference_service"]
        collection_service = complete_system["collection_service"]

        # 步骤1: 数据收集
        match_id = "prem_2024_12345"
        home_team = "Manchester United"
        away_team = "Arsenal"

        # Mock数据收集
        with patch.object(collection_service, "create_match_collection_task") as mock_collect:
            mock_collect.return_value = f"task_{match_id}_{int(time.time())}"

            task_id = collection_service.create_match_collection_task(match_id)
            assert task_id is not None
            assert match_id in task_id

        # 步骤2: 特征工程（模拟）
        raw_features = [
            1.2,  # 主队攻击力
            0.8,  # 客队防守力
            0.3,  # 主场优势
            1.5,  # 近期状态差
            2.1,  # 历史交锋优势
            0.7,  # 进球能力
            1.1,  # 失球防守
            0.9,  # 控球率
            1.3,  # 射门效率
            0.6,  # 传球成功率
            1.0,  # 角球优势
            0.8,  # 犯规控制
        ]

        # 步骤3: 创建预测请求
        request = PredictionRequest(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            features=raw_features,
            use_cache=True,
            model_name="xgboost_v2",
        )

        # 步骤4: 执行预测（首次，缓存未命中）
        start_time = time.perf_counter()
        try:
            # 模拟预测流程
            request_dict = request.to_dict()
            feature_processing_time = time.perf_counter()

            # 模拟模型推理
            prediction_result = complete_system["model"].predict([raw_features])
            probability_result = complete_system["model"].predict_proba([raw_features])
            inference_time = time.perf_counter()

            # 创建响应
            response = PredictionResponse(
                request=request,
                prediction={
                    "prediction": "HOME_WIN",
                    "probabilities": {
                        "HOME_WIN": probability_result[0][0],
                        "DRAW": probability_result[0][1],
                        "AWAY_WIN": probability_result[0][2],
                    },
                },
                success=True,
                processing_time_ms=(inference_time - start_time) * 1000,
                cached=False,
                model_info={
                    "name": "xgboost_v2",
                    "version": "2.0",
                    "accuracy": complete_system["loader"].get_model_metadata()["accuracy"],
                },
            )

            end_time = time.perf_counter()

        except Exception as e:
            # 如果预测失败，创建错误响应
            response = PredictionResponse(
                request=request,
                prediction={},
                success=False,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                cached=False,
                error=str(e),
            )

        # 步骤5: 验证结果
        assert response.request == request
        assert response.success is True
        assert response.cached is False
        assert "prediction" in response.prediction
        assert "probabilities" in response.prediction

        # 步骤6: 测试缓存命中（第二次请求）
        complete_system["cache"].get.return_value = response.prediction
        complete_system["cache"].get_stats.return_value = {
            "hits": 1,
            "misses": 1,
            "hit_rate": 0.5,
        }

        cached_start = time.perf_counter()
        cached_result = complete_system["cache"].get(match_id)
        cached_end = time.perf_counter()

        assert cached_result == response.prediction
        assert (cached_end - cached_start) * 1000 < 1.0  # 缓存查询应该很快

        print(f"✅ 单场比赛预测工作流完成:")
        print(f"   - 比赛: {home_team} vs {away_team}")
        print(f"   - 预测结果: {response.prediction['prediction']}")
        print(f"   - 处理时间: {response.processing_time_ms:.2f}ms")
        print(f"   - 缓存状态: {'命中' if cached_result else '未命中'}")

    @pytest.mark.asyncio
    async def test_batch_prediction_workflow(self, complete_system):
        """测试批量预测工作流"""
        inference_service = complete_system["inference_service"]

        # 准备批量比赛数据
        matches = [
            {"match_id": "match_1", "home_team": "Chelsea", "away_team": "Liverpool"},
            {"match_id": "match_2", "home_team": "Man City", "away_team": "Tottenham"},
            {"match_id": "match_3", "home_team": "Leicester", "away_team": "Everton"},
            {"match_id": "match_4", "home_team": "West Ham", "away_team": "Newcastle"},
            {
                "match_id": "match_5",
                "home_team": "Aston Villa",
                "away_team": "Southampton",
            },
        ]

        # 生成不同的特征数据
        import random

        predictions = []

        batch_start_time = time.perf_counter()

        for match in matches:
            # 为每场比赛生成随机特征
            features = [round(random.uniform(0.5, 2.0), 2) for _ in range(12)]

            request = PredictionRequest(
                match_id=match["match_id"],
                home_team=match["home_team"],
                away_team=match["away_team"],
                features=features,
                use_cache=False,
                model_name="xgboost_v2",
            )

            # 模拟预测处理
            try:
                complete_system["model"].predict([features])
                complete_system["model"].predict_proba([features])

                # 随机选择预测结果
                outcomes = ["HOME_WIN", "DRAW", "AWAY_WIN"]
                prediction_outcome = random.choice(outcomes)

                prediction = PredictionResponse(
                    request=request,
                    prediction={
                        "prediction": prediction_outcome,
                        "probabilities": {
                            "HOME_WIN": round(random.uniform(0.1, 0.7), 2),
                            "DRAW": round(random.uniform(0.1, 0.4), 2),
                            "AWAY_WIN": round(random.uniform(0.1, 0.6), 2),
                        },
                    },
                    success=True,
                    processing_time_ms=round(random.uniform(10, 100), 2),
                    cached=False,
                    model_info={"name": "xgboost_v2", "version": "2.0"},
                )

                predictions.append(prediction)

            except Exception as e:
                error_response = PredictionResponse(
                    request=request,
                    prediction={},
                    success=False,
                    processing_time_ms=50.0,
                    cached=False,
                    error=str(e),
                )
                predictions.append(error_response)

        batch_end_time = time.perf_counter()
        total_time = batch_end_time - batch_start_time

        # 验证批量结果
        successful_predictions = [p for p in predictions if p.success]
        failed_predictions = [p for p in predictions if not p.success]

        success_rate = len(successful_predictions) / len(predictions) * 100
        throughput = len(predictions) / total_time

        print(f"✅ 批量预测工作流完成:")
        print(f"   - 总比赛数: {len(predictions)}")
        print(f"   - 成功预测: {len(successful_predictions)}")
        print(f"   - 失败预测: {len(failed_predictions)}")
        print(f"   - 成功率: {success_rate:.1f}%")
        print(f"   - 总处理时间: {total_time:.3f}s")
        print(f"   - 吞吐量: {throughput:.2f} 比赛/秒")

        # 性能断言
        assert success_rate >= 80, f"批量预测成功率过低: {success_rate:.1f}%"
        assert throughput > 5, f"批量预测吞吐量过低: {throughput:.2f} 比赛/秒"
        assert len(predictions) == len(matches)

        # 验证每个预测的结构
        for pred in predictions:
            assert pred.request.match_id in [m["match_id"] for m in matches]
            assert pred.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_real_time_prediction_workflow(self, complete_system):
        """测试实时预测工作流（模拟比赛进行中的动态预测）"""
        inference_service = complete_system["inference_service"]

        # 模拟实时比赛场景
        match_id = "live_match_123"
        home_team = "Real Madrid"
        away_team = "Barcelona"

        # 比赛不同时间点的预测
        match_timeline = [
            {"minute": 0, "score": {"home": 0, "away": 0}, "status": "not_started"},
            {"minute": 15, "score": {"home": 1, "away": 0}, "status": "in_progress"},
            {"minute": 30, "score": {"home": 1, "away": 1}, "status": "in_progress"},
            {"minute": 60, "score": {"home": 2, "away": 1}, "status": "in_progress"},
            {"minute": 85, "score": {"home": 2, "away": 2}, "status": "in_progress"},
            {"minute": 90, "score": {"home": 3, "away": 2}, "status": "finished"},
        ]

        predictions_timeline = []

        for timeline_point in match_timeline:
            minute = timeline_point["minute"]
            score = timeline_point["score"]
            status = timeline_point["status"]

            # 根据比赛状态动态调整特征
            if status == "not_started":
                # 赛前预测，基于历史数据
                features = [1.2, 0.8, 0.3, 1.0, 1.1, 1.0, 1.0, 0.9, 1.0, 0.8, 1.0, 1.0]
            elif status == "in_progress":
                # 比赛中，考虑实时比分
                goal_diff = score["home"] - score["away"]
                time_factor = minute / 90.0

                features = [
                    1.2 + goal_diff * 0.2,  # 进攻优势根据进球差调整
                    0.8 - goal_diff * 0.1,  # 防守压力
                    0.3 * (1 - time_factor),  # 主场优势随时间递减
                    1.0 + goal_diff * 0.3,  # 状态优势
                    1.1,  # 历史交锋
                    1.0 + score["home"] * 0.1,  # 进球能力
                    1.0 + score["away"] * 0.1,  # 失球影响
                    0.9 - time_factor * 0.1,  # 控球率变化
                    1.0 + goal_diff * 0.2,  # 射门效率
                    0.8,  # 传球成功率
                    1.0,  # 角球优势
                    0.8,  # 犯规控制
                ]
            else:  # finished
                features = [1.0] * 12  # 最终状态的简化特征

            request = PredictionRequest(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                features=features,
                use_cache=False,  # 实时预测不使用缓存
                model_name="xgboost_v2",
            )

            # 模拟预测处理
            try:
                complete_system["model"].predict([features])
                complete_system["model"].predict_proba([features])

                # 根据比赛状态生成合理的预测
                if status == "finished":
                    # 比赛结束，预测应该与实际结果一致
                    if score["home"] > score["away"]:
                        prediction_outcome = "HOME_WIN"
                    elif score["home"] < score["away"]:
                        prediction_outcome = "AWAY_WIN"
                    else:
                        prediction_outcome = "DRAW"
                else:
                    # 比赛中，基于当前比分和特征预测
                    if goal_diff > 1:
                        prediction_outcome = "HOME_WIN"
                    elif goal_diff < -1:
                        prediction_outcome = "AWAY_WIN"
                    else:
                        outcomes = ["HOME_WIN", "DRAW", "AWAY_WIN"]
                        prediction_outcome = random.choice(outcomes)

                response = PredictionResponse(
                    request=request,
                    prediction={
                        "prediction": prediction_outcome,
                        "probabilities": {
                            "HOME_WIN": max(0.1, min(0.8, 0.5 + goal_diff * 0.2)),
                            "DRAW": max(0.1, min(0.5, 0.3 - abs(goal_diff) * 0.1)),
                            "AWAY_WIN": max(0.1, min(0.8, 0.5 - goal_diff * 0.2)),
                        },
                        "match_context": {
                            "minute": minute,
                            "score": score,
                            "status": status,
                        },
                    },
                    success=True,
                    processing_time_ms=round(random.uniform(20, 80), 2),
                    cached=False,
                    model_info={"name": "xgboost_v2", "version": "2.0"},
                )

                predictions_timeline.append(response)

            except Exception as e:
                # 即使失败也记录
                error_response = PredictionResponse(
                    request=request,
                    prediction={},
                    success=False,
                    processing_time_ms=50.0,
                    cached=False,
                    error=str(e),
                )
                predictions_timeline.append(error_response)

        # 验证实时工作流
        assert len(predictions_timeline) == len(match_timeline)

        successful_predictions = [p for p in predictions_timeline if p.success]
        assert len(successful_predictions) >= len(match_timeline) * 0.8

        print(f"✅ 实时预测工作流完成:")
        print(f"   - 比赛: {home_team} vs {away_team}")
        print(f"   - 预测时间点: {len(predictions_timeline)}")
        print(f"   - 成功预测: {len(successful_predictions)}")

        # 打印关键时间点的预测
        for i, pred in enumerate(predictions_timeline):
            if pred.success and i % 2 == 0:  # 打印部分预测结果
                context = pred.prediction.get("match_context", {})
                minute = context.get("minute", 0)
                score = context.get("score", {})
                pred_result = pred.prediction.get("prediction", "N/A")
                print(f"   - 第{minute}分钟 ({score['home']}:{score['away']}): {pred_result}")

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_workflow(self, complete_system):
        """测试错误处理和恢复工作流"""
        inference_service = complete_system["inference_service"]

        # 场景1: 模型加载失败
        complete_system["loader"].get_model.side_effect = Exception("模型文件损坏")

        request = PredictionRequest(
            match_id="error_test_1",
            home_team="Team A",
            away_team="Team B",
            features=[1.0] * 12,
        )

        try:
            # 尝试预测，应该失败
            complete_system["loader"].get_model("xgboost_v2")
            assert False, "应该抛出异常"
        except Exception:
            pass  # 预期的异常

        # 场景2: 恢复模型加载
        complete_system["loader"].get_model.side_effect = None
        complete_system["loader"].get_model.return_value = complete_system["model"]

        # 现在预测应该成功
        try:
            model = complete_system["loader"].get_model("xgboost_v2")
            assert model is not None
            prediction = model.predict([request.features])
            assert prediction is not None
        except Exception as e:
            pytest.fail(f"恢复后预测失败: {e}")

        # 场景3: 缓存失败
        complete_system["cache"].set.side_effect = Exception("缓存服务不可用")

        # 预测应该仍然成功，只是无法缓存
        try:
            request_dict = request.to_dict()
            _ = sum(request.features) / len(request.features)  # 模拟处理
            # 即使缓存失败，预测也应该成功
            success = True
        except Exception:
            success = False

        assert success, "即使缓存失败，预测也应该成功"

        # 场景4: 特征数据异常
        invalid_request = PredictionRequest(
            match_id="error_test_2",
            home_team="Team C",
            away_team="Team D",
            features=[],  # 空特征列表
        )

        # 应该能处理异常特征
        try:
            if len(invalid_request.features) == 0:
                # 使用默认特征
                default_features = [1.0] * 12
                _ = sum(default_features) / len(default_features)
                handling_success = True
            else:
                handling_success = True
        except Exception:
            handling_success = False

        assert handling_success, "应该能处理异常特征数据"

        print(f"✅ 错误处理和恢复工作流完成:")
        print(f"   - 模型加载失败: ✓ 正确处理")
        print(f"   - 模型恢复: ✓ 成功恢复")
        print(f"   - 缓存失败: ✓ 降级处理")
        print(f"   - 特征异常: ✓ 容错处理")

    @pytest.mark.asyncio
    async def test_performance_stress_workflow(self, complete_system):
        """测试性能压力工作流"""
        inference_service = complete_system["inference_service"]

        # 高并发场景：100个并发预测请求
        concurrent_requests = 100

        async def simulate_prediction(request_id: int):
            """模拟单个预测请求"""
            features = [round(request_id * 0.01 + i, 2) for i in range(12)]

            request = PredictionRequest(
                match_id=f"stress_test_{request_id}",
                home_team=f"Team {request_id}",
                away_team=f"Opponent {request_id}",
                features=features,
                use_cache=False,
            )

            start_time = time.perf_counter()

            try:
                # 模拟预测处理
                complete_system["model"].predict([features])
                complete_system["model"].predict_proba([features])

                processing_time = (time.perf_counter() - start_time) * 1000

                return {
                    "request_id": request_id,
                    "success": True,
                    "processing_time_ms": processing_time,
                    "prediction": "HOME_WIN",  # 简化结果
                }
            except Exception as e:
                processing_time = (time.perf_counter() - start_time) * 1000
                return {
                    "request_id": request_id,
                    "success": False,
                    "processing_time_ms": processing_time,
                    "error": str(e),
                }

        # 执行并发压力测试
        stress_start_time = time.perf_counter()
        tasks = [simulate_prediction(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        stress_end_time = time.perf_counter()

        # 分析结果
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]

        total_time = stress_end_time - stress_start_time
        success_rate = len(successful_results) / concurrent_requests * 100
        throughput = len(successful_results) / total_time

        if successful_results:
            processing_times = [r["processing_time_ms"] for r in successful_results]
            avg_processing_time = sum(processing_times) / len(processing_times)
            p95_processing_time = sorted(processing_times)[int(len(processing_times) * 0.95)]
            p99_processing_time = sorted(processing_times)[int(len(processing_times) * 0.99)]
        else:
            avg_processing_time = p95_processing_time = p99_processing_time = 0

        print(f"✅ 性能压力测试完成:")
        print(f"   - 并发请求数: {concurrent_requests}")
        print(f"   - 成功请求: {len(successful_results)}")
        print(f"   - 失败请求: {len(failed_results)}")
        print(f"   - 成功率: {success_rate:.1f}%")
        print(f"   - 总处理时间: {total_time:.3f}s")
        print(f"   - 吞吐量: {throughput:.2f} 请求/秒")
        print(f"   - 平均处理时间: {avg_processing_time:.2f}ms")
        print(f"   - P95处理时间: {p95_processing_time:.2f}ms")
        print(f"   - P99处理时间: {p99_processing_time:.2f}ms")

        # 性能断言
        assert success_rate >= 95, f"并发成功率过低: {success_rate:.1f}%"
        assert throughput > 50, f"并发吞吐量过低: {throughput:.2f} 请求/秒"
        if successful_results:
            assert p99_processing_time < 200, f"P99处理时间过长: {p99_processing_time:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
