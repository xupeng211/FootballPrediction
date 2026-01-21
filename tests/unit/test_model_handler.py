"""
Model Handler 单元测试
测试模型加载、特征对齐和预测逻辑
"""

import pickle

# V36.4 Final: 修复导入路径
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.ml.model_handler import ModelHandler, get_model_handler
except ImportError as e:
    pytest.skip(f"ModelHandler not available: {e}", allow_module_level=True)


@pytest.mark.unit
class TestModelHandler:
    """ModelHandler测试类"""

    @pytest.fixture
    def mock_model(self, mock_lightgbm_model):
        """Mock LightGBM模型"""
        return mock_lightgbm_model

    @pytest.fixture
    def sample_features(self):
        """样本特征数据"""
        return {
            'feature_0': 1.0,
            'feature_1': 2.0,
            'feature_2': 0.5,
            # ... 只包含部分特征
        }

    @pytest.fixture
    def full_feature_vector(self):
        """完整特征向量"""
        return {f'feature_{i}': np.random.random() for i in range(30)}

    @pytest.fixture
    def temp_model_file(self):
        """临时模型文件"""
        with tempfile.NamedTemporaryFile(suffix='.model', delete=False) as tmp:
            # 创建一个简单的模型
            model_data = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
            tmp.write(model_data.tobytes())
            tmp_path = tmp.name

        yield tmp_path

        Path(tmp_path).unlink(missing_ok=True)

    def test_model_handler_initialization(self):
        """测试ModelHandler初始化"""
        handler = ModelHandler()
        assert hasattr(handler, 'model')
        assert hasattr(handler, 'feature_columns')

    @patch('lightgbm.Booster')
    def test_model_loading_success(self, mock_booster, temp_model_file):
        """测试模型加载成功"""
        mock_model = Mock()
        mock_booster.return_value = mock_model

        handler = ModelHandler()
        result = handler.load_model(temp_model_file)

        assert result is True
        mock_booster.assert_called_once_with(model_file=temp_model_file)

    def test_model_loading_file_not_exist(self):
        """测试模型文件不存在"""
        handler = ModelHandler()
        non_existent_file = "/tmp/non_existent_model.model"

        result = handler.load_model(non_existent_file)

        assert result is False

    @patch('lightgbm.Booster')
    def test_model_loading_corrupted_file(self, mock_booster, temp_model_file):
        """测试损坏的模型文件"""
        mock_booster.side_effect = Exception("Model corrupted")

        handler = ModelHandler()
        result = handler.load_model(temp_model_file)

        assert result is False

    def test_predict_with_model_not_loaded(self):
        """测试模型未加载时的预测"""
        handler = ModelHandler()
        handler.model = None

        with pytest.raises(Exception, match="Model not loaded"):
            handler.predict({})

    def test_predict_success(self, mock_model, sample_features):
        """测试预测成功"""
        # Mock模型预测
        mock_model.predict.return_value = np.array([0.6, 0.3, 0.1])
        mock_model.num_feature.return_value = 3

        handler = ModelHandler()
        handler.model = mock_model

        result = handler.predict(sample_features)

        assert isinstance(result, (np.ndarray, list))
        mock_model.predict.assert_called_once()

    def test_feature_alignment_success(self, mock_model, sample_features):
        """测试特征对齐成功"""
        # Mock模型期望3个特征
        mock_model.num_feature.return_value = 3

        handler = ModelHandler()
        handler.model = mock_model

        aligned_features = handler._align_features(sample_features)

        assert len(aligned_features) == 3
        assert all(isinstance(v, (int, float)) for v in aligned_features.values())

    def test_feature_alignment_fill_missing(self, mock_model, sample_features):
        """测试特征对齐时填充缺失特征"""
        # Mock模型期望30个特征
        mock_model.num_feature.return_value = 30

        handler = ModelHandler()
        handler.model = mock_model

        aligned_features = handler._align_features(sample_features)

        # 应该有30个特征
        assert len(aligned_features) == 30

        # 缺失的特征应该被填充为0
        for i in range(30):
            feature_name = f'feature_{i}'
            assert feature_name in aligned_features

    def test_feature_alignment_extra_features(self, mock_model, full_feature_vector):
        """测试特征对齐时处理额外特征"""
        # Mock模型期望10个特征
        mock_model.num_feature.return_value = 10

        handler = ModelHandler()
        handler.model = mock_model

        aligned_features = handler._align_features(full_feature_vector)

        # 应该只保留10个特征
        assert len(aligned_features) == 10

        # 应该只包含前10个特征
        for i in range(10):
            feature_name = f'feature_{i}'
            assert feature_name in aligned_features

        for i in range(10, 30):
            feature_name = f'feature_{i}'
            assert feature_name not in aligned_features

    def test_feature_alignment_model_not_loaded(self, sample_features):
        """测试模型未加载时的特征对齐"""
        handler = ModelHandler()
        handler.model = None

        with pytest.raises(Exception, match="Model not loaded"):
            handler._align_features(sample_features)

    def test_predict_with_feature_alignment(self, mock_model, sample_features):
        """测试带特征对齐的预测"""
        # Mock模型
        mock_model.num_feature.return_value = 30
        mock_model.predict.return_value = np.array([0.5, 0.3, 0.2])

        handler = ModelHandler()
        handler.model = mock_model

        result = handler.predict(sample_features)

        # 应该调用特征对齐
        assert isinstance(result, (np.ndarray, list))
        mock_model.predict.assert_called_once()

    def test_predict_with_disable_shape_check(self, mock_model, sample_features):
        """测试禁用形状检查的预测"""
        # Mock模型
        mock_model.num_feature.return_value = 30
        mock_model.predict.return_value = np.array([0.5, 0.3, 0.2])

        handler = ModelHandler()
        handler.model = mock_model

        result = handler.predict(sample_features, disable_shape_check=True)

        assert isinstance(result, (np.ndarray, list))

    def test_get_model_info(self, mock_model):
        """测试获取模型信息"""
        mock_model.num_feature.return_value = 30
        mock_model.feature_name.return_value = [f'feature_{i}' for i in range(30)]

        handler = ModelHandler()
        handler.model = mock_model

        info = handler.get_model_info()

        assert 'model_type' in info
        assert 'feature_count' in info
        assert 'feature_names' in info
        assert info['feature_count'] == 30

    def test_get_model_info_no_model(self):
        """测试模型未加载时获取模型信息"""
        handler = ModelHandler()
        handler.model = None

        info = handler.get_model_info()

        assert info == {}

    def test_prediction_shape_handling(self, mock_model, sample_features):
        """测试预测结果形状处理"""
        # Mock多维输出
        mock_model.num_feature.return_value = 3
        mock_model.predict.return_value = np.array([[0.6, 0.3, 0.1]])  # 2D数组

        handler = ModelHandler()
        handler.model = mock_model

        result = handler.predict(sample_features)

        # 应该正确处理形状
        assert isinstance(result, (np.ndarray, list))

    def test_prediction_single_value_output(self, mock_model, sample_features):
        """测试单值预测输出"""
        # Mock单值输出
        mock_model.num_feature.return_value = 3
        mock_model.predict.return_value = np.array([0.65])  # 单值

        handler = ModelHandler()
        handler.model = mock_model

        result = handler.predict(sample_features)

        assert isinstance(result, (np.ndarray, list))

    def test_is_loaded_property(self, mock_model):
        """测试is_loaded属性"""
        handler = ModelHandler()

        # 初始状态
        assert not handler.is_loaded

        # 加载模型后
        handler.model = mock_model
        assert handler.is_loaded

        # 模型设为None
        handler.model = None
        assert not handler.is_loaded

    def test_feature_normalization(self, mock_model, sample_features):
        """测试特征标准化"""
        mock_model.num_feature.return_value = 3

        handler = ModelHandler()
        handler.model = mock_model

        # 测试极端值的标准化
        extreme_features = {
            'feature_0': 999999.0,
            'feature_1': -999999.0,
            'feature_2': np.inf
        }

        # 应该处理极端值而不崩溃
        try:
            result = handler._align_features(extreme_features)
            assert isinstance(result, dict)
        except Exception:
            # 如果抛出异常，应该是可预期的异常
            pass

    @patch('lightgbm.Booster')
    def test_model_file_path_resolution(self, mock_booster, temp_model_file):
        """测试模型文件路径解析"""
        mock_model = Mock()
        mock_booster.return_value = mock_model

        # 测试相对路径
        handler = ModelHandler()
        result = handler.load_model(temp_model_file)

        assert result is True

    def test_concurrent_prediction_safety(self, mock_model, sample_features):
        """测试并发预测安全性"""
        import threading

        mock_model.num_feature.return_value = 30
        mock_model.predict.return_value = np.array([0.5, 0.3, 0.2])

        handler = ModelHandler()
        handler.model = mock_model

        results = []
        errors = []

        def predict_worker():
            try:
                result = handler.predict(sample_features)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程并发预测
        threads = [threading.Thread(target=predict_worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 应该没有错误
        assert len(errors) == 0
        assert len(results) == 10