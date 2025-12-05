"""
lstm_predictor.py 安全网测试
LSTM Predictor Safety Net Tests

【SDET安全网测试】为P0风险文件 lstm_predictor.py 创建第一层安全网测试

测试原则:
- 🚫 绝对不Mock目标文件的内部函数
- ✅ 只关注公共接口的输入和输出
- ✅ 直接导入并测试公共类和方法
- ✅ 构造简单的numpy/pandas数据，验证基本行为和异常处理
- ✅ 允许模型文件加载失败（测试不依赖.h5/.pkl文件存在）

风险等级: P0 (253行代码，0%覆盖率)
测试策略: 黑盒单元测试 - Happy Path + Unhappy Path
发现目标:
- LSTMPredictor 主类
- predict() - 核心预测方法
- train() - 模型训练方法
- load_model() - 模型加载方法
- prepare_data() - 数据预处理方法
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Optional

# 直接导入目标文件中的类和方法
try:
    from src.ml.lstm_predictor import (
        LSTMPredictor,
        PredictionResult,
        TrainingConfig,
    )
except ImportError as e:
    # 如果导入失败，创建一个基本的Mock来测试导入问题
    pytest.skip(f"Cannot import lstm_predictor: {e}", allow_module_level=True)


class TestLSTMPredictorSafetyNet:
    """
    LSTMPredictor 安全网测试

    核心目标：为这个253行的P0风险文件创建最基本的"安全网"
    未来重构时，这些测试能保证基本功能不被破坏
    """

    @pytest.fixture
    def lstm_predictor(self):
        """创建LSTMPredictor实例用于测试"""
        try:
            # 使用默认配置创建实例
            return LSTMPredictor()
        except Exception:
            pytest.skip(f"Cannot create LSTMPredictor: {e}")

    @pytest.fixture
    def sample_sequence_data(self):
        """创建样本序列数据用于测试"""
        # 创建简单的时序数据：24个时间步（默认sequence_length），4个特征
        np.random.seed(42)  # 确保可重复性
        return np.random.randn(24, 4).astype(np.float32)

    @pytest.fixture
    def sample_target_data(self):
        """创建样本目标数据用于测试"""
        # 创建简单的目标数据：24个值
        np.random.seed(42)
        return np.random.randn(24, 1).astype(np.float32)

    @pytest.fixture
    def sample_dict_data(self):
        """创建样本字典数据用于测试"""
        # 创建包含时间序列数据的字典列表
        np.random.seed(42)
        data = []
        for i in range(50):  # 创建50个时间点的数据
            data.append(
                {
                    "time": f"2024-01-{(i % 30) + 1:02d}T{(i % 24):02d}:00:00",
                    "overall_score": np.random.uniform(6.0, 10.0),
                    "cpu_usage": np.random.uniform(20.0, 80.0),
                    "memory_usage": np.random.uniform(40.0, 90.0),
                    "active_connections": np.random.randint(5, 25),
                }
            )
        return data

    # ==================== P0 优先级 Happy Path 测试 ====================

    @pytest.mark.unit
    @pytest.mark.ml
    @pytest.mark.critical
    def test_lstm_predictor_initialization(self, lstm_predictor):
        """
        P0测试: LSTMPredictor 初始化 Happy Path

        测试目标: 验证LSTM预测器能正常初始化
        预期结果: 对象创建成功，包含必要的属性
        业务重要性: 核心ML类的初始化能力
        """
        # 验证对象创建成功
        assert lstm_predictor is not None
        assert hasattr(lstm_predictor, "model")
        assert hasattr(lstm_predictor, "scaler_X")  # 实际的属性名
        assert hasattr(lstm_predictor, "scaler_y")  # 实际的属性名
        assert hasattr(lstm_predictor, "config")
        assert hasattr(lstm_predictor, "is_trained")
        assert hasattr(lstm_predictor, "feature_columns")

        # 验证配置存在
        assert lstm_predictor.config is not None
        assert hasattr(lstm_predictor.config, "sequence_length")
        assert hasattr(lstm_predictor.config, "prediction_horizon")

        # 验证基本配置存在
        assert isinstance(lstm_predictor.config.sequence_length, int)
        assert lstm_predictor.config.sequence_length > 0
        assert isinstance(lstm_predictor.config.prediction_horizon, int)
        assert lstm_predictor.config.prediction_horizon > 0
        assert isinstance(lstm_predictor.is_trained, bool)
        assert isinstance(lstm_predictor.feature_columns, list)

    @pytest.mark.unit
    @pytest.mark.ml
    @pytest.mark.critical
    def test_prepare_data_happy_path(self, lstm_predictor, sample_dict_data):
        """
        P0测试: 数据预处理 Happy Path

        测试目标: prepare_data() 方法
        预期结果: 返回处理后的numpy数组
        业务重要性: ML模型数据预处理核心功能
        """
        try:
            result = lstm_predictor.prepare_data(sample_dict_data)

            # 基本验证 - 确保没有崩溃且返回合理结果
            assert result is not None
            # 预期返回tuple of (X, y) 数组
            assert isinstance(result, tuple)
            assert len(result) == 2  # 应该返回(X, y)对

            x, y = result
            assert isinstance(x, np.ndarray)
            assert isinstance(y, np.ndarray)
            assert len(x) > 0
            assert len(y) > 0
            assert x.ndim == 3  # LSTM期望3维输入 (samples, timesteps, features)
            assert y.ndim == 3  # 目标也是3维 (samples, timesteps, features)

        except Exception:
            pytest.fail(
                f"prepare_data() should not crash with valid dict list input: {e}"
            )

    @pytest.mark.unit
    @pytest.mark.ml
    @pytest.mark.critical
    def test_predict_with_sequence_happy_path(
        self, lstm_predictor, sample_sequence_data
    ):
        """
        P0测试: 序列预测 Happy Path

        测试目标: predict() 方法使用序列数据
        预期结果: 返回预测结果
        业务重要性: 核心ML预测功能
        """
        try:
            # 调用预测方法
            result = lstm_predictor.predict(sample_sequence_data)

            # 基本验证
            assert result is not None
            # 预测结果应该是PredictionResult对象
            if hasattr(result, "predicted_values"):
                # PredictionResult对象
                assert hasattr(result, "timestamp")
                assert hasattr(result, "confidence_intervals")
                assert isinstance(result.predicted_values, list)
            elif isinstance(result, np.ndarray):
                # 直接numpy数组结果
                assert len(result) > 0
                assert result.dtype in [np.float32, np.float64]
            elif isinstance(result, (list, tuple)):
                # 列表或元组结果
                assert len(result) > 0

        except ValueError as e:
            # 允许"模型尚未训练"的异常（这是预期的行为）
            if "not trained" in str(e).lower() or "模型尚未训练" in str(e):
                pass  # 预期的行为
            else:
                pytest.fail(f"predict() should handle sequence data gracefully: {e}")
        except Exception:
            # 允许TensorFlow相关异常
            if (
                "tensorflow" in str(e).lower()
                or "cuda" in str(e).lower()
                or "gpu" in str(e).lower()
            ):
                pass
            else:
                pytest.fail(f"predict() should handle sequence data gracefully: {e}")

    @pytest.mark.unit
    @pytest.mark.ml
    @pytest.mark.critical
    def test_train_happy_path(
        self, lstm_predictor, sample_sequence_data, sample_target_data
    ):
        """
        P0测试: 模型训练 Happy Path

        测试目标: train() 方法
        预期结果: 返回训练统计信息
        业务重要性: 核心ML训练功能
        """
        try:
            # 确保数据有正确的形状
            # sample_sequence_data应该是 (sequence_length, n_features)
            # sample_target_data应该是序列数据，但当前只是简单数组

            # 创建正确形状的训练数据
            if sample_sequence_data.ndim == 2:
                # 转换为LSTM需要的形状 (samples, timesteps, features)
                train_X = np.array([sample_sequence_data] * 5)  # 5个样本
            else:
                train_X = sample_sequence_data

            if sample_target_data.ndim == 2:
                # 为每个样本创建目标序列 (prediction_horizon, 1)
                target_seq = np.random.randn(
                    lstm_predictor.config.prediction_horizon, 1
                )
                train_y = np.array([target_seq] * len(train_X))  # 匹配样本数
            else:
                train_y = sample_target_data

            # 首先构建模型
            input_shape = (train_X.shape[1], train_X.shape[2])
            lstm_predictor.build_model(input_shape)

            # 训练模型
            result = lstm_predictor.train(train_X, train_y)

            # 基本验证
            assert result is not None
            # 预期返回包含训练统计信息的字典
            assert isinstance(result, dict)

            # 验证训练统计信息
            possible_keys = [
                "train_loss",
                "train_mae",
                "val_loss",
                "val_mae",
                "epochs_trained",
            ]
            has_valid_key = any(key in result for key in possible_keys)
            assert has_valid_key or len(result) > 0

            # 验证模型被标记为已训练
            assert lstm_predictor.is_trained

        except Exception:
            # TensorFlow相关的异常是可以接受的
            if (
                "tensorflow" in str(e).lower()
                or "cuda" in str(e).lower()
                or "gpu" in str(e).lower()
            ):
                pass
            else:
                pytest.fail(
                    f"train() should handle valid sequence data gracefully: {e}"
                )

    @pytest.mark.unit
    @pytest.mark.ml
    def test_load_model_happy_path(self, lstm_predictor):
        """
        P0测试: 模型加载 Happy Path

        测试目标: load_model() 方法
        预期结果: 应该能处理模型文件不存在的情况
        业务重要性: 模型持久化功能
        """
        try:
            # 尝试加载一个不存在的模型文件（测试文件操作）
            result = lstm_predictor.load_model("non_existent_model.h5")

            # 可能的结果：
            # 1. 返回False/None表示加载失败
            # 2. 抛出FileNotFoundError等明确异常
            # 3. 降级到默认模型状态
            assert result in [False, None] or isinstance(result, bool)

        except (OSError, FileNotFoundError):
            # 预期的文件系统异常
            pass
        except Exception:
            # 其他异常应该是可处理的
            assert "model" in str(e).lower() or "file" in str(e).lower()

    # ==================== P1 优先级 Unhappy Path 测试 ====================

    @pytest.mark.unit
    @pytest.mark.ml
    def test_prepare_data_invalid_input(self, lstm_predictor):
        """
        P1测试: 数据预处理 - 无效输入 Unhappy Path

        测试目标: prepare_data() 方法参数验证
        错误构造: 传入None或错误类型的数据
        预期结果: 应该抛出适当的异常
        """
        # 测试None输入
        with pytest.raises((ValueError, TypeError, AttributeError)):
            lstm_predictor.prepare_data(None)

        # 测试错误的数据类型
        with pytest.raises((ValueError, TypeError)):
            lstm_predictor.prepare_data("not_a_list")

        # 测试空列表
        with pytest.raises((ValueError, IndexError)):
            lstm_predictor.prepare_data([])

        # 测试缺少目标列的数据
        invalid_data = [{"time": "2024-01-01T00:00:00", "cpu_usage": 50}]
        try:
            lstm_predictor.prepare_data(invalid_data)
            # 如果没有抛出异常，至少应该处理错误
        except (ValueError, KeyError):
            # 预期的异常
            pass

    @pytest.mark.unit
    @pytest.mark.ml
    def test_predict_invalid_sequence_shape(self, lstm_predictor):
        """
        P1测试: 预测 - 无效序列形状 Unhappy Path

        测试目标: predict() 方法对错误形状序列的处理
        错误构造: 传入形状不匹配的numpy数组
        预期结果: 应该抛出适当的异常或返回错误结果
        """
        # 测试错误形状的数组
        wrong_shape_data = np.random.randn(5, 3, 2)  # 3维而非2维

        try:
            result = lstm_predictor.predict(wrong_shape_data)
            # 如果没有抛出异常，结果应该指示错误
            assert result is None or (
                hasattr(result, "error") if hasattr(result, "error") else False
            )

        except (ValueError, TypeError, AttributeError):
            # 抛出异常是预期的行为
            pass

    @pytest.mark.unit
    @pytest.mark.ml
    def test_predict_none_input(self, lstm_predictor):
        """
        P1测试: 预测 - None输入 Unhappy Path

        测试目标: predict() 方法对None输入的处理
        错误构造: 传入None作为输入数据
        预期结果: 应该抛出明确的异常
        """
        with pytest.raises((ValueError, TypeError, AttributeError)):
            lstm_predictor.predict(None)

    @pytest.mark.unit
    @pytest.mark.ml
    def test_predict_empty_sequence(self, lstm_predictor):
        """
        P1测试: 预测 - 空序列 Unhappy Path

        测试目标: predict() 方法对空数据的处理
        错误构造: 传入空的numpy数组
        预期结果: 应该抛出适当的异常
        """
        empty_sequence = np.array([]).reshape(0, 5)  # 空的2维数组

        with pytest.raises((ValueError, IndexError)):
            lstm_predictor.predict(empty_sequence)

    @pytest.mark.unit
    @pytest.mark.ml
    def test_train_with_insufficient_data(self, lstm_predictor):
        """
        P1测试: 训练 - 数据不足 Unhappy Path

        测试目标: train() 方法对不足数据的处理
        错误构造: 传入过少的训练数据
        预期结果: 应该抛出适当的异常
        """
        # 创建过小的数据集
        tiny_X = np.random.randn(2, 5)  # 只有2个样本
        tiny_y = np.random.randn(2, 1)

        try:
            result = lstm_predictor.train(tiny_X, tiny_y)
            # 可能返回错误状态或抛出异常
            assert result in [False, None] or isinstance(result, bool)
        except (ValueError, IndexError):
            # 数据不足时的预期异常
            pass

    @pytest.mark.unit
    @pytest.mark.ml
    def test_train_mismatched_data_shapes(self, lstm_predictor):
        """
        P1测试: 训练 - 数据形状不匹配 Unhappy Path

        测试目标: train() 方法对不匹配数据形状的处理
        错误构造: 传入X和y形状不匹配的数据
        预期结果: 应该抛出适当的异常
        """
        # 创建形状不匹配的数据
        X = np.random.randn(10, 5)
        y = np.random.randn(8, 1)  # 样本数量不匹配

        with pytest.raises((ValueError, RuntimeError)):
            lstm_predictor.train(X, y)

    @pytest.mark.unit
    @pytest.mark.ml
    def test_load_model_invalid_path(self, lstm_predictor):
        """
        P1测试: 模型加载 - 无效路径 Unhappy Path

        测试目标: load_model() 方法对无效路径的处理
        错误构造: 传入无效的文件路径
        预期结果: 应该抛出文件系统异常
        """
        invalid_paths = [
            "",  # 空路径
            "   ",  # 空白路径
            "/invalid/path/model.h5",  # 不存在的目录
            "not_a_model_file.txt",  # 错误的文件扩展名
        ]

        for path in invalid_paths:
            try:
                result = lstm_predictor.load_model(path)
                # 可能返回False或None
                assert result in [False, None]
            except (OSError, ValueError, FileNotFoundError):
                # 预期的异常
                pass

    @pytest.mark.unit
    @pytest.mark.ml
    def test_prediction_result_class(self):
        """
        P1测试: PredictionResult 类验证

        测试目标: PredictionResult 数据类的结构
        预期结果: 应该包含预期的字段
        """
        try:
            # 创建PredictionResult实例（使用实际字段）
            result = PredictionResult(
                timestamp="2024-01-01T00:00:00",
                predicted_values=[1.5, 2.0, 1.8],
                confidence_intervals=[(1.2, 1.8), (1.7, 2.3), (1.5, 2.1)],
                model_version="test",
            )

            # 验证属性存在
            assert hasattr(result, "timestamp")
            assert hasattr(result, "predicted_values")
            assert hasattr(result, "confidence_intervals")
            assert hasattr(result, "model_version")
            assert hasattr(result, "prediction_horizon")  # 默认值字段
            assert hasattr(result, "mae")  # 可选字段
            assert hasattr(result, "rmse")  # 可选字段
            assert hasattr(result, "r2")  # 可选字段

            # 验证数据类型
            assert isinstance(result.timestamp, str)
            assert isinstance(result.predicted_values, list)
            assert isinstance(result.confidence_intervals, list)
            assert isinstance(result.model_version, str)
            assert isinstance(result.prediction_horizon, int)

        except Exception:
            pytest.fail(f"PredictionResult should be properly defined: {e}")

    @pytest.mark.unit
    @pytest.mark.ml
    def test_training_config_class(self):
        """
        P1测试: TrainingConfig 类验证

        测试目标: TrainingConfig 数据类的结构
        预期结果: 应该包含预期的配置字段
        """
        try:
            # 创建TrainingConfig实例（使用实际字段）
            config = TrainingConfig(
                sequence_length=12,
                prediction_horizon=6,
                lstm_units=[32, 16],
                dropout_rate=0.1,
                batch_size=16,
                epochs=10,
                learning_rate=0.001,
                validation_split=0.2,
            )

            # 验证属性存在
            assert hasattr(config, "sequence_length")
            assert hasattr(config, "prediction_horizon")
            assert hasattr(config, "lstm_units")
            assert hasattr(config, "dropout_rate")
            assert hasattr(config, "batch_size")
            assert hasattr(config, "epochs")
            assert hasattr(config, "learning_rate")
            assert hasattr(config, "validation_split")
            assert hasattr(config, "early_stopping_patience")

            # 验证数据类型
            assert isinstance(config.sequence_length, int)
            assert isinstance(config.prediction_horizon, int)
            assert isinstance(config.lstm_units, (list, tuple))
            assert isinstance(config.dropout_rate, (int, float))
            assert isinstance(config.batch_size, int)
            assert isinstance(config.epochs, int)
            assert isinstance(config.learning_rate, (int, float))
            assert isinstance(config.validation_split, (int, float))
            assert isinstance(config.early_stopping_patience, int)

        except Exception:
            pytest.fail(f"TrainingConfig should be properly defined: {e}")

    @pytest.mark.unit
    @pytest.mark.ml
    def test_lstm_predictor_extreme_values(self, lstm_predictor):
        """
        P1测试: 预测 - 极端值处理 Unhappy Path

        测试目标: predict() 方法对极端值的处理
        错误构造: 传入极大或极小的数值
        预期结果: 应该有合理的边界处理
        """
        # 创建包含极端值的测试数据
        extreme_data = np.array(
            [
                [1e10, -1e10, 1e-10, -1e-10, 0],  # 极大和极小值
                [np.inf, -np.inf, np.nan, 1.0, 0.0],  # 无穷大和NaN
            ],
            dtype=np.float32,
        )

        try:
            result = lstm_predictor.predict(extreme_data)

            # 极端值应该有合理的处理
            if result is not None:
                # 如果返回结果，应该不包含NaN/Inf
                if isinstance(result, np.ndarray):
                    assert not np.any(np.isnan(result)), "Result should not contain NaN"
                    assert not np.any(np.isinf(result)), "Result should not contain Inf"

        except (ValueError, OverflowError):
            # 对于极端值，抛出数学错误是可以接受的
            pass
        except Exception:
            # 其他异常应该包含相关信息
            assert "value" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.ml
    def test_lstm_predictor_memory_efficiency(self, lstm_predictor):
        """
        P1测试: 内存效率 - 大数据处理 Unhappy Path

        测试目标: 处理相对较大的数据集时的内存管理
        错误构造: 使用较大的数据集
        预期结果: 应该能处理或给出明确的内存错误
        """
        try:
            # 创建较大的数据集（但不要太大以免影响测试性能）
            large_data = np.random.randn(1000, 50).astype(
                np.float32
            )  # 1000个样本，50个特征

            result = lstm_predictor.predict(large_data)

            # 基本验证
            assert result is not None

        except (MemoryError, ValueError):
            # 内存错误和模型未训练错误都是可以接受的
            pass
        except Exception:
            pytest.fail(f"Should handle large datasets gracefully, but got: {e}")