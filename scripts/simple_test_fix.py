#!/usr/bin/env python3
"""
简单测试修复脚本
Simple Test Fix Script
"""

import os
from pathlib import Path


def run_fix():
    """运行简单修复"""
    print("🔧 执行简单测试修复")
    print("=" * 50)

    # 1. 先修复一个具体的文件作为示例
    test_file = "tests/unit/core/test_adapters_base.py"

    if Path(test_file).exists():
        print(f"\n修复文件: {test_file}")

        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 备份原文件
        with open(test_file + ".bak", "w", encoding="utf-8") as f:
            f.write(content)

        # 简单的修复：添加必要的导入
        if "from unittest.mock import Mock" not in content:
            content = (
                """from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

"""
                + content
            )

        # 修复self参数问题
        content = content.replace(
            "def test_adapter_initialization(self):",
            "def test_adapter_initialization():",
        )
        content = content.replace(
            "def test_adapter_request(self):", "def test_adapter_request():"
        )
        content = content.replace(
            "def test_adapter_health_check(self):", "def test_adapter_health_check():"
        )

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        print("  ✅ 已修复")

    # 2. 创建简单的conftest.py
    conftest_path = Path("tests/conftest.py")
    if not conftest_path.exists():
        conftest_content = '''"""
pytest配置文件
"""

import sys
from pathlib import Path
from unittest.mock import Mock

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "src")

# Mock外部依赖
sys.modules['requests'] = Mock()
sys.modules['httpx'] = Mock()
sys.modules['psycopg2'] = Mock()
sys.modules['redis'] = Mock()
sys.modules['kafka'] = Mock()
'''

        with open(conftest_path, "w") as f:
            f.write(conftest_content)

        print("\n✅ 创建了 tests/conftest.py")

    # 3. 给出测试命令
    print("\n" + "=" * 50)
    print("✅ 修复完成！")
    print("\n🚀 验证修复效果:")
    print(f"  pytest {test_file} -v")

    print("\n📋 批量修复建议:")
    print("1. 先查看具体的失败信息")
    print("2. 针对每个错误类型进行修复")
    print("3. 常见修复模式:")
    print("   - ModuleNotFoundError: 添加sys.path和import")
    print("   - AttributeError: 使用Mock()创建属性")
    print("   - fixture 'self' not found: 移除self参数")
    print("   - AssertionError: 检查断言逻辑")


if __name__ == "__main__":
    run_fix()
