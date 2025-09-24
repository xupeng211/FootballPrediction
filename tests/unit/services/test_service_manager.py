import pytest

from src.services.base import BaseService
from src.services.manager import ServiceManager

pytestmark = pytest.mark.unit


class _SuccessfulService(BaseService):
    def __init__(self, name: str = "success") -> None:
        super().__init__(name)
        self.initialized = 0
        self.shutdown_calls = 0

    async def initialize(self) -> bool:
        self.initialized += 1
        return True

    async def shutdown(self) -> None:
        self.shutdown_calls += 1


class _FailingService(BaseService):
    def __init__(self, should_raise: bool = False) -> None:
        super().__init__("failing")
        self.should_raise = should_raise

    async def initialize(self) -> bool:
        if self.should_raise:
            raise RuntimeError("init failure")
        return False

    async def shutdown(self) -> None:
        if self.should_raise:
            raise RuntimeError("shutdown failure")


@pytest.mark.asyncio
async def test_register_and_retrieve_services() -> None:
    manager = ServiceManager()
    service = _SuccessfulService("analytics")
    manager.register_service("analytics", service)

    assert manager.get_service("analytics") is service
    assert "analytics" in manager.list_services()
    assert manager.services["analytics"] is service


@pytest.mark.asyncio
async def test_initialize_all_handles_success_and_failure() -> None:
    manager = ServiceManager()
    good_service = _SuccessfulService("good")
    failing_service = _FailingService()

    manager.register_service("good", good_service)
    manager.register_service("bad", failing_service)

    result = await manager.initialize_all()

    assert result is False
    assert good_service.initialized == 1


@pytest.mark.asyncio
async def test_initialize_all_captures_exceptions_and_shutdown_continues() -> None:
    manager = ServiceManager()
    raising_service = _FailingService(should_raise=True)
    normal_service = _SuccessfulService("normal")

    manager.register_service("raise", raising_service)
    manager.register_service("normal", normal_service)

    result = await manager.initialize_all()
    assert result is False

    await manager.shutdown_all()
    assert normal_service.shutdown_calls == 1
