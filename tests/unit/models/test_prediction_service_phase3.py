"""
Phase 3：预测服务模块综合测试
目标：全面提升prediction_service.py模块覆盖率到60%+
重点：测试预测服务核心功能、模型加载、预测逻辑、缓存机制、结果验证和批量处理
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest


class MockAsyncResult:
    """Mock for SQLAlchemy async result with proper scalars().all() support"""

    def __init__(self, scalars_result=None, scalar_one_or_none_result=None):
        self._scalars_result = scalars_result or []
        self._scalar_one_or_none_result = scalar_one_or_none_result

    def scalars(self):
        return MockScalarResult(self._scalars_result)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_result


class MockScalarResult:
    """Mock for SQLAlchemy scalars() result"""

    def __init__(self, result):
        self._result = result if isinstance(result, list) else [result]

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.prediction_service import PredictionResult, PredictionService


class TestPredictionServiceBasic:
    """预测服务基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    def test_service_initialization(self):
        """测试预测服务初始化"""
        assert self.service is not None
        assert hasattr(self.service, "mlflow_tracking_uri")
        assert hasattr(self.service, "model_cache")
        assert hasattr(self.service, "cache_ttl")
        assert hasattr(self.service, "retries")
        assert hasattr(self.service, "timeout")
        assert self.service.mlflow_tracking_uri == "http://localhost:5002"
        assert isinstance(self.service.model_cache, dict)
        assert self.service.cache_ttl > 0


class TestPredictionServiceModelLoading:
    """预测服务模型加载测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    @pytest.mark.asyncio
    async def test_get_production_model_success(self):
        """测试成功获取生产模型"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1, 0, 1])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.3, 0.5]])

        with patch("src.models.prediction_service.mlflow") as mock_mlflow:
            # Mock MLflow运行
            mock_run = MagicMock()
            mock_run.info.run_id = "test_run_id"
            mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
            mock_mlflow.start_run.return_value.__exit__.return_value = None

            # Mock MLflow客户端
            mock_client = MagicMock()
            mock_client.get_latest_versions.return_value = [MagicMock(version="1")]
            mock_client.get_model_version_download_uri.return_value = "test_uri"
            mock_client.transition_model_version_stage.return_value = None
            mock_client.update_model_version.return_value = None

            # Mock模型加载
            with patch(
                "src.models.prediction_service.mlflow.sklearn.load_model"
            ) as mock_load:
                mock_load.return_value = mock_model

                model, run_id = await self.service.get_production_model("test_model")

                assert model is not None
                assert run_id == "test_run_id"
                mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_production_model_default_name(self):
        """测试使用默认模型名称获取生产模型"""
        mock_model = MagicMock()

        with patch("src.models.prediction_service.mlflow") as mock_mlflow:
            mock_run = MagicMock()
            mock_run.info.run_id = "default_run_id"
            mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
            mock_mlflow.start_run.return_value.__exit__.return_value = None

            mock_client = MagicMock()
            mock_client.get_latest_versions.return_value = [MagicMock(version="1")]
            mock_client.get_model_version_download_uri.return_value = "test_uri"

            with patch(
                "src.models.prediction_service.mlflow.sklearn.load_model"
            ) as mock_load:
                mock_load.return_value = mock_model

                model, run_id = await self.service.get_production_model()

                assert model is not None
                assert run_id == "default_run_id"

    @pytest.mark.asyncio
    async def test_get_production_model_no_versions(self):
        """测试没有可用模型版本的情况"""
        with patch("src.models.prediction_service.mlflow") as mock_mlflow:
            mock_client = MagicMock()
            mock_client.get_latest_versions.return_value = []

            with pytest.raises(ValueError, match="No available versions"):
                await self.service.get_production_model("nonexistent_model")

    @pytest.mark.asyncio
    async def test_get_production_model_load_error(self):
        """测试模型加载错误处理"""
        with patch("src.models.prediction_service.mlflow") as mock_mlflow:
            mock_run = MagicMock()
            mock_run.info.run_id = "test_run_id"
            mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
            mock_mlflow.start_run.return_value.__exit__.return_value = None

            mock_client = MagicMock()
            mock_client.get_latest_versions.return_value = [MagicMock(version="1")]
            mock_client.get_model_version_download_uri.return_value = "test_uri"

            with patch(
                "src.models.prediction_service.mlflow.sklearn.load_model"
            ) as mock_load:
                mock_load.side_effect = Exception("Model load error")

                with pytest.raises(Exception, match="Model load error"):
                    await self.service.get_production_model("test_model")

    @pytest.mark.asyncio
    async def test_get_production_model_cache_hit(self):
        """测试模型缓存命中"""
        # 预先缓存模型
        cached_model = MagicMock()
        self.service.model_cache["test_model"] = {
            "model": cached_model,
            "timestamp": datetime.now(),
            "run_id": "cached_run_id",
        }

        model, run_id = await self.service.get_production_model("test_model")

        assert model is cached_model
        assert run_id == "cached_run_id"

    @pytest.mark.asyncio
    async def test_get_production_model_cache_expired(self):
        """测试模型缓存过期"""
        # 预先缓存过期模型
        cached_model = MagicMock()
        expired_time = datetime.now() - timedelta(hours=2)  # 2小时前
        self.service.model_cache["test_model"] = {
            "model": cached_model,
            "timestamp": expired_time,
            "run_id": "expired_run_id",
        }

        mock_model = MagicMock()

        with patch("src.models.prediction_service.mlflow") as mock_mlflow:
            mock_run = MagicMock()
            mock_run.info.run_id = "new_run_id"
            mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
            mock_mlflow.start_run.return_value.__exit__.return_value = None

            mock_client = MagicMock()
            mock_client.get_latest_versions.return_value = [MagicMock(version="1")]
            mock_client.get_model_version_download_uri.return_value = "test_uri"

            with patch(
                "src.models.prediction_service.mlflow.sklearn.load_model"
            ) as mock_load:
                mock_load.return_value = mock_model

                model, run_id = await self.service.get_production_model("test_model")

                assert model is mock_model  # 应该返回新加载的模型
                assert run_id == "new_run_id"


