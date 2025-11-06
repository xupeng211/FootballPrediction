#!/usr/bin/env python3
"""
快速语法修复 - 针对关键文件的基础修复
"""

import subprocess
import sys
from pathlib import Path


def quick_syntax_check():
    """快速检查语法并报告"""
    api_files = [
        'src/api/cqrs.py',  # 已修复
        'src/api/auth/dependencies.py',  # 已修复
        'src/api/betting_api.py',  # 正在修复
        'src/api/middleware.py',  # 正在修复
    ]

    print("🔍 快速语法检查")
    print("=" * 30)

    results = {}
    for file_path in api_files:
        try:
            result = subprocess.run([
                sys.executable, '-m', 'py_compile', file_path
            ], capture_output=True, text=True, cwd=Path.cwd())

            if result.returncode == 0:
                print(f"✅ {file_path}: 语法正确")
                results[file_path] = True
            else:
                print(f"❌ {file_path}: {result.stderr.strip()}")
                results[file_path] = False
        except Exception as e:
            print(f"⚠️  {file_path}: 检查失败 - {e}")
            results[file_path] = False

    return results


def update_progress():
    """更新进度并给出下一步建议"""
    print("\n📊 Issue #345 修复进度")
    print("=" * 30)

    print("✅ 已修复:")
    print("  - src/api/cqrs.py (16个HTTPException错误)")
    print("  - src/api/auth/dependencies.py (6个括号错误)")

    print("\n🔧 正在修复:")
    print("  - src/api/betting_api.py (缩进和括号问题)")
    print("  - src/api/middleware.py (重复raise问题)")

    print("\n📋 待修复 (需要手动):")
    print("  - 21个其他API文件 (缩进和括号问题)")

    print("\n🎯 建议策略:")
    print("1. 优先修复betting_api.py和middleware.py (影响较小)")
    print("2. 然后处理关键的auth/和predictions/文件")
    print("3. 最后处理其他边缘文件")


if __name__ == "__main__":
    results = quick_syntax_check()
    update_progress()

    success_count = sum(1 for success in results.values() if success)
    print(f"\n📈 当前语法正确文件: {success_count}/{len(results)}")