"""
V2服务层测试
测试inference_service_v2和其他v2服务功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.inference_service_v2 import InferenceServiceV2
from src.core.exceptions import PredictionError, ModelError, ValidationError


class TestInferenceServiceV2:
    """V2推理服务测试"""

    @pytest.fixture
    def mock_model_loader(self):
        """Mock模型加载器"""
        loader = Mock()
        mock_model = Mock()
        mock_model.predict.return_value = [1]  # Draw
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.n_features_in_ = 3
        mock_model.classes_ = [0, 1, 2]

        loader.get_model.return_value = mock_model
        loader.get_model_metadata.return_value = Mock()
        loader.list_models.return_value = ["xgboost_v2.pkl", "neural_net_v1.pkl"]

        return loader

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock缓存管理器"""
        cache = Mock()
        cache.get.return_value = None  # 默认缓存未命中
        cache.set.return_value = True
        cache.clear.return_value = True
        cache.get_stats.return_value = {"hits": 10, "misses": 5, "hit_rate": 0.67}

        return cache

    @pytest.fixture
    def inference_service(self):
        """推理服务实例"""
        # 修复构造函数参数，只接受model_path参数
        return InferenceServiceV2(model_path="test_model_path")

    def test_service_initialization(self, inference_service):
        """测试服务初始化"""
        # 检查组件是否正确初始化
        assert inference_service.model_loader is not None
        assert inference_service.cache_manager is not None
        assert inference_service.feature_extractor is not None
        assert inference_service.default_model_path == "test_model_path"
        assert inference_service.default_model_name == "football_model"

    @pytest.mark.asyncio
    async def test_predict_match_simple(self, inference_service):
        """测试简化预测接口"""
        # Mock内部组件
        with patch.object(inference_service, "is_initialized", True):
            # Mock预测器
            mock_predictor = Mock()
            mock_predictor.predict = AsyncMock(
                return_value={
                    "prediction": "HOME_WIN",
                    "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
                }
            )
            mock_predictor.get_model_info.return_value = {"name": "test_model"}

            with patch("src.ml.inference.MatchPredictor", return_value=mock_predictor):
                result = await inference_service.predict_match_simple(
                    match_id="123", home_team="Manchester United", away_team="Arsenal"
                )

                # 验证结果结构
                assert "request" in result
                assert "prediction" in result
                assert "success" in result
                assert result["success"] is True
                assert result["prediction"]["prediction"] == "HOME_WIN"

    @pytest.mark.asyncio
    async def test_predict_with_cache_hit(self, inference_service, mock_cache_manager):
        """测试缓存命中"""
        # 设置缓存命中
        cached_result = {
            "prediction": "HOME_WIN",
            "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
            "confidence": 0.6,
            "model_name": "xgboost_v2",
            "cached": True,
        }
        mock_cache_manager.get.return_value = cached_result

        features = [1.0, 2.0, 3.0]

        result = await inference_service.predict_single_match(
            home_team="Team A", away_team="Team B", features=features
        )

        # 应该返回缓存结果
        assert result == cached_result
        assert result["cached"] is True

        # 验证没有调用模型
        inference_service.model_loader.get_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_predict_with_different_model(
        self, inference_service, mock_model_loader
    ):
        """测试使用不同模型预测"""
        features = [1.0, 2.0, 3.0]
        model_name = "neural_net_v1"

        result = await inference_service.predict_single_match(
            home_team="Team A",
            away_team="Team B",
            features=features,
            model_name=model_name,
        )

        # 验证使用了指定模型
        mock_model_loader.get_model.assert_called_with(model_name)
        assert result["model_name"] == model_name

    @pytest.mark.asyncio
    async def test_predict_invalid_features(self, inference_service):
        """测试无效特征"""
        invalid_features = []  # 空特征列表

        with pytest.raises(ValidationError):
            await inference_service.predict_single_match(
                home_team="Team A", away_team="Team B", features=invalid_features
            )

    @pytest.mark.asyncio
    async def test_predict_model_not_found(self, inference_service, mock_model_loader):
        """测试模型未找到"""
        mock_model_loader.get_model.return_value = None
        features = [1.0, 2.0, 3.0]

        with pytest.raises(ModelError):
            await inference_service.predict_single_match(
                home_team="Team A", away_team="Team B", features=features
            )

    @pytest.mark.asyncio
    async def test_predict_batch_matches(self, inference_service):
        """测试批量预测"""
        matches = [
            {"home_team": "Team A", "away_team": "Team B", "features": [1.0, 2.0, 3.0]},
            {"home_team": "Team C", "away_team": "Team D", "features": [4.0, 5.0, 6.0]},
        ]

        results = await inference_service.predict_batch_matches(matches)

        # 验证批量结果
        assert len(results) == 2
        for result in results:
            assert "prediction" in result
            assert "probabilities" in result
            assert "confidence" in result
            assert "model_name" in result

    @pytest.mark.asyncio
    async def test_get_available_models(self, inference_service, mock_model_loader):
        """测试获取可用模型列表"""
        models = await inference_service.get_available_models()

        # 验证返回模型列表
        assert isinstance(models, list)
        assert len(models) > 0

        # 验证调用了模型加载器
        mock_model_loader.list_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_service_stats(self, inference_service, mock_cache_manager):
        """测试获取服务统计"""
        stats = await inference_service.get_service_stats()

        # 验证统计信息结构
        assert isinstance(stats, dict)
        assert "predictions_count" in stats
        assert "cache_hit_rate" in stats
        assert "models_loaded" in stats
        assert "service_uptime" in stats

        # 验证缓存统计
        mock_cache_manager.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache(self, inference_service, mock_cache_manager):
        """测试清除缓存"""
        await inference_service.clear_cache()

        # 验证调用了缓存清除
        mock_cache_manager.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_features(self, inference_service):
        """测试特征验证"""
        # 有效特征
        valid_features = [1.0, 2.0, 3.0]
        assert await inference_service._validate_features(valid_features) is True

        # 无效特征 - 空列表
        invalid_features = []
        with pytest.raises(ValidationError):
            await inference_service._validate_features(invalid_features)

        # 无效特征 - 包含非数字
        invalid_features = [1.0, "invalid", 3.0]
        with pytest.raises(ValidationError):
            await inference_service._validate_features(invalid_features)

        # 无效特征 - 长度不匹配
        too_short_features = [1.0, 2.0]  # 需要至少3个特征
        with pytest.raises(ValidationError):
            await inference_service._validate_features(too_short_features)

    @pytest.mark.asyncio
    async def test_format_prediction_result(self, inference_service):
        """测试预测结果格式化"""
        mock_model = Mock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.classes_ = [0, 1, 2]

        raw_result = {
            "predicted_class": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "processing_time": 0.1,
        }

        formatted_result = await inference_service._format_prediction_result(
            raw_result=raw_result,
            model=mock_model,
            model_name="test_model",
            home_team="Team A",
            away_team="Team B",
        )

        # 验证格式化结果
        assert formatted_result["prediction"] == "DRAW"
        assert formatted_result["probabilities"]["HOME_WIN"] == 0.2
        assert formatted_result["probabilities"]["DRAW"] == 0.5
        assert formatted_result["probabilities"]["AWAY_WIN"] == 0.3
        assert formatted_result["model_name"] == "test_model"
        assert formatted_result["home_team"] == "Team A"
        assert formatted_result["away_team"] == "Team B"

    def test_service_config_validation(self):
        """测试服务配置验证"""
        # 测试有效配置
        config = {
            "model_loader": Mock(),
            "cache_manager": Mock(),
            "default_model": "test_model",
        }

        service = InferenceServiceV2(**config)
        assert service.default_model == "test_model"

        # 测试无效配置 - 缺少必需参数
        with pytest.raises(ValueError):
            InferenceServiceV2(
                model_loader=Mock(),
                cache_manager=Mock(),
                # 缺少 default_model
            )

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, inference_service):
        """测试错误处理和恢复"""
        features = [1.0, 2.0, 3.0]

        # 模拟模型加载失败
        inference_service.model_loader.get_model.side_effect = [
            None,  # 第一次失败
            Mock(),  # 第二次成功
        ]

        # 第一次调用应该失败
        with pytest.raises(ModelError):
            await inference_service.predict_single_match(
                home_team="Team A", away_team="Team B", features=features
            )

        # 重置side effect
        inference_service.model_loader.get_model.side_effect = None
        inference_service.model_loader.get_model.return_value = Mock(
            predict=Mock(return_value=[1]),
            predict_proba=Mock(return_value=[[0.2, 0.5, 0.3]]),
            classes_=[0, 1, 2],
        )

        # 第二次调用应该成功
        result = await inference_service.predict_single_match(
            home_team="Team A", away_team="Team B", features=features
        )

        assert "prediction" in result

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, inference_service):
        """测试并发预测"""
        import asyncio

        async def predict_task(match_data):
            return await inference_service.predict_single_match(**match_data)

        matches = [
            {"home_team": "Team A", "away_team": "Team B", "features": [1.0, 2.0, 3.0]},
            {"home_team": "Team C", "away_team": "Team D", "features": [4.0, 5.0, 6.0]},
            {"home_team": "Team E", "away_team": "Team F", "features": [7.0, 8.0, 9.0]},
        ]

        # 并发执行多个预测
        tasks = [predict_task(match) for match in matches]
        results = await asyncio.gather(*tasks)

        # 验证所有预测都成功
        assert len(results) == 3
        for result in results:
            assert "prediction" in result
            assert "probabilities" in result

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, inference_service):
        """测试性能监控"""
        features = [1.0, 2.0, 3.0]

        # 执行预测
        result = await inference_service.predict_single_match(
            home_team="Team A", away_team="Team B", features=features
        )

        # 验证性能指标被记录
        assert "processing_time" in result
        assert result["processing_time"] > 0

        # 获取服务统计
        stats = await inference_service.get_service_stats()
        assert "predictions_count" in stats
        assert "average_processing_time" in stats

    def test_service_logging(self, inference_service, caplog):
        """测试服务日志记录"""
        # 由于这是异步测试，我们需要在异步上下文中测试
        import logging

        # 设置日志级别
        logger = logging.getLogger("src.services.inference_service_v2")
        logger.setLevel(logging.INFO)

        # 创建服务实例（会记录初始化日志）
        service = InferenceServiceV2(
            model_loader=Mock(), cache_manager=Mock(), default_model="test_model"
        )

        # 验证日志记录
        assert "InferenceServiceV2 initialized" in caplog.text


