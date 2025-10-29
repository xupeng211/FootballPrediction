from typing import Optional
from typing import Dict
"""
TestContainers模拟模块
为测试环境提供容器服务的Mock实现
"""


class MockContainer:
    """模拟容器基类"""

    def __init__(self, image: str, **kwargs):
        self.image = image
        self.kwargs = kwargs
        self._container_id = f"mock_container_{id(self)}"
        self._is_running = False
        self._host = "localhost"
        self._port = 5432  # 默认端口
        self._env = {}

    def start(self) -> None:
        """启动容器"""
        self._is_running = True

    def stop(self) -> None:
        """停止容器"""
        self._is_running = False

    def get_container_host_ip(self) -> str:
        """获取容器主机IP"""
        return self._host

    def get_exposed_port(self, port: int) -> str:
        """获取暴露的端口"""
        return str(self._port)

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()

    @property
    def is_running(self) -> bool:
        """检查容器是否运行"""
        return self._is_running


class PostgresContainer(MockContainer):
    """模拟PostgreSQL容器"""

    def __init__(
        self,
        image: str = "postgres:13",
        user: str = "test",
        password: str = "test",
        dbname: str = "test_db",
        port: int = 5432,
        **kwargs,
    ):
        super().__init__(image, **kwargs)
        self.user = user
        self.password = password
        self.dbname = dbname
        self._port = port
        self._env = {
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": dbname,
        }

    def get_connection_url(self) -> str:
        """获取连接URL"""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self._port)
        return f"postgresql://{self.user}:{self.password}@{host}:{port}/{self.dbname}"


class RedisContainer(MockContainer):
    """模拟Redis容器"""

    def __init__(self, image: str = "redis:6", port: int = 6379, **kwargs):
        super().__init__(image, **kwargs)
        self._port = port

    def get_connection_url(self) -> str:
        """获取连接URL"""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self._port)
        return f"redis://{host}:{port}"


class TestPostgresContainer(PostgresContainer):
    """扩展的PostgreSQL容器，配置了测试数据库"""

    def __init__(
        self,
        user: str = "test_user",
        password: str = "test_pass",
        dbname: str = "test_db",
        port: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            image="postgres:13",
            user=user,
            password=password,
            dbname=dbname,
            port=port or 15432,  # 避免与主PostgreSQL冲突
            **kwargs,
        )

    def setup_test_database(self) -> None:
        """设置测试数据库"""
        # 在实际实现中，这里会创建表和插入测试数据
        pass


class TestRedisContainer(RedisContainer):
    """扩展的Redis容器，配置了测试环境"""

    def __init__(self, port: Optional[int] = None, **kwargs):
        super().__init__(image="redis:6", port=port or 16379, **kwargs)  # 避免与主Redis冲突

    def setup_test_data(self) -> None:
        """设置测试数据"""
        # 在实际实现中，这里会插入测试数据
        pass


def wait_for_logs(container, predicate: str, timeout: int = 30, interval: float = 1.0) -> None:
    """等待容器日志中出现指定内容"""
    # Mock实现，直接返回
    pass


def create_test_database_container(
    user: str = "test_user", password: str = "test_pass", dbname: str = "test_db"
) -> TestPostgresContainer:
    """创建测试数据库容器"""
    return TestPostgresContainer(user=user, password=password, dbname=dbname)


def create_test_redis_container(port: Optional[int] = None) -> TestRedisContainer:
    """创建测试Redis容器"""
    return TestRedisContainer(port=port)


# 便捷函数
def start_test_containers():
    """启动所有测试容器"""
    postgres = create_test_database_container()
    redis = create_test_redis_container()

    postgres.start()
    redis.start()

    return {"postgres": postgres, "redis": redis}


def stop_test_containers(containers: Dict[str, MockContainer]) -> None:
    """停止所有测试容器"""
    for container in containers.values():
        container.stop()


# 模拟装饰器，用于不需要真实容器的测试
def mock_containers(func):
    """Mock容器装饰器"""

    def wrapper(*args, **kwargs):
        # 创建mock容器实例
        mock_postgres = TestPostgresContainer()
        mock_redis = TestRedisContainer()

        # 启动mock容器
        mock_postgres.start()
        mock_redis.start()

        try:
            return func(mock_postgres, mock_redis, *args, **kwargs)
        finally:
            # 清理
            mock_postgres.stop()
            mock_redis.stop()

    return wrapper


# 向外提供的接口
__all__ = [
    "PostgresContainer",
    "RedisContainer",
    "TestPostgresContainer",
    "TestRedisContainer",
    "wait_for_logs",
    "create_test_database_container",
    "create_test_redis_container",
    "start_test_containers",
    "stop_test_containers",
    "mock_containers",
]
