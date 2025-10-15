#!/usr/bin/env python3
"""
修复最终语法错误脚本
Fix Final Syntax Errors Script
"""

import os
import re
from pathlib import Path

def fix_adapters_football():
    """修复src/adapters/football.py的语法错误"""
    print("🔧 修复 src/adapters/football.py...")

    file_path = Path("src/adapters/football.py")
    if not file_path.exists():
        print(f"  ❌ 文件不存在: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 修复第465行附近的语法错误
    # 可能是FootballMatch类型未定义
    if 'from .base import' in content:
        # 确保导入包含所有需要的类型
        content = re.sub(
            r'from \.base import.*',
            'from .base import BaseAdapter, AdapterStatus, FootballMatch',
            content
        )

    # 修复Dict类型注解
    content = re.sub(
        r'-> Dict\[str, List\[FootballMatch\]:',
        '-> Dict[str, List[FootballMatch]]:',
        content
    )

    # 检查并修复其他类型注解
    content = re.sub(
        r'-> Dict\[str, Any\]:',
        '-> Dict[str, Any]:',
        content
    )

    content = re.sub(
        r'-> List\[Dict\[str, Any\]:',
        '-> List[Dict[str, Any]]:',
        content
    )

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ 修复了 src/adapters/football.py")
        return True
    else:
        print("  ℹ️ 没有需要修复的语法错误")
        return False

def fix_cache_redis():
    """修复src/cache/redis/__init__.py的语法错误"""
    print("\n🔧 修复 src/cache/redis/__init__.py...")

    file_path = Path("src/cache/redis/__init__.py")
    if not file_path.exists():
        print(f"  ❌ 文件不存在: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 修复第101行的语法错误
    content = re.sub(
        r'async def amget_cache\(keys: List\[str\]\) -> List\[Optional\[Any\]:',
        'async def amget_cache(keys: List[str]) -> List[Optional[Any]]:',
        content
    )

    # 修复其他可能的语法错误
    content = re.sub(
        r'-> List\[Optional\[Any\]:',
        '-> List[Optional[Any]]:',
        content
    )

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ 修复了 src/cache/redis/__init__.py")
        return True
    else:
        print("  ℹ️ 没有需要修复的语法错误")
        return False

def fix_security_auth():
    """修复src/security/auth.py的语法错误"""
    print("\n🔧 修复 src/security/auth.py...")

    file_path = Path("src/security/auth.py")
    if not file_path.exists():
        print(f"  ❌ 文件不存在: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 修复第270行附近的语法错误
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 查找并修复未闭合的括号
        if 'def ' in line and '->' in line and not line.strip().endswith(':'):
            # 检查是否缺少冒号
            if ')' in line and ':' not in line[line.rfind(')'):]:
                lines[i] = line + ':'
                print(f"    修复第{i+1}行: 添加缺失的冒号")

    content = '\n'.join(lines)

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ 修复了 src/security/auth.py")
        return True
    else:
        print("  ℹ️ 没有需要修复的语法错误")
        return False

def verify_syntax():
    """验证语法修复结果"""
    print("\n🔍 验证语法修复结果...")

    files_to_check = [
        "src/adapters/football.py",
        "src/cache/redis/__init__.py",
        "src/security/auth.py"
    ]

    all_good = True

    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            print(f"  ⚠️ 文件不存在: {file_path}")
            continue

        try:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "py_compile", str(path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"  ✅ {file_path}: 语法正确")
            else:
                print(f"  ❌ {file_path}: 仍有语法错误")
                print(f"    {result.stderr.strip()}")
                all_good = False

        except Exception as e:
            print(f"  ❌ {file_path}: 检查失败 - {e}")
            all_good = False

    return all_good

def main():
    """主函数"""
    print("=" * 60)
    print("           最终语法错误修复工具")
    print("=" * 60)

    # 修复各个文件
    fix_adapters_football()
    fix_cache_redis()
    fix_security_auth()

    # 验证结果
    if verify_syntax():
        print("\n" + "=" * 60)
        print("✅ 所有语法错误已修复！")
        print("\n📊 下一步：")
        print("1. 运行 'make coverage' 获取完整测试覆盖率")
        print("2. 运行 'make test' 运行所有测试")
        print("=" * 60)
    else:
        print("\n⚠️ 仍有语法错误需要手动修复")

if __name__ == "__main__":
    main()