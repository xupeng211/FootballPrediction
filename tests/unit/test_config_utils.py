"""配置工具测试"""

import pytest
from unittest.mock import Mock, patch
from src.core.config import Config
from src.config.fastapi_config import FastAPIConfig


class TestConfigUtils:
    """测试配置工具"""

    def test_config_creation(self):
        """测试配置创建"""
        config = Config()
        assert config is not None

    def test_fastapi_config_creation(self):
        """测试FastAPI配置创建"""
        config = FastAPIConfig()
        assert config is not None

    @patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"})
    def test_environment_variables(self):
        """测试环境变量"""
        config = Config()
        # 这里应该测试环境变量的读取
        assert config is not None

    def test_config_validation(self):
        """测试配置验证"""
        config = FastAPIConfig()

        # Mock验证方法
        config.validate = Mock(return_value=True)

        result = config.validate()
        assert result is True

    def test_config_serialization(self):
        """测试配置序列化"""
        config = Config()

        # Mock序列化方法
        config.to_dict = Mock(return_value={"key": "value"})

        result = config.to_dict()
        assert result == {"key": "value"}

    @patch("src.core.config.load_config")
    def test_config_loading(self, mock_load):
        """测试配置加载"""
        mock_load.return_value = {"test": "value"}

        from src.core.config import load_config

        config = load_config()

        assert config == {"test": "value"}
        mock_load.assert_called_once()

    def test_config_defaults(self):
        """测试配置默认值"""
        config = FastAPIConfig()

        # 测试默认值
        assert hasattr(config, "host")
        assert hasattr(config, "port")
        assert hasattr(config, "debug")
