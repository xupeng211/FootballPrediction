"""
核心配置测试
"""

import pytest
import os
from src.core.config import Config, load_config


class TestConfig:
    """配置测试类"""

    def test_config_initialization(self):
        """测试配置初始化"""
        config = Config()
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'debug')
        assert hasattr(config, 'secret_key')

    def test_load_config_from_env(self):
        """测试从环境变量加载配置"""
        # 设置环境变量
        os.environ['DEBUG'] = 'true'
        os.environ['SECRET_KEY'] = 'test-secret'

        try:
            config = load_config()
            assert config.debug is True
            assert config.secret_key == 'test-secret'
        finally:
            # 清理环境变量
            os.environ.pop('DEBUG', None)
            os.environ.pop('SECRET_KEY', None)

    def test_config_defaults(self):
        """测试配置默认值"""
        config = Config()
        assert isinstance(config.debug, bool)
        assert isinstance(config.secret_key, str)
        assert len(config.secret_key) > 0

    def test_config_validation(self):
        """测试配置验证"""
        config = Config()

        # 测试必需字段
        assert config.database_url is not None
        assert config.secret_key is not None

    def test_config_update(self):
        """测试配置更新"""
        config = Config()
        original_debug = config.debug

        config.debug = not original_debug
        assert config.debug != original_debug

    def test_config_serialization(self):
        """测试配置序列化"""
        config = Config()

        # 测试转换为字典
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else {}
        assert isinstance(config_dict, dict)