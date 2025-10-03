"""
MLflow安全模块测试
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import mlflow
from mlflow.exceptions import MlflowException

from src.utils.mlflow_security import (
    SecureMLflowLoader,
    SecureMLflowLogger,
    mlflow_security_check,
    secure_loader,
    secure_logger
)


class TestSecureMLflowLoader:
    """测试安全MLflow加载器"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.loader = SecureMLflowLoader()

    def test_init_default_values(self):
        """测试默认初始化值"""
        loader = SecureMLflowLoader()
        assert loader.allowed_model_types == ['sklearn', 'xgboost', 'lightgbm', 'catboost']
        assert loader.temp_dir is None

    def test_init_custom_allowed_types(self):
        """测试自定义允许的模型类型"""
        custom_types = ['pytorch', 'tensorflow']
        loader = SecureMLflowLoader(allowed_model_types=custom_types)
        assert loader.allowed_model_types == custom_types

    def test_context_manager_creates_temp_dir(self):
        """测试上下文管理器创建临时目录"""
        with SecureMLflowLoader() as loader:
            assert loader.temp_dir is not None
            assert Path(loader.temp_dir).exists()
            assert 'mlflow_sandbox_' in loader.temp_dir

    def test_context_manager_cleans_up(self):
        """测试上下文管理器清理临时目录"""
        with SecureMLflowLoader() as loader:
            temp_dir = loader.temp_dir

        assert loader.temp_dir is not None
        assert not Path(loader.temp_dir).exists()

    def test_context_manager_cleanup_on_exception(self):
        """测试异常时也能清理临时目录"""
        try:
            with SecureMLflowLoader() as loader:
                temp_dir = loader.temp_dir
                raise ValueError("测试异常")
        except ValueError:
            pass

        assert not Path(temp_dir).exists()

    @patch('builtins.open', new_callable=mock_open, read_data=b"fake model data")
    @patch('src.utils.mlflow_security.Path')
    def test_validate_model_signature_success(self, mock_path_class, mock_file):
        """测试模型签名验证成功"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.__str__ = lambda: "model/sklearn_model.pkl"
        mock_path_class.return_value = mock_path_instance

        result = self.loader.validate_model_signature("fake_path")
        assert result is True

    @patch('src.utils.mlflow_security.Path')
    def test_validate_model_signature_file_not_exists(self, mock_path):
        """测试模型文件不存在"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        result = self.loader.validate_model_signature("nonexistent_path")
        assert result is False

    @patch('builtins.open', new_callable=mock_open, read_data=b"fake model data")
    @patch('src.utils.mlflow_security.Path')
    def test_validate_model_signature_unsupported_type(self, mock_path, mock_file):
        """测试不支持的模型类型"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.__str__ = lambda: "model/unsupported_model.pkl"
        mock_path.return_value = mock_path_instance

        result = self.loader.validate_model_signature("fake_path")
        assert result is False

    @patch('src.utils.mlflow_security.Path')
    def test_validate_model_signature_exception(self, mock_path):
        """测试验证过程中的异常"""
        mock_path.side_effect = Exception("文件系统错误")

        result = self.loader.validate_model_signature("fake_path")
        assert result is False

    @patch('src.utils.mlflow_security.mlflow.sklearn.load_model')
    @patch.object(SecureMLflowLoader, 'validate_model_signature')
    def test_safe_load_model_success(self, mock_validate, mock_load):
        """测试安全加载模型成功"""
        mock_validate.return_value = True
        mock_model = MagicMock()
        mock_model.predict = MagicMock()
        mock_load.return_value = mock_model

        result = self.loader.safe_load_model("valid_model")
        assert result == mock_model
        mock_validate.assert_called_once_with("valid_model")

    @patch('src.utils.mlflow_security.mlflow.sklearn.load_model')
    @patch.object(SecureMLflowLoader, 'validate_model_signature')
    def test_safe_load_model_validation_failure(self, mock_validate, mock_load):
        """测试模型签名验证失败"""
        mock_validate.return_value = False

        with pytest.raises(ValueError, match="模型签名验证失败"):
            self.loader.safe_load_model("invalid_model")

    @patch('src.utils.mlflow_security.mlflow.sklearn.load_model')
    @patch.object(SecureMLflowLoader, 'validate_model_signature')
    def test_safe_load_model_mlflow_exception(self, mock_validate, mock_load):
        """测试MLflow异常"""
        mock_validate.return_value = True
        mock_load.side_effect = MlflowException("MLflow错误")

        with pytest.raises(MlflowException):
            self.loader.safe_load_model("model")

    @patch('src.utils.mlflow_security.mlflow.sklearn.load_model')
    @patch.object(SecureMLflowLoader, 'validate_model_signature')
    def test_safe_load_model_invalid_model_object(self, mock_validate, mock_load):
        """测试加载无效模型对象"""
        mock_validate.return_value = True
        mock_invalid_model = MagicMock()
        del mock_invalid_model.predict  # 删除predict属性
        mock_load.return_value = mock_invalid_model

        with pytest.raises(ValueError, match="加载的对象不是有效的模型"):
            self.loader.safe_load_model("invalid_model")

    @patch('src.utils.mlflow_security.mlflow.sklearn.load_model')
    @patch.object(SecureMLflowLoader, 'validate_model_signature')
    def test_safe_load_model_generic_exception(self, mock_validate, mock_load):
        """测试加载过程中的通用异常"""
        mock_validate.return_value = True
        mock_load.side_effect = Exception("通用错误")

        with pytest.raises(ValueError, match="模型加载失败"):
            self.loader.safe_load_model("model")

    @patch.object(SecureMLflowLoader, 'validate_model_signature')
    def test_safe_load_model_sets_environment_variables(self, mock_validate):
        """测试设置安全环境变量"""
        mock_validate.return_value = True

        with patch('src.utils.mlflow_security.mlflow.sklearn.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.predict = MagicMock()
            mock_load.return_value = mock_model

            self.loader.safe_load_model("model")

            assert os.environ.get('MLFLOW_ENABLE_MODEL_LOGGING') == 'false'
            assert os.environ.get('MLFLOW_ENABLE_ARTIFACT_LOGGING') == 'false'


class TestSecureMLflowLogger:
    """测试安全MLflow日志记录器"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.logger = SecureMLflowLogger()

    def test_init_default_safe_params(self):
        """测试默认安全参数列表"""
        expected_params = {
            'model_type', 'algorithm', 'version', 'feature_count',
            'training_samples', 'test_samples', 'accuracy', 'precision',
            'recall', 'f1_score', 'auc', 'training_time'
        }
        assert self.logger.safe_params == expected_params

    @patch('src.utils.mlflow_security.mlflow.log_param')
    def test_safe_log_param_success(self, mock_log):
        """测试安全记录参数成功"""
        self.logger.safe_log_param("accuracy", 0.95)
        mock_log.assert_called_once_with("accuracy", "0.95")

    @patch('src.utils.mlflow_security.mlflow.log_param')
    def test_safe_log_param_invalid_key_type(self, mock_log):
        """测试无效的参数键类型"""
        self.logger.safe_log_param(123, "value")
        mock_log.assert_not_called()

    @patch('src.utils.mlflow_security.mlflow.log_param')
    def test_safe_log_param_key_too_long(self, mock_log):
        """测试参数键过长"""
        long_key = "a" * 101
        self.logger.safe_log_param(long_key, "value")
        mock_log.assert_not_called()

    @patch('src.utils.mlflow_security.mlflow.log_param')
    def test_safe_log_param_unsafe_value(self, mock_log):
        """测试不安全的参数值"""
        # 测试过长的字符串
        long_value = "a" * 1001
        self.logger.safe_log_param("param", long_value)
        mock_log.assert_not_called()

    @patch('src.utils.mlflow_security.mlflow.log_param')
    def test_safe_log_param_exception(self, mock_log):
        """测试参数记录异常"""
        mock_log.side_effect = Exception("记录失败")

        # 不应该抛出异常，只记录错误
        self.logger.safe_log_param("param", "value")

    @patch('src.utils.mlflow_security.mlflow.log_metric')
    def test_safe_log_metric_success(self, mock_log):
        """测试安全记录指标成功"""
        self.logger.safe_log_metric("accuracy", 0.95)
        mock_log.assert_called_once_with("accuracy", 0.95, step=None)

    @patch('src.utils.mlflow_security.mlflow.log_metric')
    def test_safe_log_metric_with_step(self, mock_log):
        """测试带步骤的指标记录"""
        self.logger.safe_log_metric("loss", 0.1, step=100)
        mock_log.assert_called_once_with("loss", 0.1, step=100)

    @patch('src.utils.mlflow_security.mlflow.log_metric')
    def test_safe_log_metric_invalid_key(self, mock_log):
        """测试无效的指标键"""
        self.logger.safe_log_metric(123, 0.95)
        mock_log.assert_not_called()

    @patch('src.utils.mlflow_security.mlflow.log_metric')
    def test_safe_log_metric_invalid_value_type(self, mock_log):
        """测试无效的指标值类型"""
        self.logger.safe_log_metric("metric", "invalid")
        mock_log.assert_not_called()

    @patch('src.utils.mlflow_security.mlflow.log_metric')
    def test_safe_log_metric_value_out_of_range(self, mock_log):
        """测试指标值超出范围"""
        # 测试过大的值
        self.logger.safe_log_metric("metric", 1e11)
        mock_log.assert_not_called()

        # 测试过小的值
        self.logger.safe_log_metric("metric", -1e11)
        mock_log.assert_not_called()

    @patch('src.utils.mlflow_security.mlflow.log_metric')
    def test_safe_log_metric_exception(self, mock_log):
        """测试指标记录异常"""
        mock_log.side_effect = Exception("记录失败")

        # 不应该抛出异常
        self.logger.safe_log_metric("metric", 0.95)

    @patch('src.utils.mlflow_security.mlflow.sklearn.log_model')
    def test_safe_log_model_success(self, mock_log):
        """测试安全记录模型成功"""
        mock_model = MagicMock()
        mock_model.predict = MagicMock()

        self.logger.safe_log_model(mock_model, "model_path")

        # 验证调用参数
        args, kwargs = mock_log.call_args
        assert args[0] == mock_model
        assert args[1] == "model_path"
        assert kwargs.get('input_example') is None
        assert kwargs.get('pip_requirements') is None

    @patch('src.utils.mlflow_security.mlflow.sklearn.log_model')
    def test_safe_log_model_invalid_model(self, mock_log):
        """测试无效模型对象"""
        invalid_model = MagicMock()
        del invalid_model.predict

        with pytest.raises(ValueError, match="无效的模型对象"):
            self.logger.safe_log_model(invalid_model, "path")

    @patch('src.utils.mlflow_security.mlflow.sklearn.log_model')
    def test_safe_log_model_invalid_path(self, mock_log):
        """测试无效模型路径"""
        mock_model = MagicMock()
        mock_model.predict = MagicMock()

        with pytest.raises(ValueError, match="无效的模型路径"):
            self.logger.safe_log_model(mock_model, 123)

        long_path = "a" * 201
        with pytest.raises(ValueError, match="无效的模型路径"):
            self.logger.safe_log_model(mock_model, long_path)

    @patch('src.utils.mlflow_security.mlflow.sklearn.log_model')
    def test_safe_log_model_with_kwargs(self, mock_log):
        """测试带额外参数的模型记录"""
        mock_model = MagicMock()
        mock_model.predict = MagicMock()

        self.logger.safe_log_model(
            mock_model,
            "path",
            registered_model_name="test_model",
            signature="test_signature",
            extra_param="should_be_ignored"
        )

        args, kwargs = mock_log.call_args
        assert kwargs.get('registered_model_name') == "test_model"
        assert kwargs.get('signature') == "test_signature"
        assert 'extra_param' not in kwargs

    @patch('src.utils.mlflow_security.mlflow.sklearn.log_model')
    def test_safe_log_model_exception(self, mock_log):
        """测试模型记录异常"""
        mock_log.side_effect = Exception("记录失败")
        mock_model = MagicMock()
        mock_model.predict = MagicMock()

        with pytest.raises(Exception, match="记录失败"):
            self.logger.safe_log_model(mock_model, "path")

    def test_is_safe_value_primitive_types(self):
        """测试基本类型的安全检查"""
        assert self.logger._is_safe_value("test") is True
        assert self.logger._is_safe_value(123) is True
        assert self.logger._is_safe_value(12.34) is True
        assert self.logger._is_safe_value(True) is True

    def test_is_safe_value_string_too_long(self):
        """测试过长的字符串"""
        long_string = "a" * 1001
        assert self.logger._is_safe_value(long_string) is False

    def test_is_safe_value_list(self):
        """测试列表的安全检查"""
        safe_list = [1, 2, "test", True]
        assert self.logger._is_safe_value(safe_list) is True

        # 测试过长的列表
        long_list = list(range(101))
        assert self.logger._is_safe_value(long_list) is False

        # 测试包含不安全项的列表
        unsafe_list = [{"a": 1}, 2, 3]
        assert self.logger._is_safe_value(unsafe_list) is False

    def test_is_safe_value_tuple(self):
        """测试元组的安全检查"""
        safe_tuple = (1, 2, "test")
        assert self.logger._is_safe_value(safe_tuple) is True

    def test_is_safe_value_dict(self):
        """测试字典的安全检查"""
        safe_dict = {"a": 1, "b": "test", "c": True}
        assert self.logger._is_safe_value(safe_dict) is True

        # 测试过长的字典
        long_dict = {f"key_{i}": i for i in range(51)}
        assert self.logger._is_safe_value(long_dict) is False

        # 测试键过长的字典
        long_key_dict = {"a" * 101: 1}
        assert self.logger._is_safe_value(long_key_dict) is False

        # 测试值不安全的字典
        unsafe_dict = {"a": {"nested": "dict"}}
        assert self.logger._is_safe_value(unsafe_dict) is False

    def test_is_safe_value_unsupported_type(self):
        """测试不支持的类型"""
        assert self.logger._is_safe_value(set([1, 2, 3])) is False
        assert self.logger._is_safe_value(lambda x: x) is False

    def test_is_safe_item(self):
        """测试单个项目的安全检查"""
        assert self.logger._is_safe_item("test") is True
        assert self.logger._is_safe_item(123) is True
        assert self.logger._is_safe_item(12.34) is True
        assert self.logger._is_safe_item(True) is True

        # 测试过长的字符串
        long_string = "a" * 501
        assert self.logger._is_safe_item(long_string) is False

        # 测试不支持的类型
        assert self.logger._is_safe_item({"a": 1}) is False
        assert self.logger._is_safe_item([1, 2, 3]) is False


