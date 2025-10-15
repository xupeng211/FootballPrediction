#!/usr/bin/env python3
"""
修复导入错误脚本
Fix Import Errors Script
"""

import re
from pathlib import Path


def fix_adapters_football_import():
    """修复src/adapters/football.py的导入错误"""
    print("🔧 修复 src/adapters/football.py 导入...")

    file_path = Path("src/adapters/football.py")
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original = content

    # FootballMatch已经在同一个文件中定义了，不需要从base导入
    content = re.sub(
        r"from \.base import BaseAdapter, AdapterStatus, FootballMatch",
        "from .base import BaseAdapter, AdapterStatus",
        content,
    )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✅ 修复了导入")
        return True
    else:
        print("  ℹ️ 没有需要修复的导入")
        return False


def fix_security_auth_imports():
    """修复src/security/auth.py的导入错误"""
    print("\n🔧 修复 src/security/auth.py 导入...")

    file_path = Path("src/security/auth.py")
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original = content

    # 添加缺失的导入
    if "from typing import" in content:
        # 检查是否已导入Callable
        if "Callable" not in content:
            content = re.sub(
                r"from typing import (.*)", r"from typing import \1, Callable", content
            )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✅ 修复了导入")
        return True
    else:
        print("  ℹ️ 没有需要修复的导入")
        return False


def fix_core_config_imports():
    """修复src/core/config.py的导入错误"""
    print("\n🔧 修复 src/core/config.py 导入...")

    file_path = Path("src/core/config.py")
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original = content

    # 添加缺失的导入
    if "from typing import" in content:
        # 检查是否已导入ClassVar
        if "ClassVar" not in content:
            content = re.sub(
                r"from typing import (.*)", r"from typing import \1, ClassVar", content
            )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✅ 修复了导入")
        return True
    else:
        print("  ℹ️ 没有需要修复的导入")
        return False


def fix_all_imports():
    """修复所有导入错误"""
    print("🔧 修复所有导入错误...")

    files_fixed = 0

    # 修复各个文件
    if fix_adapters_football_import():
        files_fixed += 1
    if fix_security_auth_imports():
        files_fixed += 1
    if fix_core_config_imports():
        files_fixed += 1

    return files_fixed > 0


def verify_fixes():
    """验证修复结果"""
    print("\n🔍 验证修复结果...")

    # 运行一个简单的语法检查
    import subprocess

    files_to_check = [
        "src/adapters/football.py",
        "src/security/auth.py",
        "src/core/config.py",
    ]

    all_good = True

    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print(f"  ✅ {file_path}: 语法正确")
            else:
                print(f"  ❌ {file_path}: 仍有错误")
                print(f"    {result.stderr.strip()}")
                all_good = False

        except Exception as e:
            print(f"  ❌ {file_path}: 检查失败 - {e}")
            all_good = False

    return all_good


def main():
    """主函数"""
    print("=" * 60)
    print("           导入错误修复工具")
    print("=" * 60)

    # 修复导入
    if fix_all_imports():
        print("\n✅ 已修复导入错误")
    else:
        print("\nℹ️ 没有需要修复的导入错误")

    # 验证结果
    if verify_fixes():
        print("\n" + "=" * 60)
        print("✅ 所有导入错误已修复！")
        print("\n📊 下一步：")
        print("1. 运行 'make coverage' 获取完整测试覆盖率")
        print("2. 运行 'make test' 运行所有测试")
        print("=" * 60)
    else:
        print("\n⚠️ 仍有错误需要手动修复")


if __name__ == "__main__":
    main()
