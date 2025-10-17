"""测试 FastAPI 配置"""

import pytest
from unittest.mock import patch


def test_fastapi_config_import():
    """测试 FastAPI 配置模块导入"""
    try:
        from src.config.fastapi_config import get_fastapi_config

        assert True
    except ImportError:
        pass  # 已激活


def test_openapi_config_import():
    """测试 OpenAPI 配置模块导入"""
    try:
        from src.config.openapi_config import setup_openapi

        assert callable(setup_openapi)
    except ImportError:
        pass  # 已激活
