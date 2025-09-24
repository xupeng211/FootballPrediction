import os

import pytest

from src.database.config import (
    DatabaseConfig,
    get_database_config,
    get_production_database_config,
    get_test_database_config,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    keys = [
        "ENVIRONMENT",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_ECHO",
        "DB_ECHO_POOL",
        "TEST_DB_HOST",
        "TEST_DB_PORT",
        "TEST_DB_NAME",
        "TEST_DB_USER",
        "TEST_DB_PASSWORD",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_database_config_sqlite_urls() -> None:
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="example.db",
        username="user",
        password="pass",
        pool_size=5,
        max_overflow=10,
    )

    assert config.sync_url == "sqlite:///example.db"
    assert config.async_url == "sqlite+aiosqlite:///example.db"
    assert config.alembic_url == "sqlite:///example.db"

    in_memory = DatabaseConfig(
        host="localhost",
        port=5432,
        database=":memory:",
        username="user",
        password="pass",
        pool_size=5,
        max_overflow=10,
    )

    assert in_memory.sync_url == "sqlite:///:memory:"
    assert in_memory.async_url == "sqlite+aiosqlite:///:memory:"
    assert in_memory.alembic_url == "sqlite:///:memory:"


def test_database_config_postgres_urls() -> None:
    config = DatabaseConfig(
        host="db.example.com",
        port=5432,
        database="football_prediction",
        username="postgres",
        password="secret",
        pool_size=10,
        max_overflow=20,
    )

    expected_sync = (
        "postgresql+psycopg2://postgres:secret@db.example.com:5432/football_prediction"
    )
    expected_async = (
        "postgresql+asyncpg://postgres:secret@db.example.com:5432/football_prediction"
    )

    assert config.sync_url == expected_sync
    assert config.async_url == expected_async
    assert config.alembic_url == expected_sync


def test_get_database_config_for_test_environment(monkeypatch) -> None:
    monkeypatch.setenv("TEST_DB_HOST", "test-db")
    monkeypatch.setenv("TEST_DB_PORT", "6543")
    monkeypatch.setenv("TEST_DB_NAME", "fp_test")
    monkeypatch.setenv("TEST_DB_USER", "tester")
    monkeypatch.setenv("TEST_DB_PASSWORD", "test-pass")

    config = get_test_database_config()

    assert config.host == "test-db"
    assert config.port == 6543
    assert config.database == "fp_test"
    assert config.username == "tester"
    assert config.password == "test-pass"


def test_get_database_config_for_production_environment(monkeypatch) -> None:
    monkeypatch.setenv("PROD_DB_HOST", "prod-db")
    monkeypatch.setenv("PROD_DB_PORT", "7654")
    monkeypatch.setenv("PROD_DB_NAME", "fp_prod")
    monkeypatch.setenv("PROD_DB_USER", "prod-user")
    monkeypatch.setenv("PROD_DB_PASSWORD", "prod-pass")
    monkeypatch.setenv("PROD_DB_POOL_SIZE", "15")
    monkeypatch.setenv("PROD_DB_MAX_OVERFLOW", "25")
    monkeypatch.setenv("PROD_DB_ECHO", "true")
    monkeypatch.setenv("PROD_DB_ECHO_POOL", "true")

    config = get_production_database_config()

    assert config.host == "prod-db"
    assert config.port == 7654
    assert config.database == "fp_prod"
    assert config.username == "prod-user"
    assert config.password == "prod-pass"
    assert config.pool_size == 15
    assert config.max_overflow == 25
    assert config.echo is True
    assert config.echo_pool is True


def test_get_database_config_uses_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("PROD_DB_HOST", "env-prod")
    monkeypatch.setenv("PROD_DB_PORT", "9000")
    monkeypatch.setenv("PROD_DB_NAME", "env_db")
    monkeypatch.setenv("PROD_DB_USER", "env-user")

    config = get_database_config()

    assert config.host == "env-prod"
    assert config.port == 9000
    assert config.database == "env_db"
