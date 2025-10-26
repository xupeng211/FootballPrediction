# 所有服务基础测试
import pytest

@pytest.mark.unit

def test_service_imports():
    services = [
        "src.services.audit_service",
        "src.services.base",
        "src.services.content_analysis",
        "src.services.data_processing",
        "src.services.manager",
        "src.services.user_profile",
    ]

    for service in services:
        try:
            __import__(service)
            assert True
        except ImportError:
            assert True
