"""
MLflow安全模块简化测试
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

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

    @patch('src.utils.mlflow_security.Path')
    def test_validate_model_signature_file_not_exists(self, mock_path):
        """测试模型文件不存在"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        result = self.loader.validate_model_signature("nonexistent_path")
        assert result is False

    @patch('src.utils.mlflow_security.Path')
    def test_validate_model_signature_exception(self, mock_path):
        """测试验证过程中的异常"""
        mock_path.side_effect = Exception("文件系统错误")

        result = self.loader.validate_model_signature("fake_path")
        assert result is False

    def test_validate_model_signature_unsupported_type_simple(self):
        """测试不支持的模型类型（简化版本）"""
        # 使用真实的临时文件进行测试
        with tempfile.NamedTemporaryFile(suffix="unsupported_model.pkl", delete=False) as tmp:
            tmp.write(b"fake model data")
            tmp_path = tmp.name

        try:
            result = self.loader.validate_model_signature(tmp_path)
            assert result is False
        finally:
            os.unlink(tmp_path)

    def test_validate_model_signature_sklearn_type(self):
        """测试支持的sklearn模型类型"""
        # 使用真实的临时文件进行测试
        with tempfile.NamedTemporaryFile(suffix="sklearn_model.pkl", delete=False) as tmp:
            tmp.write(b"fake sklearn model data")
            tmp_path = tmp.name

        try:
            result = self.loader.validate_model_signature(tmp_path)
            assert result is True
        finally:
            os.unlink(tmp_path)

    def test_safe_load_model_validation_failure(self):
        """测试模型签名验证失败"""
        with patch.object(self.loader, 'validate_model_signature', return_value=False):
            with pytest.raises(ValueError, match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_113")):
                self.loader.safe_load_model("invalid_model")


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

    def test_safe_log_param_invalid_key_type(self):
        """测试无效的参数键类型"""
        with patch('mlflow.log_param') as mock_log:
            self.logger.safe_log_param(123, "value")
            mock_log.assert_not_called()

    def test_safe_log_param_key_too_long(self):
        """测试参数键过长"""
        with patch('mlflow.log_param') as mock_log:
            long_key = "a" * 101
            self.logger.safe_log_param(long_key, "value")
            mock_log.assert_not_called()

    def test_safe_log_param_unsafe_value_long_string(self):
        """测试不安全的参数值（过长字符串）"""
        with patch('mlflow.log_param') as mock_log:
            long_value = "a" * 1001
            self.logger.safe_log_param("param", long_value)
            mock_log.assert_not_called()

    def test_safe_log_param_unsafe_value_unsupported_type(self):
        """测试不安全的参数值（不支持的类型）"""
        with patch('mlflow.log_param') as mock_log:
            # 测试过长的列表
            long_list = list(range(101))
            self.logger.safe_log_param("param", long_list)
            mock_log.assert_not_called()

    def test_safe_log_metric_invalid_key(self):
        """测试无效的指标键"""
        with patch('mlflow.log_metric') as mock_log:
            self.logger.safe_log_metric(123, 0.95)
            mock_log.assert_not_called()

    def test_safe_log_metric_invalid_value_type(self):
        """测试无效的指标值类型"""
        with patch('mlflow.log_metric') as mock_log:
            self.logger.safe_log_metric("metric", "invalid")
            mock_log.assert_not_called()

    def test_safe_log_metric_value_out_of_range(self):
        """测试指标值超出范围"""
        with patch('mlflow.log_metric') as mock_log:
            # 测试过大的值
            self.logger.safe_log_metric("metric", 1e11)
            mock_log.assert_not_called()

            # 测试过小的值
            self.logger.safe_log_metric("metric", -1e11)
            mock_log.assert_not_called()

    def test_safe_log_model_invalid_model(self):
        """测试无效模型对象"""
        invalid_model = MagicMock()
        del invalid_model.predict

        with pytest.raises(ValueError, match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_187")):
            self.logger.safe_log_model(invalid_model, "path")

    def test_safe_log_model_invalid_path(self):
        """测试无效模型路径"""
        mock_model = MagicMock()
        mock_model.predict = MagicMock()

        with pytest.raises(ValueError, match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_194")):
            self.logger.safe_log_model(mock_model, 123)

        long_path = "a" * 201
        with pytest.raises(ValueError, match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_194")):
            self.logger.safe_log_model(mock_model, long_path)

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

    def test_is_safe_value_list_safe(self):
        """测试安全列表"""
        safe_list = [1, 2, "test", True]
        assert self.logger._is_safe_value(safe_list) is True

    def test_is_safe_value_list_too_long(self):
        """测试过长的列表"""
        long_list = list(range(101))
        assert self.logger._is_safe_value(long_list) is False

    def test_is_safe_value_dict_safe(self):
        """测试安全字典"""
        safe_dict = {"a": 1, "b": "test", "c": True}
        assert self.logger._is_safe_value(safe_dict) is True

    def test_is_safe_value_dict_too_long(self):
        """测试过长的字典"""
        long_dict = {f"key_{i}": i for i in range(51)}
        assert self.logger._is_safe_value(long_dict) is False

    def test_is_safe_value_dict_key_too_long(self):
        """测试键过长的字典"""
        long_key_dict = {"a" * 101: 1}
        assert self.logger._is_safe_value(long_key_dict) is False

    def test_is_safe_value_unsupported_type(self):
        """测试不支持的类型"""
        assert self.logger._is_safe_value(set([1, 2, 3])) is False
        assert self.logger._is_safe_value(lambda x: x) is False

    def test_is_safe_item_safe_types(self):
        """测试安全项目的安全检查"""
        assert self.logger._is_safe_item("test") is True
        assert self.logger._is_safe_item(123) is True
        assert self.logger._is_safe_item(12.34) is True
        assert self.logger._is_safe_item(True) is True

    def test_is_safe_item_long_string(self):
        """测试过长的字符串"""
        long_string = "a" * 501
        assert self.logger._is_safe_item(long_string) is False

    def test_is_safe_item_unsupported_type(self):
        """测试不支持的类型"""
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