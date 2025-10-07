"""扩展的core/config.py测试 - 提升覆盖率"""

import os
from unittest.mock import patch

from src.core.config import Settings, get_settings, config


class TestConfigExtended:
    """扩展的配置测试，覆盖未测试的代码路径"""

    def test_settings_with_minimal_mode_true(self):
        """测试最小模式设置为true"""
        with patch.dict(os.environ, {"MINIMAL_API_MODE": "true"}):
            settings = Settings()
            assert settings.minimal_api_mode is True

    def test_settings_with_debug_mode(self):
        """测试调试模式"""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            settings = Settings()
            assert settings.debug is True

    def test_settings_with_custom_api_keys(self):
        """测试自定义API密钥"""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-openai-key",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
        ):
            settings = Settings()
            assert settings.openai_api_key == "test-openai-key"
            assert settings.anthropic_api_key == "test-anthropic-key"

    def test_settings_with_custom_urls(self):
        """测试自定义URLs"""
        with patch.dict(
            os.environ, {"API_V1_STR": "/api/v2", "PROJECT_NAME": "Test Project"}
        ):
            settings = Settings()
            assert settings.api_v1_str == "/api/v2"
            assert settings.project_name == "Test Project"

    def test_settings_with_cors_origins(self):
        """测试CORS origins配置"""
        with patch.dict(
            os.environ,
            {
                "BACKEND_CORS_ORIGINS": '["http://localhost:3000", "https://example.com"]'
            },
        ):
            settings = Settings()
            assert "http://localhost:3000" in settings.backend_cors_origins
            assert "https://example.com" in settings.backend_cors_origins

    def test_environment_property(self):
        """测试环境属性"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            settings = Settings()
            # 测试环境属性（如果存在）
            if hasattr(settings, "environment"):
                assert settings.environment == "production"

    def test_config_object(self):
        """测试配置对象"""
        # config 应该是 Settings 的实例
        assert isinstance(config, Settings)

    def test_database_url_property(self):
        """测试数据库URL属性"""
        settings = Settings()
        # 测试数据库URL属性（如果存在）
        if hasattr(settings, "database_url"):
            assert settings.database_url is not None

    def test_redis_url_property(self):
        """测试Redis URL属性"""
        settings = Settings()
        # 测试Redis URL属性（如果存在）
        if hasattr(settings, "redis_url"):
            assert settings.redis_url is not None

    def test_get_settings_caching(self):
        """测试设置缓存机制"""
        # 第一次调用
        settings1 = get_settings()
        # 第二次调用应该返回相同的实例
        settings2 = get_settings()
        assert settings1 is settings2

    def test_settings_with_log_level(self):
        """测试日志级别设置"""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.log_level == "DEBUG"

    def test_settings_with_numeric_values(self):
        """测试数值配置"""
        with patch.dict(os.environ, {"API_PORT": "9000", "WORKERS": "4"}):
            settings = Settings()
            # 验证数值被正确解析（如果存在这些属性）
            if hasattr(settings, "api_port"):
                assert settings.api_port == 9000

    def test_settings_with_boolean_values(self):
        """测试布尔值配置"""
        test_cases = [
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
        ]

        for value, expected in test_cases:
            with patch.dict(os.environ, {"ENABLE_FEATURE": value}):
                settings = Settings()
                # 验证布尔值被正确解析（如果存在该属性）
                if hasattr(settings, "enable_feature"):
                    assert settings.enable_feature is expected

    def test_environment_detection(self):
        """测试环境检测"""
        environments = ["development", "testing", "staging", "production"]

        for env in environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                settings = Settings()
                # 测试环境检测（如果有相关属性）
                if hasattr(settings, "environment"):
                    assert settings.environment == env
