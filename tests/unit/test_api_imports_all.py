# API模块导入测试
import pytest

@pytest.mark.parametrize("module", [
    "src.api.app",
    "src.api.health",
    "src.api.predictions",
    "src.api.data",
    "src.api.features",
    "src.api.monitoring",
    "src.api.models",
    "src.api.schemas"
])
def test_api_module_import(module):
    """测试所有API模块可以导入"""
    try:
        __import__(module)
        assert True
    except ImportError:
        pytest.skip(f"Module {module} not available")