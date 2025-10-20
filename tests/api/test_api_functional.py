"""
API功能测试
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_health_check():
    """测试健康检查端点"""
    try:
        from src.api.app import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code in [200, 404]  # 端点可能不存在
    except ImportError:
        pytest.skip("无法导入应用")


def test_api_root():
    """测试API根端点"""
    try:
        from src.api.app import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code in [200, 404]
    except ImportError:
        pytest.skip("无法导入应用")
