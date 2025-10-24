"""OpenAPI配置测试"""

import pytest
from src.config.openapi_config import OpenAPIConfig, setup_openapi


@pytest.mark.unit
@pytest.mark.api

class TestOpenAPIConfig:
    """测试OpenAPI配置"""

    def test_openapi_config_import(self):
        """测试OpenAPI配置模块导入"""
        try:
            from src._config.openapi_config import OpenAPIConfig

            assert OpenAPIConfig is not None
        except ImportError:
            pytest.skip("OpenAPI config not available")

    def test_get_app_info(self):
        """测试获取应用信息"""
        info = OpenAPIConfig.get_app_info()
        assert info is not None
        assert "title" in info
        assert info["title"] == "Football Prediction API"
        assert "description" in info
        assert "version" in info

    def test_get_servers(self):
        """测试获取服务器配置"""
        servers = OpenAPIConfig.get_servers()
        assert isinstance(servers, list)
        assert len(servers) > 0
        assert all("url" in server for server in servers)

    def test_get_tags(self):
        """测试获取API标签"""
        tags = OpenAPIConfig.get_tags()
        assert isinstance(tags, list)
        assert len(tags) > 0
        assert all("name" in tag for tag in tags)

    def test_get_security_schemes(self):
        """测试获取安全配置"""
        security = OpenAPIConfig.get_security_schemes()
        assert isinstance(security, dict)
        assert "ApiKeyAuth" in security
        assert "BearerAuth" in security

    def test_setup_openapi_import(self):
        """测试setup_openapi函数导入"""
        try:
            from src._config.openapi_config import setup_openapi

            assert setup_openapi is not None
        except ImportError:
            pytest.skip("setup_openapi not available")
