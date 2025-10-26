#!/usr/bin/env python3
"""
修复测试文件脚本
解决常见的测试问题，让测试能够运行
"""

import os
import re
from pathlib import Path


def fix_test_file(file_path: str):
    """修复单个测试文件"""
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 1. 修复导入问题
    # 添加缺失的导入
    if "from fastapi import" in content and "TestClient" in content:
        if "from fastapi.testclient import TestClient" not in content:
            content = content.replace(
                "from fastapi import",
                "from fastapi.testclient import TestClient\nfrom fastapi import",
            )

    # 2. 修复 pytest-asyncio 警告
    if "@pytest.mark.asyncio" in content and "asyncio_mode" not in content:
        # 在文件开头添加配置
        if 'pytest_plugins = "asyncio"' not in content:
            lines = content.split("\n")
            # 找到第一个import前插入
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    lines.insert(i, 'pytest_plugins = "asyncio"')
                    lines.insert(i + 1, "")
                    break
            content = "\n".join(lines)

    # 3. 修复 MagicMock 的导入问题
    if "MagicMock" in content or "AsyncMock" in content:
        if "from unittest.mock import" not in content:
            # 找到现有的导入位置
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import pytest"):
                    lines.insert(
                        i + 1, "from unittest.mock import MagicMock, AsyncMock, patch"
                    )
                    break
            content = "\n".join(lines)

    # 4. 修复数据库连接相关的测试
    if "database" in content.lower() or "db" in content:
        # 添加 mock 数据库连接
        if "@patch" not in content:
            # 为数据库测试添加 patch
            content = re.sub(
                r"(def test_(.*database.*|.*db.*))",
                r'\n    @patch("src.database.connection.DatabaseManager")\n    def test_\2',
                content,
                flags=re.IGNORECASE,
            )

    # 5. 修复异步函数的调用
    content = re.sub(r"(\w+)\.(\w+)\(\s*\)(?!\s*\.)", r"\1.\2()", content)

    # 6. 添加缺失的类型导入
    if "Dict[" in content or "List[" in content:
        if "from typing import" in content:
            # 添加到现有的 typing import
            if "Dict" not in content:
                content = re.sub(
                    r"from typing import ([^\n]+)",
                    lambda m: f"from typing import {m.group(1).rstrip()}, Dict",
                    content,
                )
            if "List" not in content:
                content = re.sub(
                    r"from typing import ([^\n]+)",
                    lambda m: f"from typing import {m.group(1).rstrip()}, List",
                    content,
                )
        else:
            # 添加新的 typing import
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import pytest"):
                    lines.insert(i + 1, "from typing import Dict, List, Any, Optional")
                    break
            content = "\n".join(lines)

    # 如果内容有变化，写回文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def create_test_config():
    """创建测试配置文件"""
    conftest_path = Path("tests/conftest.py")

    if not conftest_path.exists():
        conftent = '''"""
pytest配置文件
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# 设置异步测试模式
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mock fixtures
@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    redis = MagicMock()
    redis.get.return_value = None
    redis.set.return_value = True
    return redis

@pytest.fixture
def mock_db_session():
    """Mock数据库会话"""
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    return session

@pytest.fixture
def mock_cache():
    """Mock缓存"""
    cache = MagicMock()
    cache.get.return_value = None
    cache.set.return_value = True
    return cache

# 测试数据库配置
@pytest.fixture(scope="session")
def test_db_url():
    """测试数据库URL"""
    return "sqlite:///:memory:"

# 禁用外部服务调用
@pytest.fixture(autouse=True)
def disable_external_calls():
    """自动禁用外部服务调用"""
    import sys
    from unittest.mock import patch

    # Mock requests
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {}
        mock_get.return_value.status_code = 200
        yield
'''
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(conftent)
        print(f"✓ 创建 {conftest_path}")


def main():
    """主函数"""
    print("🔧 开始修复测试文件...\n")

    # 1. 创建测试配置
    create_test_config()

    # 2. 修复测试文件
    test_dir = Path("tests/unit")
    fixed_count = 0

    # 需要修复的核心测试文件列表
    core_tests = [
        "test_api_simple.py",
        "test_adapters_base.py",
        "test_adapters_factory.py",
        "test_adapters_registry.py",
        "test_api_dependencies.py",
        "test_api_middleware.py",
        "test_data_validator.py",
        "test_prediction_model.py",
        "test_facade.py",
    ]

    for test_file in core_tests:
        file_path = test_dir / test_file
        if file_path.exists():
            if fix_test_file(str(file_path)):
                print(f"✓ 修复 {test_file}")
                fixed_count += 1
            else:
                print(f"- 无需修复 {test_file}")
        else:
            print(f"⚠ 文件不存在: {test_file}")

    print(f"\n✅ 修复完成！共修复 {fixed_count} 个文件")

    # 3. 运行测试验证
    print("\n运行测试验证...")
    os.system("pytest tests/unit/test_api_simple.py -v --tb=short | head -30")


if __name__ == "__main__":
    main()
