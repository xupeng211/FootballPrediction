#!/usr/bin/env python3
"""
自动缩进修复工具 - 简化版本
"""

import subprocess
import sys


def fix_indentation():
    """修复缩进问题"""
    try:
        # 使用ruff格式化修复缩进
        result = subprocess.run([
            'ruff', 'format', 'src/', 'tests/', '--fix'
        ], capture_output=True, text=True)

        return result.returncode == 0
    except Exception:
        return False

if __name__ == '__main__':
    print("🔧 开始缩进修复...")

    if fix_indentation():
        print("✅ 缩进修复完成")
        sys.exit(0)
    else:
        print("❌ 缩进修复失败")
        sys.exit(1)
