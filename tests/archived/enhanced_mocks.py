"""
Mock TestContainers模块
用于替代真实的TestContainers，避免复杂的依赖
"""

import pytest
from typing import Optional
from unittest.mock import Mock, AsyncMock


class EnhancedMock:
    """增强版Mock类"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value if not callable(value) else Mock())

    def __call__(self, *args, **kwargs):
        return Mock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockPostgresContainer:
    """模拟PostgreSQL容器"""

    def __init__(self, image="postgres:15-alpine", dbname="test", username="test", password="test", port=5432):
        self.image = image
        self.dbname = dbname
        self.username = username
        self.password = password
        self.port = port
        self._container = None

    def start(self):
        """模拟启动容器"""
        print(f"📦 Mock PostgreSQL容器启动: {self.image}")
        return self

    def stop(self):
        """模拟停止容器"""
        print("📦 Mock PostgreSQL容器停止")

    def get_connection_url(self):
        """获取连接URL"""
        return f"postgresql://{self.username}:{self.password}@localhost:{self.port}/{self.dbname}"


class MockRedisContainer:
    """模拟Redis容器"""

    def __init__(self, image="redis:7-alpine", port=6379):
        self.image = image
        self.port = port
        self._container = None

    def start(self):
        """模拟启动容器"""
        print(f"📦 Mock Redis容器启动: {self.image}")
        return self

    def stop(self):
        """模拟停止容器"""
        print("📦 Mock Redis容器停止")

    def get_connection_url(self):
        """获取连接URL"""
        return f"redis://localhost:{self.port}"


# 为了兼容性，提供别名
PostgresContainer = MockPostgresContainer
RedisContainer = MockRedisContainer


class TestPostgresContainer(MockPostgresContainer):
    """测试用PostgreSQL容器"""

    def __init__(self):
        super().__init__(
            image="postgres:15-alpine",
            dbname="football_prediction_test",
            username="test_user",
            password="test_password",
            port=5432,
        )


class TestRedisContainer(MockRedisContainer):
    """测试用Redis容器"""

    def __init__(self):
        super().__init__(image="redis:7-alpine", port=6379)