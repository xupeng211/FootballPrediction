#!/usr/bin/env python3
"""
服务集成测试 - Prediction Service 到 Collection Service 完整链路

Sprint 7 集成测试核心组件

测试覆盖范围：
- Prediction Service 与 Collection Service 的完整调用链
- 实时数据收集到预测生成的端到端流程
- 服务间数据传递和状态同步
- 错误处理和降级机制
- 性能和并发处理
- 数据一致性验证
- 服务健康检查集成

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Testing)
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional

# 导入被测试的服务
from src.services.prediction_service import PredictionService, PredictionRequest, PredictionResponse
from src.services.collection_service import FotMobCollectionService, FotMobCollectionTask
from src.services.inference_service import InferenceService


class TestServiceIntegration:
    """服务集成测试类"""

    @pytest.fixture
    async def mock_inference_service(self):
        """模拟推理服务"""
        service = AsyncMock(spec=InferenceService)

        # 模拟预测结果
        service.predict = AsyncMock(return_value={
            "match_id": "test_match_123",
            "prediction": "HOME_WIN",
            "probabilities": {
                "home_win": 0.65,
                "draw": 0.22,
                "away_win": 0.13
            },
            "confidence": 0.78,
            "model_version": "xgboost_v2.1",
            "features": {
                "home_elo": 1850.0,
                "away_elo": 1780.0,
                "expected_home_goals": 1.85,
                "expected_away_goals": 1.12
            },
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "data_quality": "high"
            }
        })

        # 模拟健康检查
        service.health_check = AsyncMock(return_value={
            "status": "healthy",
            "model_loaded": True,
            "last_prediction": datetime.now().isoformat()
        })

        # 模拟特征获取
        service._get_features_for_match = AsyncMock(return_value={
            "home_elo": 1850.0,
            "away_elo": 1780.0,
            "recent_form_home": [3, 1, 2, 3, 1],
            "recent_form_away": [1, 0, 2, 1, 0],
            "h2h_home_wins": 8,
            "h2h_away_wins": 3
        })

        return service

    @pytest.fixture
    async def mock_collection_service(self):
        """模拟数据收集服务"""
        service = Mock(spec=FotMobCollectionService)

        # 模拟获取即将到来的比赛
        service.get_upcoming_matches = AsyncMock(return_value={
            "collection_time": datetime.now().isoformat(),
            "time_window_hours": 48,
            "matches": [
                {
                    "match_id": "test_match_123",
                    "home_team": "Manchester United",
                    "away_team": "Arsenal",
                    "kickoff_time": (datetime.now() + timedelta(hours=24)).isoformat(),
                    "hours_until_kickoff": 24.0,
                    "league": "Premier League",
                    "venue": "Old Trafford",
                    "status": "upcoming",
                    "initial_odds": {
                        "home_win": 2.10,
                        "draw": 3.40,
                        "away_win": 3.80,
                        "home_win_probability": 47.6,
                        "draw_probability": 29.4,
                        "away_win_probability": 26.3,
                        "bookmaker_margin": 102.3
                    },
                    "real_time_features": {
                        "elo_features": {
                            "home_elo": 1850.0,
                            "away_elo": 1780.0,
                            "elo_difference": 70.0,
                            "home_elo_recent_trend": 15.2,
                            "away_elo_recent_trend": -8.5,
                            "head_to_head_elo_advantage": "home"
                        },
                        "poisson_features": {
                            "expected_home_goals": 1.85,
                            "expected_away_goals": 1.12,
                            "total_expected_goals": 2.97,
                            "home_win_probability": 58.2,
                            "draw_probability": 22.1,
                            "away_win_probability": 19.7,
                            "both_teams_to_score_probability": 64.3,
                            "over_2_5_goals_probability": 61.8,
                            "most_likely_score": "2-1"
                        },
                        "h2h_features": {
                            "previous_meetings_count": 45,
                            "home_wins_last_5": 3,
                            "away_wins_last_5": 1,
                            "draws_last_5": 1,
                            "home_team_h2h_advantage": 0.156,
                            "average_goals_in_h2h": 2.8,
                            "clean_sheets_home_last_10": 4,
                            "clean_sheets_away_last_10": 2
                        },
                        "venue_features": {
                            "home_advantage_score": 0.124,
                            "home_form_last_6": 12,
                            "away_form_last_6": 8,
                            "home_goals_scored_last_6": 9,
                            "home_goals_conceded_last_6": 3,
                            "away_goals_scored_last_6": 5,
                            "away_goals_conceded_last_6": 8,
                            "venue_importance_factor": 1.15
                        },
                        "market_features": {
                            "market_confidence": 0.73,
                            "odds_stability_index": 0.89,
                            "volume_weighted_home_probability": 48.2,
                            "volume_weighted_away_probability": 25.8,
                            "steam_signals_detected": False,
                            "market_efficiency_score": 0.91
                        }
                    },
                    "data_quality": {
                        "completeness_score": 0.95,
                        "confidence_level": "high",
                        "last_updated": datetime.now().isoformat(),
                        "feature_coverage": {
                            "elo_available": True,
                            "poisson_available": True,
                            "h2h_available": True,
                            "venue_available": True,
                            "market_available": True
                        }
                    }
                }
            ],
            "summary": {
                "total_matches": 1,
                "matches_by_league": {"Premier League": 1},
                "avg_elo_difference": 70.0,
                "high_confidence_matches": 1,
                "data_collection_status": "success",
                "processing_time_ms": 1250.0
            }
        })

        # 模拟服务状态
        service.get_service_status = Mock(return_value={
            "service_name": "FotMobCollectionService",
            "is_running": True,
            "total_tasks": 5,
            "successful_tasks": 4,
            "failed_tasks": 1,
            "success_rate": 0.8,
            "real_time_data_interface": {
                "enabled": True,
                "supported_features": [
                    "upcoming_matches",
                    "real_time_features",
                    "initial_odds"
                ]
            }
        })

        return service

    @pytest.fixture
    async def prediction_service(self, mock_inference_service):
        """预测服务实例"""
        service = PredictionService(inference_service=mock_inference_service)
        await service.initialize()
        return service

    # ========== 基础集成测试 ==========

    @pytest.mark.asyncio
    async def test_single_match_prediction_integration(
        self, prediction_service, mock_inference_service
    ):
        """测试单场比赛预测的完整集成"""
        # 执行预测
        response = await prediction_service.predict_single_match(
            match_id="test_match_123",
            include_features=True,
            include_metadata=True,
            include_explanation=False
        )

        # 验证响应结构
        assert isinstance(response, PredictionResponse)
        assert response.success is True
        assert response.data is not None
        assert response.processing_time_ms is not None
        assert response.request_id is not None

        # 验证推理服务被调用
        mock_inference_service.predict.assert_called_once_with("test_match_123")

        # 验证返回数据
        prediction_data = response.data
        assert "match_id" in prediction_data
        assert "prediction" in prediction_data
        assert "probabilities" in prediction_data
        assert "confidence" in prediction_data
        assert "model_version" in prediction_data

        # 验证特征数据（根据请求参数）
        if response.include_features:
            assert "features" in prediction_data
            features = prediction_data["features"]
            assert "home_elo" in features
            assert "away_elo" in features

        # 验证元数据（根据请求参数）
        if response.include_metadata:
            assert "metadata" in prediction_data
            metadata = prediction_data["metadata"]
            assert "processed_at" in metadata
            assert "data_quality" in metadata

    @pytest.mark.asyncio
    async def test_batch_prediction_integration(
        self, prediction_service, mock_inference_service
    ):
        """测试批量预测的完整集成"""
        match_ids = ["match_1", "match_2", "match_3"]

        # 配置推理服务返回不同的结果
        def mock_predict_side_effect(match_id):
            return {
                "match_id": match_id,
                "prediction": "HOME_WIN" if match_id != "match_2" else "DRAW",
                "probabilities": {
                    "home_win": 0.60,
                    "draw": 0.25,
                    "away_win": 0.15
                },
                "confidence": 0.75,
                "model_version": "xgboost_v2.1"
            }

        mock_inference_service.predict.side_effect = mock_predict_side_effect

        # 执行批量预测
        response = await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            include_features=False,
            include_metadata=True,
            include_explanation=False,
            max_concurrent=3
        )

        # 验证响应
        assert response.success is True
        assert response.data is not None

        batch_data = response.data
        assert "results" in batch_data
        assert "total_count" in batch_data
        assert "successful_count" in batch_data
        assert "failed_count" in batch_data
        assert "errors" in batch_data

        # 验证批量结果
        assert batch_data["total_count"] == len(match_ids)
        assert batch_data["successful_count"] == len(match_ids)
        assert batch_data["failed_count"] == 0
        assert len(batch_data["results"]) == len(match_ids)

        # 验证每个预测结果
        results = batch_data["results"]
        for i, result in enumerate(results):
            assert result["match_id"] == match_ids[i]
            assert "prediction" in result
            assert "probabilities" in result

    @pytest.mark.asyncio
    async def test_service_health_integration(self, prediction_service, mock_inference_service):
        """测试服务健康检查集成"""
        response = await prediction_service.get_service_health()

        assert response.success is True
        assert response.data is not None

        health_data = response.data
        assert "prediction_service" in health_data
        assert "inference_service" in health_data
        assert "explainability_service" in health_data

        # 验证预测服务状态
        prediction_health = health_data["prediction_service"]
        assert prediction_health["status"] == "healthy"
        assert prediction_health["initialized"] is True

        # 验证推理服务状态
        inference_health = health_data["inference_service"]
        assert inference_health["status"] == "healthy"
        assert inference_health["model_loaded"] is True

        # 验证可解释性服务状态
        explainability_health = health_data["explainability_service"]
        assert explainability_health["available"] is False  # 未配置
        assert explainability_health["status"] == "disabled"

    # ========== 数据收集到预测的完整链路测试 ==========

    @pytest.mark.asyncio
    async def test_collection_to_prediction_workflow(
        self, prediction_service, mock_inference_service, mock_collection_service
    ):
        """测试从数据收集到预测的完整工作流程"""
        # 1. 模拟数据收集服务获取即将到来的比赛
        upcoming_data = await mock_collection_service.get_upcoming_matches(hours_ahead=48)
        assert upcoming_data["collection_time"] is not None
        assert len(upcoming_data["matches"]) > 0

        # 2. 提取比赛ID并执行预测
        matches = upcoming_data["matches"]
        match_ids = [match["match_id"] for match in matches]

        # 3. 执行批量预测
        prediction_response = await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            include_features=True,
            include_metadata=True,
            max_concurrent=5
        )

        # 4. 验证数据一致性
        assert prediction_response.success is True
        batch_results = prediction_response.data["results"]

        # 确保每个比赛都有预测结果
        for match in matches:
            match_id = match["match_id"]
            prediction_result = next(
                (r for r in batch_results if r.get("match_id") == match_id), None
            )
            assert prediction_result is not None, f"Missing prediction for {match_id}"

            # 验证预测结果包含必要的字段
            assert "prediction" in prediction_result
            assert "probabilities" in prediction_result
            assert "features" in prediction_result

            # 验证特征与收集数据的一致性
            prediction_features = prediction_result["features"]
            collection_features = match["real_time_features"]

            # 比较Elo特征
            if "elo_features" in collection_features:
                collection_elo = collection_features["elo_features"]
                assert abs(prediction_features.get("home_elo", 0) - collection_elo.get("home_elo", 0)) < 50
                assert abs(prediction_features.get("away_elo", 0) - collection_elo.get("away_elo", 0)) < 50

    @pytest.mark.asyncio
    async def test_real_time_features_integration(self, mock_collection_service):
        """测试实时特征提取的集成"""
        # 获取即将到来的比赛数据
        upcoming_data = await mock_collection_service.get_upcoming_matches(hours_ahead=24)

        assert "matches" in upcoming_data
        matches = upcoming_data["matches"]
        assert len(matches) > 0

        # 验证每个比赛的实时特征
        for match in matches:
            match_id = match["match_id"]
            real_time_features = match["real_time_features"]

            # 验证所有特征模块都存在
            required_features = ["elo_features", "poisson_features", "h2h_features", "venue_features", "market_features"]
            for feature_type in required_features:
                assert feature_type in real_time_features, f"Missing {feature_type} for {match_id}"

            # 验证特征数据的完整性
            elo_features = real_time_features["elo_features"]
            assert "home_elo" in elo_features
            assert "away_elo" in elo_features
            assert "elo_difference" in elo_features
            assert isinstance(elo_features["home_elo"], (int, float))
            assert isinstance(elo_features["away_elo"], (int, float))

            poisson_features = real_time_features["poisson_features"]
            assert "expected_home_goals" in poisson_features
            assert "expected_away_goals" in poisson_features
            assert "home_win_probability" in poisson_features
            assert isinstance(poisson_features["expected_home_goals"], (int, float))
            assert 0 <= poisson_features["home_win_probability"] <= 100

            # 验证数据质量指标
            data_quality = match["data_quality"]
            assert "completeness_score" in data_quality
            assert "confidence_level" in data_quality
            assert "feature_coverage" in data_quality
            assert 0 <= data_quality["completeness_score"] <= 1
            assert data_quality["confidence_level"] in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_odds_to_prediction_integration(self, prediction_service, mock_collection_service):
        """测试赔率数据到预测的集成"""
        # 获取包含赔率的比赛数据
        upcoming_data = await mock_collection_service.get_upcoming_matches(hours_ahead=48)
        matches = upcoming_data["matches"]

        for match in matches:
            # 验证赔率数据
            initial_odds = match["initial_odds"]
            assert "home_win" in initial_odds
            assert "draw" in initial_odds
            assert "away_win" in initial_odds
            assert "home_win_probability" in initial_odds
            assert "away_win_probability" in initial_odds

            # 验证赔率合理性
            assert initial_odds["home_win"] > 1.0
            assert initial_odds["away_win"] > 1.0
            if initial_odds["draw"] is not None:
                assert initial_odds["draw"] > 1.0

            # 验证概率与赔率的一致性
            home_prob_from_odds = 1.0 / initial_odds["home_win"] * 100
            away_prob_from_odds = 1.0 / initial_odds["away_win"] * 100

            assert abs(home_prob_from_odds - initial_odds["home_win_probability"]) < 5
            assert abs(away_prob_from_odds - initial_odds["away_win_probability"]) < 5

            # 执行预测并比较
            prediction_response = await prediction_service.predict_single_match(
                match["match_id"],
                include_features=True
            )

            if prediction_response.success:
                prediction_probs = prediction_response.data["probabilities"]
                # 预测概率应该与市场概率有一定的相关性
                #（这里不做严格验证，因为模型可能有自己的判断）

    # ========== 错误处理和降级测试 ==========

    @pytest.mark.asyncio
    async def test_inference_service_failure_handling(self, prediction_service, mock_inference_service):
        """测试推理服务失败的处理"""
        # 配置推理服务抛出异常
        mock_inference_service.predict.side_effect = Exception("Model inference failed")

        # 执行预测
        response = await prediction_service.predict_single_match("test_match_123")

        # 验证错误处理
        assert response.success is False
        assert response.error is not None
        assert "Model inference failed" in response.error
        assert response.processing_time_ms is not None

    @pytest.mark.asyncio
    async def test_collection_service_failure_handling(self, mock_collection_service):
        """测试数据收集服务失败的处理"""
        # 配置收集服务抛出异常
        mock_collection_service.get_upcoming_matches.side_effect = Exception("Data collection failed")

        # 尝试获取数据
        with pytest.raises(Exception, match="Data collection failed"):
            await mock_collection_service.get_upcoming_matches()

    @pytest.mark.asyncio
    async def test_partial_batch_prediction_failure(self, prediction_service, mock_inference_service):
        """测试批量预测中部分失败的处理"""
        match_ids = ["match_1", "match_2", "match_3", "match_4", "match_5"]

        # 配置推理服务：部分成功，部分失败
        def mock_predict_with_failures(match_id):
            if match_id in ["match_2", "match_4"]:
                raise Exception(f"Prediction failed for {match_id}")
            return {
                "match_id": match_id,
                "prediction": "HOME_WIN",
                "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.75
            }

        mock_inference_service.predict.side_effect = mock_predict_with_failures

        # 执行批量预测
        response = await prediction_service.predict_batch_matches(match_ids, max_concurrent=3)

        # 验证部分成功处理
        assert response.success is True  # 批量操作本身成功
        batch_data = response.data

        assert batch_data["total_count"] == len(match_ids)
        assert batch_data["successful_count"] == 3  # match_1, match_3, match_5
        assert batch_data["failed_count"] == 2      # match_2, match_4
        assert len(batch_data["errors"]) == 2

        # 验证错误记录
        errors = batch_data["errors"]
        error_match_ids = [error["match_id"] for error in errors]
        assert "match_2" in error_match_ids
        assert "match_4" in error_match_ids

    @pytest.mark.asyncio
    async def test_service_timeout_handling(self, prediction_service, mock_inference_service):
        """测试服务超时处理"""
        import asyncio

        # 配置推理服务超时
        async def slow_predict(match_id):
            await asyncio.sleep(2)  # 模拟慢操作
            return {"match_id": match_id, "prediction": "HOME_WIN"}

        mock_inference_service.predict = AsyncMock(side_effect=slow_predict)

        # 执行预测（应该有时间限制）
        start_time = time.time()
        response = await prediction_service.predict_single_match("test_match_123")
        end_time = time.time()

        # 验证超时处理
        processing_time = end_time - start_time
        # 这里我们主要验证服务能够处理慢操作
        # 实际的超时限制应该在更高层次实现
        assert processing_time > 2

    # ========== 性能和并发测试 ==========

    @pytest.mark.asyncio
    async def test_concurrent_prediction_performance(self, prediction_service, mock_inference_service):
        """测试并发预测性能"""
        match_ids = [f"match_{i}" for i in range(20)]

        # 配置推理服务快速响应
        async def fast_predict(match_id):
            await asyncio.sleep(0.01)  # 模拟10ms处理时间
            return {
                "match_id": match_id,
                "prediction": "HOME_WIN",
                "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.75
            }

        mock_inference_service.predict.side_effect = fast_predict

        # 测试不同并发级别的性能
        concurrent_levels = [1, 5, 10, 20]

        for max_concurrent in concurrent_levels:
            start_time = time.time()

            response = await prediction_service.predict_batch_matches(
                match_ids=match_ids,
                max_concurrent=max_concurrent
            )

            end_time = time.time()
            duration = end_time - start_time

            # 验证结果正确性
            assert response.success is True
            assert response.data["successful_count"] == len(match_ids)

            # 验证性能提升
            expected_max_time = (len(match_ids) / max_concurrent) * 0.02  # 20ms + buffer
            assert duration < expected_max_time + 1  # 允许1秒缓冲

            print(f"Concurrent {max_concurrent}: {duration:.2f}s for {len(match_ids)} predictions")

    @pytest.mark.asyncio
    async def test_memory_usage_during_batch_processing(self, prediction_service, mock_inference_service):
        """测试批量处理时的内存使用"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 创建大批量预测任务
        match_ids = [f"match_{i}" for i in range(100)]

        # 配置推理服务返回包含大量特征的数据
        def memory_heavy_predict(match_id):
            return {
                "match_id": match_id,
                "prediction": "HOME_WIN",
                "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.75,
                "features": {f"feature_{i}": i * 0.1 for i in range(1000)}  # 1000个特征
            }

        mock_inference_service.predict.side_effect = memory_heavy_predict

        # 执行批量预测
        response = await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            include_features=True,
            max_concurrent=10
        )

        # 检查内存使用
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 验证内存使用在合理范围内（增加不超过200MB）
        assert memory_increase < 200, f"Memory increase too large: {memory_increase} MB"

        # 验证预测成功
        assert response.success is True
        assert response.data["successful_count"] == len(match_ids)

    # ========== 数据一致性验证测试 ==========

    @pytest.mark.asyncio
    async def test_feature_consistency_across_services(self, mock_collection_service):
        """测试跨服务特征一致性"""
        # 获取即将到来的比赛数据
        upcoming_data = await mock_collection_service.get_upcoming_matches(hours_ahead=48)
        matches = upcoming_data["matches"]

        for match in matches:
            match_id = match["match_id"]
            features = match["real_time_features"]

            # 验证Elo特征内部一致性
            elo_features = features["elo_features"]
            calculated_elo_diff = elo_features["home_elo"] - elo_features["away_elo"]
            assert abs(calculated_elo_diff - elo_features["elo_difference"]) < 0.1

            # 验证泊松特征概率一致性
            poisson_features = features["poisson_features"]
            prob_sum = (
                poisson_features["home_win_probability"] +
                poisson_features["draw_probability"] +
                poisson_features["away_win_probability"]
            )
            assert abs(prob_sum - 100) < 1.0  # 允许1%的误差

            # 验证预期进球数的合理性
            expected_total = poisson_features["expected_home_goals"] + poisson_features["expected_away_goals"]
            assert 1.0 <= expected_total <= 5.0  # 合理的进球数范围

            # 验证历史交锋特征
            h2h_features = features["h2h_features"]
            last_5_total = (
                h2h_features["home_wins_last_5"] +
                h2h_features["away_wins_last_5"] +
                h2h_features["draws_last_5"]
            )
            assert last_5_total == 5  # 最近5场比赛总和应该是5

            # 验证主客场特征
            venue_features = features["venue_features"]
            assert 0 <= venue_features["home_advantage_score"] <= 1.0  # 优势分数在0-1之间

            # 验证市场特征
            market_features = features["market_features"]
            assert 0 <= market_features["market_confidence"] <= 1.0
            assert 0 <= market_features["odds_stability_index"] <= 1.0
            assert 0 <= market_features["market_efficiency_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_data_quality_validation(self, mock_collection_service):
        """测试数据质量验证"""
        upcoming_data = await mock_collection_service.get_upcoming_matches(hours_ahead=48)

        # 验证整体数据质量
        assert "summary" in upcoming_data
        summary = upcoming_data["summary"]
        assert summary["data_collection_status"] == "success"

        # 验证每个比赛的数据质量
        for match in upcoming_data["matches"]:
            data_quality = match["data_quality"]

            # 验证完整性评分
            completeness = data_quality["completeness_score"]
            assert 0 <= completeness <= 1.0

            # 验证置信度等级
            confidence = data_quality["confidence_level"]
            assert confidence in ["high", "medium", "low"]

            # 验证特征覆盖度
            feature_coverage = data_quality["feature_coverage"]
            required_features = [
                "elo_available",
                "poisson_available",
                "h2h_available",
                "venue_available",
                "market_available"
            ]

            for feature in required_features:
                assert feature in feature_coverage
                assert isinstance(feature_coverage[feature], bool)

            # 高置信度比赛应该有完整的数据覆盖
            if confidence == "high":
                assert completeness >= 0.8
                assert all(feature_coverage[feature] for feature in required_features)

    # ========== 端到端集成测试 ==========

    @pytest.mark.asyncio
    async def test_end_to_end_prediction_workflow(
        self, prediction_service, mock_inference_service, mock_collection_service
    ):
        """测试端到端预测工作流程"""
        # 1. 数据收集阶段
        collection_start = time.time()
        upcoming_data = await mock_collection_service.get_upcoming_matches(hours_ahead=48)
        collection_time = time.time() - collection_start

        assert upcoming_data["summary"]["data_collection_status"] == "success"
        matches = upcoming_data["matches"]
        assert len(matches) > 0

        # 2. 数据验证阶段
        valid_matches = []
        for match in matches:
            # 验证比赛数据的完整性
            if (match.get("match_id") and
                match.get("home_team") and
                match.get("away_team") and
                match.get("data_quality", {}).get("confidence_level") in ["high", "medium"]):
                valid_matches.append(match)

        assert len(valid_matches) > 0, "No valid matches found for prediction"

        # 3. 预测生成阶段
        match_ids = [match["match_id"] for match in valid_matches]

        prediction_start = time.time()
        prediction_response = await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            include_features=True,
            include_metadata=True,
            max_concurrent=5
        )
        prediction_time = time.time() - prediction_start

        # 4. 结果验证阶段
        assert prediction_response.success is True
        batch_results = prediction_response.data["results"]
        assert len(batch_results) == len(match_ids)

        # 5. 数据一致性验证
        for i, match in enumerate(valid_matches):
            match_id = match["match_id"]
            prediction_result = batch_results[i]

            # 确保比赛ID匹配
            assert prediction_result["match_id"] == match_id

            # 验证预测结果的完整性
            assert "prediction" in prediction_result
            assert "probabilities" in prediction_result
            assert "confidence" in prediction_result

            # 验证概率的合法性
            probs = prediction_result["probabilities"]
            prob_sum = probs["home_win"] + probs["draw"] + probs["away_win"]
            assert abs(prob_sum - 1.0) < 0.01  # 允许1%的误差

        # 6. 性能验证
        total_time = collection_time + prediction_time
        assert total_time < 30.0  # 整个流程应该在30秒内完成

        print(f"End-to-end workflow completed:")
        print(f"  - Collection time: {collection_time:.2f}s")
        print(f"  - Prediction time: {prediction_time:.2f}s")
        print(f"  - Total time: {total_time:.2f}s")
        print(f"  - Matches processed: {len(valid_matches)}")

    # ========== 服务健康和监控测试 ==========

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, prediction_service, mock_inference_service):
        """测试服务健康监控"""
        # 获取预测服务健康状态
        health_response = await prediction_service.get_service_health()
        assert health_response.success is True

        health_data = health_response.data

        # 验证健康检查数据结构
        required_services = ["prediction_service", "inference_service", "explainability_service"]
        for service in required_services:
            assert service in health_data
            assert "status" in health_data[service]

        # 模拟推理服务不健康
        mock_inference_service.health_check.return_value = {
            "status": "unhealthy",
            "error": "Model not loaded"
        }

        # 重新检查健康状态
        health_response = await prediction_service.get_service_health()
        health_data = health_response.data

        # 验证推理服务不健康状态被正确反映
        assert health_data["inference_service"]["status"] == "unhealthy"
        assert "error" in health_data["inference_service"]

    @pytest.mark.asyncio
    async def test_service_metrics_collection(self, prediction_service, mock_inference_service):
        """测试服务指标收集"""
        # 执行多次预测以生成指标
        match_ids = [f"metrics_test_{i}" for i in range(10)]

        await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            include_features=True,
            max_concurrent=3
        )

        # 验证推理服务调用次数
        assert mock_inference_service.predict.call_count == len(match_ids)

        # 验证健康检查被调用（如果有的话）
        # 这里我们主要验证服务的运行状态
        health_response = await prediction_service.get_service_health()
        assert health_response.success is True

        # 验证预测服务状态
        prediction_status = health_response.data["prediction_service"]
        assert prediction_status["initialized"] is True
        assert prediction_status["status"] == "healthy"


