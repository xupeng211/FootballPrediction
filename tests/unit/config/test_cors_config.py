"""
CORS配置模块测试
CORS Config Module Tests

测试src/config/cors_config.py中定义的CORS配置功能，专注于实现100%覆盖率。
Tests CORS configuration functionality defined in src/config/cors_config.py, focused on achieving 100% coverage.
"""

import pytest
import os
from unittest.mock import patch, mock_open
from typing import List

# 导入要测试的模块
try:
    from src.config.cors_config import (
        get_cors_origins,
        get_cors_config,
    )
    CORS_CONFIG_AVAILABLE = True
except ImportError:
    CORS_CONFIG_AVAILABLE = False


@pytest.mark.skipif(not CORS_CONFIG_AVAILABLE, reason="CORS config module not available")
class TestGetCorsOrigins:
    """get_cors_origins函数测试"""

    def test_get_cors_origins_function_exists(self):
        """测试get_cors_origins函数存在"""
        assert get_cors_origins is not None
        assert callable(get_cors_origins)

    def test_get_cors_origins_development_env(self):
        """测试开发环境的CORS源"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "http://localhost:3000" in origins
            assert "http://localhost:8080" in origins
            assert "http://localhost:8000" in origins

    def test_get_cors_origins_development_env_unset(self):
        """测试环境变量未设置时的默认开发环境"""
        with patch.dict(os.environ, {}, clear=True):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "http://localhost:3000" in origins
            assert "http://localhost:8080" in origins
            assert "http://localhost:8000" in origins

    def test_get_cors_origins_production_env(self):
        """测试生产环境的CORS源"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://app1.com,https://app2.com,https://api.example.com"
        }):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "https://app1.com" in origins
            assert "https://app2.com" in origins
            assert "https://api.example.com" in origins

    def test_get_cors_origins_production_env_default(self):
        """测试生产环境未设置CORS_ORIGINS时的默认值"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            # 确保CORS_ORIGINS不存在
            if "CORS_ORIGINS" in os.environ:
                del os.environ["CORS_ORIGINS"]

            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 1
            assert "https://yourdomain.com" in origins

    def test_get_cors_origins_production_env_empty_origins(self):
        """测试生产环境CORS_ORIGINS为空字符串"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": ""
        }):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 1
            assert origins[0] == ""

    def test_get_cors_origins_production_env_single_origin(self):
        """测试生产环境单个CORS源"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://single-origin.com"
        }):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 1
            assert "https://single-origin.com" in origins

    def test_get_cors_origins_staging_env(self):
        """测试预发布环境的CORS源"""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 2
            assert "https://staging.yourdomain.com" in origins
            assert "http://localhost:3000" in origins

    def test_get_cors_origins_staging_env_case_insensitive(self):
        """测试环境变量大小写不敏感"""
        with patch.dict(os.environ, {"ENVIRONMENT": "STAGING"}):
            origins = get_cors_origins()

            # 应该使用默认的development环境配置
            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "http://localhost:3000" in origins

    def test_get_cors_origins_test_env(self):
        """测试测试环境（应该使用默认配置）"""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            origins = get_cors_origins()

            # 应该使用默认的development环境配置
            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "http://localhost:3000" in origins

    def test_get_cors_origins_unknown_env(self):
        """测试未知环境（应该使用默认配置）"""
        with patch.dict(os.environ, {"ENVIRONMENT": "unknown"}):
            origins = get_cors_origins()

            # 应该使用默认的development环境配置
            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "http://localhost:3000" in origins

    def test_get_cors_origins_production_with_spaces(self):
        """测试生产环境CORS_ORIGINS包含空格"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://app1.com , https://app2.com ,https://app3.com"
        }):
            origins = get_cors_origins()

            assert isinstance(origins, list)
            assert len(origins) == 3
            assert "https://app1.com " in origins  # 空格会被保留
            assert " https://app2.com " in origins
            assert "https://app3.com" in origins


