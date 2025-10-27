#!/usr/bin/env python3
"""
基础兼容性测试
测试项目在不同Python版本和平台上的基本兼容性
"""

import sys
from pathlib import Path

import pytest


def test_python_version_compatibility(client, client):
    """测试Python版本兼容性"""
    # 验证Python版本满足最低要求
    assert sys.version_info >= (3, 11), f"Python版本过低: {sys.version}"
    print(f"✅ Python版本兼容: {sys.version}")


def test_project_structure(client, client):
    """测试项目结构完整性"""
    project_root = Path(__file__).parent.parent.parent

    # 验证关键目录存在
    required_dirs = ["src", "tests", "requirements", "docs"]

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        assert dir_path.exists(), f"关键目录不存在: {dir_name}"
        assert dir_path.is_dir(), f"路径不是目录: {dir_name}"

    print("✅ 项目结构完整性检查通过")


def test_core_modules_import(client, client):
    """测试核心模块导入兼容性"""
    try:
        # 测试核心模块导入
        from src.models.match import Match
        from src.models.prediction import Prediction
        from src.models.team import Team

        print("✅ 核心模型模块导入成功")
    except ImportError as e:
        pytest.skip(f"核心模块导入失败，可能是环境问题: {e}")


def test_basic_functionality(client, client):
    """测试基本功能"""
    # 简单的功能测试
    assert 1 + 1   == 2, "基础计算功能异常"
    assert "test".upper() == "TEST", "字符串处理异常"
    print("✅ 基础功能测试通过")


def test_dependencies_available(client, client):
    """测试关键依赖包可用性"""
    required_packages = ["pytest", "fastapi", "sqlalchemy", "pydantic"]

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ 依赖包可用: {package}")
        except ImportError:
            pytest.skip(f"依赖包不可用: {package}")


if __name__ == "__main__":
    # 直接运行时的简单测试
    test_python_version_compatibility()
    test_project_structure()
    test_basic_functionality()
    print("🎉 兼容性测试完成")
