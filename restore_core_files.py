#!/usr/bin/env python3
"""
恢复核心文件到正确状态
"""

import subprocess
import sys

def restore_core_files():
    """恢复核心文件"""
    files_to_restore = [
        'src/core/config.py',
        'src/core/logger.py', 
        'src/core/di.py',
        'src/core/exceptions.py',
        'src/core/prediction_engine.py'
    ]
    
    print("恢复核心文件...")
    for file_path in files_to_restore:
        try:
            result = subprocess.run(
                ['git', 'checkout', 'HEAD', '--', file_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ 恢复: {file_path}")
            else:
                print(f"  ✗ 失败: {file_path}")
        except Exception as e:
            print(f"  ✗ 错误: {file_path} - {e}")

if __name__ == '__main__':
    restore_core_files()
