"""
ML推理模块扩展测试
基于实际API的全面测试，专注于推理组件功能
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import patch, Mock, AsyncMock
import pickle
import tempfile
import os


class TestModelLoader:
    """模型加载器测试"""

    def test_model_loader_creation(self):
        """测试模型加载器创建"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        assert loader is not None
        assert hasattr(loader, "load_model")
        assert hasattr(loader, "get_model")
        assert hasattr(loader, "unload_model")

    def test_model_loader_load_model_success(self):
        """测试模型加载成功"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 创建临时模型文件
        model_data = {"test": "model", "version": "1.0"}
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pkl", delete=False) as f:
            pickle.dump(model_data, f)
            model_path = f.name

        try:
            # 模拟模型加载
            with patch("pickle.load", return_value=model_data):
                result = loader.load_model("test_model", model_path)

                assert result is True
        finally:
            os.unlink(model_path)

    def test_model_loader_load_model_file_not_found(self):
        """测试模型文件不存在"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError

        loader = ModelLoader()

        with pytest.raises(ModelLoadError):
            loader.load_model("test_model", "/nonexistent/path/model.pkl")

    def test_model_loader_load_model_corrupted(self):
        """测试模型文件损坏"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError

        loader = ModelLoader()

        # 创建损坏的模型文件
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pkl", delete=False) as f:
            f.write(b"corrupted data")
            model_path = f.name

        try:
            with pytest.raises(ModelLoadError):
                loader.load_model("test_model", model_path)
        finally:
            os.unlink(model_path)

    def test_model_loader_get_loaded_model(self):
        """测试获取已加载模型"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()
        mock_model = Mock()

        # 模拟模型已加载
        loader._models = {"test_model": mock_model}

        result = loader.get_model("test_model")

        assert result == mock_model

    def test_model_loader_get_unloaded_model(self):
        """测试获取未加载模型"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError

        loader = ModelLoader()

        with pytest.raises(ModelLoadError):
            loader.get_model("nonexistent_model")

    def test_model_loader_unload_model(self):
        """测试模型卸载"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()
        mock_model = Mock()

        # 模拟模型已加载
        loader._models = {"test_model": mock_model}

        result = loader.unload_model("test_model")

        assert result is True
        assert "test_model" not in loader._models

    def test_model_loader_list_models(self):
        """测试列出所有模型"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()
        mock_model1 = Mock()
        mock_model2 = Mock()

        # 模拟多个模型已加载
        loader._models = {"model1": mock_model1, "model2": mock_model2}

        models = loader.list_models()

        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models


class TestMatchPredictor:
    """比赛预测器测试"""

    def test_match_predictor_creation(self):
        """测试比赛预测器创建"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        predictor = MatchPredictor(model_loader=mock_loader)

        assert predictor.model_loader == mock_loader
        assert hasattr(predictor, "predict")
        assert hasattr(predictor, "predict_batch")

    def test_match_predictor_predict_success(self):
        """测试预测成功"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.6, 0.3, 0.1])
        mock_loader.get_model.return_value = mock_model

        predictor = MatchPredictor(model_loader=mock_loader)

        features = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = predictor.predict(features=features, model_name="test_model")

        assert "probabilities" in result
        assert "predicted_class" in result
        assert len(result["probabilities"]) == 3
        assert result["predicted_class"] == 0  # HOME_WIN (index 0)
        mock_model.predict.assert_called_once()

    def test_match_predictor_predict_model_not_loaded(self):
        """测试预测时模型未加载"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        mock_loader.get_model.side_effect = ModelLoadError("Model not loaded")

        predictor = MatchPredictor(model_loader=mock_loader)

        features = [1.0, 2.0, 3.0, 4.0, 5.0]

        with pytest.raises(ModelLoadError):
            predictor.predict(features=features, model_name="nonexistent_model")

    def test_match_predictor_predict_invalid_features(self):
        """测试预测时无效特征"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        mock_model = Mock()
        mock_model.predict.side_effect = ValueError("Invalid feature shape")

        predictor = MatchPredictor(model_loader=mock_loader)

        features = []  # 空特征

        with pytest.raises(ValueError):
            predictor.predict(features=features, model_name="test_model")

    def test_match_predictor_predict_with_cache(self):
        """测试带缓存的预测"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.6, 0.3, 0.1])
        mock_loader.get_model.return_value = mock_model

        predictor = MatchPredictor(model_loader=mock_loader)

        features = [1.0, 2.0, 3.0, 4.0, 5.0]

        # 第一次预测
        result1 = predictor.predict(
            features=features,
            model_name="test_model",
            use_cache=True,
            cache_key="test_key",
        )

        # 第二次预测（应该使用缓存）
        result2 = predictor.predict(
            features=features,
            model_name="test_model",
            use_cache=True,
            cache_key="test_key",
        )

        assert result1 == result2
        # 模型应该只被调用一次（第二次使用缓存）
        mock_model.predict.assert_called_once()

    def test_match_predictor_get_model_info(self):
        """测试获取模型信息"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        mock_model = Mock()
        mock_model.__dict__ = {
            "version": "1.0",
            "feature_names": ["f1", "f2", "f3"],
            "classes": ["HOME_WIN", "DRAW", "AWAY_WIN"],
        }
        mock_loader.get_model.return_value = mock_model

        predictor = MatchPredictor(model_loader=mock_loader)
        predictor.default_model_name = "test_model"

        info = predictor.get_model_info()

        assert info["model_name"] == "test_model"
        assert info["version"] == "1.0"
        assert "feature_names" in info
        assert "classes" in info


class TestCacheManager:
    """缓存管理器测试"""

    def test_cache_manager_creation(self):
        """测试缓存管理器创建"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache(max_size=100, ttl=300)

        assert cache.max_size == 100
        assert cache.ttl == 300
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")
        assert hasattr(cache, "clear")

    def test_cache_manager_set_and_get(self):
        """测试缓存设置和获取"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        # 设置缓存
        prediction_data = {
            "result": "HOME_WIN",
            "probabilities": [0.6, 0.3, 0.1],
            "confidence": 0.6,
        }
        cache.set("test_key", prediction_data)

        # 获取缓存
        result = cache.get("test_key")

        assert result == prediction_data

    def test_cache_manager_get_nonexistent(self):
        """测试获取不存在的缓存"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_manager_ttl_expiry(self):
        """测试缓存TTL过期"""
        from src.ml.inference.cache_manager import PredictionCache
        import time

        # 创建TTL为1秒的缓存
        cache = PredictionCache(ttl=1)

        prediction_data = {"result": "HOME_WIN"}
        cache.set("test_key", prediction_data)

        # 等待TTL过期
        time.sleep(1.1)

        result = cache.get("test_key")

        assert result is None

    def test_cache_manager_max_size_eviction(self):
        """测试缓存最大容量淘汰"""
        from src.ml.inference.cache_manager import PredictionCache

        # 创建容量为2的缓存
        cache = PredictionCache(max_size=2)

        # 添加3个缓存项
        cache.set("key1", {"result": "HOME_WIN"})
        cache.set("key2", {"result": "DRAW"})
        cache.set("key3", {"result": "AWAY_WIN"})

        # 检查最旧的项是否被淘汰
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_manager_clear(self):
        """测试缓存清空"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        # 添加一些缓存
        cache.set("key1", {"result": "HOME_WIN"})
        cache.set("key2", {"result": "DRAW"})

        # 清空缓存
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_manager_stats(self):
        """测试缓存统计"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        # 添加一些缓存
        cache.set("key1", {"result": "HOME_WIN"})
        cache.set("key2", {"result": "DRAW"})

        # 获取缓存命中
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()

        assert "total_requests" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "hit_rate" in stats
        assert stats["total_requests"] == 3
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 2
        assert stats["hit_rate"] == 1 / 3

    def test_cache_manager_cleanup_expired(self):
        """测试清理过期缓存"""
        from src.ml.inference.cache_manager import PredictionCache
        import time

        cache = PredictionCache(ttl=1)

        # 添加缓存
        cache.set("key1", {"result": "HOME_WIN"})
        cache.set("key2", {"result": "DRAW"})

        # 等待TTL过期
        time.sleep(1.1)

        # 添加新缓存（触发清理）
        cache.set("key3", {"result": "AWAY_WIN"})

        # 验证过期缓存被清理
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None


