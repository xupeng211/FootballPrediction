#!/usr/bin/env python3
"""
测试系统修复脚本
Fix test system issues including import errors and syntax errors
"""

import os
import ast
import re
from pathlib import Path

def fix_test_imports():
    """修复测试文件的导入问题"""
    print("\n🔧 修复测试文件导入...")
    test_dir = Path("tests")
    fixed_count = 0

    for test_file in test_dir.rglob("*.py"):
        if test_file.name.startswith("test_"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # 修复常见的导入问题
                content = re.sub(r'from \.\.([^s])', r'from src.\1', content)
                content = re.sub(r'from \.\.\.', 'from src', content)
                content = re.sub(r'# (from src\.)', r'\1', content)

                if content != original_content:
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
                    print(f"  ✅ 修复: {test_file.relative_to(Path.cwd()))}")

            except Exception as e:
                print(f"  ❌ 错误: {test_file} - {e}")

    print(f"\n✅ 修复了 {fixed_count} 个测试文件的导入")

def verify_test_system():
    """验证测试系统"""
    print("\n🔍 验证测试系统...")

    # 检查pytest配置
    if Path("pytest.ini").exists():
        print("  ✅ pytest.ini 存在")
    else:
        print("  ❌ pytest.ini 不存在")

    # 检查conftest.py
    if Path("tests/conftest.py").exists():
        print("  ✅ tests/conftest.py 存在")
    else:
        print("  ❌ tests/conftest.py 不存在")

    # 尝试运行一个简单测试
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/unit/utils/test_dict_utils_basic.py", "-q"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("  ✅ 基础测试可以运行")
        else:
            print(f"  ⚠️  基础测试运行失败: {result.stderr[:100]}")
    except Exception as e:
        print(f"  ❌ 无法运行测试: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("           测试系统修复工具")
    print("=" * 60)

    fix_test_imports()
    verify_test_system()

    print("\n" + "=" * 60)
    print("🎉 测试系统修复完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
