"""End-to-end test fixtures."""

from collections.abc import Generator

import httpx
import pytest


@pytest.fixture(scope="session", autouse=True)
def server() -> Generator[None, None, None]:
    """Placeholder server fixture; real server managed by higher-level orchestration."""
    yield


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for E2E requests."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def test_api_client(api_base_url: str) -> Generator[httpx.Client, None, None]:
    """Provide an HTTP client for API requests."""
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client
