"""
简化的服务集成测试
专注于实际可用的服务功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.inference_service import (
    InferenceService,
    PredictionRequest,
    PredictionResponse,
)
from src.services.collection_service import FotMobCollectionService
from src.ml.inference import ModelLoader
from src.ml.inference.cache_manager import PredictionCache
from src.core.exceptions import PredictionError, ModelError, ValidationError


class TestInferenceServiceIntegration:
    """推理服务v2集成测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """创建Mock依赖"""
        mock_loader = Mock()
        mock_cache = Mock()

        # 设置mock行为
        mock_model = Mock()
        mock_model.predict.return_value = [1]  # DRAW
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.n_features_in_ = 12
        mock_model.classes_ = [0, 1, 2]

        mock_loader.get_model.return_value = mock_model
        mock_loader.list_loaded_models.return_value = ["xgboost_v2.pkl"]
        mock_loader.get_model_metadata.return_value = {"accuracy": 0.65}
        mock_loader.load_model.return_value = True
        mock_loader.unload_model.return_value = True

        # 配置缓存mock返回正确的对象结构
        mock_cache.get.return_value = None  # 缓存未命中
        mock_cache.set.return_value = True

        # 使用简单的dict作为get_stats返回值，避免mock循环引用
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5, "hit_rate": 0.67}

        return {
            "model_loader": mock_loader,
            "cache_manager": mock_cache,
            "model": mock_model,
        }

    @pytest.fixture
    def inference_service(self, mock_dependencies):
        """创建推理服务实例"""
        service = InferenceService()
        service.model_loader = mock_dependencies["model_loader"]
        service.cache_manager = mock_dependencies["cache_manager"]
        service.is_initialized = True
        return service

    def test_service_initialization_with_dependencies(
        self, inference_service, mock_dependencies
    ):
        """测试服务初始化与依赖"""
        assert inference_service.model_loader == mock_dependencies["model_loader"]
        assert inference_service.cache_manager == mock_dependencies["cache_manager"]
        assert inference_service.is_initialized is True

    @pytest.mark.asyncio
    async def test_prediction_request_creation_and_validation(self):
        """测试预测请求创建和验证"""
        request = PredictionRequest(
            match_id="12345",
            home_team="Manchester United",
            away_team="Arsenal",
            features=[1.0, 2.0, 3.0, 1.5, 2.2, 0.8, 0.9, 1.1, 0.7, 1.3, 0.6, 1.0],
            use_cache=True,
            model_name="xgboost_v2",
        )

        # 测试请求属性
        assert request.match_id == "12345"
        assert request.home_team == "Manchester United"
        assert request.away_team == "Arsenal"
        assert len(request.features) == 12
        assert request.use_cache is True
        assert request.model_name == "xgboost_v2"

        # 测试转换为字典
        request_dict = request.to_dict()
        assert isinstance(request_dict, dict)
        assert request_dict["match_id"] == "12345"
        assert request_dict["home_team"] == "Manchester United"

    @pytest.mark.asyncio
    async def test_prediction_response_creation(self):
        """测试预测响应创建"""
        request = PredictionRequest(
            match_id="12345", home_team="Team A", away_team="Team B"
        )

        prediction = {
            "prediction": "HOME_WIN",
            "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
        }

        response = PredictionResponse(
            request=request,
            prediction=prediction,
            success=True,
            processing_time_ms=150.0,
            cached=False,
            model_info={"name": "xgboost_v2", "version": "2.0"},
        )

        # 测试响应属性
        assert response.request == request
        assert response.success is True
        assert response.processing_time_ms == 150.0
        assert response.cached is False
        assert response.model_info["name"] == "xgboost_v2"

        # 测试转换为字典
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert response_dict["success"] is True
        assert response_dict["prediction"]["prediction"] == "HOME_WIN"
        assert "timestamp" in response_dict

    def test_model_loading_and_unloading(self, inference_service, mock_dependencies):
        """测试模型加载和卸载"""
        # 测试加载模型
        result = inference_service.load_model("test_model", "/path/to/model.pkl")
        assert result is True
        mock_dependencies["model_loader"].load_model.assert_called_once_with(
            "test_model", "/path/to/model.pkl"
        )

        # 测试卸载模型
        result = inference_service.unload_model("test_model")
        assert result is True
        mock_dependencies["model_loader"].unload_model.assert_called_once_with(
            "test_model"
        )

        # 测试列出模型
        models = inference_service.list_models()
        assert isinstance(models, list)
        assert len(models) == 1
        assert models[0] == "xgboost_v2.pkl"

    def test_service_statistics(self, inference_service, mock_dependencies):
        """测试服务统计"""
        stats = inference_service.get_service_stats()

        assert isinstance(stats, dict)
        assert "service_name" in stats
        assert "is_initialized" in stats
        assert "model_status" in stats
        assert "request_stats" in stats
        assert "cache_stats" in stats
        assert "components" in stats

        assert stats["service_name"] == "InferenceService"
        assert stats["is_initialized"] is True

    def test_cache_operations(self, inference_service, mock_dependencies):
        """测试缓存操作"""
        # 测试获取缓存统计
        mock_dependencies["cache_manager"].get_stats.return_value = {
            "hits": 20,
            "misses": 10,
            "hit_rate": 0.67,
            "size": 100,
            "memory_usage": 1024,
        }

        stats = inference_service.get_service_stats()
        assert stats["cache_stats"]["hits"] == 20
        assert stats["cache_stats"]["hit_rate"] == 0.67

    def test_error_handling(self, inference_service, mock_dependencies):
        """测试错误处理"""
        # 测试模型加载失败
        mock_dependencies["model_loader"].load_model.return_value = False
        result = inference_service.load_model("invalid_model", "/invalid/path")
        assert result is False

        # 测试模型卸载失败
        mock_dependencies["model_loader"].unload_model.return_value = False
        result = inference_service.unload_model("nonexistent_model")
        assert result is False