class TestInferenceIntegration:
    """推理集成测试"""

    def test_inference_pipeline_creation(self):
        """测试推理管道创建"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.cache_manager import PredictionCache

        mock_loader = Mock()
        predictor = MatchPredictor(model_loader=mock_loader)
        cache = PredictionCache()

        # 验证组件创建
        assert predictor is not None
        assert cache is not None
        assert hasattr(predictor, "predict")
        assert hasattr(cache, "get")

    def test_inference_with_cache_integration(self):
        """测试推理与缓存集成"""
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.cache_manager import PredictionCache

        mock_loader = Mock()
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.6, 0.3, 0.1])
        mock_loader.get_model.return_value = mock_model

        predictor = MatchPredictor(model_loader=mock_loader)
        cache = PredictionCache()

        features = [1.0, 2.0, 3.0, 4.0, 5.0]
        cache_key = "test_cache_key"

        # 第一次预测（无缓存）
        result1 = predictor.predict(features=features, model_name="test_model", use_cache=False)

        # 手动缓存结果
        cache.set(cache_key, result1)

        # 第二次预测（使用缓存）
        result2 = cache.get(cache_key)

        assert result1 == result2
        assert result1["predicted_class"] == 0

    def test_inference_error_handling(self):
        """测试推理错误处理"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError
        from src.ml.inference.predictor import MatchPredictor

        mock_loader = Mock()
        mock_loader.get_model.side_effect = ModelLoadError("Model not available")

        predictor = MatchPredictor(model_loader=mock_loader)
        features = [1.0, 2.0, 3.0, 4.0, 5.0]

        with pytest.raises(ModelLoadError):
            predictor.predict(features=features, model_name="nonexistent_model")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
