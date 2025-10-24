from unittest.mock import Mock, patch
"""
测试监控API的依赖注入功能
Test monitoring API dependency injection
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.database.dependencies import get_db


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.monitoring

class TestMonitoringDependencyInjection:
    """测试监控API的依赖注入"""

    def test_monitoring_with_test_db(self):
        """测试监控API使用测试数据库依赖"""
        # 创建模拟的数据库会话
        mock_db = Mock()
        mock_db.execute.return_value.fetchall.return_value = [
            {"count": 10},
            {"count": 20},
            {"count": 5},
        ]

        # 重写依赖注入
        def override_get_db():
            yield mock_db

        # 应用依赖覆盖
        app.dependency_overrides[get_db] = override_get_db

        # 创建测试客户端
        with TestClient(app) as client:
            # 测试 metrics 端点
            response = client.get("/api/v1/metrics")
            assert response.status_code == 200
            _data = response.json()
            assert "status" in _data

            # 测试 status 端点
            response = client.get("/api/v1/status")
            assert response.status_code == 200
            _data = response.json()
            assert "status" in _data

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_dependency_override_isolation(self):
        """测试依赖覆盖不会影响其他测试"""
        # 确保依赖覆盖已清理
        assert get_db not in app.dependency_overrides

        # 创建另一个模拟会话
        mock_db_2 = Mock()
        mock_db_2.execute.return_value.fetchall.return_value = []

        # 应用新的依赖覆盖
        def override_get_db_2():
            yield mock_db_2

        app.dependency_overrides[get_db] = override_get_db_2

        # 验证覆盖生效
        with TestClient(app) as client:
            response = client.get("/api/v1/metrics")
            assert response.status_code == 200

        # 清理
        app.dependency_overrides.clear()

        # 验证清理成功
        assert get_db not in app.dependency_overrides
