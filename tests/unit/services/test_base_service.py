import pytest

from src.services.base import AbstractBaseService, BaseService

pytestmark = pytest.mark.unit


class _SampleService(AbstractBaseService):
    def __init__(self) -> None:
        super().__init__("SampleService")
        self.initialized = False
        self.stopped = False

    async def initialize(self) -> bool:
        self.initialized = True
        return True

    async def shutdown(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_base_service_lifecycle() -> None:
    service = BaseService("TestService")

    assert service.start() is True
    assert service.get_status() == "running"

    assert service.stop() is True
    assert service.get_status() == "stopped"

    assert await service.initialize() is True
    assert service.get_status() == "stopped"

    await service.shutdown()
    assert service.get_status() == "stopped"


@pytest.mark.asyncio
async def test_abstract_base_service_contract() -> None:
    service = _SampleService()

    assert await service.initialize() is True
    assert service.initialized is True

    await service.shutdown()
    assert service.stopped is True