class TestPredictionServiceMatchPrediction:
    """预测服务比赛预测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    @pytest.mark.asyncio
    async def test_predict_match_success(self):
        """测试成功预测比赛"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])  # 预测主队胜利
        mock_model.predict_proba.return_value = np.array(
            [[0.2, 0.3, 0.5]]
        )  # [客场, 平局, 主队]

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            result = await self.service.predict_match(12345)

            assert isinstance(result, PredictionResult)
            assert result.match_id == 12345
            assert result.predicted_result == "home"  # 主队胜利
            assert abs(result.confidence_score - 0.5) < 0.001  # 主队胜利概率
            assert result.run_id == "test_run_id"
            assert result.prediction_time is not None

    @pytest.mark.asyncio
    async def test_predict_match_draw_prediction(self):
        """测试平局预测"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0])  # 预测平局
        mock_model.predict_proba.return_value = np.array([[0.2, 0.5, 0.3]])

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            result = await self.service.predict_match(12345)

            assert result.predicted_result == "draw"
            assert abs(result.confidence_score - 0.5) < 0.001

    @pytest.mark.asyncio
    async def test_predict_match_away_prediction(self):
        """测试客场胜利预测"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2])  # 预测客场胜利
        mock_model.predict_proba.return_value = np.array([[0.6, 0.2, 0.2]])

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            result = await self.service.predict_match(12345)

            assert result.predicted_result == "away"
            assert abs(result.confidence_score - 0.6) < 0.001

    @pytest.mark.asyncio
    async def test_predict_match_model_loading_failure(self):
        """测试模型加载失败"""
        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.side_effect = Exception("Model loading failed")

            with pytest.raises(Exception, match="Model loading failed"):
                await self.service.predict_match(12345)

    @pytest.mark.asyncio
    async def test_predict_match_prediction_error(self):
        """测试预测过程错误"""
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Prediction error")

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            with pytest.raises(Exception, match="Prediction error"):
                await self.service.predict_match(12345)