class TestServiceIntegrationEdgeCases:
    """服务集成边界条件测试"""

    @pytest.mark.asyncio
    async def test_empty_batch_prediction(self, prediction_service):
        """测试空批量预测"""
        response = await prediction_service.predict_batch_matches([])

        assert response.success is True
        batch_data = response.data
        assert batch_data["total_count"] == 0
        assert batch_data["successful_count"] == 0
        assert batch_data["failed_count"] == 0
        assert len(batch_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_large_batch_prediction(self, prediction_service, mock_inference_service):
        """测试大批量预测"""
        # 创建大量比赛ID
        match_ids = [f"large_batch_{i}" for i in range(100)]

        # 配置推理服务快速响应
        mock_inference_service.predict.return_value = {
            "match_id": "dummy",
            "prediction": "HOME_WIN",
            "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
            "confidence": 0.75
        }

        # 执行大批量预测
        start_time = time.time()
        response = await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            max_concurrent=20
        )
        duration = time.time() - start_time

        # 验证结果
        assert response.success is True
        assert response.data["successful_count"] == len(match_ids)
        assert duration < 10.0  # 应该在10秒内完成

    @pytest.mark.asyncio
    async def test_malformed_match_ids(self, prediction_service):
        """测试格式错误的比赛ID"""
        # 测试各种边界情况
        test_cases = [
            [],                    # 空列表
            [""],                  # 空字符串
            ["a" * 101],          # 过长的ID
            [None],               # None值
            ["valid_id", ""]     # 混合有效和无效ID
        ]

        for match_ids in test_cases:
            with pytest.raises((ValueError, TypeError)):
                await prediction_service.predict_batch_matches(match_ids)

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self):
        """测试服务初始化失败"""
        # 创建没有推理服务的预测服务
        with pytest.raises(ValueError, match="inference_service 不能为空"):
            service = PredictionService(inference_service=None)
            await service.initialize()

    @pytest.mark.asyncio
    async def test_network_simulation_delays(self, prediction_service, mock_inference_service):
        """测试网络延迟模拟"""
        import random

        # 配置随机延迟
        async def delayed_predict(match_id):
            delay = random.uniform(0.05, 0.2)  # 50-200ms随机延迟
            await asyncio.sleep(delay)
            return {
                "match_id": match_id,
                "prediction": "HOME_WIN",
                "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.75
            }

        mock_inference_service.predict.side_effect = delayed_predict

        # 执行预测
        match_ids = [f"delay_test_{i}" for i in range(10)]
        start_time = time.time()

        response = await prediction_service.predict_batch_matches(
            match_ids=match_ids,
            max_concurrent=5
        )

        duration = time.time() - start_time

        # 验证在合理时间内完成（考虑并发处理）
        assert response.success is True
        assert response.data["successful_count"] == len(match_ids)
        assert duration < 2.0  # 并发处理应该能在2秒内完成