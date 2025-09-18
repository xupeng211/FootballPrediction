"""
End-to-end test fixtures.
"""

import asyncio
import os
import sys
import threading

# Add project root to path for imports - must be before local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import httpx  # noqa: E402
import pytest  # noqa: E402
import uvicorn  # noqa: E402

from src.api.main import app  # noqa: E402


class TestServer(uvicorn.Server):
    """Uvicorn server for testing."""

    def __init__(self, config: uvicorn.Config):
        super().__init__(config)
        self.is_started = asyncio.Event()

    async def startup(self, sockets=None):
        """Override startup to set event."""
        await super().startup(sockets=sockets)
        self.is_started.set()

    async def force_exit(self):
        """Force server exit."""
        self.should_exit = True
        # Wait for the server to shut down
        await asyncio.sleep(0.1)


@pytest.fixture(scope="session")
def server(event_loop):
    """Start a test server in a separate thread."""
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = TestServer(config)

    server_thread = threading.Thread(target=server.run)
    server_thread.start()

    # Wait for the server to start
    event_loop.run_until_complete(server.is_started.wait())

    yield

    # Stop the server
    event_loop.run_until_complete(server.force_exit())
    server_thread.join()


@pytest.fixture(scope="session")
def api_base_url():
    """Return the base URL for the test API."""
    return "http://127.0.0.1:8000"


@pytest.fixture(scope="session")
def test_api_client(api_base_url, server):
    """Create a test API client."""
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client
