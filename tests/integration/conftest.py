"""Integration test fixtures."""

import asyncio
import os
import threading

import pytest
import uvicorn

from main import app


class IntegrationTestServer(uvicorn.Server):
    """Uvicorn server wrapper that exposes lifecycle hooks for tests."""

    def __init__(self, config: uvicorn.Config):
        super().__init__(config)
        self._started_event: asyncio.Event = asyncio.Event()

    async def startup(self, sockets=None):  # type: ignore[override]
        await super().startup(sockets=sockets)
        self._started_event.set()

    async def shutdown(self, sockets=None) -> None:
        self.should_exit = True
        await asyncio.sleep(0.1)


@pytest.fixture(scope="session", autouse=True)
def integration_server(event_loop):
    """Spin up the FastAPI application for integration tests."""

    os.environ.setdefault("ENVIRONMENT", "test")

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        lifespan="on",
    )
    server = IntegrationTestServer(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # wait until the server reports ready
    event_loop.run_until_complete(server._started_event.wait())

    try:
        yield
    finally:
        event_loop.run_until_complete(server.force_exit())
        server_thread.join(timeout=5)


@pytest.fixture(scope="session")
def api_base_url():
    return "http://127.0.0.1:8000"