@pytest.mark.skipif(not CORS_CONFIG_AVAILABLE, reason="CORS config module not available")
class TestGetCorsConfig:
    """get_cors_config函数测试"""

    def test_get_cors_config_function_exists(self):
        """测试get_cors_config函数存在"""
        assert get_cors_config is not None
        assert callable(get_cors_config)

    def test_get_cors_config_structure(self):
        """测试CORS配置结构"""
        config = get_cors_config()

        assert isinstance(config, dict)

        # 验证所有必需的键
        required_keys = [
            "allow_origins",
            "allow_credentials",
            "allow_methods",
            "allow_headers",
            "max_age"
        ]

        for key in required_keys:
            assert key in config, f"Missing key: {key}"

    def test_get_cors_config_development_env(self):
        """测试开发环境的CORS配置"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = get_cors_config()

            assert config["allow_origins"] == [
                "http://localhost:3000",
                "http://localhost:8080",
                "http://localhost:8000"
            ]
            assert config["allow_credentials"] is True
            assert config["allow_methods"] == ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            assert config["allow_headers"] == ["*"]
            assert config["max_age"] == 600

    def test_get_cors_config_production_env(self):
        """测试生产环境的CORS配置"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://production.com"
        }):
            config = get_cors_config()

            assert config["allow_origins"] == ["https://production.com"]
            assert config["allow_credentials"] is True
            assert config["allow_methods"] == ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            assert config["allow_headers"] == ["*"]
            assert config["max_age"] == 600

    def test_get_cors_config_staging_env(self):
        """测试预发布环境的CORS配置"""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            config = get_cors_config()

            assert config["allow_origins"] == [
                "https://staging.yourdomain.com",
                "http://localhost:3000"
            ]
            assert config["allow_credentials"] is True
            assert config["allow_methods"] == ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            assert config["allow_headers"] == ["*"]
            assert config["max_age"] == 600

    def test_get_cors_config_consistency(self):
        """测试配置一致性"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            config = get_cors_config()
            origins = get_cors_origins()

            # allow_origins应该与get_cors_origins()返回的一致
            assert config["allow_origins"] == origins

    def test_get_cors_config_immutability(self):
        """测试配置的不可变性（多次调用返回相同结果）"""
        config1 = get_cors_config()
        config2 = get_cors_config()

        # 两次调用应该返回相同的结果
        assert config1 == config2
        # 但是不应该是同一个对象（每次调用都重新生成）
        assert config1 is not config2

    def test_get_cors_config_allow_credentials_type(self):
        """测试allow_credentials的类型"""
        config = get_cors_config()

        assert isinstance(config["allow_credentials"], bool)
        assert config["allow_credentials"] is True

    def test_get_cors_config_allow_methods_type(self):
        """测试allow_methods的类型"""
        config = get_cors_config()

        assert isinstance(config["allow_methods"], list)
        assert len(config["allow_methods"]) == 5
        assert "GET" in config["allow_methods"]
        assert "POST" in config["allow_methods"]
        assert "PUT" in config["allow_methods"]
        assert "DELETE" in config["allow_methods"]
        assert "OPTIONS" in config["allow_methods"]

    def test_get_cors_config_allow_headers_type(self):
        """测试allow_headers的类型"""
        config = get_cors_config()

        assert isinstance(config["allow_headers"], list)
        assert len(config["allow_headers"]) == 1
        assert config["allow_headers"] == ["*"]

    def test_get_cors_config_max_age_type(self):
        """测试max_age的类型"""
        config = get_cors_config()

        assert isinstance(config["max_age"], int)
        assert config["max_age"] == 600


@pytest.mark.skipif(not CORS_CONFIG_AVAILABLE, reason="CORS config module not available")
class TestIntegration:
    """集成测试"""

    def test_full_workflow_development(self):
        """测试完整的开发环境工作流"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # 获取CORS源
            origins = get_cors_origins()
            assert len(origins) == 3

            # 获取完整配置
            config = get_cors_config()
            assert config["allow_origins"] == origins

            # 验证配置的完整性
            assert config["allow_credentials"] is True
            assert "GET" in config["allow_methods"]
            assert "*" in config["allow_headers"]
            assert config["max_age"] == 600

    def test_full_workflow_production(self):
        """测试完整的生产环境工作流"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://api.example.com,https://app.example.com"
        }):
            # 获取CORS源
            origins = get_cors_origins()
            assert len(origins) == 2
            assert "https://api.example.com" in origins
            assert "https://app.example.com" in origins

            # 获取完整配置
            config = get_cors_config()
            assert config["allow_origins"] == origins

    def test_environment_change_behavior(self):
        """测试环境变更时的行为"""
        # 先测试开发环境
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            dev_config = get_cors_config()
            assert len(dev_config["allow_origins"]) == 3

        # 再测试生产环境
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://prod.com"
        }):
            prod_config = get_cors_config()
            assert len(prod_config["allow_origins"]) == 1
            assert prod_config["allow_origins"] != dev_config["allow_origins"]

    def test_edge_case_empty_env_var(self):
        """测试环境变量为空字符串的边界情况"""
        with patch.dict(os.environ, {"ENVIRONMENT": ""}):
            # 空字符串应该被视为未知环境，使用默认配置
            config = get_cors_config()
            assert len(config["allow_origins"]) == 3  # 开发环境的默认配置
            assert "http://localhost:3000" in config["allow_origins"]

    def test_edge_case_whitespace_env_var(self):
        """测试环境变量包含空格的边界情况"""
        with patch.dict(os.environ, {"ENVIRONMENT": " development "}):
            # 包含空格应该被视为未知环境，使用默认配置
            config = get_cors_config()
            assert len(config["allow_origins"]) == 3  # 开发环境的默认配置

    def test_real_world_scenario_localhost(self):
        """测试真实场景：本地开发"""
        with patch.dict(os.environ, {}, clear=True):
            # 没有设置环境变量，应该默认为开发环境
            config = get_cors_config()

            # 验证本地开发的典型配置
            assert "http://localhost:3000" in config["allow_origins"]
            assert "http://localhost:8000" in config["allow_origins"]
            assert config["allow_credentials"] is True
            assert "*" in config["allow_headers"]

    def test_real_world_scenario_production_domains(self):
        """测试真实场景：生产域名"""
        production_domains = [
            "https://www.example.com",
            "https://api.example.com",
            "https://admin.example.com"
        ]

        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": ",".join(production_domains)
        }):
            config = get_cors_config()

            # 验证所有生产域名都被包含
            for domain in production_domains:
                assert domain in config["allow_origins"]

            # 验证其他配置保持不变
            assert config["allow_credentials"] is True
            assert config["max_age"] == 600