#!/usr/bin/env python3
"""
CreateAPITests单元测试
验证API测试生成器的核心功能
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from create_api_tests import create_api_health_test


class TestCreateAPITests:
    """API测试生成器测试"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_create_api_health_test(self):
        """测试API健康检查测试生成"""
        result = create_api_health_test()

        # 函数应该创建测试文件并返回None
        assert result is None

        # 检查测试文件是否被创建
        test_file = (
            project_root / "tests" / "unit" / "api" / "test_api_health_extended.py"
        )
        assert test_file.exists()

        # 检查文件内容
        if test_file.exists():
            content = test_file.read_text(encoding="utf-8")
            assert "class TestAPIHealthExtended" in content
            assert "def test_" in content
            assert "import pytest" in content

    def test_generated_api_test_file_structure(self):
        """测试生成的API测试文件结构"""
        create_api_health_test()

        test_file = (
            project_root / "tests" / "unit" / "api" / "test_api_health_extended.py"
        )
        if test_file.exists():
            content = test_file.read_text(encoding="utf-8")

            # 检查基本结构
            assert '"""API健康检查扩展测试"""' in content
            assert "import pytest" in content
            assert "from fastapi.testclient import TestClient" in content
            assert "class TestAPIHealthExtended:" in content

            # 检查测试方法
            assert "def test_" in content
            assert "@pytest.fixture" in content

    def test_api_test_content_quality(self):
        """测试API测试内容质量"""
        create_api_health_test()

        test_file = (
            project_root / "tests" / "unit" / "api" / "test_api_health_extended.py"
        )
        if test_file.exists():
            content = test_file.read_text(encoding="utf-8")

            # 检查API特有功能
            assert "TestClient" in content
            assert "client.get(" in content
            assert "response.status_code" in content
            assert "response.json()" in content

            # 检查健康检查相关测试
            assert "health" in content.lower()
            assert "database" in content.lower() or "redis" in content.lower()

    def teardown_method(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