class TestMlflowSecurityCheck:
    """测试MLflow安全检查装饰器"""

    @patch('src.utils.mlflow_security.logger')
    def test_security_check_enabled(self, mock_logger):
        """测试启用安全模式"""
        with patch.dict(os.environ, {'MLFLOW_SECURITY_MODE': 'true'}):
            @mlflow_security_check
            def test_func():
                return "test"

            result = test_func()
            assert result == "test"
            mock_logger.info.assert_called_with("MLflow 安全模式已启用")

    @patch('src.utils.mlflow_security.logger')
    def test_security_check_disabled(self, mock_logger):
        """测试禁用安全模式"""
        with patch.dict(os.environ, {'MLFLOW_SECURITY_MODE': 'false'}):
            @mlflow_security_check
            def test_func():
                return "test"

            result = test_func()
            assert result == "test"
            mock_logger.info.assert_not_called()

    def test_decorator_with_arguments(self):
        """测试装饰器处理参数"""
        @mlflow_security_check
        def test_func(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_func("a", "b", kwarg1="c")
        assert result == "a-b-c"


class TestGlobalInstances:
    """测试全局实例"""

    def test_secure_loader_global_instance(self):
        """测试全局安全加载器实例"""
        assert secure_loader is not None
        assert isinstance(secure_loader, SecureMLflowLoader)

    def test_secure_logger_global_instance(self):
        """测试全局安全日志记录器实例"""
        assert secure_logger is not None
        assert isinstance(secure_logger, SecureMLflowLogger)