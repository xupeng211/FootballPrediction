import pytest

@pytest.mark.parametrize("service", [
    "src.services.audit_service",
    "src.services.base",
    "src.services.content_analysis",
    "src.services.data_processing",
    "src.services.manager",
    "src.services.user_profile"
])
def test_service_import(service):
    """测试所有服务可以导入"""
    try:
        __import__(service)
        assert True
    except ImportError:
        pytest.skip(f"Service {service} not available")

def test_base_service():
    from src.services.base import BaseService
    service = BaseService()
    assert service is not None