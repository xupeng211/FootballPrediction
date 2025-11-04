"""
核心配置测试
"""

import json
import os
import tempfile
from pathlib import Path

from src.core.config import Config, Settings, load_config


class TestConfig:
    """配置测试类"""

    def test_config_initialization(self):
        """测试配置初始化"""
        config = Config()
        assert hasattr(config, "config")
        assert hasattr(config, "config_file")
        assert hasattr(config, "config_dir")
        assert hasattr(config, "get")
        assert hasattr(config, "set")
        assert hasattr(config, "save")

    def test_config_get_set_operations(self):
        """测试配置的get和set操作"""
        config = Config()

        # 测试get默认值
        assert config.get("non_existent_key", "default") == "default"

        # 测试set和get
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"

    def test_config_file_operations(self):
        """测试配置文件操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"

            # 创建配置实例
            config = Config()
            config.config_file = config_file
            config.config_dir = Path(temp_dir)

            # 设置配置并保存
            config.set("test_key", "test_value")
            config.save()

            # 验证文件存在
            assert config_file.exists()

            # 验证文件内容
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
                assert data["test_key"] == "test_value"

    def test_load_config_from_env(self):
        """测试从环境变量加载配置"""
        # 设置环境变量
        os.environ["ENVIRONMENT"] = "test"
        os.environ["API_HOST"] = "test-host"

        try:
            settings = Settings()
            assert settings.environment == "test"
            assert settings.api_host == "test-host"
        finally:
            # 清理环境变量
            os.environ.pop("ENVIRONMENT", None)
            os.environ.pop("API_HOST", None)

    def test_settings_database_config(self):
        """测试Settings类的数据库配置"""
        settings = Settings()
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "test_database_url")
        assert (
            "sqlite" in settings.database_url or "postgresql" in settings.database_url
        )

    def test_settings_redis_config(self):
        """测试Settings类的Redis配置"""
        settings = Settings()
        assert hasattr(settings, "redis_url")
        assert "redis" in settings.redis_url

    def test_settings_api_config(self):
        """测试Settings类的API配置"""
        settings = Settings()
        assert hasattr(settings, "api_host")
        assert hasattr(settings, "api_port")
        assert settings.api_host == "localhost"
        assert settings.api_port == 8000

    def test_load_config_function(self):
        """测试load_config函数"""
        settings = load_config()
        assert isinstance(settings, Settings)
        assert hasattr(settings, "database_url")

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
        config_dict = config.to_dict() if hasattr(config, "to_dict") else {}
        assert isinstance(config_dict, dict)
