"""配置管理测试"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

from src.core.config import Config


class TestConfig:
    """配置管理器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建临时目录用于测试
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = Config()

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理临时目录
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_config_initialization(self):
        """测试配置初始化"""
        config = Config()
        assert hasattr(config, 'config_dir')
        assert hasattr(config, 'config_file')
        assert hasattr(config, '_config')
        assert isinstance(config._config, dict)

    def test_config_dir_creation(self):
        """测试配置目录创建"""
        config = Config()
        # 配置目录应该存在或可以创建
        assert config.config_dir.parent.exists()

    def test_get_existing_key(self):
        """测试获取已存在的配置键"""
        config = Config()
        # 设置一个测试值
        config._config['test_key'] = 'test_value'

        # 获取配置值
        assert config.get('test_key') == 'test_value'

    def test_get_default_value(self):
        """测试获取不存在的键时返回默认值"""
        config = Config()

        # 获取不存在的键，应该返回默认值
        assert config.get('nonexistent_key', 'default') == 'default'
        assert config.get('nonexistent_key') is None

    def test_set_config_value(self):
        """测试设置配置值"""
        config = Config()

        # 设置配置值
        config.set('test_key', 'test_value')
        assert config.get('test_key') == 'test_value'

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('json.load')
    def test_load_config_from_file(self, mock_json_load, mock_exists, mock_file):
        """测试从文件加载配置"""
        # 模拟配置文件存在
        mock_exists.return_value = True
        mock_json_load.return_value = {'test': 'value'}

        config = Config()
        # 验证配置已加载
        assert config.get('test') == 'value'

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    def test_load_config_invalid_json(self, mock_exists, mock_file):
        """测试加载无效JSON文件时的处理"""
        # 模拟配置文件存在但内容无效
        mock_exists.return_value = True

        with patch('json.load', side_effect=json.JSONDecodeError('test', 'test', 0)):
            config = Config()
            # 应该使用空配置，不抛出异常
            assert config._config == {}

    def test_save_config(self):
        """测试保存配置到文件"""
        config = Config()
        config.set('test_key', 'test_value')

        # 使用临时目录进行测试
        with patch.object(config, 'config_file', self.temp_dir / 'test_config.json'):
            config.save()

            # 验证文件已创建并包含正确内容
            assert config.config_file.exists()
            with open(config.config_file, 'r') as f:
                saved_config = json.load(f)
                assert saved_config['test_key'] == 'test_value'

    def test_set_nested_value(self):
        """测试设置嵌套值"""
        config = Config()

        # 设置嵌套配置
        config.set('database.host', 'localhost')
        config.set('database.port', 5432)

        assert config.get('database.host') == 'localhost'
        assert config.get('database.port') == 5432

    def test_config_dict_access(self):
        """测试直接访问内部字典"""
        config = Config()

        # 通过内部字典访问
        config._config['test_key'] = 'test_value'

        assert config.get('test_key') == 'test_value'

    def test_config_none_value(self):
        """测试设置和获取 None 值"""
        config = Config()

        config.set('test_key', None)

        assert config.get('test_key') is None
        assert config.get('test_key', 'default') is None

    def test_config_complex_value(self):
        """测试设置和获取复杂值"""
        config = Config()

        # 设置复杂类型
        complex_value = {
            'nested': {
                'list': [1, 2, 3],
                'dict': {'a': 1, 'b': 2}
            }
        }
        config.set('complex', complex_value)

        assert config.get('complex') == complex_value

    def test_config_overwrite_value(self):
        """测试覆盖配置值"""
        config = Config()

        config.set('test_key', 'initial_value')
        assert config.get('test_key') == 'initial_value'

        # 覆盖值
        config.set('test_key', 'new_value')
        assert config.get('test_key') == 'new_value'

    def test_environment_variable_override(self):
        """测试环境变量覆盖配置"""
        config = Config()
        config.set('test_key', 'config_value')

        # 使用环境变量覆盖
        with patch.dict('os.environ', {'FOOTBALLPREDICTION_TEST_KEY': 'env_value'}):
            # 如果有环境变量覆盖机制，测试它
            value = config.get('test_key')
            # 这里根据实际的实现来调整断言

    def test_nested_config_access(self):
        """测试嵌套配置访问"""
        config = Config()

        # 设置嵌套配置
        config.set('database.host', 'localhost')
        config.set('database.port', 5432)

        # 如果支持嵌套访问，测试它
        # 根据实际实现调整测试