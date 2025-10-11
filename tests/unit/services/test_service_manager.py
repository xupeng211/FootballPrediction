from src.services.manager_mod import ServiceManager


def test_service_manager():
    manager = ServiceManager()
    assert manager is not None


def test_manager_methods():
    manager = ServiceManager()
    assert hasattr(manager, "register_service")
    assert hasattr(manager, "get_service")
