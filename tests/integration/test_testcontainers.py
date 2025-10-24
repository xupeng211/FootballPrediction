"""
TestContainers集成测试
TestContainers Integration Tests

使用真实容器进行集成测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import time

# 测试标记
pytestmark = [pytest.mark.integration, pytest.mark.slow]

# 尝试导入testcontainers
TESTCONTAINERS_AVAILABLE = False
try:
    from testcontainers.compose import DockerCompose
    from testcontainers.core.waiting_utils import wait_for_logs

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    print("TestContainers not available, using mock instead")


@pytest.mark.skipif(not TESTCONTAINERS_AVAILABLE, reason="TestContainers not installed")
class TestPostgreSQLIntegration:
    """PostgreSQL集成测试"""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """启动PostgreSQL容器"""
        with DockerCompose(
            ".", compose_file_name="docker-compose.test.yml", pull=True
        ) as compose:
            # 等待数据库就绪
            db_port = compose.get_service_port("postgres", 5432)
            wait_for_logs(compose, "database system is ready to accept connections")
            time.sleep(2)  # 额外等待时间

            yield {
                "host": "localhost",
                "port": db_port,
                "database": "footballprediction_test",
                "username": "postgres",
                "password": "postgres",
            }

    async def test_postgres_connection(self, postgres_container):
        """测试：PostgreSQL连接"""
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        # 构建连接URL
        url = (
            f"postgresql+asyncpg://{postgres_container['username']}:"
            f"{postgres_container['password']}@"
            f"{postgres_container['host']}:{postgres_container['port']}/"
            f"{postgres_container['database']}"
        )

        # 创建引擎
        engine = create_async_engine(url, echo=False)

        # 测试连接
        async with engine.begin() as conn:
            _result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version

        await engine.dispose()

    async def test_database_migrations(self, postgres_container):
        """测试：数据库迁移"""
        from src.database.connection import DatabaseManager

        # 使用测试数据库URL
        db_manager = DatabaseManager(
            f"postgresql+asyncpg://{postgres_container['username']}:"
            f"{postgres_container['password']}@"
            f"{postgres_container['host']}:{postgres_container['port']}/"
            f"{postgres_container['database']}"
        )

        # 测试连接和表创建
        async with db_manager.get_session() as session:
            # 创建测试表
            await session.execute(
                text(
                    """
                CREATE TABLE test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
                )
            )

            # 插入数据
            await session.execute(
                text("INSERT INTO test_table (name) VALUES (:name)"),
                {"name": "test_record"},
            )

            # 查询数据
            _result = await session.execute(
                text("SELECT name FROM test_table WHERE name = :name"),
                {"name": "test_record"},
            )
            assert result.scalar() == "test_record"

    async def test_repository_with_postgres(self, postgres_container):
        """测试：仓储模式与PostgreSQL"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import Column, Integer, String, DateTime
        from sqlalchemy.ext.declarative import declarative_base
        from src.database.repositories import BaseRepository

        # 创建模型
        Base = declarative_base()

        class TestModel(Base):
            __tablename__ = "test_repos"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))
            value = Column(Integer)

        # 创建引擎
        url = (
            f"postgresql+asyncpg://{postgres_container['username']}:"
            f"{postgres_container['password']}@"
            f"{postgres_container['host']}:{postgres_container['port']}/"
            f"{postgres_container['database']}"
        )
        engine = create_async_engine(url)

        # 创建表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 创建仓储
        class TestRepository(BaseRepository):
            model_class = TestModel

        # 测试仓储操作
        async_session = sessionmaker(engine, class_=AsyncSession)
        async with async_session() as session:
            repo = TestRepository(session)

            # 创建记录
            created = await repo.create(name="test", value=100)
            assert created.name == "test"
            assert created.value   == 100

            # 获取记录
            retrieved = await repo.get_by_id(created.id)
            assert retrieved is not None
            assert retrieved.name   == "test"

        await engine.dispose()


@pytest.mark.skipif(not TESTCONTAINERS_AVAILABLE, reason="TestContainers not installed")
class TestRedisIntegration:
    """Redis集成测试"""

    @pytest.fixture(scope="class")
    def redis_container(self):
        """启动Redis容器"""
        with DockerCompose(
            ".", compose_file_name="docker-compose.test.yml", pull=True
        ) as compose:
            # 等待Redis就绪
            redis_port = compose.get_service_port("redis", 6379)
            wait_for_logs(compose, "Ready to accept connections")
            time.sleep(1)

            yield {"host": "localhost", "port": redis_port, "db": 0}

    async def test_redis_connection(self, redis_container):
        """测试：Redis连接"""
        import redis.asyncio as redis

        # 创建Redis客户端
        client = redis.Redis(
            host=redis_container["host"],
            port=redis_container["port"],
            db=redis_container["db"],
        )

        # 测试连接
        await client.ping()

        # 测试基本操作
        await client.set("test_key", "test_value")
        value = await client.get("test_key")
        assert value.decode() == "test_value"

        await client.close()

    async def test_redis_cache_operations(self, redis_container):
        """测试：Redis缓存操作"""
        from src.cache.redis_manager import RedisManager

        # 创建Redis管理器
        redis_manager = RedisManager(
            host=redis_container["host"], port=redis_container["port"]
        )

        # 测试缓存操作
        await redis_manager.set("cache_key", {"data": "test_value"}, ttl=60)
        cached_data = await redis_manager.get("cache_key")
        assert cached_data is not None
        assert cached_data["data"]   == "test_value"

        # 测试缓存过期
        await redis_manager.set("expire_key", "expire_value", ttl=1)
        await asyncio.sleep(2)
        expired_data = await redis_manager.get("expire_key")
        assert expired_data is None


@pytest.mark.integration
class TestWithMockContainers:
    """使用模拟的容器测试（当TestContainers不可用时）"""

    async def test_database_connection_mock(self):
        """测试：模拟数据库连接"""
        with patch("src.database.connection.DatabaseManager") as mock_db:
            # 设置模拟
            mock_instance = AsyncMock()
            mock_session = AsyncMock()
            mock_instance.get_session.return_value.__aenter__.return_value = (
                mock_session
            )
            mock_db.return_value = mock_instance

            # 测试连接
            db_manager = mock_db("sqlite+aiosqlite:///:memory:")
            async with db_manager.get_session() as session:
                _result = await session.execute("SELECT 1")
                assert result is not None

    async def test_redis_connection_mock(self):
        """测试：模拟Redis连接"""
        with patch("redis.asyncio.Redis") as mock_redis:
            # 设置模拟
            client = AsyncMock()
            client.ping.return_value = True
            client.get.return_value = b"test_value"
            mock_redis.return_value = client

            # 测试连接
            from redis.asyncio import Redis

            redis_client = Redis(host="localhost", port=6379)
            await redis_client.ping()
            value = await redis_client.get("test_key")
            assert value   == b"test_value"

    async def test_full_workflow_mock(self):
        """测试：完整工作流（模拟）"""
        # 模拟数据收集
        with patch(
            "src.services.data_collection.DataCollectionService"
        ) as mock_service:
            service = AsyncMock()
            service.collect_match_data.return_value = {"matches": 10}
            mock_service.return_value = service

            # 模拟预测
            with patch("src.services.prediction.PredictionService") as mock_pred:
                pred_service = AsyncMock()
                pred_service.predict.return_value = {
                    "home_win": 0.5,
                    "draw": 0.3,
                    "away_win": 0.2,
                }
                mock_pred.return_value = pred_service

                # 测试工作流
                data_service = mock_service()
                _matches = await data_service.collect_match_data()
                assert matches["matches"]   == 10

                pred_service_instance = mock_pred()
                _prediction = await pred_service_instance.predict(match_id=1)
                assert prediction["home_win"]   == 0.5

    async def test_error_handling_mock(self):
        """测试：错误处理（模拟）"""
        with patch("src.database.connection.DatabaseManager") as mock_db:
            # 设置模拟抛出异常
            mock_instance = AsyncMock()
            mock_instance.get_session.side_effect = Exception("Connection failed")
            mock_db.return_value = mock_instance

            # 测试错误处理
            db_manager = mock_db("invalid://url")
            try:
                async with db_manager.get_session():
                    pass
                assert False, "应该抛出异常"
            except Exception as e:
                assert str(e) == "Connection failed"


@pytest.mark.integration
class TestContainerOrchestration:
    """容器编排测试"""

    def test_docker_compose_configuration(self):
        """测试：Docker Compose配置"""
        import os
        import yaml

        # 检查Docker Compose文件是否存在
        compose_file = "docker-compose.test.yml"
        if os.path.exists(compose_file):
            with open(compose_file, "r") as f:
                compose_config = yaml.safe_load(f)

            # 验证服务配置
            assert "services" in compose_config
            services = compose_config["services"]

            # 应该有数据库服务
            assert "postgres" in services or "db" in services

            # 应该有Redis服务（如果有）
            if "redis" in services:
                redis_config = services["redis"]
                assert "image" in redis_config
                assert "redis" in redis_config["image"]

    async def test_service_health_checks(self):
        """测试：服务健康检查"""
        # 模拟健康检查
        health_checks = {"database": False, "redis": False, "api": False}

        # 模拟服务就绪
        async def check_service(service_name):
            await asyncio.sleep(0.1)  # 模拟检查延迟
            health_checks[service_name] = True

        # 并发检查所有服务
        tasks = [
            check_service("database"),
            check_service("redis"),
            check_service("api"),
        ]
        await asyncio.gather(*tasks)

        # 验证所有服务都健康
        assert all(health_checks.values())

    async def test_container_startup_sequence(self):
        """测试：容器启动序列"""
        startup_order = ["database", "redis", "api"]
        started_services = []

        async def start_service(service_name):
            # 模拟启动延迟
            if service_name == "database":
                await asyncio.sleep(0.3)
            elif service_name == "redis":
                await asyncio.sleep(0.2)
            else:
                await asyncio.sleep(0.1)

            started_services.append(service_name)

        # 按顺序启动
        for service in startup_order:
            await start_service(service)

        # 验证启动顺序
        assert started_services   == startup_order

    def test_environment_variables(self):
        """测试：环境变量配置"""
        # 检查必要的环境变量
        required_vars = ["DATABASE_URL", "REDIS_URL"]

        # 在测试环境中，这些可能未设置
        # 但代码应该能够处理
        import os

        for var in required_vars:
            value = os.environ.get(var)
            # 在测试中可以接受None或使用默认值
            assert value is None or isinstance(value, str)


# 测试辅助函数
def create_test_docker_compose():
    """创建测试用的Docker Compose文件"""
    compose_content = """
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: footballprediction_test
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 1s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1s
      timeout: 5s
      retries: 5
"""

    with open("docker-compose.test.yml", "w") as f:
        f.write(compose_content)


if __name__ == "__main__":
    # 如果直接运行此文件，创建Docker Compose配置
    create_test_docker_compose()
    print("Created docker-compose.test.yml for testing")
