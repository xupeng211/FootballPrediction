"""
预测引擎单元测试
Unit Tests for Prediction Engine
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.core.prediction_engine import PredictionEngine
from src.models.prediction_service import PredictionResult


@pytest.fixture
async def prediction_engine():
    """创建预测引擎测试夹具"""
    engine = PredictionEngine()
    yield engine
    await engine.close()


@pytest.fixture
def mock_match():
    """创建模拟比赛数据"""
    return {
        "id": 12345,
        "home_team_id": 100,
        "away_team_id": 200,
        "league_id": 1,
        "match_time": datetime.now() + timedelta(hours=2),
        "match_status": "scheduled",
        "venue": "Test Stadium",
        "home_team": "Team A",
        "away_team": "Team B",
        "league": "Test League",
    }


@pytest.fixture
def mock_prediction_result():
    """创建模拟预测结果"""
    return PredictionResult(
        match_id=12345,
        model_version="1.0.0",
        home_win_probability=0.5,
        draw_probability=0.3,
        away_win_probability=0.2,
        predicted_result="home",
        confidence_score=0.65,
        created_at=datetime.now(),
    )


class TestPredictionEngine:
    """预测引擎测试类"""

    @pytest.mark.asyncio
    async def test_predict_match_success(self, prediction_engine, mock_match, mock_prediction_result):
        """测试成功预测比赛"""
        # 模拟依赖
        prediction_engine._get_match_info = AsyncMock(return_value=mock_match)
        prediction_engine.prediction_service.predict_match = AsyncMock(return_value=mock_prediction_result)
        prediction_engine._get_match_odds = AsyncMock(return_value={
            "home_win": 2.0,
            "draw": 3.2,
            "away_win": 3.8,
            "bookmaker": "test_bookmaker",
            "last_updated": datetime.now().isoformat(),
        })

        # 执行预测
        result = await prediction_engine.predict_match(12345)

        # 验证结果
        assert result["match_id"] == 12345
        assert result["prediction"] == "home"
        assert result["probabilities"]["home_win"] == 0.5
        assert result["confidence"] == 0.65
        assert "match_info" in result
        assert "odds" in result

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self, prediction_engine):
        """测试比赛不存在的情况"""
        prediction_engine._get_match_info = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="比赛 12345 不存在"):
            await prediction_engine.predict_match(12345)

    @pytest.mark.asyncio
    async def test_predict_match_from_cache(self, prediction_engine, mock_prediction_result):
        """测试从缓存获取预测"""
        # 设置缓存
        cache_key = prediction_engine.cache_key_manager.prediction_key(12345)
        cached_data = {
            "match_id": 12345,
            "prediction": "home",
            "probabilities": {"home_win": 0.5, "draw": 0.3, "away_win": 0.2},
            "confidence": 0.65,
            "model_version": "1.0.0",
            "model_name": "football_baseline_model",
            "prediction_time": datetime.now().isoformat(),
        }
        await prediction_engine.redis_manager.aset(cache_key, cached_data)

        # 执行预测
        result = await prediction_engine.predict_match(12345)

        # 验证返回缓存数据
        assert result == cached_data
        assert prediction_engine.stats["cache_hits"] == 1

    @pytest.mark.asyncio
    async def test_batch_predict(self, prediction_engine):
        """测试批量预测"""
        # 模拟单个预测
        prediction_engine.predict_match = AsyncMock(side_effect=[
            {"match_id": 12345, "prediction": "home"},
            {"match_id": 12346, "prediction": "draw"},
            {"match_id": 12347, "prediction": "away"},
        ])

        # 执行批量预测
        results = await prediction_engine.batch_predict([12345, 12346, 12347])

        # 验证结果
        assert len(results) == 3
        assert results[0]["prediction"] == "home"
        assert results[1]["prediction"] == "draw"
        assert results[2]["prediction"] == "away"

    @pytest.mark.asyncio
    async def test_batch_predict_with_error(self, prediction_engine):
        """测试批量预测包含错误"""
        # 模拟预测，其中第二个失败
        prediction_engine.predict_match = AsyncMock(side_effect=[
            {"match_id": 12345, "prediction": "home"},
            ValueError("Match not found"),
            {"match_id": 12347, "prediction": "away"},
        ])

        # 执行批量预测
        results = await prediction_engine.batch_predict([12345, 12346, 12347])

        # 验证结果
        assert len(results) == 3
        assert results[0]["prediction"] == "home"
        assert results[1]["error"] == "Match not found"
        assert results[2]["prediction"] == "away"

    @pytest.mark.asyncio
    async def test_predict_upcoming_matches(self, prediction_engine):
        """测试预测即将开始的比赛"""
        # 模拟即将开始的比赛
        upcoming_matches = [
            {"id": 12345, "match_time": (datetime.now() + timedelta(hours=1)).isoformat()},
            {"id": 12346, "match_time": (datetime.now() + timedelta(hours=2)).isoformat()},
        ]
        prediction_engine._get_upcoming_matches = AsyncMock(return_value=upcoming_matches)
        prediction_engine.batch_predict = AsyncMock(return_value=[
            {"match_id": 12345, "prediction": "home"},
            {"match_id": 12346, "prediction": "draw"},
        ])

        # 执行预测
        results = await prediction_engine.predict_upcoming_matches(hours_ahead=24)

        # 验证结果
        assert len(results) == 2
        assert results[0]["prediction"] == "home"
        assert results[1]["prediction"] == "draw"

    @pytest.mark.asyncio
    async def test_verify_predictions(self, prediction_engine):
        """测试验证预测结果"""
        # 模拟验证
        prediction_engine.prediction_service.verify_prediction = AsyncMock(return_value=True)

        # 执行验证
        stats = await prediction_engine.verify_predictions([12345, 12346])

        # 验证结果
        assert stats["total_matches"] == 2
        assert stats["verified"] == 2
        assert stats["correct"] == 0  # 模拟数据中没有实际结果

    @pytest.mark.asyncio
    async def test_warmup_cache(self, prediction_engine):
        """测试缓存预热"""
        # 模拟即将开始的比赛
        upcoming_matches = [
            {"id": 12345},
            {"id": 12346},
        ]
        prediction_engine._get_upcoming_matches = AsyncMock(return_value=upcoming_matches)
        prediction_engine.predict_match = AsyncMock(return_value={"prediction": "home"})

        # 执行缓存预热
        stats = await prediction_engine.warmup_cache(hours_ahead=24)

        # 验证结果
        assert stats["warmed_up"] == 2
        assert stats["skipped"] == 0

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, prediction_engine):
        """测试获取性能统计"""
        # 添加一些统计数据
        prediction_engine.stats = {
            "total_predictions": 100,
            "cache_hits": 70,
            "cache_misses": 30,
            "prediction_errors": 5,
            "avg_prediction_time": 0.15,
        }

        # 获取统计
        stats = prediction_engine.get_performance_stats()

        # 验证结果
        assert stats["total_predictions"] == 100
        assert stats["cache_hit_rate"] == 0.7
        assert stats["error_rate"] == 0.05
        assert stats["avg_prediction_time"] == 0.15

    @pytest.mark.asyncio
    async def test_health_check(self, prediction_engine):
        """测试健康检查"""
        # 模拟所有组件健康
        prediction_engine.prediction_service.get_production_model = AsyncMock()
        prediction_engine.redis_manager.aping = AsyncMock()

        async with prediction_engine.db_manager.get_async_session() as session:
            session.execute = AsyncMock()

        # 执行健康检查
        health = await prediction_engine.health_check()

        # 验证结果
        assert health["status"] == "healthy"
        assert "components" in health
        assert health["components"]["database"] == "healthy"
        assert health["components"]["redis"] == "healthy"
        assert health["components"]["mlflow"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, prediction_engine):
        """测试健康检查 - 降级状态"""
        # 模拟Redis不健康
        prediction_engine.prediction_service.get_production_model = AsyncMock()
        prediction_engine.redis_manager.aping = AsyncMock(side_effect=Exception("Redis error"))

        async with prediction_engine.db_manager.get_async_session() as session:
            session.execute = AsyncMock()

        # 执行健康检查
        health = await prediction_engine.health_check()

        # 验证结果
        assert health["status"] == "degraded"
        assert health["components"]["redis"].startswith("unhealthy")

    @pytest.mark.asyncio
    async def test_clear_cache(self, prediction_engine):
        """测试清理缓存"""
        # 模拟Redis操作
        prediction_engine.redis_manager.client.keys = AsyncMock(return_value=["key1", "key2"])
        prediction_engine.redis_manager.adelete = AsyncMock(return_value=2)

        # 执行清理
        cleared = await prediction_engine.clear_cache("predictions:*")

        # 验证结果
        assert cleared == 2

    @pytest.mark.asyncio
    async def test_collect_latest_data(self, prediction_engine):
        """测试收集最新数据"""
        match_info = {
            "match_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "match_status": "scheduled",
        }

        prediction_engine._init_collectors = AsyncMock()
        prediction_engine.collectors = {
            "odds": MagicMock(),
            "scores": MagicMock(),
        }
        prediction_engine.collectors["odds"].collect_match_odds = AsyncMock()
        prediction_engine.collectors["scores"].collect_match_score = AsyncMock()

        # 执行数据收集
        await prediction_engine._collect_latest_data(12345, match_info)

        # 验证调用了收集器
        prediction_engine.collectors["odds"].collect_match_odds.assert_called_once_with(12345)
        prediction_engine.collectors["scores"].collect_match_score.assert_not_called()  # 比赛未开始