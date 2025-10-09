"""
测试基础设施
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Any, Dict, Optional
from pathlib import Path

# 测试配置
TEST_CONFIG = {
    "database_url": "sqlite:///:memory:",
    "redis_url": "redis://localhost:6379/1",
    "api_base_url": "http://localhost:8000",
}


class BaseTestCase:
    """基础测试类"""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        """自动使用的 fixtures"""
        self.mock_config = Mock()
        self.mock_logger = Mock()

    def create_mock_service(self, service_class: type) -> Mock:
        """创建 mock 服务"""
        mock_service = Mock(spec=service_class)
        return mock_service

    def create_mock_model(self, **kwargs) -> Mock:
        """创建 mock 模型"""
        mock_model = Mock()
        for key, value in kwargs.items():
            setattr(mock_model, key, value)
        return mock_model

    def assert_valid_response(self, response: Dict[str, Any]):
        """验证响应格式"""
        assert "status" in response
        assert "data" in response or "error" in response


class ServiceTestCase(BaseTestCase):
    """服务层测试基类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 不需要调用 super().setup_method()，因为 BaseTestCase 没有这个方法
        self.service_patches = []

    def teardown_method(self):
        """每个测试方法后的清理"""
        for patch in self.service_patches:
            patch.stop()

    def patch_service(self, service_path: str, **kwargs) -> Mock:
        """patch 服务"""
        import unittest.mock

        patch = unittest.mock.patch(service_path, **kwargs)
        mock = patch.start()
        self.service_patches.append(patch)
        return mock


class APITestCase(BaseTestCase):
    """API 测试基类"""

    @pytest.fixture
    def client(self):
        """FastAPI 测试客户端"""
        from fastapi.testclient import TestClient

        # 延迟导入避免循环依赖
        from src.api.app import app

        return TestClient(app)

    def assert_valid_api_response(self, response, expected_status: int = 200):
        """验证 API 响应"""
        assert response.status_code == expected_status
        assert response.json() is not None
        return response.json()


class DatabaseTestCase(BaseTestCase):
    """数据库测试基类"""

    @pytest.fixture
    def test_db(self):
        """测试数据库会话"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(TEST_CONFIG["database_url"])
        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        session.close()
        engine.dispose()
