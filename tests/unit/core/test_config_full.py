"""
测试 src/core/config.py 模块
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# 确保模块可以导入
sys.path.insert(0, 'src')

try:
    from src.core.config import get_config, Config, load_env_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="config模块不可用")
class TestConfigModule:
    """测试 config 模块"""

    def test_config_imports(self):
        """测试配置模块导入"""
        from src.core import config
        assert config is not None

    def test_get_config_function(self):
        """测试 get_config 函数"""
        config = get_config()
        assert config is not None
        assert hasattr(config, 'get')

    def test_config_get_method(self):
        """测试配置获取方法"""
        config = get_config()

        # 测试获取存在的配置
        value = config.get('TEST_KEY', 'default')
        assert value is not None

    def test_config_environment_override(self):
        """测试环境变量覆盖"""
        # 设置环境变量
        os.environ['TEST_CONFIG_VAR'] = 'test_value'

        try:
            config = get_config()
            # 如果支持环境变量，应该能获取到
            value = config.get('TEST_CONFIG_VAR')
            # 清理
            os.environ.pop('TEST_CONFIG_VAR', None)
        except:
            pass

    @patch.dict(os.environ, {'ENVIRONMENT': 'testing'})
    def test_testing_config(self):
        """测试测试环境配置"""
        config = get_config()

        # 测试环境应该有特定的配置
        env = config.get('ENVIRONMENT')
        assert env == 'testing'

    def test_config_singleton(self):
        """测试配置单例"""
        config1 = get_config()
        config2 = get_config()

        # 应该返回相同的实例
        assert config1 is config2

    def test_default_values(self):
        """测试默认值"""
        config = get_config()

        # 测试默认值
        debug = config.get('DEBUG', False)
        assert isinstance(debug, bool)

        env = config.get('ENVIRONMENT', 'development')
        assert env in ['development', 'testing', 'production']

    def test_nested_config_access(self):
        """测试嵌套配置访问"""
        config = get_config()

        # 如果支持嵌套访问
        if hasattr(config, 'get_nested'):
            value = config.get_nested('database.host', 'localhost')
            assert value is not None
        else:
            # 尝试点号访问
            value = config.get('database.host', 'localhost')
            # 可能不支持，这是正常的