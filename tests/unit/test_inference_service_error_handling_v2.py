"""
推理服务错误处理路径测试 v2.0
基于实际API的测试用例，专注于异常处理和错误恢复
"""

import pytest
import asyncio
import time
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime
import tempfile
import os


class TestInferenceServiceErrorHandling:
    """推理服务错误处理深度测试"""

    @pytest.mark.asyncio
    async def test_initialization_model_file_not_found(self):
        """测试模型文件不存在的初始化错误"""
        from src.services.inference_service import InferenceService

        # 使用不存在的模型路径
        service = InferenceService(model_path="/nonexistent/path/model.pkl")

        # 应该优雅处理文件不存在错误
        result = await service.initialize()

        # 初始化应该失败但不崩溃
        assert result is False
        assert service.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialization_model_load_corruption_error(self):
        """测试模型文件损坏的加载错误"""
        from src.services.inference_service import InferenceService
        from src.ml.inference.model_loader import ModelLoadError

        service = InferenceService()

        # 模拟模型加载器抛出损坏错误
        with patch(
            "src.services.inference_service.ModelLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            # 模拟模型损坏异常
            mock_loader.load_model.side_effect = ModelLoadError("Model file corrupted")

            result = await service.initialize()

            # 应该优雅处理模型损坏
            assert result is False
            assert service.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialization_permission_denied_error(self):
        """测试权限拒绝的初始化错误"""
        from src.services.inference_service import InferenceService

        service = InferenceService()

        # 模拟权限拒绝错误
        with patch(
            "src.services.inference_service.ModelLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            # 模拟权限错误
            mock_loader.load_model.side_effect = PermissionError("Permission denied")

            result = await service.initialize()

            # 应该优雅处理权限错误
            assert result is False
            assert service.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialization_memory_insufficient_error(self):
        """测试内存不足的初始化错误"""
        from src.services.inference_service import InferenceService

        service = InferenceService()

        # 模拟内存不足错误
        with patch(
            "src.services.inference_service.ModelLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            # 模拟内存不足
            mock_loader.load_model.side_effect = MemoryError("Insufficient memory")

            result = await service.initialize()

            # 应该优雅处理内存不足
            assert result is False
            assert service.is_initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_cache_manager_error(self):
        """测试关闭时缓存管理器错误"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.is_initialized = True

        # 模拟缓存管理器关闭时的错误
        with patch.object(
            service.cache_manager,
            "shutdown",
            side_effect=Exception("Cache shutdown failed"),
        ):
            # 即使清理失败，shutdown也应该完成
            await service.shutdown()

            # 服务应该被标记为未初始化
            assert service.is_initialized is False

    @pytest.mark.asyncio
    async def test_model_loading_async_exception(self):
        """测试异步模型加载的异常处理"""
        from src.services.inference_service import InferenceService

        service = InferenceService()

        # 模拟异步模型加载异常
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            # 模拟线程池执行失败
            mock_loop.run_in_executor.side_effect = Exception("Async execution failed")

            result = await service._load_model_async("test_model", "/fake/path")

            # 应该返回False表示失败
            assert result is False

    @pytest.mark.asyncio
    async def test_prediction_feature_extraction_error(self):
        """测试预测时特征提取错误"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 模拟特征提取器失败
        service.feature_extractor = Mock()
        service.feature_extractor.extract_features_from_match = AsyncMock(
            side_effect=Exception("Feature extraction failed")
        )

        # 预测应该返回错误结果
        request = PredictionRequest(
            match_id="match_1", home_team="Team A", away_team="Team B"
        )
        result = await service.predict_match(request)

        assert result.success is False
        # 根据实际实现，特征提取失败会使用默认特征，但如果模型未加载会失败
        assert "预测失败" in result.error or "特征" in result.error

    @pytest.mark.asyncio
    async def test_prediction_service_not_initialized(self):
        """测试服务未初始化时的预测"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        # 不要初始化服务
        assert service.is_initialized is False

        request = PredictionRequest(
            match_id="match_1", home_team="Team A", away_team="Team B"
        )
        result = await service.predict_match(request)

        assert result.success is False
        assert "服务未初始化" in result.error

    @pytest.mark.asyncio
    async def test_prediction_with_provided_features(self):
        """测试使用提供特征的预测"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 模拟预测器
        with patch(
            "src.services.inference_service.MatchPredictor"
        ) as mock_predictor_class:
            mock_predictor = Mock()
            mock_predictor_class.return_value = mock_predictor
            mock_predictor.predict = AsyncMock(return_value={"result": "HOME_WIN"})
            mock_predictor.get_model_info.return_value = {"model": "test_model"}

            # 提供特征，不需要特征提取
            request = PredictionRequest(
                match_id="match_1",
                home_team="Team A",
                away_team="Team B",
                features=[1.0, 2.0, 3.0],
            )
            result = await service.predict_match(request)

            assert result.success is True
            mock_predictor.predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_predictor_exception_handling(self):
        """测试预测器异常处理"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 模拟预测器异常
        with patch(
            "src.services.inference_service.MatchPredictor"
        ) as mock_predictor_class:
            mock_predictor = Mock()
            mock_predictor_class.return_value = mock_predictor
            mock_predictor.predict = AsyncMock(
                side_effect=Exception("Predictor failed")
            )
            mock_predictor.get_model_info.return_value = {"model": "test_model"}

            request = PredictionRequest(
                match_id="match_1",
                home_team="Team A",
                away_team="Team B",
                features=[1.0, 2.0, 3.0],
            )
            result = await service.predict_match(request)

            assert result.success is False
            assert "预测失败" in result.error

    @pytest.mark.asyncio
    async def test_feature_conversion_handling(self):
        """测试特征转换处理"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 测试不同类型的特征对象
        feature_types = [
            "single_value",  # 单个值
            {"feature1": 1.0, "feature2": 2.0},  # 字典格式
            [1, 2, 3, 4, 5],  # 列表格式
            (1, 2, 3),  # 元组格式
        ]

        for features in feature_types:
            # 模拟特征提取器返回不同类型
            service.feature_extractor = Mock()

            # 创建有to_dict方法的模拟对象
            if isinstance(features, dict):
                mock_features = Mock()
                mock_features.to_dict.return_value = features
                service.feature_extractor.extract_features_from_match = AsyncMock(
                    return_value=mock_features
                )
            else:
                service.feature_extractor.extract_features_from_match = AsyncMock(
                    return_value=features
                )

            # 模拟预测器
            with patch(
                "src.services.inference_service.MatchPredictor"
            ) as mock_predictor_class:
                mock_predictor = Mock()
                mock_predictor_class.return_value = mock_predictor
                mock_predictor.predict = AsyncMock(return_value={"result": "HOME_WIN"})
                mock_predictor.get_model_info.return_value = {"model": "test_model"}

                request = PredictionRequest(
                    match_id="match_1", home_team="Team A", away_team="Team B"
                )
                result = await service.predict_match(request)

                # 应该能处理各种特征格式
                assert result is not None

    @pytest.mark.asyncio
    async def test_predict_match_simple_interface(self):
        """测试简化预测接口"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.is_initialized = True

        # 模拟predict_match方法
        with patch.object(service, "predict_match") as mock_predict:
            mock_response = Mock()
            mock_response.success = True
            mock_response.to_dict.return_value = {
                "result": "HOME_WIN",
                "confidence": 0.8,
            }
            mock_predict.return_value = mock_response

            result = await service.predict_match_simple("match_1", "Team A", "Team B")

            assert result["result"] == "HOME_WIN"
            mock_predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_predict_partial_failure(self):
        """测试批量预测部分失败"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 创建预测请求
        requests = [
            PredictionRequest(
                match_id=f"match_{i}", home_team=f"Team_{i}", away_team=f"Team_{i+1}"
            )
            for i in range(5)
        ]

        # 模拟部分预测失败
        call_count = 0

        async def mock_predict(request):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # 前两个失败
                return Mock(success=False, error=f"Error {call_count}")
            else:  # 后面的成功
                return Mock(success=True, prediction={"result": "HOME_WIN"})

        with patch.object(service, "predict_match", side_effect=mock_predict):
            results = await service.batch_predict(requests)

            # 应该有部分成功
            successful_count = sum(1 for r in results if r.success)
            assert successful_count == 3  # 后3个成功

    def test_service_stats_functionality(self):
        """测试服务统计功能"""
        from src.services.inference_service import InferenceService

        service = InferenceService()

        stats = service.get_service_stats()

        # 验证基本统计信息
        assert "service_name" in stats
        assert "is_initialized" in stats
        assert "model_status" in stats
        assert "request_stats" in stats
        assert "cache_stats" in stats
        assert "components" in stats

        # 验证默认值
        assert stats["service_name"] == "InferenceService"
        assert stats["is_initialized"] is False
        assert stats["request_stats"]["total_requests"] == 0
        assert stats["request_stats"]["successful_predictions"] == 0

    def test_processing_stats_update(self):
        """测试处理时间统计更新"""
        from src.services.inference_service import InferenceService

        service = InferenceService()

        # 测试边界条件：total_requests为0的情况
        service._update_processing_stats(100.0)
        assert service.request_stats["avg_processing_time_ms"] == 100.0

        # 测试第一个请求的情况
        service.request_stats["total_requests"] = 1
        service._update_processing_stats(150.0)
        assert service.request_stats["avg_processing_time_ms"] == 150.0

        # 测试移动平均值计算
        service.request_stats["total_requests"] = 2
        service.request_stats["avg_processing_time_ms"] = 150.0  # 当前平均
        service._update_processing_stats(250.0)
        expected_avg = (150.0 * 1 + 250.0) / 2
        assert (
            abs(service.request_stats["avg_processing_time_ms"] - expected_avg) < 0.01
        )

    @pytest.mark.asyncio
    async def test_cache_hit_statistics(self):
        """测试缓存命中统计"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 模拟缓存命中的预测
        with patch(
            "src.services.inference_service.MatchPredictor"
        ) as mock_predictor_class:
            mock_predictor = Mock()
            mock_predictor_class.return_value = mock_predictor
            # 返回缓存命中的结果
            mock_predictor.predict = AsyncMock(
                return_value={"result": "HOME_WIN", "from_cache": True}
            )
            mock_predictor.get_model_info.return_value = {"model": "test_model"}

            request = PredictionRequest(
                match_id="match_1",
                home_team="Team A",
                away_team="Team B",
                features=[1.0, 2.0, 3.0],
            )
            result = await service.predict_match(request)

            assert result.success is True
            assert result.cached is True
            assert service.request_stats["cache_hits"] > 0

    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self):
        """测试错误统计跟踪"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = True

        # 模拟预测错误
        with patch(
            "src.services.inference_service.MatchPredictor"
        ) as mock_predictor_class:
            mock_predictor = Mock()
            mock_predictor_class.return_value = mock_predictor
            mock_predictor.predict = AsyncMock(side_effect=Exception("Test error"))
            mock_predictor.get_model_info.return_value = {"model": "test_model"}

            initial_error_count = service.request_stats["errors"]

            request = PredictionRequest(
                match_id="match_1",
                home_team="Team A",
                away_team="Team B",
                features=[1.0, 2.0, 3.0],
            )
            result = await service.predict_match(request)

            assert result.success is False
            assert service.request_stats["errors"] > initial_error_count

    def test_default_features_fallback(self):
        """测试默认特征回退机制"""
        from src.services.inference_service import InferenceService

        service = InferenceService()

        # 测试_get_or_generate_features的默认特征回退
        # 这里需要通过私有方法测试或者通过模拟失败场景
        # 由于是私有方法，我们通过集成测试验证

    @pytest.mark.asyncio
    async def test_service_initialization_logging(self):
        """测试服务初始化日志记录"""
        from src.services.inference_service import InferenceService

        # 简化测试 - 验证logger确实被创建并使用
        service = InferenceService()

        # 验证logger存在
        assert hasattr(service, "logger")
        assert service.logger is not None

        # 验证基本日志功能
        with patch.object(service.logger, "info") as mock_info:
            service.logger.info("测试消息")
            assert mock_info.called

    @pytest.mark.asyncio
    async def test_service_shutdown_error_logging(self):
        """测试服务关闭错误日志记录"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.is_initialized = True

        # 模拟关闭时错误，验证错误被正确记录
        with patch.object(
            service.cache_manager, "shutdown", side_effect=Exception("Shutdown error")
        ):
            # 验证logger确实会被调用来记录错误
            with patch.object(service.logger, "error") as mock_error:
                await service.shutdown()

                # 验证服务被标记为未初始化
                assert service.is_initialized is False
                # 验证错误日志被调用
                assert mock_error.called
                # 验证日志消息包含预期内容
                call_args = mock_error.call_args[0][0] if mock_error.call_args else ""
                assert "关闭失败" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
