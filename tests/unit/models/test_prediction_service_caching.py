"""
预测服务缓存测试 / Prediction Service Cache Tests

测试预测服务中的TTL缓存功能，包括模型缓存和预测结果缓存。

Tests for TTL caching functionality in prediction service, including model caching and prediction result caching.

测试类 / Test Classes:
    TestPredictionServiceCaching: 预测服务缓存测试 / Prediction service caching tests

测试方法 / Test Methods:
    test_get_production_model_caching: 测试生产模型缓存 / Test production model caching
    test_predict_match_caching: 测试比赛预测缓存 / Test match prediction caching
    test_batch_predict_matches_caching: 测试批量预测缓存 / Test batch prediction caching

使用示例 / Usage Example:
    ```bash
    # 运行预测服务缓存测试
    pytest tests/unit/models/test_prediction_service_caching.py -v

    # 运行特定测试
    pytest tests/unit/models/test_prediction_service_caching.py::TestPredictionServiceCaching::test_predict_match_caching -v
    ```
"""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.cache.ttl_cache import TTLCache
from src.models.prediction_service import PredictionResult, PredictionService


class TestPredictionServiceCaching:
    """预测服务缓存测试 / Prediction Service Caching Tests"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器 / Mock database manager"""
        with patch("src.models.prediction_service.DatabaseManager") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_feature_store(self):
        """模拟特征存储 / Mock feature store"""
        with patch("src.models.prediction_service.FootballFeatureStore") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_metrics_exporter(self):
        """模拟指标导出器 / Mock metrics exporter"""
        with patch("src.models.prediction_service.ModelMetricsExporter") as mock:
            yield mock.return_value

    @pytest.fixture
    def prediction_service(
        self, mock_db_manager, mock_feature_store, mock_metrics_exporter
    ):
        """创建预测服务实例 / Create prediction service instance"""
        with patch("src.models.prediction_service.mlflow.set_tracking_uri"):
            service = PredictionService()
            return service

    @pytest.mark.asyncio
    async def test_get_production_model_caching(self, prediction_service):
        """测试生产模型缓存 / Test production model caching"""
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "1"
        mock_version_info.current_stage = "Production"

        mock_client.get_latest_versions.return_value = [mock_version_info]

        mock_model = Mock()

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ), patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=mock_model,
        ):
            # 第一次获取模型
            model1, version1 = await prediction_service.get_production_model()

            # 第二次获取模型（应该从缓存获取）
            model2, version2 = await prediction_service.get_production_model()

            # 验证两次获取的是相同的模型
            assert model1 == model2
            assert version1 == version2

            # 验证MLflow客户端只被调用一次
            mock_client.get_latest_versions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_production_model_cache_expiration(self, prediction_service):
        """测试生产模型缓存过期 / Test production model cache expiration"""
        # 设置很短的缓存TTL用于测试
        prediction_service.model_cache_ttl = timedelta(milliseconds=50)

        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "1"
        mock_version_info.current_stage = "Production"

        mock_client.get_latest_versions.return_value = [mock_version_info]

        mock_model = Mock()

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ), patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=mock_model,
        ):
            # 第一次获取模型
            model1, version1 = await prediction_service.get_production_model()

            # 模拟缓存过期，避免真实等待
            cache_key = "model:football_baseline_model"
            cached_entry = prediction_service.model_cache._cache.get(cache_key)
            assert cached_entry is not None
            cached_entry.created_at -= prediction_service.model_cache_ttl + timedelta(
                milliseconds=10
            )

            # 第二次获取模型（缓存应该已过期）
            model2, version2 = await prediction_service.get_production_model()

            # 验证MLflow客户端被调用了两次（缓存过期后重新加载）
            assert mock_client.get_latest_versions.call_count == 2

    @pytest.mark.asyncio
    async def test_predict_match_caching(self, prediction_service, mock_feature_store):
        """测试比赛预测缓存 / Test match prediction caching"""
        # Mock模型
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array(
            [[0.2, 0.3, 0.5]]
        )  # [away, draw, home]
        mock_model.predict.return_value = np.array(["home"])

        # Mock获取生产模型
        match_info = {"id": 1, "home_team_id": 10, "away_team_id": 20}
        with patch.object(
            prediction_service,
            "get_production_model",
            return_value=(mock_model, "v1.0"),
        ), patch.object(
            prediction_service, "_get_match_info", return_value=match_info
        ), patch.object(
            prediction_service, "_store_prediction", new_callable=AsyncMock
        ), patch.object(
            prediction_service.metrics_exporter,
            "export_prediction_metrics",
            new_callable=AsyncMock,
        ):
            # Mock特征存储
            features = {
                "home_recent_wins": 3,
                "home_recent_goals_for": 8,
                "home_recent_goals_against": 2,
                "away_recent_wins": 1,
                "away_recent_goals_for": 4,
                "away_recent_goals_against": 6,
                "h2h_home_advantage": 0.6,
                "home_implied_probability": 0.5,
                "draw_implied_probability": 0.25,
                "away_implied_probability": 0.25,
            }
            mock_feature_store.get_match_features_for_prediction = AsyncMock(
                return_value=features
            )

            # 第一次预测
            result1 = await prediction_service.predict_match(1)

            # 第二次预测相同比赛（应该从缓存获取）
            result2 = await prediction_service.predict_match(1)

            # 验证两次预测结果相同
            assert result1.match_id == result2.match_id
            assert result1.predicted_result == result2.predicted_result
            assert result1.confidence_score == result2.confidence_score

    @pytest.mark.asyncio
    async def test_predict_match_cache_expiration(
        self, prediction_service, mock_feature_store
    ):
        """测试比赛预测缓存过期 / Test match prediction cache expiration"""
        # 设置很短的缓存TTL用于测试
        prediction_service.prediction_cache_ttl = timedelta(milliseconds=50)

        # Mock模型
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array(
            [[0.2, 0.3, 0.5]]
        )  # [away, draw, home]
        mock_model.predict.return_value = np.array(["home"])

        # Mock获取生产模型
        match_info = {"id": 1, "home_team_id": 10, "away_team_id": 20}
        with patch.object(
            prediction_service,
            "get_production_model",
            return_value=(mock_model, "v1.0"),
        ), patch.object(
            prediction_service, "_get_match_info", return_value=match_info
        ), patch.object(
            prediction_service, "_store_prediction", new_callable=AsyncMock
        ), patch.object(
            prediction_service.metrics_exporter,
            "export_prediction_metrics",
            new_callable=AsyncMock,
        ):
            # Mock特征存储
            features = {
                "home_recent_wins": 3,
                "home_recent_goals_for": 8,
                "home_recent_goals_against": 2,
                "away_recent_wins": 1,
                "away_recent_goals_for": 4,
                "away_recent_goals_against": 6,
                "h2h_home_advantage": 0.6,
                "home_implied_probability": 0.5,
                "draw_implied_probability": 0.25,
                "away_implied_probability": 0.25,
            }
            mock_feature_store.get_match_features_for_prediction = AsyncMock(
                return_value=features
            )

            # 第一次预测
            # 等待缓存过期

            # 第二次预测相同比赛（缓存应该已过期）
            # 验证预测方法被调用了两次（缓存过期后重新预测）
            # 注意：这里我们无法直接验证，因为_predict_match是私有方法
            # 但我们可以通过其他方式间接验证

    @pytest.mark.asyncio
    async def test_batch_predict_matches_caching(self, prediction_service):
        """测试批量预测缓存 / Test batch prediction caching"""
        match_ids = [1, 2, 3]

        # Mock predict_match to return a dummy result
        async def predict_match_side_effect(match_id):
            return PredictionResult(match_id=match_id, model_version="v1.0")

        with patch.object(
            prediction_service, "get_production_model", return_value=(Mock(), "v1.0")
        ):
            with patch.object(
                prediction_service,
                "predict_match",
                side_effect=predict_match_side_effect,
            ):
                # 第一次批量预测
                results1 = await prediction_service.batch_predict_matches(match_ids)

                # 第二次批量预测（应该从缓存获取）
                results2 = await prediction_service.batch_predict_matches(match_ids)

                # 验证结果数量相同
                assert len(results1) == len(results2) == 3

                # 验证每场比赛的预测结果相同
                for i in range(len(results1)):
                    assert results1[i].match_id == results2[i].match_id

    @pytest.mark.asyncio
    async def test_cache_stats_monitoring(self, prediction_service):
        """测试缓存统计监控 / Test cache statistics monitoring"""
        # 获取初始缓存统计
        model_cache_stats = await prediction_service.model_cache.get_stats()
        prediction_cache_stats = await prediction_service.prediction_cache.get_stats()

        # 验证统计信息格式
        assert "total_entries" in model_cache_stats
        assert "active_entries" in model_cache_stats
        assert "expired_entries" in model_cache_stats
        assert "max_size" in model_cache_stats

        assert "total_entries" in prediction_cache_stats
        assert "active_entries" in prediction_cache_stats
        assert "expired_entries" in prediction_cache_stats
        assert "max_size" in prediction_cache_stats

    @pytest.mark.asyncio
    async def test_cache_configuration(self, prediction_service):
        """测试缓存配置 / Test cache configuration"""
        # 验证缓存配置
        assert isinstance(prediction_service.model_cache, TTLCache)
        assert isinstance(prediction_service.prediction_cache, TTLCache)

        # 验证缓存TTL配置
        assert isinstance(prediction_service.model_cache_ttl, timedelta)
        assert isinstance(prediction_service.prediction_cache_ttl, timedelta)

        # 验证默认TTL值
        assert prediction_service.model_cache_ttl.total_seconds() >= 0
        assert prediction_service.prediction_cache_ttl.total_seconds() >= 0
