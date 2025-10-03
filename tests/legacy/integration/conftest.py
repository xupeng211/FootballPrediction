"""Integration test fixtures used across the suite."""

import os
from collections.abc import Generator

import pytest


@pytest.fixture(scope = os.getenv("CONFTEST_SCOPE_9"), autouse=True)
def integration_server() -> Generator[None, None, None]:
    """Ensure integration tests run against the test environment."""
    os.environ.setdefault("ENVIRONMENT", "test")
    yield


@pytest.fixture(scope = os.getenv("CONFTEST_SCOPE_9"))
def api_base_url() -> str:
    """Default base URL for integration test clients."""
    return "http://localhost:8000"
