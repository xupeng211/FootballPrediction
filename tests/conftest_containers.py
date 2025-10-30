"""
pytest容器配置模块
提供TestContainers相关的pytest fixtures和配置
"""

from typing import Any, Dict, Generator

import pytest

from helpers.testcontainers import (
    TestPostgresContainer,
    TestRedisContainer,
    create_test_database_container,
    create_test_redis_container,
    mock_containers,
)


@pytest.fixture(scope="session")
def test_postgres_container() -> Generator[TestPostgresContainer, None, None]:
    """测试PostgreSQL容器fixture"""
    container = create_test_database_container()
    container.start()
    container.setup_test_database()

    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def test_redis_container() -> Generator[TestRedisContainer, None, None]:
    """测试Redis容器fixture"""
    container = create_test_redis_container()
    container.start()
    container.setup_test_data()

    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def test_containers(
    test_postgres_container: TestPostgresContainer,
    test_redis_container: TestRedisContainer,
) -> Dict[str, Any]:
    """测试容器fixture"""
    return {"postgres": test_postgres_container, "redis": test_redis_container}


@pytest.fixture
def mock_containers_fixture() -> Generator[Dict[str, Any], None, None]:
    """Mock容器fixture"""
    postgres = create_test_database_container()
    redis = create_test_redis_container()

    postgres.start()
    redis.start()

    try:
        yield {"postgres": postgres, "redis": redis}
    finally:
        postgres.stop()
        redis.stop()


@pytest.fixture
def postgres_connection_url(test_postgres_container: TestPostgresContainer) -> str:
    """PostgreSQL连接URL"""
    return test_postgres_container.get_connection_url()


@pytest.fixture
def redis_connection_url(test_redis_container: TestRedisContainer) -> str:
    """Redis连接URL"""
    return test_redis_container.get_connection_url()


# 当没有真实Docker环境时使用的Mock fixtures
@pytest.fixture
def mock_postgres_container() -> Generator[TestPostgresContainer, None, None]:
    """Mock PostgreSQL容器"""
    container = TestPostgresContainer()
    container.start()
    container.setup_test_database()

    try:
        yield container
    finally:
        container.stop()


@pytest.fixture
def mock_redis_container() -> Generator[TestRedisContainer, None, None]:
    """Mock Redis容器"""
    container = TestRedisContainer()
    container.start()
    container.setup_test_data()

    try:
        yield container
    finally:
        container.stop()


# 跳过真实容器的标记
pytest_plugins = []


# 如果没有Docker环境,自动使用Mock
def pytest_configure(config):
    """pytest配置钩子"""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        # Docker可用，可以使用真实容器
    except Exception:
        # Docker不可用,添加标记以跳过需要真实容器的测试
        config.addinivalue_line(
            "markers", "requires_docker: mark test as requiring Docker"
        )
