#!/usr/bin/env python3
"""
自动更新脚本 - 更新依赖和配置
"""

import subprocess
import sys
import os
from pathlib import Path


def auto_update():
    """执行自动更新"""
    print("🔄 开始自动更新...")
    print("=" * 50)

    updates = []

    # 1. 更新依赖锁文件
    try:
        print("📦 更新依赖锁文件...")
        result = subprocess.run(
            ["make", "update-lock"], capture_output=True, text=True, timeout=300
        )
        updates.append(("依赖锁文件", "✅ 已更新" if result.returncode == 0 else "⚠️ 无变化"))
    except Exception as e:
        updates.append(("依赖锁文件", f"❌ 失败: {e}"))

    # 2. 更新文档
    try:
        print("📚 更新文档...")
        result = subprocess.run(["make", "docs-all"], capture_output=True, text=True, timeout=180)
        updates.append(("项目文档", "✅ 已更新" if result.returncode == 0 else "⚠️ 跳过"))
    except Exception as e:
        updates.append(("项目文档", f"❌ 失败: {e}"))

    # 3. 清理临时文件
    try:
        print("🧹 清理临时文件...")
        temp_patterns = [".coverage", "__pycache__", "*.pyc", ".pytest_cache"]
        cleaned = 0

        for pattern in temp_patterns:
            result = subprocess.run(
                ["find", ".", "-name", pattern, "-delete"], capture_output=True, text=True
            )
            if result.returncode == 0:
                cleaned += 1

        updates.append(("临时文件清理", f"✅ 已清理 {cleaned} 类文件"))
    except Exception as e:
        updates.append(("临时文件清理", f"❌ 失败: {e}"))

    # 显示结果
    print("\n📊 更新结果:")
    for name, status in updates:
        print(f"  {name}: {status}")

    return True


if __name__ == "__main__":
    success = auto_update()
    sys.exit(0 if success else 1)
