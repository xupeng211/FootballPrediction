"""
端到端测试 - 预测工作流
测试从数据收集到预测的完整流程
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.e2e
class TestPredictionWorkflow:
    """预测工作流端到端测试"""

    @pytest.fixture
    def mock_services(self):
        """Mock所有依赖服务"""
        services = {
            "match_service": AsyncMock(),
            "prediction_service": AsyncMock(),
            "feature_service": AsyncMock(),
            "cache_manager": MagicMock(),
            "db_session": AsyncMock(),
        }
        return services

    @pytest.mark.asyncio
    async def test_complete_prediction_workflow(self, api_client_full, mock_services):
        """测试完整的预测工作流"""
        # 1. 设置数据
        match_data = {
            "match_id": 12345,
            "home_team_id": 10,
            "away_team_id": 20,
            "match_time": "2025-10-05T15:00:00Z",
            "status": "scheduled",
        }

        # 2. Mock比赛服务响应
        mock_services["match_service"].get_match_by_id.return_value = match_data

        # 3. Mock特征计算
        mock_services["feature_service"].calculate_features.return_value = {
            "match_id": 12345,
            "features": {
                "home_form": [1, 1, 0, 1, 0],
                "away_form": [0, 1, 1, 0, 1],
                "head_to_head": {"home_wins": 3, "away_wins": 2},
                "team_strength": {"home": 85, "away": 78},
            },
        }

        # 4. Mock预测服务
        mock_services["prediction_service"].predict_match.return_value = {
            "match_id": 12345,
            "prediction": "home_win",
            "probabilities": {"home_win": 0.65, "draw": 0.25, "away_win": 0.10},
            "confidence": 0.85,
            "model_version": "2.1",
        }

        # 5. 执行工作流
        with patch(
            "src.services.prediction_workflow.MatchService",
            return_value=mock_services["match_service"],
        ), patch(
            "src.services.prediction_workflow.FeatureService",
            return_value=mock_services["feature_service"],
        ), patch(
            "src.services.prediction_workflow.PredictionService",
            return_value=mock_services["prediction_service"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()
            result = await workflow.run_prediction_workflow(12345)

            # 6. 验证结果
            assert result["match_id"] == 12345
            assert "features" in result
            assert "prediction" in result
            assert result["prediction"]["prediction"] == "home_win"

    @pytest.mark.asyncio
    async def test_batch_prediction_workflow(self, api_client_full, mock_services):
        """测试批量预测工作流"""
        # 准备多场比赛数据
        match_ids = [12345, 12346, 12347]

        # Mock批量特征计算
        mock_services["feature_service"].calculate_batch_features.return_value = {
            "features": [
                {"match_id": 12345, "home_form": [1, 1, 0]},
                {"match_id": 12346, "home_form": [0, 1, 1]},
                {"match_id": 12347, "home_form": [1, 0, 1]},
            ]
        }

        # Mock批量预测
        mock_services["prediction_service"].batch_predict.return_value = {
            "predictions": [
                {"match_id": 12345, "prediction": "home_win"},
                {"match_id": 12346, "prediction": "draw"},
                {"match_id": 12347, "prediction": "away_win"},
            ]
        }

        with patch(
            "src.services.prediction_workflow.FeatureService",
            return_value=mock_services["feature_service"],
        ), patch(
            "src.services.prediction_workflow.PredictionService",
            return_value=mock_services["prediction_service"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()
            results = await workflow.run_batch_predictions(match_ids)

            assert len(results["predictions"]) == 3
            assert all("match_id" in pred for pred in results["predictions"])

    @pytest.mark.asyncio
    async def test_prediction_with_caching(self, api_client_full, mock_services):
        """测试带缓存的预测工作流"""
        # Mock缓存命中
        mock_services["cache_manager"].get.return_value = {
            "match_id": 12345,
            "prediction": "home_win",
            "timestamp": datetime.now().isoformat(),
        }

        # 设置缓存过期时间
        mock_services["cache_manager"].exists.return_value = True

        with patch(
            "src.services.prediction_workflow.get_cache_manager",
            return_value=mock_services["cache_manager"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()
            result = await workflow.get_cached_prediction(12345)

            assert result is not None
            assert result["match_id"] == 12345
            mock_services["cache_manager"].get.assert_called_once()

    @pytest.mark.asyncio
    async def test_prediction_error_handling(self, api_client_full, mock_services):
        """测试预测工作流错误处理"""
        # Mock特征计算失败
        mock_services["feature_service"].calculate_features.side_effect = Exception(
            "Feature calculation failed"
        )

        with patch(
            "src.services.prediction_workflow.FeatureService",
            return_value=mock_services["feature_service"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()

            # 应该优雅地处理错误
            with pytest.raises(Exception) as exc_info:
                await workflow.run_prediction_workflow(12345)

            assert "Feature calculation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_prediction_workflow_with_db_persistence(
        self, api_client_full, mock_services
    ):
        """测试带数据库持久化的预测工作流"""
        # Mock数据库操作
        mock_services["db_session"].execute = AsyncMock()
        mock_services["db_session"].commit = AsyncMock()
        mock_services["db_session"].add = MagicMock()

        # Mock查询结果
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # 预测不存在
        mock_services["db_session"].execute.return_value = mock_result

        prediction_result = {
            "match_id": 12345,
            "prediction": "home_win",
            "probabilities": {"home_win": 0.6, "draw": 0.3, "away_win": 0.1},
            "confidence": 0.75,
        }

        with patch(
            "src.services.prediction_workflow.get_async_session",
            return_value=mock_services["db_session"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()

            # 保存预测到数据库
            await workflow.save_prediction_to_db(prediction_result)

            # 验证数据库操作
            mock_services["db_session"].add.assert_called()
            mock_services["db_session"].commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_time_prediction_update(self, api_client_full, mock_services):
        """测试实时预测更新"""
        # 模拟实时比赛数据
        live_match_data = {
            "match_id": 12345,
            "status": "live",
            "minute": 65,
            "score": {"home": 1, "away": 1},
            "events": [
                {"minute": 23, "type": "goal", "team": "home"},
                {"minute": 45, "type": "goal", "team": "away"},
            ],
        }

        # Mock实时特征更新
        mock_services["feature_service"].update_features_with_live_data.return_value = {
            "updated_features": {
                "live_goal_difference": 0,
                "time_remaining": 25,
                "momentum": "balanced",
            }
        }

        # Mock动态预测更新
        mock_services["prediction_service"].update_prediction.return_value = {
            "updated_prediction": "draw",
            "new_probabilities": {"home_win": 0.35, "draw": 0.45, "away_win": 0.20},
            "confidence": 0.90,
        }

        with patch(
            "src.services.prediction_workflow.FeatureService",
            return_value=mock_services["feature_service"],
        ), patch(
            "src.services.prediction_workflow.PredictionService",
            return_value=mock_services["prediction_service"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()
            result = await workflow.update_live_prediction(12345, live_match_data)

            assert "updated_prediction" in result
            assert result["updated_prediction"] == "draw"

    @pytest.mark.asyncio
    async def test_prediction_workflow_performance(
        self, api_client_full, mock_services
    ):
        """测试预测工作流性能"""
        import time

        # Mock快速响应
        mock_services["feature_service"].calculate_features.return_value = {
            "features": [1, 0, 1]
        }
        mock_services["prediction_service"].predict_match.return_value = {
            "prediction": "home_win"
        }

        with patch(
            "src.services.prediction_workflow.FeatureService",
            return_value=mock_services["feature_service"],
        ), patch(
            "src.services.prediction_workflow.PredictionService",
            return_value=mock_services["prediction_service"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()

            # 测量执行时间
            start_time = time.time()
            result = await workflow.run_prediction_workflow(12345)
            end_time = time.time()

            execution_time = end_time - start_time

            # 验证结果
            assert result is not None

            # 性能断言（应该在1秒内完成）
            assert execution_time < 1.0, f"工作流耗时过长: {execution_time}秒"

    @pytest.mark.asyncio
    async def test_prediction_workflow_monitoring(self, api_client_full, mock_services):
        """测试预测工作流监控"""
        # Mock监控指标收集
        metrics = {
            "workflow_duration": 0.5,
            "feature_calculation_time": 0.2,
            "prediction_time": 0.1,
            "cache_hit": False,
            "db_operations": 2,
        }

        with patch(
            "src.services.prediction_workflow.collect_metrics", return_value=metrics
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()

            # 模拟工作流执行
            await workflow.run_prediction_workflow(12345)

            # 获取监控数据
            monitoring_data = workflow.get_monitoring_data()

            assert monitoring_data is not None
            assert "workflow_duration" in monitoring_data
            assert monitoring_data["workflow_duration"] == 0.5

    @pytest.mark.asyncio
    async def test_prediction_workflow_with_model_ensemble(
        self, api_client_full, mock_services
    ):
        """测试使用模型集成的预测工作流"""
        # Mock多个模型的预测结果
        model_predictions = [
            {
                "model": "logistic_regression",
                "prediction": "home_win",
                "confidence": 0.7,
            },
            {"model": "random_forest", "prediction": "home_win", "confidence": 0.8},
            {"model": "neural_network", "prediction": "draw", "confidence": 0.6},
        ]

        # Mock集成预测
        mock_services["prediction_service"].ensemble_predict.return_value = {
            "ensemble_prediction": "home_win",
            "probabilities": {"home_win": 0.62, "draw": 0.28, "away_win": 0.10},
            "confidence": 0.75,
            "model_contributions": {
                "logistic_regression": 0.35,
                "random_forest": 0.45,
                "neural_network": 0.20,
            },
        }

        with patch(
            "src.services.prediction_workflow.PredictionService",
            return_value=mock_services["prediction_service"],
        ):
            from src.services.prediction_workflow import PredictionWorkflow

            workflow = PredictionWorkflow()
            result = await workflow.run_ensemble_prediction(12345)

            assert result["ensemble_prediction"] == "home_win"
            assert "model_contributions" in result

    @pytest.mark.asyncio
    async def test_prediction_workflow_validation(self, api_client_full, mock_services):
        """测试预测工作流验证"""
        # 测试无效的match_id
        from src.services.prediction_workflow import PredictionWorkflow

        workflow = PredictionWorkflow()

        # 应该拒绝无效的match_id
        with pytest.raises(ValueError):
            await workflow.run_prediction_workflow(-1)

        with pytest.raises(ValueError):
            await workflow.run_prediction_workflow(None)

    @pytest.mark.asyncio
    async def test_prediction_workflow_cleanup(self, api_client_full, mock_services):
        """测试预测工作流清理"""
        from src.services.prediction_workflow import PredictionWorkflow

        workflow = PredictionWorkflow()

        # 模拟工作流执行后清理资源
        await workflow.cleanup()

        # 验证资源被正确清理
        assert workflow._cleaned_up is True