class TestPredictionServiceResultVerification:
    """预测服务结果验证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    @pytest.mark.asyncio
    async def test_verify_prediction_correct_prediction(self):
        """测试验证正确预测"""
        # 创建一个正确的预测结果
        prediction_time = datetime.now() - timedelta(hours=1)
        self.service.prediction_cache[12345] = {
            "predicted_result": "home",
            "confidence_score": 0.8,
            "prediction_time": prediction_time,
            "run_id": "test_run_id",
        }

        with patch("src.database.connection.DatabaseManager") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_session = AsyncMock()
            mock_match = MagicMock()
            mock_match.home_score = 2
            mock_match.away_score = 1
            mock_match.match_status = "completed"
            mock_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_match
            )

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            result = await self.service.verify_prediction(12345)

            assert result is True  # 主队2:1胜利，预测正确

    @pytest.mark.asyncio
    async def test_verify_prediction_incorrect_prediction(self):
        """测试验证错误预测"""
        prediction_time = datetime.now() - timedelta(hours=1)
        self.service.prediction_cache[12345] = {
            "predicted_result": "home",
            "confidence_score": 0.8,
            "prediction_time": prediction_time,
            "run_id": "test_run_id",
        }

        with patch("src.database.connection.DatabaseManager") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_session = AsyncMock()
            mock_match = MagicMock()
            mock_match.home_score = 1
            mock_match.away_score = 2
            mock_match.match_status = "completed"
            mock_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_match
            )

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            result = await self.service.verify_prediction(12345)

            assert result is False  # 客场胜利，预测错误

    @pytest.mark.asyncio
    async def test_verify_prediction_draw_prediction(self):
        """测试验证平局预测"""
        prediction_time = datetime.now() - timedelta(hours=1)
        self.service.prediction_cache[12345] = {
            "predicted_result": "draw",
            "confidence_score": 0.6,
            "prediction_time": prediction_time,
            "run_id": "test_run_id",
        }

        with patch("src.database.connection.DatabaseManager") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_session = AsyncMock()
            mock_match = MagicMock()
            mock_match.home_score = 1
            mock_match.away_score = 1
            mock_match.match_status = "completed"
            mock_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_match
            )

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            result = await self.service.verify_prediction(12345)

            assert result is True  # 平局，预测正确

    @pytest.mark.asyncio
    async def test_verify_prediction_no_prediction_found(self):
        """测试验证不存在的预测"""
        result = await self.service.verify_prediction(99999)

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_prediction_match_not_completed(self):
        """测试验证未完成的比赛"""
        prediction_time = datetime.now() - timedelta(hours=1)
        self.service.prediction_cache[12345] = {
            "predicted_result": "home",
            "confidence_score": 0.8,
            "prediction_time": prediction_time,
            "run_id": "test_run_id",
        }

        with patch("src.database.connection.DatabaseManager") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_session = AsyncMock()
            mock_match = MagicMock()
            mock_match.home_score = None
            mock_match.away_score = None
            mock_match.match_status = "scheduled"
            mock_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_match
            )

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            result = await self.service.verify_prediction(12345)

            assert result is False  # 比赛未完成，无法验证

    @pytest.mark.asyncio
    async def test_verify_prediction_database_error(self):
        """测试数据库错误处理"""
        prediction_time = datetime.now() - timedelta(hours=1)
        self.service.prediction_cache[12345] = {
            "predicted_result": "home",
            "confidence_score": 0.8,
            "prediction_time": prediction_time,
            "run_id": "test_run_id",
        }

        with patch("src.database.connection.DatabaseManager") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db
            mock_db.get_async_session.side_effect = Exception("Database error")

            result = await self.service.verify_prediction(12345)

            assert result is False  # 数据库错误，返回False


class TestPredictionServiceBatchPrediction:
    """预测服务批量预测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    @pytest.mark.asyncio
    async def test_batch_predict_matches_success(self):
        """测试成功批量预测"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1, 0, 2])  # [主队, 平局, 客场]
        mock_model.predict_proba.return_value = np.array(
            [
                [0.2, 0.3, 0.5],  # 主队胜利
                [0.2, 0.5, 0.3],  # 平局
                [0.6, 0.2, 0.2],  # 客场胜利
            ]
        )

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            results = await self.service.batch_predict_matches([12345, 67890, 11111])

            assert len(results) == 3
            assert results[0].match_id == 12345
            assert results[0].predicted_result == "home"
            assert results[0].confidence_score == 0.5

            assert results[1].match_id == 67890
            assert results[1].predicted_result == "draw"
            assert results[1].confidence_score == 0.5

            assert results[2].match_id == 11111
            assert results[2].predicted_result == "away"
            assert results[2].confidence_score == 0.6

    @pytest.mark.asyncio
    async def test_batch_predict_matches_empty_list(self):
        """测试空列表批量预测"""
        results = await self.service.batch_predict_matches([])

        assert results == []

    @pytest.mark.asyncio
    async def test_batch_predict_matches_partial_failure(self):
        """测试部分失败的批量预测"""
        mock_model = MagicMock()
        mock_model.predict.side_effect = [
            np.array([1]),
            Exception("Prediction error"),
            np.array([2]),
        ]
        mock_model.predict_proba.side_effect = [
            np.array([[0.2, 0.3, 0.5]]),
            Exception("Prediction error"),
            np.array([[0.6, 0.2, 0.2]]),
        ]

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            results = await self.service.batch_predict_matches([12345, 67890, 11111])

            assert len(results) == 2  # 只有2个成功
            assert results[0].match_id == 12345
            assert results[1].match_id == 11111

    @pytest.mark.asyncio
    async def test_batch_predict_matches_model_loading_failure(self):
        """测试模型加载失败的批量预测"""
        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.side_effect = Exception("Model loading failed")

            with pytest.raises(Exception, match="Model loading failed"):
                await self.service.batch_predict_matches([12345, 67890])


class TestPredictionServiceCacheManagement:
    """预测服务缓存管理测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self):
        """测试清理过期缓存"""
        # 添加一些缓存数据
        current_time = datetime.now()
        expired_time = current_time - timedelta(hours=2)
        valid_time = current_time - timedelta(minutes=30)

        self.service.model_cache["expired_model"] = {
            "model": MagicMock(),
            "timestamp": expired_time,
            "run_id": "expired_run",
        }
        self.service.model_cache["valid_model"] = {
            "model": MagicMock(),
            "timestamp": valid_time,
            "run_id": "valid_run",
        }

        self.service.prediction_cache[12345] = {
            "predicted_result": "home",
            "confidence_score": 0.8,
            "prediction_time": expired_time,
            "run_id": "test_run_id",
        }
        self.service.prediction_cache[67890] = {
            "predicted_result": "away",
            "confidence_score": 0.6,
            "prediction_time": valid_time,
            "run_id": "test_run_id",
        }

        # 清理过期缓存
        await self.service._cleanup_expired_cache()

        # 检查过期缓存被删除
        assert "expired_model" not in self.service.model_cache
        assert "valid_model" in self.service.model_cache
        assert 12345 not in self.service.prediction_cache
        assert 67890 in self.service.prediction_cache

    def test_is_cache_expired(self):
        """测试缓存过期检查"""
        current_time = datetime.now()
        expired_time = current_time - timedelta(hours=2)
        valid_time = current_time - timedelta(minutes=30)

        assert self.service._is_cache_expired(expired_time) is True
        assert self.service._is_cache_expired(valid_time) is False


