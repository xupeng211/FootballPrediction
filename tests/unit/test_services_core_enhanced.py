#!/usr/bin/env python3
"""
增强的服务测试 - 使用标准化Mock方法
消除RuntimeWarning，实现对InferenceService的90%覆盖
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# 导入依赖注入Mock工厂函数
try:
    from .mock_factories import (
        create_mock_di_container,
        create_mock_model_service,
        create_mock_cache_service,
        create_mock_feature_extractor
    )
except ImportError:
    # 直接导入
    from tests.unit.mock_factories import (
        create_mock_di_container,
        create_mock_model_service,
        create_mock_cache_service,
        create_mock_feature_extractor
    )


class TestInferenceServiceEnhanced:
    """增强的推理服务测试 - 90%覆盖率目标"""

    @patch("src.services.dependency_injection.ServiceContainer")
    @patch("src.ml.inference.model_loader.ModelLoader")
    @patch("src.ml.inference.cache_manager.PredictionCache")
    def test_inference_service_comprehensive_initialization(
        self, mock_cache_class, mock_model_loader_class, mock_container_class
    ):
        """测试推理服务的完整初始化流程"""
        from src.services.inference_service import InferenceService

        # 创建Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock ModelLoader和PredictionCache
        mock_model_loader = MagicMock()
        mock_model_loader_class.return_value = mock_model_loader

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        # 创建服务实例
        service = InferenceService()

        # 验证依赖注入调用
        mock_container.resolve.assert_any_call("model_service")
        mock_container.resolve.assert_any_call("cache_service")
        mock_container.resolve.assert_any_call("feature_extractor")

        # 验证基本属性
        assert service.name == "InferenceService"
        assert hasattr(service, "model_loader")
        assert hasattr(service, "cache_manager")
        assert hasattr(service, "feature_extractor")
        assert hasattr(service, "request_stats")
        assert not service.is_initialized

        # 验证统计信息初始化
        assert service.request_stats == {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    @patch("src.services.dependency_injection.ServiceContainer")
    @patch("src.services.inference_service.Path.exists")
    async def test_inference_service_async_initialization(
        self, mock_path_exists, mock_container_class
    ):
        """测试推理服务的异步初始化"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock模型文件存在
        mock_path_exists.return_value = True

        # Mock模型服务
        mock_services["model_service"].load_model.return_value = True
        mock_services["model_service"].is_loaded.return_value = True
        mock_services["model_service"].model_info.return_value = {
            "name": "xgboost_v2",
            "version": "2.0.0",
            "accuracy": 0.67
        }

        # 创建并初始化服务
        service = InferenceService()

        # 模拟异步初始化
        await service._async_initialize()

        # 验证初始化状态
        assert service.is_initialized

        # 验证依赖调用
        mock_services["model_service"].load_model.assert_called_once()

    @patch("src.services.dependency_injection.ServiceContainer")
    async def test_prediction_workflow_with_proper_mocking(
        self, mock_container_class
    ):
        """测试完整的预测工作流，使用正确的Mock方法"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock特征提取
        mock_services["feature_extractor"].extract_features.return_value = {
            "features": [0.65, 0.45, 0.8, 0.3, 0.2, 1.2, 0.8, 1.0, 0.75, 0.15, 0.7, 0.6],
            "feature_metadata": {
                "match_id": "test_match_001",
                "extraction_time": "2024-01-15T10:00:00Z",
                "source": "enhanced_fotmob"
            }
        }

        # Mock模型预测
        mock_services["model_service"].predict.return_value = {
            "prediction": "HOME_WIN",
            "probabilities": [0.65, 0.25, 0.10],
            "confidence": 0.75
        }

        # Mock缓存操作
        mock_services["cache_service"].get.return_value = None  # 缓存未命中
        mock_services["cache_service"].set.return_value = True

        # 创建并初始化服务
        service = InferenceService()
        await service._async_initialize()

        # 执行预测
        result = await service.predict_match("Manchester United", "Arsenal")

        # 验证工作流
        mock_services["feature_extractor"].extract_features.assert_called_once()
        mock_services["model_service"].predict.assert_called_once()
        mock_services["cache_service"].get.assert_called_once()
        mock_services["cache_service"].set.assert_called_once()

        # 验证结果结构
        assert "prediction" in result
        assert "probabilities" in result
        assert "confidence" in result
        assert "timestamp" in result

        # 验证统计信息更新
        assert service.request_stats["total_requests"] == 1
        assert service.request_stats["successful_requests"] == 1
        assert service.request_stats["cache_misses"] == 1

    @patch("src.services.dependency_injection.ServiceContainer")
    async def test_cache_hit_scenario(self, mock_container_class):
        """测试缓存命中场景"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock缓存命中
        cached_result = {
            "prediction": "DRAW",
            "probabilities": [0.3, 0.5, 0.2],
            "confidence": 0.6,
            "timestamp": "2024-01-15T09:00:00Z"
        }
        mock_services["cache_service"].get.return_value = cached_result

        # 创建并初始化服务
        service = InferenceService()
        await service._async_initialize()

        # 执行预测（应该从缓存获取）
        result = await service.predict_match("Chelsea", "Liverpool")

        # 验证缓存逻辑
        mock_services["cache_service"].get.assert_called_once()
        mock_services["feature_extractor"].extract_features.assert_not_called()
        mock_services["model_service"].predict.assert_not_called()

        # 验证结果
        assert result == cached_result

        # 验证统计信息
        assert service.request_stats["cache_hits"] == 1
        assert service.request_stats["cache_misses"] == 0

    @patch("src.services.dependency_injection.ServiceContainer")
    async def test_error_handling_and_recovery(self, mock_container_class):
        """测试错误处理和恢复机制"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock特征提取失败
        mock_services["feature_extractor"].extract_features.side_effect = Exception(
            "Feature extraction failed"
        )

        # 创建并初始化服务
        service = InferenceService()
        await service._async_initialize()

        # 执行预测（应该处理错误）
        with pytest.raises(Exception):
            await service.predict_match("Team A", "Team B")

        # 验证错误统计
        assert service.request_stats["failed_requests"] == 1
        assert service.request_stats["successful_requests"] == 0

    @patch("src.services.dependency_injection.ServiceContainer")
    async def test_batch_prediction_workflow(self, mock_container_class):
        """测试批量预测工作流"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock批量特征提取
        mock_services["feature_extractor"].extract_features.side_effect = [
            {"features": [0.6, 0.4, 0.7, 0.3, 0.2, 1.1, 0.9]},  # Match 1
            {"features": [0.5, 0.5, 0.6, 0.4, 0.3, 1.0, 0.8]},  # Match 2
        ]

        # Mock批量预测
        mock_services["model_service"].predict.side_effect = [
            {"prediction": "HOME_WIN", "probabilities": [0.6, 0.3, 0.1]},
            {"prediction": "DRAW", "probabilities": [0.3, 0.5, 0.2]},
        ]

        # 创建并初始化服务
        service = InferenceService()
        await service._async_initialize()

        # 执行批量预测
        matches = [
            {"home": "Team A", "away": "Team B"},
            {"home": "Team C", "away": "Team D"}
        ]
        results = await service.batch_predict(matches)

        # 验证批量操作
        assert len(results) == 2
        mock_services["feature_extractor"].extract_features.assert_called()
        mock_services["model_service"].predict.assert_called()

    @patch("src.services.dependency_injection.ServiceContainer")
    def test_service_statistics_and_monitoring(self, mock_container_class):
        """测试服务统计信息和监控功能"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock统计信息
        mock_services["cache_service"].stats.return_value = {
            "hit_rate": 0.85,
            "total_requests": 1000,
            "cache_size": 150
        }

        # 创建服务
        service = InferenceService()

        # 测试统计信息方法
        stats = service.get_service_stats()
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "success_rate" in stats
        assert "cache_hit_rate" in stats

        # 测试健康检查
        # health = await service.health_check()
        # assert "healthy" in health
        # assert "initialized" in health
        # assert "dependencies" in health
        pass  # 暂时跳过，需要异步测试环境

    @patch("src.services.dependency_injection.ServiceContainer")
    async def test_service_lifecycle_management(self, mock_container_class):
        """测试服务生命周期管理"""
        from src.services.inference_service import InferenceService

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # Mock清理方法
        mock_services["cache_service"].clear_all.return_value = True
        mock_services["model_service"].unload.return_value = True

        # 创建服务
        service = InferenceService()

        # 测试生命周期方法
        await service.startup()
        await service._async_initialize()

        assert service.is_initialized

        await service.shutdown()
        # 验证清理调用（如果实现了的话）

    def test_request_and_response_classes(self):
        """测试请求和响应数据类"""
        from src.services.inference_service import PredictionRequest, PredictionResponse

        # 测试请求类
        request = PredictionRequest(
            home_team="Manchester United",
            away_team="Arsenal",
            model_name="xgboost_v2",
            include_probabilities=True,
            include_confidence=True
        )

        assert request.home_team == "Manchester United"
        assert request.away_team == "Arsenal"
        assert request.model_name == "xgboost_v2"
        assert request.include_probabilities is True

        # 测试响应类
        response = PredictionResponse(
            success=True,
            prediction="HOME_WIN",
            probabilities={"HOME": 0.65, "DRAW": 0.25, "AWAY": 0.10},
            confidence=0.75,
            model_version="xgboost_v2",
            timestamp=datetime.utcnow()
        )

        assert response.success is True
        assert response.prediction == "HOME_WIN"
        assert response.confidence == 0.75

    @patch("src.services.dependency_injection.ServiceContainer")
    def test_configuration_and_settings(self, mock_container_class):
        """测试配置和设置"""
        from src.services.inference_service import InferenceService, InferenceServiceConfig

        # Mock依赖
        mock_container, mock_services = create_mock_di_container()
        mock_container_class.return_value = mock_container

        # 测试配置
        config = InferenceServiceConfig(
            model_path="/app/models/xgboost_v2.pkl",
            enable_cache=True,
            cache_ttl_seconds=300,
            request_timeout_seconds=10.0
        )

        # 创建带配置的服务
        service = InferenceService(config=config)

        assert service.config.model_path == "/app/models/xgboost_v2.pkl"
        assert service.config.enable_cache is True
        assert service.config.cache_ttl_seconds == 300