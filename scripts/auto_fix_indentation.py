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

    if fix_indentation():
        sys.exit(0)
    else:
        sys.exit(1)
