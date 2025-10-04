from pathlib import Path
import json

from src.core import (
from unittest.mock import mock_open, patch
from unittest.mock import patch
import logging
import pytest
import tempfile

"""
测试core模块的功能
"""
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch
import pytest
from src.core import (
    Config,
    ConfigError,
    DataError,
    FootballPredictionError,
    Logger,
    config,
    logger)
pytestmark = pytest.mark.unit
class TestConfig:
    """测试配置管理类"""
    def test_config_initialization(self):
        """测试配置初始化"""
        test_config = Config()
        assert test_config.config_dir ==Path.home() / ".footballprediction[" assert test_config.config_file ==test_config.config_dir / "]config.json[" assert isinstance(test_config._config, dict)""""
    def test_config_load_nonexistent_file(self):
        "]""测试加载不存在的配置文件"""
        with patch.object(Path, "exists[", return_value = False)": test_config = Config()": assert test_config._config =={}" def test_config_load_existing_file(self):"
        "]""测试加载存在的配置文件"""
        test_data = {"key[: "value"", "number]: 123}": mock_file_content = json.dumps(test_data)": with (:": patch.object(Path, "exists[", return_value=True),": patch("]builtins.open[", mock_open(read_data=mock_file_content))):": test_config = Config()": assert test_config._config ==test_data[" def test_config_load_corrupted_file(self):"
        "]]""测试加载损坏的配置文件"""
        with (:
            patch.object(Path, "exists[", return_value=True),": patch("]builtins.open[", mock_open(read_data="]invalid json[")),": patch("]logging.warning[") as mock_warning):": test_config = Config()": assert test_config._config =={}" mock_warning.assert_called_once()"
    def test_config_get_existing_key(self):
        "]""测试获取存在的配置项"""
        test_config = Config()
        test_config._config = {"test_key[": ["]test_value["}": result = test_config.get("]test_key[")": assert result =="]test_value[" def test_config_get_nonexistent_key_with_default("
    """"
        "]""测试获取不存在的配置项（有默认值）"""
        test_config = Config()
        test_config._config = {}
        result = test_config.get("nonexistent_key[", "]default_value[")": assert result =="]default_value[" def test_config_get_nonexistent_key_without_default("
    """"
        "]""测试获取不存在的配置项（无默认值）"""
        test_config = Config()
        test_config._config = {}
        result = test_config.get("nonexistent_key[")": assert result is None[" def test_config_set(self):""
        "]]""测试设置配置项"""
        test_config = Config()
        test_config.set("new_key[", "]new_value[")": assert test_config._config["]new_key["] =="]new_value[" def test_config_save_success("
    """"
        "]""测试成功保存配置"""
        test_config = Config()
        test_config._config = {"key[" "]value["}": with (:": patch.object(Path, "]mkdir[") as mock_mkdir,": patch("]builtins.open[", mock_open()) as mock_file):": test_config.save()": mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)": mock_file.assert_called_once()"
    def test_config_save_with_chinese_characters(self):
        "]""测试保存包含中文字符的配置"""
        test_config = Config()
        test_config._config = {"用户名[: "测试用户"", "描述[" "]这是一个测试]}": mock_file_handle = mock_open()": with (:": patch.object(Path, "mkdir["),": patch("]builtins.open[", mock_file_handle) as mock_file):": test_config.save()"""
            # 验证json.dump被调用时使用了ensure_ascii=False
            mock_file.assert_called_once()
            # 验证文件是以UTF-8编码打开的
            args, kwargs = mock_file.call_args
            assert kwargs.get("]encoding[") =="]utf-8[" class TestLogger:""""
    "]""测试日志管理类"""
    def test_setup_logger_default_level(self):
        """测试设置默认级别的日志器"""
        test_logger = Logger.setup_logger("test_logger[")": assert isinstance(test_logger, logging.Logger)" assert test_logger.name =="]test_logger[" assert test_logger.level ==logging.INFO[""""
    def test_setup_logger_custom_level(self):
        "]]""测试设置自定义级别的日志器"""
        test_logger = Logger.setup_logger("test_logger[", "]DEBUG[")": assert test_logger.level ==logging.DEBUG[" def test_setup_logger_invalid_level(self):""
        "]]""测试设置无效级别的日志器"""
        # 由于使用getattr，无效级别会抛出AttributeError
        with pytest.raises(AttributeError):
            Logger.setup_logger("test_logger[", "]INVALID[")": def test_setup_logger_handlers(self):"""
        "]""测试日志器处理器设置"""
        test_logger = Logger.setup_logger("test_logger_handlers[")""""
        # 第一次调用应该添加处理器
        assert len(test_logger.handlers) ==1
        # 第二次调用不应该重复添加处理器
        test_logger2 = Logger.setup_logger("]test_logger_handlers[")": assert len(test_logger2.handlers) ==1[" assert test_logger is test_logger2  # 应该是同一个实例[""
    def test_logger_formatter(self):
        "]]]""测试日志格式器"""
        test_logger = Logger.setup_logger("test_formatter[")": handler = test_logger.handlers[0]": formatter = handler.formatter[": assert isinstance(formatter, logging.Formatter)"
        assert "]]%(asctime)s[" in formatter._fmt[""""
        assert "]]%(name)s[" in formatter._fmt[""""
        assert "]]%(levelname)s[" in formatter._fmt[""""
        assert "]]%(message)s[" in formatter._fmt[""""
class TestExceptions:
    "]]""测试异常类"""
    def test_footballprediction_error(self):
        """测试基础异常类"""
        error = FootballPredictionError("test error message[")": assert isinstance(error, Exception)" assert str(error) =="]test error message[" def test_config_error("
    """"
        "]""测试配置异常类"""
        error = ConfigError("config error message[")": assert isinstance(error, FootballPredictionError)" assert isinstance(error, Exception)""
        assert str(error) =="]config error message[" def test_data_error("
    """"
        "]""测试数据异常类"""
        error = DataError("data error message[")": assert isinstance(error, FootballPredictionError)" assert isinstance(error, Exception)""
        assert str(error) =="]data error message[" def test_exception_inheritance("
    """"
        "]""测试异常继承关系"""
        # 验证所有自定义异常都继承自FootballPredictionError
        config_error = ConfigError("test[")": data_error = DataError("]test[")": assert isinstance(config_error, FootballPredictionError)" assert isinstance(data_error, FootballPredictionError)""
        # 验证它们也是标准异常
        assert isinstance(config_error, Exception)
        assert isinstance(data_error, Exception)
class TestGlobalInstances:
    "]""测试全局实例"""
    def test_global_config_instance(self):
        """测试全局配置实例"""
        assert config is not None
        assert isinstance(config, Config)
    def test_global_logger_instance(self):
        """测试全局日志器实例"""
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name =="footballprediction[" def test_global_instances_usability("
    """"
        "]""测试全局实例的可用性"""
        # 测试全局配置可以使用
        config.set("test_global[", "]test_value[")": assert config.get("]test_global[") =="]test_value["""""
        # 测试全局日志器可以使用
        assert hasattr(logger, "]info[")" assert hasattr(logger, "]error[")" assert hasattr(logger, "]warning[")" assert hasattr(logger, "]debug[")" class TestConfigIntegration:"""
    "]""测试配置类集成功能"""
    def test_config_full_workflow(self):
        """测试配置的完整工作流程"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir = temp_config_dir Path(temp_dir) / ".footballprediction[": temp_config_file = temp_config_dir / "]config.json["""""
            # 模拟配置类使用临时目录
            with patch.object(Path, "]home[", return_value = Path(temp_dir))": test_config = Config()"""
                # 设置一些配置
                test_config.set("]user_name[", "]测试用户[")": test_config.set("]preferences[", {"]language[": "]zh[", "]theme[": "]dark["))""""
                # 保存配置
                test_config.save()
                # 验证文件被创建
                assert temp_config_file.exists()
            # 验证内容正确
            with open(temp_config_file, "]r[", encoding = "]utf-8[") as f[": saved_data = json.load(f)": assert saved_data["]]user_name["] =="]测试用户[" assert saved_data["]preferences["]"]language[" =="]zh[" def test_config_error_handling_workflow("
    """"
        "]""测试配置错误处理工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一个损坏的配置文件
            temp_config_dir = Path(temp_dir) / ".footballprediction[": temp_config_dir.mkdir(parents=True)": temp_config_file = temp_config_dir / "]config.json[": with open(temp_config_file, "]w[") as f:": f.write("]这不是有效的JSON{[]})")""""
            # 模拟配置类使用临时目录
            with (:
                patch.object(Path, "home[", return_value=Path(temp_dir)),": patch("]logging.warning[") as mock_warning):": test_config = Config()"""
                # 应该记录警告并使用空配置
                mock_warning.assert_called_once()
                assert test_config._config =={}
            # 应该仍然可以正常工作
            test_config.set("]recovery_test[", "]success[")": assert test_config.get("]recovery_test[") =="]success"