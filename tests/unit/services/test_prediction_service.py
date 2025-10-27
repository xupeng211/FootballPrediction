# TODO: Consider creating a fixture for 22 repeated Mock creations

# TODO: Consider creating a fixture for 22 repeated Mock creations

# noqa: F401,F811,F821,E402
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.models.prediction_service import PredictionResult, PredictionService

"""
PredictionService单元测试 / Unit Tests for PredictionService

测试预测服务的核心功能，包括：
- 模型加载和缓存
- 单场比赛预测
- 批量预测
- 预测结果验证
- 统计信息获取

Tests core functionality of prediction service, including:
- Model loading and caching
- Single match prediction
- Batch prediction
- Prediction result verification
- Statistics retrieval
"""


@pytest.mark.unit
class TestPredictionService:
    """PredictionService测试类"""

    @pytest.fixture
    def mock_service(self):
        """创建模拟的PredictionService实例"""
        with (
            patch("src.models.prediction_service.DatabaseManager"),
            patch("src.models.prediction_service.FootballFeatureStore"),
            patch("src.models.prediction_service.ModelMetricsExporter"),
            patch("src.models.prediction_service.mlflow"),
        ):
            service = PredictionService(mlflow_tracking_uri="http://test:5002")
            return service

    @pytest.fixture
    def mock_model(self):
        """创建模拟的机器学习模型"""
        model = MagicMock()
        # 模拟预测结果：[away, draw, home] 概率
        model.predict_proba.return_value = np.array([[0.25, 0.30, 0.45]])
        model.predict.return_value = np.array(["home"])
        return model

    @pytest.fixture
    def sample_prediction_result(self):
        """创建示例预测结果"""
        return PredictionResult(
            match_id=12345,
            model_version="1.0",
            model_name="football_baseline_model",
            home_win_probability=0.45,
            draw_probability=0.30,
            away_win_probability=0.25,
            predicted_result="home",
            confidence_score=0.45,
            features_used={"home_recent_wins": 2, "away_recent_wins": 1},
            prediction_metadata={"test": True},
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_prediction_service_initialization(self, mock_service):
        """测试PredictionService初始化"""
        assert mock_service.mlflow_tracking_uri == "http://test:5002"
        assert mock_service.model_cache is not None
        assert mock_service.prediction_cache is not None
        assert len(mock_service.feature_order) == 10
        assert mock_service.model_cache_ttl.total_seconds() == 3600  # 1 hour

    @pytest.mark.asyncio
    async def test_get_default_features(self, mock_service):
        """测试获取默认特征"""
        features = mock_service._get_default_features()

        assert isinstance(features, dict)
        assert "home_recent_wins" in features
        assert "away_recent_wins" in features
        assert "h2h_home_advantage" in features
        assert features["home_recent_wins"] == 2
        assert features["away_recent_wins"] == 2

    @pytest.mark.asyncio
    async def test_prepare_features_for_prediction(self, mock_service):
        """测试特征数组准备"""
        features = {
            "home_recent_wins": 3,
            "away_recent_wins": 2,
            "h2h_home_advantage": 0.6,
            "home_implied_probability": 0.5,
            "draw_implied_probability": 0.3,
            "away_implied_probability": 0.2,
        }

        feature_array = mock_service._prepare_features_for_prediction(features)

        assert isinstance(feature_array, np.ndarray)
        assert feature_array.shape == (1, 10)  # 10个特征
        assert feature_array[0][0] == 3.0  # home_recent_wins
        assert feature_array[0][1] == 0.0  # home_recent_goals_for (默认值)

    @pytest.mark.asyncio
    async def test_prepare_features_with_missing_values(self, mock_service):
        """测试处理缺失值的特征准备"""
        features = {"home_recent_wins": 3}  # 只提供部分特征

        feature_array = mock_service._prepare_features_for_prediction(features)

        assert isinstance(feature_array, np.ndarray)
        assert feature_array.shape == (1, 10)
        # 缺失的特征应该使用默认值0.0
        assert feature_array[0][1] == 0.0  # home_recent_goals_for缺失

    @pytest.mark.asyncio
    async def test_get_match_info_success(self, mock_service):
        """测试获取比赛信息 - 成功"""
        # Mock数据库查询
        mock_session = AsyncMock()
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now()
        mock_match.match_status = "scheduled"
        mock_match.season = "2024-25"

        mock_result = MagicMock()
        mock_result.first.return_value = mock_match
        mock_session.execute.return_value = mock_result

        # 正确mock异步上下文管理器
        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        mock_service.db_manager.get_async_session.return_value.__aexit__.return_value = (
            None
        )

        # 调用方法
        _result = await mock_service._get_match_info(12345)

        # 验证结果
        assert _result is not None
        assert _result["id"] == 12345
        assert _result["home_team_id"] == 10
        assert _result["away_team_id"] == 20

    @pytest.mark.asyncio
    async def test_get_match_info_not_found(self, mock_service):
        """测试获取比赛信息 - 比赛不存在"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        # 正确mock异步上下文管理器
        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        mock_service.db_manager.get_async_session.return_value.__aexit__.return_value = (
            None
        )

        _result = await mock_service._get_match_info(99999)

        assert _result is None

    @pytest.mark.asyncio
    async def test_calculate_actual_result(self, mock_service):
        """测试计算实际比赛结果"""
        # 主队赢
        assert mock_service._calculate_actual_result(2, 1) == "home"
        # 客队赢
        assert mock_service._calculate_actual_result(1, 2) == "away"
        # 平局
        assert mock_service._calculate_actual_result(1, 1) == "draw"

    @pytest.mark.asyncio
    async def test_prediction_result_to_dict(self, sample_prediction_result):
        """测试PredictionResult转换为字典"""
        result_dict = sample_prediction_result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["match_id"] == 12345
        assert result_dict["model_version"] == "1.0"
        assert result_dict["predicted_result"] == "home"
        assert result_dict["home_win_probability"] == 0.45
        assert "created_at" in result_dict

    @pytest.mark.asyncio
    async def test_get_production_model_from_cache(self, mock_service, mock_model):
        """测试从缓存获取生产模型"""
        # 设置缓存
        cache_key = "model:football_baseline_model"
        await mock_service.model_cache.set(cache_key, (mock_model, "1.0"))

        # 获取模型
        model, version = await mock_service.get_production_model()

        assert model is mock_model
        assert version == "1.0"

    @pytest.mark.asyncio
    async def test_get_production_model_load_new(self, mock_service, mock_model):
        """测试加载新的生产模型"""
        with patch.object(
            mock_service, "get_production_model_with_retry"
        ) as mock_retry:
            mock_retry.return_value = (mock_model, "2.0")

            model, version = await mock_service.get_production_model("test_model")

            assert model is mock_model
            assert version == "2.0"
            mock_retry.assert_called_once_with("test_model")

    @pytest.mark.asyncio
    async def test_get_production_model_cache_miss(self, mock_service, mock_model):
        """测试缓存未命中时加载模型"""
        with patch.object(
            mock_service, "get_production_model_with_retry"
        ) as mock_retry:
            mock_retry.return_value = (mock_model, "2.0")

            # 第一次调用会加载模型
            model1, version1 = await mock_service.get_production_model()
            # 第二次调用应该使用缓存
            model2, version2 = await mock_service.get_production_model()

            assert model1 is model2
            assert version1 == version2
            mock_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_match_success(self, mock_service, mock_model):
        """测试预测比赛结果 - 成功"""
        # Mock依赖
        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "_get_match_info") as mock_match_info,
            patch.object(
                mock_service.feature_store, "get_match_features_for_prediction"
            ) as mock_features,
            patch.object(mock_service, "_store_prediction"),
        ):
            # 设置mock返回值
            mock_get_model.return_value = (mock_model, "1.0")
            mock_match_info.return_value = {
                "id": 12345,
                "home_team_id": 10,
                "away_team_id": 20,
            }
            mock_features.return_value = {"home_recent_wins": 2, "away_recent_wins": 1}

            # 执行预测
            _result = await mock_service.predict_match(12345)

            # 验证结果
            assert isinstance(result, PredictionResult)
            assert _result.match_id == 12345
            assert _result.model_version == "1.0"
            assert _result.predicted_result == "home"
            assert _result.home_win_probability == 0.45
            assert _result.confidence_score == 0.45

    @pytest.mark.asyncio
    async def test_predict_match_with_cached_result(self, mock_service):
        """测试使用缓存预测结果"""
        # 设置缓存的预测结果
        cached_result = PredictionResult(
            match_id=12345,
            model_version="1.0",
            predicted_result="home",
            home_win_probability=0.45,
        )
        cache_key = "prediction:12345"
        await mock_service.prediction_cache.set(cache_key, cached_result)

        # 执行预测
        _result = await mock_service.predict_match(12345)

        # 应该返回缓存的结果
        assert _result is cached_result

    @pytest.mark.asyncio
    async def test_predict_match_using_default_features(self, mock_service, mock_model):
        """测试特征获取失败时使用默认特征"""
        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "_get_match_info") as mock_match_info,
            patch.object(
                mock_service.feature_store, "get_match_features_for_prediction"
            ) as mock_features,
            patch.object(mock_service, "_store_prediction"),
        ):
            mock_get_model.return_value = (mock_model, "1.0")
            mock_match_info.return_value = {
                "id": 12345,
                "home_team_id": 10,
                "away_team_id": 20,
            }
            # 特征获取失败
            mock_features.side_effect = Exception("Feature service unavailable")

            _result = await mock_service.predict_match(12345)

            # 应该使用默认特征继续预测
            assert isinstance(result, PredictionResult)
            assert _result.match_id == 12345

    @pytest.mark.asyncio
    async def test_predict_match_match_not_found(self, mock_service, mock_model):
        """测试预测不存在的比赛"""
        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "_get_match_info") as mock_match_info,
        ):
            mock_get_model.return_value = (mock_model, "1.0")
            mock_match_info.return_value = None  # 比赛不存在

            with pytest.raises(ValueError, match="比赛 12345 不存在"):
                await mock_service.predict_match(12345)

    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(self, mock_service, mock_model):
        """测试批量预测 - 成功"""
        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "predict_match") as mock_predict,
        ):
            mock_get_model.return_value = (mock_model, "1.0")

            # Mock单个预测结果
            result1 = PredictionResult(match_id=12345, model_version="1.0")
            _result2 = PredictionResult(match_id=12346, model_version="1.0")
            mock_predict.side_effect = [result1, result2]

            # 执行批量预测
            results = await mock_service.batch_predict_matches([12345, 12346])

            # 验证结果
            assert len(results) == 2
            assert results[0].match_id == 12345
            assert results[1].match_id == 12346
            # 模型应该只加载一次
            mock_get_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_predict_with_cached_results(self, mock_service, mock_model):
        """测试批量预测使用缓存结果"""
        # 设置部分缓存结果
        cached_result = PredictionResult(match_id=12345, model_version="1.0")
        await mock_service.prediction_cache.set("prediction:12345", cached_result)

        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "predict_match") as mock_predict,
        ):
            mock_get_model.return_value = (mock_model, "1.0")
            _result2 = PredictionResult(match_id=12346, model_version="1.0")
            mock_predict.return_value = result2

            results = await mock_service.batch_predict_matches([12345, 12346])

            # 第一个应该使用缓存，第二个应该预测
            assert len(results) == 2
            assert results[0] is cached_result
            assert results[1].match_id == 12346
            # 只调用一次predict_match
            mock_predict.assert_called_once_with(12346)

    @pytest.mark.asyncio
    async def test_batch_predict_partial_failure(self, mock_service, mock_model):
        """测试批量预测部分失败"""
        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "predict_match") as mock_predict,
        ):
            mock_get_model.return_value = (mock_model, "1.0")

            # 第一个成功，第二个失败
            result1 = PredictionResult(match_id=12345, model_version="1.0")
            mock_predict.side_effect = [result1, Exception("Prediction failed")]

            results = await mock_service.batch_predict_matches([12345, 12346])

            # 应该只返回成功的结果
            assert len(results) == 1
            assert results[0].match_id == 12345

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, mock_service):
        """测试验证预测结果 - 成功"""
        mock_session = AsyncMock()
        mock_match = MagicMock()
        mock_match.home_score = 2
        mock_match.away_score = 1

        mock_result = MagicMock()
        mock_result.first.return_value = mock_match
        mock_session.execute.return_value = mock_result

        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # 执行验证
        success = await mock_service.verify_prediction(12345)

        assert success is True
        # 验证SQL更新被执行
        mock_session.execute.assert_called()
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_verify_prediction_match_not_finished(self, mock_service):
        """测试验证未结束的比赛"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None  # 比赛未结束或不存在
        mock_session.execute.return_value = mock_result

        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        success = await mock_service.verify_prediction(12345)

        assert success is False

    @pytest.mark.asyncio
    async def test_get_model_accuracy_success(self, mock_service):
        """测试获取模型准确率 - 成功"""
        mock_session = AsyncMock()
        mock_row = MagicMock()
        mock_row.total = 100
        mock_row.correct = 75

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        accuracy = await mock_service.get_model_accuracy("test_model", 7)

        assert accuracy == 0.75

    @pytest.mark.asyncio
    async def test_get_model_accuracy_no_data(self, mock_service):
        """测试获取模型准确率 - 无数据"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        accuracy = await mock_service.get_model_accuracy("test_model", 7)

        assert accuracy is None

    @pytest.mark.asyncio
    async def test_get_prediction_statistics(self, mock_service):
        """测试获取预测统计信息"""
        mock_session = AsyncMock()
        mock_row1 = MagicMock()
        mock_row1.model_version = "1.0"
        mock_row1.total_predictions = 100
        mock_row1.avg_confidence = 0.75
        mock_row1.home_predictions = 40
        mock_row1.draw_predictions = 30
        mock_row1.away_predictions = 30
        mock_row1.correct_predictions = 70
        mock_row1.verified_predictions = 90

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row1]))
        mock_session.execute.return_value = mock_result

        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        _stats = await mock_service.get_prediction_statistics(30)

        assert stats["period_days"] == 30
        assert len(stats["statistics"]) == 1
        stat = stats["statistics"][0]
        assert stat["model_version"] == "1.0"
        assert stat["total_predictions"] == 100
        assert stat["accuracy"] == 70 / 90  # 0.777...

    @pytest.mark.asyncio
    async def test_store_prediction(self, mock_service, sample_prediction_result):
        """测试存储预测结果"""
        mock_session = AsyncMock()
        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        await mock_service._store_prediction(sample_prediction_result)

        # 验证session.add被调用
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_prediction_failure(
        self, mock_service, sample_prediction_result
    ):
        """测试存储预测结果失败"""
        mock_session = AsyncMock()
        mock_session.add.side_effect = Exception("Database error")
        mock_service.db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        with pytest.raises(Exception, match="Database error"):
            await mock_service._store_prediction(sample_prediction_result)

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_prediction_service_with_mlflow_error(self, mock_service):
        """测试MLflow错误处理"""
        with patch.object(mock_service, "get_production_model") as mock_get_model:
            mock_get_model.side_effect = Exception("MLflow connection failed")

            with pytest.raises(Exception, match="MLflow connection failed"):
                await mock_service.predict_match(12345)

    @pytest.mark.asyncio
    async def test_prediction_result_metadata(self, mock_service, mock_model):
        """测试预测结果元数据"""
        with (
            patch.object(mock_service, "get_production_model") as mock_get_model,
            patch.object(mock_service, "_get_match_info") as mock_match_info,
            patch.object(
                mock_service.feature_store, "get_match_features_for_prediction"
            ) as mock_features,
            patch.object(mock_service, "_store_prediction"),
        ):
            mock_get_model.return_value = (mock_model, "1.0")
            mock_match_info.return_value = {
                "id": 12345,
                "home_team_id": 10,
                "away_team_id": 20,
            }
            mock_features.return_value = {"feature1": 1.0, "feature2": 2.0}

            _result = await mock_service.predict_match(12345)

            # 验证元数据
            assert _result.prediction_metadata is not None
            assert "model_uri" in result.prediction_metadata
            assert "prediction_time" in result.prediction_metadata
            assert "feature_count" in result.prediction_metadata
            assert (
                result.prediction_metadata["model_uri"]
                == "models:/football_baseline_model/1.0"
            )