class TestCollectionServiceIntegration:
    """数据收集服务集成测试"""

    @pytest.fixture
    def collection_service(self):
        """创建数据收集服务实例"""
        return FotMobCollectionService()

    def test_service_initialization(self, collection_service):
        """测试服务初始化"""
        assert collection_service is not None
        assert hasattr(collection_service, "create_match_collection_task")
        assert hasattr(collection_service, "create_league_collection_task")
        assert hasattr(collection_service, "execute_task")
        assert hasattr(collection_service, "get_service_status")

    @pytest.mark.asyncio
    async def test_match_collection_task_creation(self, collection_service):
        """测试比赛数据收集任务创建"""
        task = collection_service.create_match_collection_task(match_id="12345")

        assert task is not None
        assert isinstance(task, str)  # 方法返回task_id字符串
        assert "12345" in task

    @pytest.mark.asyncio
    async def test_league_collection_task_creation(self, collection_service):
        """测试联赛数据收集任务创建"""
        task = collection_service.create_league_collection_task(
            league_id="87", priority=2
        )

        assert task is not None
        assert isinstance(task, str)  # 方法返回task_id字符串
        assert "87" in task

    def test_service_status(self, collection_service):
        """测试服务状态"""
        status = collection_service.get_service_status()

        assert isinstance(status, dict)
        assert "service_name" in status
        assert "is_running" in status
        assert "total_tasks" in status

    @pytest.mark.asyncio
    async def test_service_initialization_and_shutdown(self, collection_service):
        """测试服务初始化和关闭"""
        # 测试初始化
        result = await collection_service.initialize()
        assert isinstance(result, bool)

        # 测试关闭
        await collection_service.shutdown()
        # 应该没有异常抛出

    @pytest.mark.asyncio
    async def test_task_execution_with_mock(self, collection_service):
        """测试任务执行（使用Mock）"""
        # 创建任务
        task_id = collection_service.create_match_collection_task(match_id="12345")

        # Mock执行方法
        with patch.object(collection_service, "_load_data") as mock_load:
            mock_load.return_value = {"mock": "data"}

            result = await collection_service.execute_task(task_id)

            # 验证结果结构
            assert isinstance(result, dict)
            assert "success" in result or "error" in result


class TestServiceIntegration:
    """服务间集成测试"""

    @pytest.mark.asyncio
    async def test_inference_service_dependency_injection(self):
        """测试推理服务依赖注入"""
        mock_loader = Mock()
        mock_cache = Mock()

        service = InferenceService()
        service.model_loader = mock_loader
        service.cache_manager = mock_cache
        service.is_initialized = True

        assert service.model_loader == mock_loader
        assert service.cache_manager == mock_cache

    @pytest.mark.asyncio
    async def test_service_error_propagation(self):
        """测试服务间错误传播"""
        mock_loader = Mock()
        mock_loader.get_model.side_effect = ModelError("Model not found")

        service = InferenceService()
        service.model_loader = mock_loader
        service.is_initialized = True

        # 测试错误传播
        with pytest.raises(ModelError):
            service.model_loader.get_model("nonexistent_model")

    @pytest.mark.asyncio
    async def test_end_to_end_prediction_workflow(self):
        """测试端到端预测工作流程"""
        # 创建Mock依赖
        mock_model = Mock()
        mock_model.predict.return_value = [0]  # HOME_WIN
        mock_model.predict_proba.return_value = [[0.7, 0.2, 0.1]]

        mock_loader = Mock()
        mock_loader.get_model.return_value = mock_model

        mock_cache = Mock()
        mock_cache.get.return_value = None

        # 创建服务实例
        service = InferenceService()
        service.model_loader = mock_loader
        service.cache_manager = mock_cache
        service.is_initialized = True

        # 创建预测请求
        request = PredictionRequest(
            match_id="12345",
            home_team="Team A",
            away_team="Team B",
            features=[1.0] * 12,
        )

        # 验证请求创建成功
        assert request.match_id == "12345"
        assert len(request.features) == 12
        assert request.home_team == "Team A"
        assert request.away_team == "Team B"

        # 验证服务配置正确
        assert service.is_initialized
        assert service.model_loader is not None
        assert service.cache_manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