class TestPredictionServiceIntegration:
    """预测服务集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.service = PredictionService()

    @pytest.mark.asyncio
    async def test_complete_prediction_workflow(self):
        """测试完整的预测工作流"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.3, 0.5]])

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            # 执行预测
            result = await self.service.predict_match(12345)

            assert result.match_id == 12345
            assert result.predicted_result == "home"
            assert result.confidence_score == 0.5

            # 验证预测被缓存
            assert 12345 in self.service.prediction_cache
            cached_prediction = self.service.prediction_cache[12345]
            assert cached_prediction["predicted_result"] == "home"
            assert cached_prediction["confidence_score"] == 0.5

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self):
        """测试并发预测"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.3, 0.5]])

        with patch.object(self.service, "get_production_model") as mock_get_model:
            mock_get_model.return_value = (mock_model, "test_run_id")

            # 并发执行多个预测
            import asyncio

            tasks = [self.service.predict_match(i) for i in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            for i, result in enumerate(results):
                assert result.match_id == i
                assert result.predicted_result == "home"
                assert result.confidence_score == 0.5

    def test_prediction_result_serialization(self):
        """测试预测结果序列化"""
        result = PredictionResult(
            match_id=12345,
            predicted_result="home",
            confidence_score=0.8,
            run_id="test_run_id",
            prediction_time=datetime.now(),
        )

        # 检查可以转换为字典
        result_dict = result.__dict__
        assert "match_id" in result_dict
        assert "predicted_result" in result_dict
        assert "confidence_score" in result_dict
        assert "run_id" in result_dict
        assert "prediction_time" in result_dict

    def test_service_configuration_consistency(self):
        """测试服务配置一致性"""
        assert self.service.cache_ttl > 0
        assert self.service.retries >= 0
        assert self.service.timeout > 0
        assert isinstance(self.service.model_cache, dict)
        assert isinstance(self.service.prediction_cache, dict)
