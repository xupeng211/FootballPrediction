"""
核心推理组件简化单元测试

专注于关键功能测试，使用更全面的 mock 策略
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
sys.path.append('/home/user/projects/FootballPrediction/src')

from ml.inference.model_loader import ModelLoader, ModelMetadata, ModelLoadError
from ml.inference.cache_manager import PredictionCache
from ml.inference.predictor import MatchPredictor, PredictionError


class TestModelLoaderSimple(unittest.TestCase):
    """简化的 ModelLoader 测试"""

    @patch('ml.inference.model_loader.Path')
    def test_model_loader_init(self, mock_path):
        """测试 ModelLoader 初始化"""
        mock_cache_dir = Mock()
        mock_cache_dir.mkdir = Mock()
        mock_path.return_value = mock_cache_dir

        loader = ModelLoader("/mock/path")

        self.assertIsNotNone(loader)
        mock_cache_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('ml.inference.model_loader.Path')
    def test_load_model_file_not_found(self, mock_path):
        """测试加载不存在的模型文件"""
        mock_cache_dir = Mock()
        mock_cache_dir.mkdir = Mock()
        mock_path.return_value = mock_cache_dir

        loader = ModelLoader("/mock/path")

        with self.assertRaises(ModelLoadError):
            loader.load_model("test", "/nonexistent/file.pkl")


class TestPredictionCacheSimple(unittest.TestCase):
    """简化的 PredictionCache 测试"""

    @patch('ml.inference.cache_manager.asyncio.create_task')
    @patch('ml.inference.cache_manager.threading.RLock')
    @patch('ml.inference.cache_manager.time.time')
    def test_cache_basic_operations(self, mock_time, mock_lock, mock_asyncio):
        """测试缓存基本操作"""
        mock_time.return_value = 1000.0

        mock_lock_instance = Mock()
        mock_lock_instance.__enter__ = Mock(return_value=mock_lock_instance)
        mock_lock_instance.__exit__ = Mock(return_value=None)
        mock_lock.return_value = mock_lock_instance

        cache = PredictionCache(default_ttl=3600, enable_auto_cleanup=False)

        # 测试设置和获取
        features = {"feature1": 1.0}
        result = {"prediction": 0.8}

        cache.set(features, "test_model", result)
        cached_result = cache.get(features, "test_model")

        self.assertEqual(cached_result, result)

    @patch('ml.inference.cache_manager.asyncio.create_task')
    @patch('ml.inference.cache_manager.threading.RLock')
    @patch('ml.inference.cache_manager.time.time')
    def test_cache_miss(self, mock_time, mock_lock, mock_asyncio):
        """测试缓存未命中"""
        mock_time.return_value = 1000.0

        mock_lock_instance = Mock()
        mock_lock_instance.__enter__ = Mock(return_value=mock_lock_instance)
        mock_lock_instance.__exit__ = Mock(return_value=None)
        mock_lock.return_value = mock_lock_instance

        cache = PredictionCache(enable_auto_cleanup=False)

        result = cache.get({"feature1": 1.0}, "test_model")
        self.assertIsNone(result)


class TestMatchPredictorSimple(unittest.TestCase):
    """简化的 MatchPredictor 测试"""

    def test_predictor_init(self):
        """测试 MatchPredictor 初始化"""
        mock_loader = Mock()
        mock_cache = Mock()

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model"
        )

        self.assertIsNotNone(predictor)
        self.assertEqual(predictor.default_model_name, "test_model")

    @patch('ml.inference.predictor.time.time')
    @patch('ml.inference.predictor.datetime')
    def test_predict_model_not_loaded(self, mock_datetime, mock_time):
        """测试模型未加载时的预测"""
        mock_time.return_value = 1000.0
        mock_datetime.now.return_value.isoformat.return_value = "2021-01-01T00:00:00"

        mock_loader = Mock()
        mock_loader.get_model.return_value = None
        mock_cache = Mock()
        mock_cache.get.return_value = None

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model"
        )

        features = [[1.0, 2.0, 3.0]]
        result = predictor.predict(features)

        self.assertIsNone(result)

    @patch('ml.inference.predictor.time.time')
    @patch('ml.inference.predictor.datetime')
    def test_predict_cache_hit(self, mock_datetime, mock_time):
        """测试缓存命中"""
        mock_time.return_value = 1000.0
        mock_datetime.now.return_value.isoformat.return_value = "2021-01-01T00:00:00"

        mock_loader = Mock()
        mock_cache = Mock()

        cached_result = {
            'prediction': 1,
            'probabilities': [0.2, 0.5, 0.3],
            'timestamp': 1000.0
        }
        mock_cache.get.return_value = cached_result

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model"
        )

        features = [[1.0, 2.0, 3.0]]
        result = predictor.predict(features)

        # 验证返回缓存结果（可能包含额外的元数据）
        self.assertIsNotNone(result)
        self.assertIn('prediction', result)
        self.assertEqual(result['prediction'], 1)

    def test_get_prediction_stats(self):
        """测试获取预测统计信息"""
        mock_loader = Mock()
        mock_cache = Mock()

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model"
        )

        stats = predictor.get_prediction_stats()

        # 验证统计信息结构
        self.assertIsInstance(stats, dict)
        self.assertIn('total_predictions', stats)
        self.assertIn('cache_hits', stats)
        self.assertIn('cache_misses', stats)


class TestInferenceIntegrationSimple(unittest.TestCase):
    """简化的集成测试"""

    def test_component_integration(self):
        """测试组件间集成"""
        # 创建 mock 对象
        mock_model = Mock()
        mock_model.predict.return_value = 1  # Draw
        mock_model.predict_proba.return_value = [0.2, 0.5, 0.3]
        mock_model.n_features_in_ = 3
        mock_model.classes_ = [0, 1, 2]

        mock_loader = Mock()
        mock_loader.get_model.return_value = mock_model

        mock_cache = Mock()
        mock_cache.get.return_value = None  # 缓存未命中

        # 创建预测器
        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model"
        )

        # 执行预测
        with patch('ml.inference.predictor.time.time', return_value=1000.0), \
             patch('ml.inference.predictor.datetime') as mock_datetime:

            mock_datetime.now.return_value.isoformat.return_value = "2021-01-01T00:00:00"

            features = [[1.0, 2.0, 3.0]]
            result = predictor.predict(features)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertIn('prediction', result)

        # 验证调用
        mock_loader.get_model.assert_called_once_with("test_model")
        mock_cache.get.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)