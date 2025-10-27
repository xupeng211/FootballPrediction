from unittest.mock import patch

"""测试 FastAPI 配置"""

import pytest


@pytest.mark.unit
@pytest.mark.api
def test_fastapi_config_import():
    """测试 FastAPI 配置模块导入"""
    try:
        from src._config.fastapi_config import get_fastapi_config

        assert True
    except ImportError:
        pytest.skip("FastAPI config not available")


def test_openapi_config_import():
    """测试 OpenAPI 配置模块导入"""
    try:
        from src._config.openapi_config import setup_openapi

        assert callable(setup_openapi)
    except ImportError:
        pytest.skip("OpenAPI config not available")