class TestServiceIntegration:
    """服务集成测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock所有依赖"""
        mock_model_loader = Mock()
        mock_cache_manager = Mock()
        mock_metrics_collector = Mock()

        # 设置mock行为
        mock_model = Mock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.n_features_in_ = 3
        mock_model.classes_ = [0, 1, 2]

        mock_model_loader.get_model.return_value = mock_model
        mock_cache_manager.get.return_value = None
        mock_cache_manager.set.return_value = True

        return {
            "model_loader": mock_model_loader,
            "cache_manager": mock_cache_manager,
            "metrics_collector": mock_metrics_collector,
        }

    @pytest.mark.asyncio
    async def test_end_to_end_prediction_flow(self, mock_dependencies):
        """测试端到端预测流程"""
        service = InferenceServiceV2(
            model_loader=mock_dependencies["model_loader"],
            cache_manager=mock_dependencies["cache_manager"],
            default_model="xgboost_v2",
        )

        # 模拟完整的预测流程
        features = [1.0, 2.0, 3.0]
        home_team = "Manchester United"
        away_team = "Liverpool"

        # 1. 验证特征
        validated_features = await service._validate_features(features)
        assert validated_features is True

        # 2. 检查缓存
        cached_result = mock_dependencies["cache_manager"].get.return_value
        assert cached_result is None  # 缓存未命中

        # 3. 获取模型
        model = mock_dependencies["model_loader"].get_model("xgboost_v2")
        assert model is not None

        # 4. 执行预测
        raw_result = {
            "predicted_class": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "processing_time": 0.15,
        }

        # 5. 格式化结果
        formatted_result = await service._format_prediction_result(
            raw_result=raw_result,
            model=model,
            model_name="xgboost_v2",
            home_team=home_team,
            away_team=away_team,
        )

        # 6. 缓存结果
        mock_dependencies["cache_manager"].set.assert_called_once()

        # 验证最终结果
        assert formatted_result["home_team"] == home_team
        assert formatted_result["away_team"] == away_team
        assert formatted_result["prediction"] == "DRAW"

    @pytest.mark.asyncio
    async def test_service_lifecycle(self, mock_dependencies):
        """测试服务生命周期"""
        # 1. 创建服务
        service = InferenceServiceV2(
            model_loader=mock_dependencies["model_loader"],
            cache_manager=mock_dependencies["cache_manager"],
        )

        # 2. 执行预测
        result = await service.predict_single_match(
            home_team="Team A", away_team="Team B", features=[1.0, 2.0, 3.0]
        )

        assert result is not None

        # 3. 获取统计
        stats = await service.get_service_stats()
        assert stats["predictions_count"] >= 1

        # 4. 清理缓存
        await service.clear_cache()
        mock_dependencies["cache_manager"].clear.assert_called_once()

    def test_service_configuration_compatibility(self):
        """测试服务配置兼容性"""
        # 测试多种配置方式
        configs = [
            # 最小配置
            {
                "model_loader": Mock(),
                "cache_manager": Mock(),
                "default_model": "test_model",
            },
            # 完整配置
            {
                "model_loader": Mock(),
                "cache_manager": Mock(),
                "default_model": "test_model",
                "cache_ttl": 3600,
                "max_concurrent_predictions": 10,
            },
        ]

        for config in configs:
            service = InferenceServiceV2(**config)
            assert service.model_loader is not None
            assert service.cache_manager is not None
            assert service.default_model == "test_model"


if __name__ == "__main__":
    # 运行服务测试
    pytest.main([__file__, "-v", "-s"])
