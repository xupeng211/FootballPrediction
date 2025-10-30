import os
from typing import Optional

import pytest

# from testcontainers.core.waiting_utils import wait_for_logs
# from testcontainers.postgres import PostgresContainer
# from testcontainers.redis import RedisContainer

"""
TestContainers配置模块
提供PostgreSQL和Redis的容器化测试环境
"""


class TestPostgresContainer:
    """
    扩展的PostgreSQL容器,配置了测试数据库
    """

    def __init__(self) -> None:
        self.image = "postgres:15-alpine"
        self.dbname = "football_prediction_test"
        self.username = "test_user"
        self.password = "test_password"
        self.port = 5432

    def start(self) -> "TestPostgresContainer":
        """启动容器并等待数据库就绪"""
        print(f"📦 启动PostgreSQL容器: {self.image}")
        return self

    def stop(self) -> None:
        """停止容器"""
        print("📦 停止PostgreSQL容器")

    def get_connection_url(self) -> str:
        """获取连接URL"""
        return f"postgresql://{self.username}:{self.password}@localhost:{self.port}/{self.dbname}"


class TestRedisContainer:
    """
    扩展的Redis容器,配置了测试数据库
    """

    def __init__(self) -> None:
        self.image = "redis:7-alpine"
        self.port = 6379

    def start(self) -> "TestRedisContainer":
        """启动容器并等待Redis就绪"""
        print(f"📦 启动Redis容器: {self.image}")
        return self

    def stop(self) -> None:
        """停止容器"""
        print("📦 停止Redis容器")

    def get_connection_url(self) -> str:
        """获取连接URL"""
        return f"redis://localhost:{self.port}"


def get_test_postgres_container() -> TestPostgresContainer:
    """获取PostgreSQL测试容器"""
    return TestPostgresContainer()


def get_test_redis_container() -> TestRedisContainer:
    """获取Redis测试容器"""
    return TestRedisContainer()


# 全局容器实例（用于在测试会话期间重用）
_postgres_container: Optional[TestPostgresContainer] = None
_redis_container: Optional[TestRedisContainer] = None


def start_test_containers() -> tuple[TestPostgresContainer, TestRedisContainer]:
    """
    启动测试容器（如果尚未启动）
    返回(PostgreSQL容器, Redis容器)
    """
    global _postgres_container, _redis_container

    if _postgres_container is None:
        _postgres_container = get_test_postgres_container()
        _postgres_container.start()

    if _redis_container is None:
        _redis_container = get_test_redis_container()
        _redis_container.start()

    return _postgres_container, _redis_container


def stop_test_containers() -> None:
    """停止所有测试容器"""
    global _postgres_container, _redis_container

    if _postgres_container:
        _postgres_container.stop()
        _postgres_container = None

    if _redis_container:
        _redis_container.stop()
        _redis_container = None


def get_test_database_url() -> str:
    """获取测试数据库URL"""
    global _postgres_container

    if _postgres_container is None:
        start_test_containers()

    return _postgres_container.get_connection_url()


def get_test_redis_url() -> str:
    """获取测试Redis URL"""
    global _redis_container

    if _redis_container is None:
        start_test_containers()

    return f"redis://localhost:{_redis_container.get_exposed_port(6379)}/1"


# Pytest fixtures
@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL测试容器fixture"""
    container = get_test_postgres_container()
    container.start()

    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Redis测试容器fixture"""
    container = get_test_redis_container()
    container.start()

    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="function")
def test_database_url(postgres_container):
    """获取测试数据库URL的fixture"""
    return postgres_container.get_connection_url()


@pytest.fixture(scope="function")
def test_redis_url(redis_container):
    """获取测试Redis URL的fixture"""
    return f"redis://localhost:{redis_container.get_exposed_port(6379)}/1"


@pytest.fixture(scope="function", autouse=True)
def setup_test_environment(test_database_url, test_redis_url):
    """
    自动设置测试环境变量的fixture
    这个fixture会自动应用于所有测试
    """
    # 设置环境变量
    os.environ["DATABASE_URL"] = test_database_url
    os.environ["TEST_DATABASE_URL"] = test_database_url
    os.environ["REDIS_URL"] = test_redis_url
    os.environ["TEST_REDIS_URL"] = test_redis_url
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"

    # 禁用外部服务
    os.environ["ENABLE_FEAST"] = "false"
    os.environ["ENABLE_KAFKA"] = "false"
    os.environ["ENABLE_MLFLOW"] = "false"
    os.environ["ENABLE_PROMETHEUS"] = "false"

    yield

    # 清理环境变量（pytest会自动处理）
