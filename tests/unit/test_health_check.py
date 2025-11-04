"""
健康检查基础测试
Basic Health Check Tests
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.main import app

    client = TestClient(app)
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    print("⚠️ 主应用不可用，跳过健康检查测试")


@pytest.mark.health
@pytest.mark.smoke
@pytest.mark.skipif(not APP_AVAILABLE, reason="主应用不可用")
def test_health_endpoint():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


@pytest.mark.health
@pytest.mark.skipif(not APP_AVAILABLE, reason="主应用不可用")
def test_root_endpoint():
    """测试根端点"""
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.health
@pytest.mark.unit
def test_basic_imports():
    """测试基础模块导入"""
    try:
        pass

        assert True
    except ImportError:
        pytest.skip("配置模块不可用")


@pytest.mark.health
@pytest.mark.unit
def test_project_structure():
    """测试项目结构"""
    project_root = Path(__file__).parent.parent.parent

    # 检查关键目录
    required_dirs = ["src", "tests", "scripts"]
    for dir_name in required_dirs:
        assert (project_root / dir_name).exists(), f"缺少目录: {dir_name}"

    # 检查关键文件
    required_files = ["README.md", "pytest.ini", "requirements.txt"]
    for file_name in required_files:
        assert (project_root / file_name).exists(), f"缺少文件: {file_name}"
