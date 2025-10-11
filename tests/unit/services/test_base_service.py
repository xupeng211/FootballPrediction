# from src.services.base_unified import BaseService


def test_base_service():
    service = BaseService()
    assert service is not None


def test_service_methods():
    service = BaseService()
    assert hasattr(service, "execute")
    assert hasattr(service, "validate")
