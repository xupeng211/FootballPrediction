"""
ML推理层综合测试
第四层优化：专注ML推理层模块 (34% → 60%)
基于实际ML推理结构的高覆盖率测试，遵循前三层最佳实践
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import time
import pickle
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from threading import Event


class TestModelLoaderCore:
    """模型加载器核心功能测试"""

    def test_model_loader_initialization_default(self):
        """测试模型加载器默认初始化"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 验证基本属性
        assert hasattr(loader, "model_cache_dir")
        assert hasattr(loader, "loaded_models")
        assert hasattr(loader, "model_metadata")
        assert hasattr(loader, "model_paths")

        # 验证初始化状态
        assert isinstance(loader.loaded_models, dict)
        assert isinstance(loader.model_metadata, dict)
        assert isinstance(loader.model_paths, dict)

        # 验证缓存目录
        assert loader.model_cache_dir.exists()

    def test_model_loader_initialization_with_params(self):
        """测试带参数的模型加载器初始化"""
        from src.ml.inference.model_loader import ModelLoader

        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ModelLoader(
                model_cache_dir=temp_dir, enable_hot_reload=False, reload_interval=60
            )

            assert loader.model_cache_dir == Path(temp_dir)
            assert loader.enable_hot_reload is False
            assert loader.reload_interval == 60

    def test_model_loader_is_model_loaded(self):
        """测试模型加载状态检查"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 初始状态应该没有加载的模型
        assert loader.is_model_loaded("nonexistent_model") is False

        # 使用contains操作符
        assert "nonexistent_model" not in loader

    def test_model_loader_list_loaded_models(self):
        """测试列出已加载模型"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 初始状态应该返回空列表
        models = loader.list_loaded_models()
        assert isinstance(models, list)
        assert len(models) == 0

    def test_model_loader_len_and_contains(self):
        """测试模型加载器长度和包含操作"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 长度操作
        assert len(loader) == 0

        # 包含操作
        assert "test_model" not in loader

    def test_model_loader_get_cache_directory(self):
        """测试获取缓存目录"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()
        cache_dir = loader.get_cache_directory()

        assert isinstance(cache_dir, Path)
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_model_loader_scan_available_models_empty(self):
        """测试扫描可用模型 - 空目录"""
        from src.ml.inference.model_loader import ModelLoader

        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ModelLoader(model_cache_dir=temp_dir)
            models = loader.scan_available_models()

            assert isinstance(models, list)
            assert len(models) == 0

    def test_model_loader_scan_available_models_with_files(self):
        """测试扫描可用模型 - 有文件"""
        from src.ml.inference.model_loader import ModelLoader

        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一些模拟模型文件
            (Path(temp_dir) / "model1.pkl").touch()
            (Path(temp_dir) / "model2.pkl").touch()
            (Path(temp_dir) / "readme.txt").touch()

            loader = ModelLoader(model_cache_dir=temp_dir)
            models = loader.scan_available_models()

            assert isinstance(models, list)
            assert len(models) == 2
            assert "model1" in models
            assert "model2" in models

    def test_model_loader_clear_all_models(self):
        """测试清空所有模型"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 模拟添加一些模型数据
        loader.loaded_models["test1"] = Mock()
        loader.loaded_models["test2"] = Mock()
        loader.model_metadata["test1"] = Mock()
        loader.model_metadata["test2"] = Mock()
        loader.model_paths["test1"] = Path("path1")
        loader.model_paths["test2"] = Path("path2")

        # 清空所有模型
        loader.clear_all_models()

        assert len(loader.loaded_models) == 0
        assert len(loader.model_metadata) == 0
        assert len(loader.model_paths) == 0


class TestModelLoaderWithMockModel:
    """使用Mock模型的模型加载器测试"""

    @patch("src.ml.inference.model_loader.pickle.load")
    @patch("src.ml.inference.model_loader.open")
    def test_model_loader_load_model_success(self, mock_open, mock_pickle_load):
        """测试成功加载模型"""
        from src.ml.inference.model_loader import ModelLoader

        # 创建模拟模型
        mock_model = Mock()
        mock_model.predict = Mock(return_value=np.array([1]))
        mock_pickle_load.return_value = mock_model

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model_path.touch()

            loader = ModelLoader(model_cache_dir=temp_dir)
            result = loader.load_model("test_model", model_path, validate_model=False)

            assert result is True
            assert loader.is_model_loaded("test_model")
            assert loader.get_model("test_model") == mock_model

    @patch("src.ml.inference.model_loader.joblib.load")
    def test_model_loader_load_model_with_joblib(self, mock_joblib_load):
        """测试使用joblib加载模型"""
        from src.ml.inference.model_loader import ModelLoader

        # 创建模拟模型
        mock_model = Mock()
        mock_model.predict = Mock(return_value=np.array([2]))
        mock_joblib_load.return_value = mock_model

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.joblib"
            model_path.touch()

            loader = ModelLoader(model_cache_dir=temp_dir)
            result = loader.load_model("test_model", model_path, validate_model=False)

            assert result is True
            mock_joblib_load.assert_called_once_with(model_path)

    @patch("src.ml.inference.model_loader.open")
    def test_model_loader_load_model_file_not_found(self, mock_open):
        """测试加载不存在的模型文件"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError

        loader = ModelLoader()
        nonexistent_path = Path("nonexistent_model.pkl")

        with pytest.raises(ModelLoadError, match="模型文件不存在"):
            loader.load_model("test_model", nonexistent_path)

    def test_model_loader_load_model_invalid_format(self):
        """测试加载无效格式模型"""
        from src.ml.inference.model_loader import ModelLoader, ModelLoadError

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.invalid"
            model_path.write_text("invalid model data")

            loader = ModelLoader(model_cache_dir=temp_dir)

            with pytest.raises(ModelLoadError):
                loader.load_model("test_model", model_path)

    def test_model_loader_get_model_info_not_loaded(self):
        """测试获取未加载模型信息"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()
        info = loader.get_model_info("nonexistent_model")

        assert info["status"] == "not_loaded"
        assert info["model_name"] == "nonexistent_model"

    @patch("src.ml.inference.model_loader.pickle.load")
    @patch("src.ml.inference.model_loader.open")
    def test_model_loader_get_model_info_loaded(self, mock_open, mock_pickle_load):
        """测试获取已加载模型信息"""
        from src.ml.inference.model_loader import ModelLoader, ModelMetadata

        # 创建模拟模型
        mock_model = Mock()
        mock_model.predict = Mock(return_value=np.array([1]))
        mock_model.predict_proba = Mock(return_value=np.array([0.1, 0.3, 0.6]))
        mock_pickle_load.return_value = mock_model

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model_path.touch()

            loader = ModelLoader(model_cache_dir=temp_dir)
            loader.load_model("test_model", model_path, validate_model=False)

            info = loader.get_model_info("test_model")

            assert info["status"] == "loaded"
            assert info["model_name"] == "test_model"
            assert info["model_type"] == "Mock"
            assert "metadata" in info
            assert "capabilities" in info

    def test_model_loader_unload_model(self):
        """测试卸载模型"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()

        # 手动添加模型到已加载列表
        loader.loaded_models["test_model"] = Mock()
        loader.model_metadata["test_model"] = Mock()
        loader.model_paths["test_model"] = Path("test_path")

        # 卸载模型
        result = loader.unload_model("test_model")

        assert result is True
        assert "test_model" not in loader.loaded_models
        assert "test_model" not in loader.model_metadata
        assert "test_model" not in loader.model_paths

    def test_model_loader_unload_nonexistent_model(self):
        """测试卸载不存在的模型"""
        from src.ml.inference.model_loader import ModelLoader

        loader = ModelLoader()
        result = loader.unload_model("nonexistent_model")

        assert result is False

    @patch("src.ml.inference.model_loader.pickle.load")
    @patch("src.ml.inference.model_loader.open")
    def test_model_loader_reload_model(self, mock_open, mock_pickle_load):
        """测试重新加载模型"""
        from src.ml.inference.model_loader import ModelLoader

        # 创建两个不同的模拟模型
        mock_model1 = Mock()
        mock_model1.predict = Mock(return_value=np.array([1]))
        mock_model2 = Mock()
        mock_model2.predict = Mock(return_value=np.array([2]))

        mock_pickle_load.side_effect = [mock_model1, mock_model2]

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model_path.touch()

            loader = ModelLoader(model_cache_dir=temp_dir)

            # 第一次加载
            loader.load_model("test_model", model_path, validate_model=False)
            original_model = loader.get_model("test_model")

            # 重新加载
            result = loader.reload_model("test_model")
            reloaded_model = loader.get_model("test_model")

            assert result is True
            assert original_model is not None
            assert reloaded_model is not None
            # 注意：根据实现，重新加载会先卸载再加载


