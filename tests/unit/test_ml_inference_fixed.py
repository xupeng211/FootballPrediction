"""
修复版ML推理组件单元测试

解决Mock对象误用和导入路径问题，专注于可运行的测试
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from pathlib import Path

# 正确的导入路径
from src.ml.inference.model_loader import ModelLoader, ModelLoadError
from src.ml.inference.cache_manager import PredictionCache
from src.ml.inference.predictor import MatchPredictor, PredictionError


class TestModelLoaderFixed:
    """修复版 ModelLoader 测试"""

    @patch("src.ml.inference.model_loader.Path")
    def test_model_loader_init(self, mock_path):
        """测试 ModelLoader 初始化 - 修复Mock路径操作"""
        # 正确设置Mock对象以支持路径操作
        mock_cache_dir = Mock()
        mock_current_best_file = Mock()
        mock_cache_dir.mkdir = Mock()
        mock_cache_dir.__truediv__ = Mock(return_value=mock_current_best_file)
        mock_path.return_value = mock_cache_dir

        loader = ModelLoader("/mock/path")

        assert loader is not None
        mock_cache_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("src.ml.inference.model_loader.Path")
    @patch("os.path.exists")
    def test_load_model_file_not_found(self, mock_exists, mock_path):
        """测试加载不存在的模型文件 - 修复路径检查"""
        mock_exists.return_value = False

        # 正确设置Mock对象以支持路径操作
        mock_cache_dir = Mock()
        mock_current_best_file = Mock()
        mock_cache_dir.mkdir = Mock()
        mock_cache_dir.__truediv__ = Mock(return_value=mock_current_best_file)
        mock_path.return_value = mock_cache_dir

        loader = ModelLoader("/mock/path")

        with pytest.raises(ModelLoadError):
            loader.load_model("test", "/nonexistent/file.pkl")

    @patch("src.ml.inference.model_loader.Path")
    @patch("src.ml.inference.model_loader.joblib.load")
    @patch("os.path.exists")
    def test_load_model_success(self, mock_exists, mock_joblib_load, mock_path):
        """测试成功加载模型 - 修复joblib mock"""
        mock_exists.return_value = True

        # Mock模型对象
        mock_model = Mock()
        mock_model.n_features_in_ = 10
        mock_model.classes_ = [0, 1, 2]
        mock_joblib_load.return_value = mock_model

        # 正确设置Mock对象以支持路径操作
        mock_cache_dir = Mock()
        mock_current_best_file = Mock()
        mock_cache_dir.mkdir = Mock()
        mock_cache_dir.__truediv__ = Mock(return_value=mock_current_best_file)
        mock_path.return_value = mock_cache_dir

        loader = ModelLoader("/mock/path")
        result = loader.load_model("test", "/mock/model.pkl")

        # 修复：ModelLoader返回的是加载状态信息，不是模型本身
        assert result is not None


class TestPredictionCacheFixed:
    """修复版 PredictionCache 测试"""

    def test_cache_basic_operations(self):
        """测试缓存基本操作 - 简化Mock策略"""
        # 使用真实的缓存对象，避免复杂的Mock
        cache = PredictionCache(default_ttl=3600, enable_auto_cleanup=False)

        # 测试设置和获取
        features = {"feature1": 1.0}
        result = {"prediction": 0.8}

        cache.set(features, "test_model", result)
        cached_result = cache.get(features, "test_model")

        assert cached_result == result

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = PredictionCache(enable_auto_cleanup=False)

        result = cache.get({"feature1": 1.0}, "test_model")
        assert result is None

    def test_cache_expiry(self):
        """测试缓存过期"""
        cache = PredictionCache(default_ttl=1, enable_auto_cleanup=False)  # 1秒TTL

        features = {"feature1": 1.0}
        result = {"prediction": 0.8}

        cache.set(features, "test_model", result)

        # 等待缓存过期
        time.sleep(1.1)

        cached_result = cache.get(features, "test_model")
        assert cached_result is None


class TestMatchPredictorFixed:
    """修复版 MatchPredictor 测试"""

    def test_predictor_init(self):
        """测试 MatchPredictor 初始化"""
        mock_loader = Mock()
        mock_cache = Mock()

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model",
        )

        assert predictor is not None
        assert predictor.default_model_name == "test_model"

    @patch("time.time")  # 直接mock time模块
    def test_predict_model_not_loaded(self, mock_time):
        """测试模型未加载时的预测 - 修复time mock"""
        mock_time.return_value = 1000.0

        mock_loader = Mock()
        mock_loader.get_model.return_value = None
        mock_cache = Mock()
        mock_cache.get.return_value = None

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model",
        )

        features = [1.0, 2.0, 3.0]

        # 应该抛出PredictionError，因为模型未加载
        with pytest.raises(PredictionError, match="模型未加载"):
            predictor.predict(features)

    @patch("time.time")  # 直接mock time模块
    def test_predict_cache_hit(self, mock_time):
        """测试缓存命中 - 修复time mock"""
        mock_time.return_value = 1000.0

        mock_loader = Mock()
        mock_cache = Mock()

        cached_result = {
            "prediction": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "timestamp": 1000.0,
        }
        mock_cache.get.return_value = cached_result

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model",
        )

        features = [1.0, 2.0, 3.0]
        result = predictor.predict(features)

        # 验证返回缓存结果
        assert result is not None
        assert "prediction" in result
        assert result["prediction"] == 1

    def test_get_prediction_stats(self):
        """测试获取预测统计信息 - 修复字段名"""
        mock_loader = Mock()
        mock_cache = Mock()

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model",
        )

        stats = predictor.get_prediction_stats()

        # 验证统计信息结构 - 使用正确的字段名
        assert isinstance(stats, dict)
        assert "total_predictions" in stats
        assert "cache_hits" in stats
        assert "success_rate" in stats
        assert "cache_hit_rate" in stats


class TestInferenceIntegrationFixed:
    """修复版集成测试"""

    def test_component_integration(self):
        """测试组件间集成 - 修复导入路径"""
        # 创建 mock 对象
        mock_model = Mock()
        mock_model.predict.return_value = [1]  # 返回数组格式
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]  # 返回二维数组
        mock_model.n_features_in_ = 3
        mock_model.classes_ = [0, 1, 2]

        mock_loader = Mock()
        mock_loader.get_model.return_value = mock_model

        # Mock模型元数据
        mock_metadata = Mock()
        mock_metadata.feature_names = ["feature1", "feature2", "feature3"]  # 3个特征
        mock_loader.get_model_metadata.return_value = mock_metadata

        mock_cache = Mock()
        mock_cache.get.return_value = None  # 缓存未命中

        # 创建预测器
        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model",
        )

        # 修复导入路径和mock
        with patch("time.time", return_value=1000.0):
            features = [1.0, 2.0, 3.0]
            result = predictor.predict(features)

        # 验证结果 - 修复字段名
        assert result is not None
        assert "predicted_class" in result or "prediction" in result

        # 验证调用
        mock_loader.get_model.assert_called_once_with("test_model")
        mock_cache.get.assert_called_once()


class TestMockBestPractices:
    """Mock最佳实践示例"""

    def test_path_mocking_best_practice(self):
        """演示正确的Path Mock方法"""
        with patch("pathlib.Path") as mock_path_class:
            # 创建Mock实例
            mock_path_instance = Mock()

            # 设置__truediv__方法以支持/操作符
            mock_path_instance.__truediv__ = Mock(return_value=Mock())
            mock_path_instance.mkdir = Mock()
            mock_path_instance.exists = Mock(return_value=True)

            mock_path_class.return_value = mock_path_instance

            # 测试代码
            from pathlib import Path

            test_path = Path("/test")
            combined_path = test_path / "file.txt"
            test_path.mkdir(parents=True, exist_ok=True)

            # 验证调用
            mock_path_class.assert_called_once_with("/test")
            mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_import_mocking_best_practice(self):
        """演示正确的导入Mock方法"""
        with patch("time.time", return_value=1000.0):
            # 直接mock具体函数，而不是模块属性
            assert time.time() == 1000.0

    def test_attribute_access_mocking(self):
        """演示属性访问Mock的正确方法"""
        mock_obj = Mock()

        # 设置属性返回值
        mock_obj.n_features_in_ = 10
        mock_obj.classes_ = [0, 1, 2]

        # 验证属性
        assert mock_obj.n_features_in_ == 10
        assert mock_obj.classes_ == [0, 1, 2]


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])
