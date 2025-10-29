# TODO: Consider creating a fixture for 19 repeated Mock creations

# TODO: Consider creating a fixture for 19 repeated Mock creations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.models.prediction_service import PredictionResult

"""
预测流程集成测试
Integration Tests for Prediction Flow

测试完整的数据收集到预测流程。
Test complete flow from data collection to prediction.
"""


@pytest.mark.integration
class TestPredictionFlow:
    """预测流程集成测试"""

    @pytest.mark.asyncio
    async def test_full_prediction_workflow(self, prediction_engine):
        """测试完整的预测工作流"""
        # 1. 准备测试数据
        match_id = 12345

        # 模拟数据库中的比赛
        mock_match = {
            "id": match_id,
            "home_team_id": 100,
            "away_team_id": 200,
            "league_id": 1,
            "match_time": datetime.now() + timedelta(hours=3),
            "match_status": "scheduled",
            "venue": "Test Stadium",
            "home_team": "Team A",
            "away_team": "Team B",
            "league": "Test League",
        }

        # 模拟特征数据
        mock_features = {
            "home_recent_wins": 3,
            "home_recent_goals_for": 7,
            "home_recent_goals_against": 3,
            "away_recent_wins": 2,
            "away_recent_goals_for": 5,
            "away_recent_goals_against": 5,
            "h2h_home_advantage": 0.55,
            "home_implied_probability": 0.45,
            "draw_implied_probability": 0.30,
            "away_implied_probability": 0.25,
        }

        # 模拟赔率数据
        mock_odds = {
            "home_win": 2.2,
            "draw": 3.4,
            "away_win": 3.1,
            "bookmaker": "test_bookmaker",
            "last_updated": datetime.now().isoformat(),
        }

        # 模拟预测结果
        mock_prediction = PredictionResult(
            match_id=match_id,
            model_version="1.0.0",
            model_name="football_baseline_model",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.65,
            features_used=mock_features,
            created_at=datetime.now(),
        )

        # 设置模拟
        prediction_engine._get_match_info = AsyncMock(return_value=mock_match)
        prediction_engine._get_match_features = AsyncMock(return_value=mock_features)
        prediction_engine._get_match_odds = AsyncMock(return_value=mock_odds)
        prediction_engine.prediction_service.predict_match = AsyncMock(return_value=mock_prediction)

        # 2. 执行预测
        _result = await prediction_engine.predict_match(match_id, include_features=True)

        # 3. 验证结果
        assert result["match_id"] == match_id
        assert result["prediction"] == "home"
        assert result["probabilities"]["home_win"] == 0.5
        assert result["confidence"] == 0.65
        assert "features" in result
        assert "odds" in result
        assert "match_info" in result

        # 4. 验证缓存
        cache_key = prediction_engine.cache_key_manager.prediction_key(match_id)
        cached_result = await prediction_engine.redis_manager.aget(cache_key)
        assert cached_result is not None
        assert cached_result["prediction"] == "home"

    @pytest.mark.asyncio
    async def test_batch_prediction_flow(self, prediction_engine):
        """测试批量预测流程"""
        # 准备多个比赛
        match_ids = [12345, 12346, 12347]

        # 模拟批量数据
        matches_data = {}
        predictions_data = {}

        for i, match_id in enumerate(match_ids):
            matches_data[match_id] = {
                "id": match_id,
                "home_team_id": 100 + i,
                "away_team_id": 200 + i,
                "league_id": 1,
                "match_time": datetime.now() + timedelta(hours=2 + i),
                "match_status": "scheduled",
                "venue": f"Stadium {i + 1}",
                "home_team": f"Team {chr(65 + i)}",
                "away_team": f"Team {chr(68 + i)}",
                "league": "Test League",
            }

            predictions_data[match_id] = {
                "match_id": match_id,
                "prediction": ["home", "draw", "away"][i],
                "probabilities": {
                    "home_win": 0.5 - i * 0.1,
                    "draw": 0.3,
                    "away_win": 0.2 + i * 0.1,
                },
                "confidence": 0.65 - i * 0.05,
                "model_version": "1.0.0",
            }

        # 设置模拟
        prediction_engine._get_match_info = AsyncMock(side_effect=lambda mid: matches_data.get(mid))
        prediction_engine.predict_match = AsyncMock(
            side_effect=lambda mid, **kw: predictions_data.get(mid)
        )

        # 执行批量预测
        results = await prediction_engine.batch_predict(match_ids)

        # 验证结果
        assert len(results) == 3
        assert all(r["prediction"] in ["home", "draw", "away"] for r in results)

        # 验证并发执行
        prediction_engine.predict_match.call_count == 3

    @pytest.mark.asyncio
    async def test_data_collection_integration(self, prediction_engine):
        """测试数据收集集成"""
        match_id = 12345
        match_info = {
            "id": match_id,
            "home_team_id": 100,
            "away_team_id": 200,
            "match_time": datetime.now() + timedelta(hours=1),
            "match_status": "in_progress",
        }

        # 模拟数据收集
        mock_scores = {
            "home_score": 1,
            "away_score": 0,
            "match_time": "2024-01-01T15:30:00",
            "minute": 35,
        }

        mock_odds = {
            "match_id": match_id,
            "bookmakers": [
                {
                    "name": "bookmaker1",
                    "home_win": 1.8,
                    "draw": 3.5,
                    "away_win": 4.2,
                }
            ],
            "best_odds": {
                "home_win": 1.8,
                "draw": 3.5,
                "away_win": 4.2,
            },
        }

        # 设置模拟
        prediction_engine._get_match_info = AsyncMock(return_value=match_info)

        with patch.object(prediction_engine, "scores_collector") as mock_scores_collector:
            with patch.object(prediction_engine, "odds_collector") as mock_odds_collector:
                mock_scores_collector.collect_match_score = AsyncMock(return_value=mock_scores)
                mock_odds_collector.collect_match_odds = AsyncMock(return_value=mock_odds)

                # 收集最新数据
                await prediction_engine._collect_latest_data(match_id, match_info)

                # 验证调用
                mock_scores_collector.collect_match_score.assert_called_once_with(match_id)
                mock_odds_collector.collect_match_odds.assert_called_once_with(match_id)

    @pytest.mark.asyncio
    async def test_cache_consistency(self, prediction_engine):
        """测试缓存一致性"""
        match_id = 12345

        # 第一次预测
        prediction_engine._get_match_info = AsyncMock(return_value={"id": match_id})
        prediction_engine.prediction_service.predict_match = AsyncMock(
            return_value=PredictionResult(
                match_id=match_id,
                model_version="1.0.0",
                predicted_result="home",
                confidence_score=0.65,
            )
        )

        result1 = await prediction_engine.predict_match(match_id)

        # 第二次预测（应该从缓存获取）
        _result2 = await prediction_engine.predict_match(match_id)

        # 验证结果一致
        assert result1["prediction"] == result2["prediction"]
        assert result1["confidence"] == result2["confidence"]

        # 验证只调用了一次预测服务
        prediction_engine.prediction_service.predict_match.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, prediction_engine):
        """测试错误恢复流程"""
        match_id = 12345

        # 模拟第一次失败
        prediction_engine.prediction_service.predict_match = AsyncMock(
            side_effect=[
                Exception("Model service unavailable"),
                PredictionResult(
                    match_id=match_id,
                    model_version="1.0.0",
                    predicted_result="home",
                    confidence_score=0.65,
                ),
            ]
        )

        prediction_engine._get_match_info = AsyncMock(return_value={"id": match_id})

        # 第一次调用应该失败
        with pytest.raises(Exception):
            await prediction_engine.predict_match(match_id)

        # 第二次调用应该成功
        _result = await prediction_engine.predict_match(match_id)
        assert result["prediction"] == "home"

    @pytest.mark.asyncio
    async def test_prediction_verification_flow(self, prediction_engine):
        """测试预测验证流程"""
        match_id = 12345

        # 模拟已完成的比赛

        # 模拟预测记录

        # 设置模拟
        prediction_engine.prediction_service.verify_prediction = AsyncMock(return_value=True)

        # 执行验证
        _stats = await prediction_engine.verify_predictions([match_id])

        # 验证结果
        assert stats["total_matches"] == 1
        assert stats["verified"] == 1
        prediction_engine.prediction_service.verify_prediction.assert_called_once_with(match_id)

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, prediction_engine):
        """测试性能监控"""
        match_ids = list(range(1000, 1010))  # 10场比赛

        # 模拟快速预测
        async def mock_predict(mid):
            await asyncio.sleep(0.01)  # 模拟10ms处理时间
            await asyncio.sleep(0.01)  # 模拟10ms处理时间
            await asyncio.sleep(0.01)  # 模拟10ms处理时间
            return {"match_id": mid, "prediction": "home"}

        prediction_engine.predict_match = AsyncMock(side_effect=mock_predict)

        # 记录开始时间
        start_time = datetime.now()

        # 执行批量预测
        results = await prediction_engine.batch_predict(match_ids)

        # 计算总时间
        total_time = (datetime.now() - start_time).total_seconds()

        # 验证性能
        assert len(results) == 10
        assert total_time < 1.0  # 应该在1秒内完成（并发执行）

        # 获取性能统计
        _stats = prediction_engine.get_performance_stats()
        assert stats["total_predictions"] >= 10
        assert stats["avg_prediction_time"] > 0

    @pytest.mark.asyncio
    async def test_health_check_integration(self, prediction_engine):
        """测试健康检查集成"""
        # 模拟所有组件健康
        prediction_engine.prediction_service.get_production_model = AsyncMock()
        prediction_engine.redis_manager.aping = AsyncMock()

        async with prediction_engine.db_manager.get_async_session() as session:
            session.execute = AsyncMock()

        # 执行健康检查
        health = await prediction_engine.health_check()

        # 验证健康状态
        assert health["status"] == "healthy"
        assert "components" in health
        assert all(status == "healthy" for status in health["components"].values())

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, prediction_engine):
        """测试并发预测"""
        match_ids = list(range(2000, 2050))  # 50场比赛

        # 模拟预测
        prediction_engine.predict_match = AsyncMock(
            side_effect=lambda mid: {
                "match_id": mid,
                "prediction": "home" if mid % 2 == 0 else "away",
            }
        )

        # 并发执行预测
        tasks = [prediction_engine.predict_match(mid) for mid in match_ids]
        results = await asyncio.gather(*tasks)

        # 验证所有预测都完成
        assert len(results) == 50
        assert all(r["prediction"] in ["home", "away"] for r in results)