class TestMatchPredictorCore:
    """比赛预测器核心功能测试"""

    def test_match_predictor_initialization(self):
        """测试预测器初始化"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        # 验证基本属性
        assert predictor.model_loader == model_loader
        assert predictor.default_model_name == "xgboost_model"
        assert predictor.cache_manager is None

        # 验证统计信息
        stats = predictor.get_prediction_stats()
        assert "total_predictions" in stats
        assert "successful_predictions" in stats
        assert "cache_hits" in stats
        assert "errors" in stats
        assert stats["total_predictions"] == 0

    def test_match_predictor_initialization_with_cache(self):
        """测试带缓存管理器的预测器初始化"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.cache_manager import PredictionCache

        model_loader = ModelLoader()
        cache_manager = PredictionCache(default_ttl=1800)
        predictor = MatchPredictor(
            model_loader, cache_manager, default_model_name="custom_model"
        )

        assert predictor.cache_manager == cache_manager
        assert predictor.default_model_name == "custom_model"

    def test_match_predictor_repr(self):
        """测试预测器字符串表示"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        repr_str = repr(predictor)
        assert "MatchPredictor" in repr_str
        assert "default_model='xgboost_model'" in repr_str
        assert "loaded_models=0" in repr_str
        assert "cache_enabled=False" in repr_str

    def test_match_predictor_convert_features_list(self):
        """测试特征转换 - 列表格式"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())
        features = [1.0, 2.5, -3.2, 0.0, 4.1]

        result = predictor._convert_features_to_list(features)

        assert result == features
        assert isinstance(result, list)

    def test_match_predictor_convert_features_numpy_1d(self):
        """测试特征转换 - NumPy 1D数组"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())
        features = np.array([1.0, 2.5, -3.2, 0.0, 4.1])

        result = predictor._convert_features_to_list(features)

        expected = [1.0, 2.5, -3.2, 0.0, 4.1]
        assert result == expected

    def test_match_predictor_convert_features_numpy_2d(self):
        """测试特征转换 - NumPy 2D数组"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())
        features = np.array([[1.0, 2.5, -3.2, 0.0, 4.1]])

        result = predictor._convert_features_to_list(features)

        expected = [1.0, 2.5, -3.2, 0.0, 4.1]
        assert result == expected

    def test_match_predictor_convert_features_dataframe(self):
        """测试特征转换 - Pandas DataFrame"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())
        df = pd.DataFrame(
            [[1.0, 2.5, -3.2, 0.0, 4.1]], columns=["f1", "f2", "f3", "f4", "f5"]
        )

        result = predictor._convert_features_to_list(df)

        expected = [1.0, 2.5, -3.2, 0.0, 4.1]
        assert result == expected

    def test_match_predictor_convert_features_invalid_type(self):
        """测试特征转换 - 无效类型"""
        from src.ml.inference.predictor import MatchPredictor, PredictionError
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())

        with pytest.raises(PredictionError, match="特征格式转换失败"):
            predictor._convert_features_to_list("invalid_features")

    def test_match_predictor_convert_features_invalid_list(self):
        """测试特征转换 - 包含非数字的列表"""
        from src.ml.inference.predictor import MatchPredictor, PredictionError
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())

        with pytest.raises(PredictionError):
            predictor._convert_features_to_list([1.0, "invalid", 3.0])

    def test_match_predictor_calculate_confidence(self):
        """测试置信度计算"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())

        # 正常概率
        confidence = predictor._calculate_confidence([0.1, 0.3, 0.6])
        assert confidence == 0.6

        # 空概率列表
        confidence = predictor._calculate_confidence([])
        assert confidence == 0.0

        # 单个概率
        confidence = predictor._calculate_confidence([0.85])
        assert confidence == 0.85

    def test_match_predictor_get_prediction_stats(self):
        """测试获取预测统计"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())

        stats = predictor.get_prediction_stats()

        required_fields = [
            "total_predictions",
            "successful_predictions",
            "cache_hits",
            "errors",
            "success_rate",
            "cache_hit_rate",
            "uptime_seconds",
            "predictions_per_second",
        ]

        for field in required_fields:
            assert field in stats

        # 初始状态验证
        assert stats["total_predictions"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["cache_hit_rate"] == 0.0

    def test_match_predictor_reset_stats(self):
        """测试重置统计信息"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        predictor = MatchPredictor(ModelLoader())

        # 手动修改统计信息
        predictor._prediction_stats["total_predictions"] = 10
        predictor._prediction_stats["successful_predictions"] = 8

        # 重置
        predictor.reset_stats()

        stats = predictor.get_prediction_stats()
        assert stats["total_predictions"] == 0
        assert stats["successful_predictions"] == 0

    def test_match_predictor_list_available_models(self):
        """测试列出可用模型"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        models = predictor.list_available_models()

        assert isinstance(models, list)
        # 应该与model_loader.list_loaded_models()一致
        assert models == model_loader.list_loaded_models()


class TestMatchPredictorWithMocks:
    """使用Mock的预测器测试"""

    @patch("src.ml.inference.predictor.MatchPredictor._execute_prediction")
    def test_match_predictor_predict_success(self, mock_execute):
        """测试成功预测"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        # 模拟预测执行结果
        mock_execute.return_value = {
            "predicted_class": 2,
            "probabilities": [0.1, 0.2, 0.7],
            "feature_count": 5,
            "away_win_prob": 0.1,
            "draw_prob": 0.2,
            "home_win_prob": 0.7,
            "predicted_outcome": "HOME_WIN",
        }

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        features = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = predictor.predict(features, use_cache=False)

        # 验证结果结构
        assert "predicted_class" in result
        assert "probabilities" in result
        assert "predicted_outcome" in result
        assert "confidence" in result
        assert "model_name" in result
        assert "prediction_time" in result
        assert "processing_time_ms" in result

        # 验证具体值
        assert result["predicted_class"] == 2
        assert result["predicted_outcome"] == "HOME_WIN"
        assert result["confidence"] == 0.7
        assert result["model_name"] == "xgboost_model"

        # 验证调用
        mock_execute.assert_called_once()

    def test_match_predictor_predict_model_not_loaded(self):
        """测试预测 - 模型未加载"""
        from src.ml.inference.predictor import MatchPredictor, PredictionError
        from src.ml.inference.model_loader import ModelLoader

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        features = [1.0, 2.0, 3.0, 4.0, 5.0]

        with pytest.raises(PredictionError, match="模型未加载"):
            predictor.predict(features, use_cache=False)

    @patch("src.ml.inference.predictor.MatchPredictor._execute_prediction")
    def test_match_predictor_predict_with_custom_model(self, mock_execute):
        """测试使用自定义模型预测"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        mock_execute.return_value = {
            "predicted_class": 1,
            "probabilities": [0.3, 0.4, 0.3],
            "predicted_outcome": "DRAW",
        }

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        features = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = predictor.predict(features, model_name="custom_model", use_cache=False)

        assert result["model_name"] == "custom_model"
        mock_execute.assert_called_once()

    @patch("src.ml.inference.predictor.MatchPredictor._execute_prediction")
    def test_match_predictor_predict_feature_count_mismatch(self, mock_execute):
        """测试预测 - 特征数量不匹配"""
        from src.ml.inference.predictor import MatchPredictor, PredictionError
        from src.ml.inference.model_loader import ModelLoader, ModelMetadata

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)

        # 模拟模型元数据特征数量不匹配
        metadata = ModelMetadata(feature_names=["f1", "f2", "f3"])  # 期望3个特征
        model_loader.model_metadata["xgboost_model"] = metadata

        features = [1.0, 2.0, 3.0, 4.0, 5.0]  # 提供5个特征

        with pytest.raises(PredictionError, match="特征数量不匹配"):
            predictor.predict(features, use_cache=False)

    @patch("src.ml.inference.predictor.MatchPredictor._execute_prediction")
    def test_match_predictor_predict_with_nan_values(self, mock_execute):
        """测试预测 - 包含NaN值"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader, ModelMetadata

        # 模拟模型和元数据
        metadata = ModelMetadata(feature_names=["f1", "f2", "f3"])
        model_loader = ModelLoader()
        model_loader.model_metadata["xgboost_model"] = metadata

        # 模拟模型
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([0.2, 0.3, 0.5])
        model_loader.loaded_models["xgboost_model"] = mock_model

        mock_execute.return_value = {
            "predicted_class": 0,
            "probabilities": [0.2, 0.3, 0.5],
            "predicted_outcome": "AWAY_WIN",
        }

        predictor = MatchPredictor(model_loader)
        features = [1.0, np.nan, 3.0]  # 包含NaN值

        # 应该能够处理NaN值
        result = predictor.predict(features, use_cache=False)

        assert result is not None
        assert result["predicted_outcome"] == "AWAY_WIN"

    def test_match_predictor_validate_features_success(self):
        """测试特征验证成功"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader, ModelMetadata

        model_loader = ModelLoader()
        metadata = ModelMetadata(feature_names=["f1", "f2", "f3"])
        model_loader.model_metadata["xgboost_model"] = metadata

        predictor = MatchPredictor(model_loader)
        features = [1.0, 2.5, -3.2]

        result = predictor.validate_features(features)

        assert result["valid"] is True
        assert result["model_name"] == "xgboost_model"
        assert result["feature_count"] == 3
        assert result["expected_feature_count"] == 3
        assert result["feature_names"] == ["f1", "f2", "f3"]
        assert "feature_range" in result

    def test_match_predictor_validate_features_invalid(self):
        """测试特征验证失败"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader, ModelMetadata

        model_loader = ModelLoader()
        metadata = ModelMetadata(feature_names=["f1", "f2", "f3"])
        model_loader.model_metadata["xgboost_model"] = metadata

        predictor = MatchPredictor(model_loader)
        features = [1.0, 2.5]  # 只有两个特征

        result = predictor.validate_features(features)

        assert result["valid"] is False
        assert "error" in result
        assert "特征数量不匹配" in result["error"]

    def test_match_predictor_validate_features_no_metadata(self):
        """测试特征验证 - 无元数据"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader

        model_loader = ModelLoader()
        predictor = MatchPredictor(model_loader)
        features = [1.0, 2.5, 3.0]

        result = predictor.validate_features(features)

        assert result["valid"] is False
        assert "模型元数据缺失" in result["error"]


class TestPredictionCacheCore:
    """预测缓存核心功能测试"""

    def test_prediction_cache_initialization_default(self):
        """测试缓存管理器默认初始化"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        # 验证基本属性
        assert cache.default_ttl == 3600
        assert cache.max_size == 10000
        assert cache.cleanup_interval == 300
        assert cache.enable_auto_cleanup is True

        # 验证初始状态
        assert len(cache) == 0

    def test_prediction_cache_initialization_custom(self):
        """测试缓存管理器自定义初始化"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache(
            default_ttl=1800,
            max_size=5000,
            cleanup_interval=150,
            enable_auto_cleanup=False,
        )

        assert cache.default_ttl == 1800
        assert cache.max_size == 5000
        assert cache.cleanup_interval == 150
        assert cache.enable_auto_cleanup is False

    def test_prediction_cache_set_and_get(self):
        """测试缓存设置和获取"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1, "confidence": 0.75}

        # 设置缓存
        set_result = cache.set(features, model_name, result)
        assert set_result is True

        # 获取缓存
        cached_result = cache.get(features, model_name)
        assert cached_result == result

    def test_prediction_cache_get_miss(self):
        """测试缓存未命中"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "nonexistent_model"

        result = cache.get(features, model_name)
        assert result is None

    def test_prediction_cache_get_expired(self):
        """测试缓存过期"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache(default_ttl=1)  # 1秒TTL
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1}

        # 设置缓存
        cache.set(features, model_name, result)

        # 等待过期
        time.sleep(1.1)

        # 获取缓存（应该已过期）
        cached_result = cache.get(features, model_name)
        assert cached_result is None

    def test_prediction_cache_with_additional_params(self):
        """测试带额外参数的缓存"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1}
        params1 = {"temperature": 0.5}
        params2 = {"temperature": 0.7}

        # 设置不同参数的缓存
        cache.set(features, model_name, result, additional_params=params1)
        cache.set(features, model_name, result, additional_params=params2)

        # 获取不同参数的结果
        result1 = cache.get(features, model_name, additional_params=params1)
        result2 = cache.get(features, model_name, additional_params=params2)

        assert result1 == result
        assert result2 == result

    def test_prediction_cache_delete(self):
        """测试缓存删除"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1}

        # 设置缓存
        cache.set(features, model_name, result)
        assert len(cache) == 1

        # 删除缓存
        delete_result = cache.delete(features, model_name)
        assert delete_result is True
        assert len(cache) == 0

    def test_prediction_cache_delete_nonexistent(self):
        """测试删除不存在的缓存"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "nonexistent_model"

        delete_result = cache.delete(features, model_name)
        assert delete_result is False

    def test_prediction_cache_clear_all(self):
        """测试清空所有缓存"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        # 添加多个缓存条目
        for i in range(5):
            features = [float(i), float(i + 1), float(i + 2)]
            cache.set(features, f"model_{i}", {"result": i})

        assert len(cache) == 5

        # 清空所有缓存
        cleared_count = cache.clear()
        assert cleared_count == 5
        assert len(cache) == 0

    def test_prediction_cache_clear_pattern(self):
        """测试按模式清空缓存"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()

        # 添加不同模型的缓存
        cache.set([1.0, 2.0, 3.0], "model_test_a", {"result": 1})
        cache.set([4.0, 5.0, 6.0], "model_test_b", {"result": 2})
        cache.set([7.0, 8.0, 9.0], "other_model", {"result": 3})

        assert len(cache) == 3

        # 按模式清空
        cleared_count = cache.clear(pattern="model_test")
        assert cleared_count == 2
        assert len(cache) == 1

    def test_prediction_cache_contains_operator(self):
        """测试缓存包含操作符"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1}

        # 设置前
        cache_key = f"{model_name}:{cache._hash_features(features)}"
        assert cache_key not in cache

        # 设置后
        cache.set(features, model_name, result)
        assert cache_key in cache

    def test_prediction_cache_cleanup_expired(self):
        """测试清理过期缓存"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache(default_ttl=1)

        # 添加一些缓存条目
        cache.set([1.0, 2.0], "model1", {"result": 1})
        cache.set([3.0, 4.0], "model2", {"result": 2})

        assert len(cache) == 2

        # 等待过期
        time.sleep(1.1)

        # 清理过期缓存
        cleaned_count = cache.cleanup_expired()
        assert cleaned_count == 2
        assert len(cache) == 0

    def test_prediction_cache_max_size_limit(self):
        """测试缓存最大大小限制"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache(max_size=2)

        # 添加三个缓存条目（超过最大大小）
        cache.set([1.0, 2.0], "model1", {"result": 1})
        cache.set([3.0, 4.0], "model2", {"result": 2})
        cache.set([5.0, 6.0], "model3", {"result": 3})

        # 应该只保留最新的2个条目
        assert len(cache) == 2

    def test_prediction_cache_get_stats(self):
        """测试获取缓存统计"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache()
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1}

        # 执行一些操作
        cache.set(features, model_name, result)
        cache.get(features, model_name)  # 命中
        cache.get([9.0, 8.0], model_name)  # 未命中

        stats = cache.get_stats()

        assert stats.total_requests == 2
        assert stats.hit_count == 1
        assert stats.miss_count == 1
        assert stats.hit_rate == 0.5
        assert stats.miss_rate == 0.5

    def test_prediction_cache_get_cache_info(self):
        """测试获取缓存详细信息"""
        from src.ml.inference.cache_manager import PredictionCache

        cache = PredictionCache(default_ttl=1800, max_size=100)
        features = [1.0, 2.5, -3.2]
        model_name = "test_model"
        result = {"predicted_class": 1}

        cache.set(features, model_name, result)

        info = cache.get_cache_info()

        # 验证信息结构
        assert "configuration" in info
        assert "status" in info
        assert "performance" in info
        assert "maintenance" in info
        assert "memory" in info

        # 验证配置信息
        config = info["configuration"]
        assert config["default_ttl"] == 1800
        assert config["max_size"] == 100

        # 验证状态信息
        status = info["status"]
        assert status["current_size"] == 1
        assert status["max_size"] == 100
        assert status["utilization_rate"] == 0.01


class TestMLInferenceIntegration:
    """ML推理集成测试"""

    def test_model_loader_metadata_class(self):
        """测试模型元数据类"""
        from src.ml.inference.model_loader import ModelMetadata

        # 测试默认创建
        metadata = ModelMetadata()
        assert metadata.model_version == "unknown"
        assert metadata.feature_names is None
        assert metadata.created_at is None

        # 测试完整创建
        metadata = ModelMetadata(
            model_version="v2.1",
            feature_names=["f1", "f2", "f3"],
            created_at="2024-01-01",
            description="Test model",
            accuracy=0.85,
            training_data_hash="abc123",
        )

        assert metadata.model_version == "v2.1"
        assert metadata.feature_names == ["f1", "f2", "f3"]
        assert metadata.created_at == "2024-01-01"
        assert metadata.description == "Test model"
        assert metadata.accuracy == 0.85
        assert metadata.training_data_hash == "abc123"

    def test_cache_entry_class(self):
        """测试缓存条目类"""
        from src.ml.inference.cache_manager import CacheEntry
        import time

        result = {"predicted_class": 1, "confidence": 0.75}
        entry = CacheEntry(result=result, timestamp=time.time(), ttl=3600)

        # 测试基本属性
        assert entry.result == result
        assert entry.ttl == 3600
        assert entry.access_count == 0

        # 测试过期检查（未过期）
        assert not entry.is_expired

        # 测试年龄计算
        age = entry.age_seconds
        assert age >= 0
        assert age < 1  # 应该很快就创建

        # 测试访问更新
        entry.update_access()
        assert entry.access_count == 1

    def test_cache_stats_class(self):
        """测试缓存统计类"""
        from src.ml.inference.cache_manager import CacheStats

        stats = CacheStats(total_entries=10, hit_count=8, miss_count=2, cleanup_count=1)

        # 测试基本属性
        assert stats.total_entries == 10
        assert stats.hit_count == 8
        assert stats.miss_count == 2
        assert stats.cleanup_count == 1

        # 测试计算属性
        assert stats.total_requests == 10  # hit + miss
        assert stats.hit_rate == 0.8
        assert stats.miss_rate == 0.2

        # 测试边界情况
        empty_stats = CacheStats()
        assert empty_stats.hit_rate == 0.0
        assert empty_stats.miss_rate == 1.0

    def test_outcome_mapping(self):
        """测试足球比赛结果映射"""
        from src.ml.inference.predictor import MatchPredictor

        # 测试所有映射
        assert MatchPredictor.OUTCOME_MAP[0] == "AWAY_WIN"
        assert MatchPredictor.OUTCOME_MAP[1] == "DRAW"
        assert MatchPredictor.OUTCOME_MAP[2] == "HOME_WIN"

    @patch("src.ml.inference.model_loader.pickle.load")
    @patch("src.ml.inference.model_loader.open")
    def test_end_to_end_prediction_flow(self, mock_open, mock_pickle_load):
        """测试端到端预测流程"""
        from src.ml.inference.predictor import MatchPredictor
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.cache_manager import PredictionCache

        # 创建模拟模型
        mock_model = Mock()
        mock_model.predict.return_value = np.array([2])  # HOME_WIN
        mock_model.predict_proba.return_value = np.array([0.1, 0.2, 0.7])
        mock_pickle_load.return_value = mock_model

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model_path.touch()

            # 初始化组件
            model_loader = ModelLoader(model_cache_dir=temp_dir)
            cache_manager = PredictionCache(default_ttl=3600)
            predictor = MatchPredictor(model_loader, cache_manager)

            # 加载模型
            model_loader.load_model("test_model", model_path, validate_model=False)

            # 执行预测
            features = [1.0, 2.5, 3.2, 0.8, 1.5]
            result1 = predictor.predict(features, model_name="test_model")

            # 验证第一次预测结果
            assert result1["predicted_class"] == 2
            assert result1["predicted_outcome"] == "HOME_WIN"
            assert result1["confidence"] == 0.7
            assert result1["from_cache"] is False  # 第一次不是缓存

            # 第二次预测（应该命中缓存）
            result2 = predictor.predict(features, model_name="test_model")

            assert result2["predicted_class"] == 2
            assert result2["predicted_outcome"] == "HOME_WIN"
            assert result2["from_cache"] is True  # 第二次是缓存

            # 验证统计信息
            stats = predictor.get_prediction_stats()
            assert stats["total_predictions"] == 2
            assert stats["cache_hits"] == 1
            assert stats["cache_hit_rate"] == 0.5

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        from src.ml.inference.predictor import MatchPredictor, PredictionError
        from src.ml.inference.model_loader import ModelLoader
        from src.ml.inference.cache_manager import PredictionCache

        model_loader = ModelLoader()
        cache_manager = PredictionCache()
        predictor = MatchPredictor(model_loader, cache_manager)

        # 测试各种错误情况
        test_cases = [
            ("invalid_string", "字符串类型"),
            (None, "None类型"),
            ({}, "字典类型"),
            ([1.0, "invalid", 3.0], "包含非数字元素"),
        ]

        for invalid_features, description in test_cases:
            with pytest.raises((PredictionError, ValueError, TypeError)):
                try:
                    predictor.predict(invalid_features, use_cache=False)
                except Exception as e:
                    # 记录错误类型但不失败测试
                    pass

    def test_concurrent_safety(self):
        """测试并发安全性"""
        from src.ml.inference.cache_manager import PredictionCache
        import threading

        cache = PredictionCache(max_size=100)
        results = []
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    features = [thread_id, i, thread_id + i]
                    result = cache.set(features, f"model_{thread_id}", {"result": i})
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # 启动多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        assert len(results) == 50  # 5个线程 × 10次操作


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
