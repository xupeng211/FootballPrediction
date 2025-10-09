"""
测试模块化的预测引擎
Test Modular Prediction Engine

验证拆分后的预测引擎模块功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.prediction_engine import (
    PredictionEngine,
    PredictionConfig,
    PredictionStatistics,
)
from src.core.prediction.cache_manager import PredictionCacheManager
from src.core.prediction.data_loader import PredictionDataLoader
from src.core.prediction.model_loader import ModelLoader


@pytest.mark.unit
class TestPredictionEngineModular:
    """测试模块化的预测引擎"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        return PredictionConfig(
            mlflow_tracking_uri="http://localhost:5002",
            max_concurrent_predictions=5,
            prediction_timeout=30.0,
            cache_warmup_enabled=False,
            cache_ttl_predictions=3600,
            cache_ttl_features=1800,
            cache_ttl_odds=300,
            performance_warning_threshold=5.0,
            performance_error_threshold=10.0,
        )

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        manager = MagicMock()
        manager.get_async_session = MagicMock()
        return manager

    @pytest.fixture
    def mock_redis_manager(self):
        """模拟Redis管理器"""
        redis = MagicMock()
        redis.aget = AsyncMock(return_value=None)
        redis.aset = AsyncMock()
        redis.aping = AsyncMock()
        redis.delete = AsyncMock()
        redis.keys = AsyncMock(return_value=[])
        return redis

    @pytest.fixture
    def mock_engine(self, mock_config, mock_db_manager, mock_redis_manager):
        """创建预测引擎实例"""
        with patch("src.core.prediction.engine.MetricsExporter"):
            engine = PredictionEngine(mock_config, mock_db_manager, mock_redis_manager)
            return engine

    @pytest.mark.asyncio
    async def test_config_creation(self):
        """测试配置创建"""
        # 测试默认配置
        config = PredictionConfig.from_env()
        assert config.mlflow_tracking_uri == "http://localhost:5002"
        assert config.max_concurrent_predictions == 10
        assert config.prediction_timeout == 30.0

        # 测试自定义配置
        config = PredictionConfig.create(
            mlflow_tracking_uri="http://custom:5000", max_concurrent_predictions=20
        )
        assert config.mlflow_tracking_uri == "http://custom:5000"
        assert config.max_concurrent_predictions == 20

    def test_prediction_statistics(self):
        """测试预测统计"""
        stats = PredictionStatistics()

        # 初始状态
        assert stats.total_predictions == 0
        assert stats.cache_hit_rate == 0.0
        assert stats.error_rate == 0.0

        # 记录预测
        stats.record_prediction(1.0)
        stats.record_prediction(2.0)
        stats.record_prediction(3.0)

        assert stats.total_predictions == 3
        assert stats.avg_prediction_time == 2.0
        assert stats.min_prediction_time == 1.0
        assert stats.max_prediction_time == 3.0

        # 记录缓存
        stats.record_cache_hit()
        stats.record_cache_hit()
        stats.record_cache_miss()

        assert stats.cache_hit_rate == 66.66666666666666

        # 记录错误
        stats.record_error("timeout")
        stats.record_error("data")

        assert stats.prediction_errors == 2
        assert stats.timeout_errors == 1
        assert stats.data_errors == 1

        # 转换为字典
        stats_dict = stats.to_dict()
        assert "total_predictions" in stats_dict
        assert "cache_hit_rate" in stats_dict
        assert "error_rate" in stats_dict

    @pytest.mark.asyncio
    async def test_cache_manager(self, mock_redis_manager):
        """测试缓存管理器"""
        from src.cache.redis.core.key_manager import CacheKeyManager

        cache_manager = PredictionCacheManager(mock_redis_manager, CacheKeyManager())

        # 测试获取和设置预测
        match_id = 123
        prediction = {"match_id": match_id, "prediction": "home_win"}

        # 缓存未命中
        result = await cache_manager.get_prediction(match_id)
        assert result is None

        # 设置缓存
        await cache_manager.set_prediction(match_id, prediction, ttl=3600)
        mock_redis_manager.aset.assert_called_once()

        # 模拟缓存命中
        mock_redis_manager.aget.return_value = prediction
        result = await cache_manager.get_prediction(match_id)
        assert result == prediction

    @pytest.mark.asyncio
    async def test_data_loader(self, mock_db_manager):
        """测试数据加载器"""
        # 模拟数据库查询结果
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        data_loader = PredictionDataLoader(mock_db_manager)

        # 测试获取比赛信息
        mock_row = MagicMock()
        mock_row.id = 123
        mock_row.home_team_id = 1
        mock_row.away_team_id = 2
        mock_row.league_id = 3
        mock_row.match_date = MagicMock()
        mock_row.match_date.isoformat.return_value = "2024-01-01"
        mock_row.status = "scheduled"
        mock_row.home_score = None
        mock_row.away_score = None
        mock_row.home_team_name = "Team A"
        mock_row.home_team_short = "TA"
        mock_row.away_team_name = "Team B"
        mock_row.away_team_short = "TB"
        mock_row.league_name = "League 1"
        mock_row.league_country = "Country"
        mock_row.league_season = "2024"

        # 创建模拟结果
        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        match_info = await data_loader.get_match_info(123)
        assert match_info is not None
        assert match_info["id"] == 123
        assert match_info["home_team"]["name"] == "Team A"
        assert match_info["away_team"]["name"] == "Team B"

    @pytest.mark.asyncio
    async def test_model_loader(self):
        """测试模型加载器"""
        with patch(
            "src.core.prediction.model_loader.PredictionService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.mlflow_client.get_latest_versions.return_value = [
                MagicMock(version="1")
            ]
            mock_service_instance.load_model = AsyncMock(return_value=True)
            mock_service_instance.predict_match = AsyncMock()

            loader = ModelLoader("http://localhost:5002")

            # 测试加载模型
            success = await loader.load_model()
            assert success
            assert loader._current_model == "football_prediction_model"
            assert loader._current_version == "1"

            # 测试预测
            mock_prediction = MagicMock()
            mock_prediction.predicted_result = "home_win"
            mock_prediction.home_win_probability = 0.5
            mock_prediction.draw_probability = 0.3
            mock_prediction.away_win_probability = 0.2
            mock_prediction.confidence_score = 0.85
            mock_prediction.model_version = "1"
            mock_prediction.model_name = "football_prediction_model"
            mock_prediction.created_at = MagicMock()
            mock_prediction.created_at.isoformat.return_value = "2024-01-01"

            mock_service_instance.predict_match.return_value = mock_prediction

            result = await loader.predict_match(123)
            assert result is not None
            assert result.predicted_result == "home_win"

    @pytest.mark.asyncio
    async def test_engine_initialization(self, mock_engine):
        """测试引擎初始化"""
        # 模拟模型加载成功
        mock_engine.model_loader.load_model = AsyncMock(return_value=True)

        await mock_engine.initialize()
        assert mock_engine._model_initialized

    @pytest.mark.asyncio
    async def test_predict_match(self, mock_engine):
        """测试预测比赛"""
        # 设置模拟
        mock_engine.model_loader.predict_match = AsyncMock()
        mock_prediction = MagicMock()
        mock_prediction.predicted_result = "home_win"
        mock_prediction.home_win_probability = 0.5
        mock_prediction.draw_probability = 0.3
        mock_prediction.away_win_probability = 0.2
        mock_prediction.confidence_score = 0.85
        mock_prediction.model_version = "1"
        mock_prediction.model_name = "model"
        mock_prediction.created_at.isoformat.return_value = "2024-01-01"
        mock_engine.model_loader.predict_match.return_value = mock_prediction

        mock_engine.data_loader.get_match_info = AsyncMock(
            return_value={
                "id": 123,
                "home_team": {"id": 1, "name": "Team A"},
                "away_team": {"id": 2, "name": "Team B"},
                "league": {"id": 3, "name": "League"},
                "match_date": "2024-01-01",
                "status": "scheduled",
            }
        )
        mock_engine.data_loader.get_match_odds = AsyncMock(return_value=None)
        mock_engine._get_match_features = AsyncMock(return_value=None)

        # 执行预测
        result = await mock_engine.predict_match(123)

        # 验证结果
        assert result is not None
        assert result["match_id"] == 123
        assert result["prediction"] == "home_win"
        assert result["probabilities"]["home_win"] == 0.5
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_batch_predict(self, mock_engine):
        """测试批量预测"""
        # 设置模拟
        mock_engine.predict_match = AsyncMock(
            side_effect=[
                {"match_id": 123, "prediction": "home_win"},
                {"match_id": 124, "prediction": "draw"},
                {"match_id": 125, "prediction": "away_win"},
            ]
        )

        # 执行批量预测
        results = await mock_engine.batch_predict([123, 124, 125])

        # 验证结果
        assert len(results) == 3
        assert results[0]["match_id"] == 123
        assert results[1]["match_id"] == 124
        assert results[2]["match_id"] == 125

    @pytest.mark.asyncio
    async def test_get_statistics(self, mock_engine):
        """测试获取统计信息"""
        # 添加一些统计数据
        mock_engine.statistics.record_prediction(1.0)
        mock_engine.statistics.record_prediction(2.0)
        mock_engine.statistics.record_cache_hit()
        mock_engine.statistics.record_cache_miss()

        # 获取统计信息
        stats = await mock_engine.get_statistics()

        # 验证统计信息
        assert "total_predictions" in stats
        assert "avg_prediction_time" in stats
        assert "cache_hit_rate" in stats
        assert "model" in stats
        assert "config" in stats

    @pytest.mark.asyncio
    async def test_health_check(self, mock_engine):
        """测试健康检查"""
        # 设置模拟
        mock_engine._model_initialized = True
        mock_engine.db_manager.get_async_session.return_value.__aenter__.return_value.execute = AsyncMock()
        mock_engine.redis_manager.aping = AsyncMock()

        # 执行健康检查
        health = await mock_engine.health_check()

        # 验证健康状态
        assert "status" in health
        assert "checks" in health
        assert health["status"] == "healthy"
        assert health["checks"]["database"] == "healthy"
        assert health["checks"]["redis"] == "healthy"
        assert health["checks"]["model"] == "healthy"

    @pytest.mark.asyncio
    async def test_switch_model(self, mock_engine):
        """测试切换模型"""
        # 设置模拟
        mock_engine.model_loader.switch_model = AsyncMock(return_value=True)
        mock_engine.cache_manager.clear_all_predictions = AsyncMock()

        # 切换模型
        success = await mock_engine.switch_model("new_model", "2")

        # 验证结果
        assert success
        assert mock_engine._model_initialized
        mock_engine.model_loader.switch_model.assert_called_once_with("new_model", "2")
        mock_engine.cache_manager.clear_all_predictions.assert_called_once()

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 测试从原始模块导入
        from src.core.prediction_engine import PredictionEngine as OldEngine
        from src.core.prediction_engine import PredictionConfig as OldConfig

        # 验证导入成功
        assert OldEngine is not None
        assert OldConfig is not None

        # 验证类是同一个
        from src.core.prediction import PredictionEngine as NewEngine
        from src.core.prediction.config import PredictionConfig as NewConfig

        assert OldEngine is NewEngine
        assert OldConfig is NewConfig
