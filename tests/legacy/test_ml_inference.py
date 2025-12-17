"""
核心推理组件单元测试

测试 src/ml/inference/ 模块的核心功能：
- ModelLoader: 模型加载、版本管理、缓存
- PredictionCache: 缓存管理、TTL、LRU策略
- MatchPredictor: 预测逻辑、特征验证、统计信息

Mock策略：
- 文件系统操作 (pathlib, pickle, joblib)
- 数据处理 (numpy, pandas)
- 时间操作 (time, datetime)
- 哈希计算 (hashlib)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import asyncio
import time
import pickle
import joblib
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from types import SimpleNamespace

# 导入被测试的模块
import sys

sys.path.append("/home/user/projects/FootballPrediction/src")

from ml.inference.model_loader import ModelLoader, ModelMetadata, ModelLoadError
from ml.inference.cache_manager import PredictionCache, CacheEntry, CacheStats
from ml.inference.predictor import MatchPredictor, PredictionError


class TestModelLoader(unittest.TestCase):
    """测试 ModelLoader 类的模型加载和管理功能"""

    @patch("ml.inference.model_loader.Path")
    def setUp(self, mock_path):
        """测试前的设置"""
        # Mock Path 对象以避免实际文件系统操作
        self.mock_cache_dir = Mock(spec=Path)
        self.mock_cache_dir.mkdir = Mock()
        self.mock_cache_dir.exists.return_value = True

        mock_path.return_value = self.mock_cache_dir
        self.model_loader = ModelLoader(self.mock_cache_dir)

    @patch("ml.inference.model_loader.Path")
    @patch("ml.inference.model_loader.pickle.load")
    def test_load_model_success(self, mock_pickle_load, mock_path):
        """测试成功加载模型"""
        # 准备测试数据
        mock_model = Mock()
        mock_pickle_load.return_value = mock_model

        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.is_file.return_value = True
        mock_path.return_value = mock_file_path

        model_path = "/mock/models/test_model.pkl"

        # 执行测试
        result = self.model_loader.load_model("test_model", model_path)

        # 验证结果
        self.assertEqual(result, mock_model)
        self.assertTrue(self.model_loader.is_model_loaded("test_model"))

    @patch("ml.inference.model_loader.Path")
    def test_load_model_file_not_exists(self, mock_path):
        """测试加载不存在的模型文件"""
        mock_file_path = Mock()
        mock_file_path.exists.return_value = False
        mock_path.return_value = mock_file_path

        model_path = "/mock/models/nonexistent_model.pkl"

        # 验证抛出异常
        with self.assertRaises(ModelLoadError):
            self.model_loader.load_model("nonexistent_model", model_path)

    @patch("ml.inference.model_loader.Path")
    @patch("ml.inference.model_loader.pickle.load")
    def test_load_model_with_metadata(self, mock_pickle_load, mock_path):
        """测试加载包含元数据的模型"""
        # 准备测试数据
        mock_model = Mock()
        mock_metadata = ModelMetadata(
            model_version="1.0.0",
            feature_names=["feature1", "feature2"],
            created_at=datetime.now(),
            model_type="xgboost",
        )

        # 模拟返回模型和元数据
        mock_pickle_load.side_effect = [mock_model, mock_metadata]

        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.is_file.return_value = True
        mock_path.return_value = mock_file_path

        model_path = "/mock/models/test_model_with_metadata.pkl"

        # 执行测试
        result = self.model_loader.load_model("test_model", model_path)

        # 验证结果
        self.assertEqual(result, mock_model)
        metadata = self.model_loader.get_model_metadata("test_model")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.model_version, "1.0.0")

    def test_get_loaded_model(self):
        """测试获取已加载的模型"""
        # 手动添加模型到缓存
        mock_model = Mock()
        self.model_loader._models["test_model"] = mock_model

        # 执行测试
        result = self.model_loader.get_model("test_model")

        # 验证结果
        self.assertEqual(result, mock_model)

    def test_get_nonexistent_model(self):
        """测试获取不存在的模型"""
        result = self.model_loader.get_model("nonexistent_model")
        self.assertIsNone(result)

    def test_unload_model(self):
        """测试卸载模型"""
        # 手动添加模型到缓存
        mock_model = Mock()
        self.model_loader._models["test_model"] = mock_model
        self.model_loader._metadata["test_model"] = Mock()

        # 执行测试
        self.model_loader.unload_model("test_model")

        # 验证结果
        self.assertNotIn("test_model", self.model_loader._models)
        self.assertNotIn("test_model", self.model_loader._metadata)

    def test_list_loaded_models(self):
        """测试列出已加载的模型"""
        # 手动添加模型到缓存
        self.model_loader._models["model1"] = Mock()
        self.model_loader._models["model2"] = Mock()

        # 执行测试
        result = self.model_loader.list_loaded_models()

        # 验证结果
        self.assertEqual(set(result), {"model1", "model2"})

    def test_clear_all_models(self):
        """测试清空所有模型"""
        # 手动添加模型到缓存
        self.model_loader._models["model1"] = Mock()
        self.model_loader._models["model2"] = Mock()
        self.model_loader._metadata["model1"] = Mock()
        self.model_loader._metadata["model2"] = Mock()

        # 执行测试
        self.model_loader.clear_all_models()

        # 验证结果
        self.assertEqual(len(self.model_loader._models), 0)
        self.assertEqual(len(self.model_loader._metadata), 0)


class TestPredictionCache(unittest.TestCase):
    """测试 PredictionCache 类的缓存管理功能"""

    @patch("ml.inference.cache_manager.asyncio.create_task")
    @patch("ml.inference.cache_manager.threading.RLock")
    @patch("ml.inference.cache_manager.time.time")
    def setUp(self, mock_time, mock_lock, mock_asyncio):
        """测试前的设置"""
        # Mock 时间函数
        mock_time.return_value = 1609459200.0  # 2021-01-01 00:00:00 UTC

        # Mock 锁
        mock_lock_instance = Mock()
        mock_lock_instance.__enter__ = Mock(return_value=mock_lock_instance)
        mock_lock_instance.__exit__ = Mock(return_value=None)
        mock_lock.return_value = mock_lock_instance

        self.cache = PredictionCache(
            default_ttl=3600,  # 1小时
            max_size=100,
            cleanup_interval=60,
            enable_auto_cleanup=False,  # 测试时禁用自动清理
        )

    def test_set_and_get_cache(self):
        """测试设置和获取缓存"""
        # 准备测试数据
        features = {"feature1": 1.0, "feature2": 2.0}
        model_name = "test_model"
        result = {"prediction": 0.75, "confidence": 0.85}

        # 设置缓存
        self.cache.set(features, model_name, result)

        # 获取缓存
        cached_result = self.cache.get(features, model_name)

        # 验证结果
        self.assertEqual(cached_result, result)

    def test_cache_miss(self):
        """测试缓存未命中"""
        features = {"feature1": 1.0, "feature2": 2.0}
        model_name = "test_model"

        # 获取不存在的缓存
        result = self.cache.get(features, model_name)

        # 验证结果
        self.assertIsNone(result)

    def test_cache_expiry(self):
        """测试缓存过期"""
        features = {"feature1": 1.0, "feature2": 2.0}
        model_name = "test_model"
        result = {"prediction": 0.75}

        # 设置短TTL的缓存
        self.cache.set(features, model_name, result, ttl=0.1)  # 0.1秒

        # 立即获取应该成功
        cached_result = self.cache.get(features, model_name)
        self.assertEqual(cached_result, result)

        # 等待过期后获取应该失败
        time.sleep(0.2)
        cached_result = self.cache.get(features, model_name)
        self.assertIsNone(cached_result)

    def test_cache_lru_eviction(self):
        """测试LRU缓存淘汰策略"""
        cache = PredictionCache(max_size=2)  # 最大容量为2

        # 添加3个缓存项，应该淘汰最旧的
        cache.set({"f": 1}, "model", "result1")
        cache.set({"f": 2}, "model", "result2")
        cache.set({"f": 3}, "model", "result3")

        # 验证第一个缓存被淘汰
        self.assertIsNone(cache.get({"f": 1}, "model"))
        self.assertEqual(cache.get({"f": 2}, "model"), "result2")
        self.assertEqual(cache.get({"f": 3}, "model"), "result3")

    def test_delete_cache(self):
        """测试删除缓存"""
        features = {"feature1": 1.0, "feature2": 2.0}
        model_name = "test_model"
        result = {"prediction": 0.75}

        # 设置缓存
        self.cache.set(features, model_name, result)

        # 删除缓存
        deleted = self.cache.delete(features, model_name)
        self.assertTrue(deleted)

        # 验证缓存已删除
        cached_result = self.cache.get(features, model_name)
        self.assertIsNone(cached_result)

    def test_clear_cache(self):
        """测试清空缓存"""
        # 设置多个缓存项
        self.cache.set({"f": 1}, "model1", "result1")
        self.cache.set({"f": 2}, "model2", "result2")
        self.cache.set({"f": 3}, "model1", "result3")

        # 清空所有缓存
        self.cache.clear()

        # 验证所有缓存已清空
        self.assertIsNone(self.cache.get({"f": 1}, "model1"))
        self.assertIsNone(self.cache.get({"f": 2}, "model2"))
        self.assertIsNone(self.cache.get({"f": 3}, "model1"))

    def test_get_cache_stats(self):
        """测试获取缓存统计信息"""
        # 设置一些缓存
        self.cache.set({"f": 1}, "model", "result1")
        self.cache.set({"f": 2}, "model", "result2")

        # 命中和未命中
        self.cache.get({"f": 1}, "model")  # 命中
        self.cache.get({"f": 3}, "model")  # 未命中

        # 获取统计信息
        stats = self.cache.get_stats()

        # 验证统计信息（根据实际 CacheStats 结构调整）
        self.assertIsInstance(stats, dict)
        self.assertIn("total_requests", stats)
        self.assertIn("size", stats)

    def test_cleanup_expired(self):
        """测试清理过期缓存"""
        # 设置一些缓存，其中一些会过期
        self.cache.set({"f": 1}, "model", "result1", ttl=0.1)  # 很快过期
        self.cache.set({"f": 2}, "model", "result2", ttl=10)  # 不过期

        # 等待第一个缓存过期
        time.sleep(0.2)

        # 清理过期缓存
        self.cache.cleanup_expired()

        # 验证过期缓存被清理
        self.assertIsNone(self.cache.get({"f": 1}, "model"))
        self.assertEqual(self.cache.get({"f": 2}, "model"), "result2")


class TestMatchPredictor(unittest.TestCase):
    """测试 MatchPredictor 类的预测逻辑"""

    @patch("ml.inference.predictor.time.time")
    @patch("ml.inference.predictor.datetime")
    def setUp(self, mock_datetime, mock_time):
        """测试前的设置"""
        # Mock 时间函数
        mock_time.return_value = 1609459200.0  # 2021-01-01 00:00:00 UTC
        mock_datetime.now.return_value.isoformat.return_value = "2021-01-01T00:00:00"

        self.mock_model_loader = Mock()
        self.mock_cache_manager = Mock()
        self.predictor = MatchPredictor(
            model_loader=self.mock_model_loader,
            cache_manager=self.mock_cache_manager,
            default_model_name="default_model",
        )

    def test_predict_success(self):
        """测试成功预测"""
        # 准备测试数据
        features = np.array([[1.0, 2.0, 3.0]])
        mock_model = Mock()
        mock_model.predict.return_value = np.array([2])  # Away win
        mock_model.predict_proba.return_value = np.array(
            [[0.1, 0.3, 0.6]]
        )  # Probabilities

        self.mock_model_loader.get_model.return_value = mock_model
        self.mock_cache_manager.get.return_value = None  # 缓存未命中

        # 执行预测
        result = self.predictor.predict(features)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertIn("prediction", result)
        self.assertIn("probabilities", result)
        self.assertEqual(result["prediction"], 2)  # Away win

        # 验证调用
        self.mock_model_loader.get_model.assert_called_once_with("default_model")
        self.mock_cache_manager.get.assert_called_once()
        self.mock_cache_manager.set.assert_called_once()

    def test_predict_with_cache_hit(self):
        """测试缓存命中的预测"""
        features = np.array([[1.0, 2.0, 3.0]])
        cached_result = {
            "prediction": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "timestamp": time.time(),
        }

        self.mock_cache_manager.get.return_value = cached_result

        # 执行预测
        result = self.predictor.predict(features)

        # 验证返回缓存结果
        self.assertEqual(result, cached_result)

        # 验证没有调用模型
        self.mock_model_loader.get_model.assert_not_called()

    def test_predict_model_not_loaded(self):
        """测试模型未加载时的预测"""
        features = np.array([[1.0, 2.0, 3.0]])
        self.mock_model_loader.get_model.return_value = None
        self.mock_cache_manager.get.return_value = None

        # 执行预测
        result = self.predictor.predict(features)

        # 验证返回错误结果
        self.assertIsNone(result)

    def test_predict_invalid_features(self):
        """测试无效特征的预测"""
        invalid_features = []  # 空数组

        # 执行预测
        result = self.predictor.predict(invalid_features)

        # 验证返回错误结果
        self.assertIsNone(result)

    def test_predict_model_prediction_error(self):
        """测试模型预测异常"""
        features = np.array([[1.0, 2.0, 3.0]])
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Model prediction failed")

        self.mock_model_loader.get_model.return_value = mock_model
        self.mock_cache_manager.get.return_value = None

        # 执行预测
        result = self.predictor.predict(features)

        # 验证返回错误结果
        self.assertIsNone(result)

    def test_validate_features_success(self):
        """测试特征验证成功"""
        features = np.array([[1.0, 2.0, 3.0]])
        mock_model = Mock()
        mock_model.n_features_in_ = 3

        self.mock_model_loader.get_model.return_value = mock_model

        # 执行验证
        is_valid = self.predictor.validate_features(features)

        # 验证结果
        self.assertTrue(is_valid)

    def test_validate_features_invalid_shape(self):
        """测试无效形状的特征验证"""
        features = np.array([1.0, 2.0])  # 1D数组而不是2D
        mock_model = Mock()
        mock_model.n_features_in_ = 3

        self.mock_model_loader.get_model.return_value = mock_model

        # 执行验证
        is_valid = self.predictor.validate_features(features)

        # 验证结果
        self.assertFalse(is_valid)

    def test_get_model_info(self):
        """测试获取模型信息"""
        mock_model = Mock()
        mock_model.n_features_in_ = 10
        mock_model.classes_ = [0, 1, 2]

        self.mock_model_loader.get_model.return_value = mock_model

        # 执行测试
        model_info = self.predictor.get_model_info()

        # 验证结果
        self.assertIsNotNone(model_info)
        self.assertIn("model_name", model_info)
        self.assertIn("model_loaded", model_info)

    def test_get_prediction_stats(self):
        """测试获取预测统计信息"""
        # 执行一些预测以生成统计信息
        features = np.array([[1.0, 2.0, 3.0]])
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.5, 0.3]])

        self.mock_model_loader.get_model.return_value = mock_model
        self.mock_cache_manager.get.return_value = None

        # 执行预测
        self.predictor.predict(features)
        self.predictor.predict(features)

        # 获取统计信息
        stats = self.predictor.get_prediction_stats()

        # 验证统计信息
        self.assertIsNotNone(stats)
        self.assertIn("total_predictions", stats)
        self.assertIn("cache_hits", stats)
        self.assertEqual(stats["total_predictions"], 2)

    def test_reset_stats(self):
        """测试重置预测统计信息"""
        # 执行预测
        features = np.array([[1.0, 2.0, 3.0]])
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.5, 0.3]])

        self.mock_model_loader.get_model.return_value = mock_model
        self.mock_cache_manager.get.return_value = None

        self.predictor.predict(features)

        # 重置统计信息
        self.predictor.reset_stats()

        # 获取统计信息
        stats = self.predictor.get_prediction_stats()

        # 验证统计信息已重置
        self.assertEqual(stats["total_predictions"], 0)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["cache_misses"], 0)


class TestIntegration(unittest.TestCase):
    """推理组件集成测试"""

    def setUp(self):
        """测试前的设置"""
        self.model_loader = ModelLoader("/mock/models")
        self.cache_manager = PredictionCache(default_ttl=3600)
        self.predictor = MatchPredictor(
            model_loader=self.model_loader,
            cache_manager=self.cache_manager,
            default_model_name="test_model",
        )

    @patch("ml.inference.model_loader.pickle.load")
    @patch("ml.inference.model_loader.Path")
    def test_end_to_end_prediction_flow(self, mock_path, mock_pickle_load):
        """测试端到端预测流程"""
        # 准备测试模型
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1])  # Draw
        mock_model.predict_proba.return_value = np.array([[0.3, 0.4, 0.3]])
        mock_model.n_features_in_ = 3
        mock_model.classes_ = [0, 1, 2]

        mock_pickle_load.return_value = mock_model

        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.is_file.return_value = True
        mock_path.return_value = mock_file_path

        # 加载模型
        self.model_loader.load_model("test_model", "/mock/test_model.pkl")

        # 执行预测
        features = np.array([[1.0, 2.0, 3.0]])
        result1 = self.predictor.predict(features)

        # 再次执行相同预测（应该使用缓存）
        result2 = self.predictor.predict(features)

        # 验证结果
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertEqual(result1["prediction"], 1)
        self.assertEqual(result2["prediction"], 1)

        # 验证缓存生效
        stats = self.predictor.get_prediction_stats()
        self.assertEqual(stats["total_predictions"], 2)
        self.assertEqual(stats["cache_hits"], 1)
        self.assertEqual(stats["cache_misses"], 1)


if __name__ == "__main__":
    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTest(unittest.makeSuite(TestModelLoader))
    suite.addTest(unittest.makeSuite(TestPredictionCache))
    suite.addTest(unittest.makeSuite(TestMatchPredictor))
    suite.addTest(unittest.makeSuite(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print(f"\n{'='*60}")
    print(f"测试总结:")
    print(f"总测试数: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(
        f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"{'='*60}")
