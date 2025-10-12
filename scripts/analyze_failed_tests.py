#!/usr/bin/env python3
"""
分析失败的测试
"""

import subprocess
import re
import os


def main():
    print("分析失败的测试...")

    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    # 运行一个较小的测试集来避免超时
    cmd = [
        "pytest",
        "tests/unit/api/test_health.py",
        "tests/unit/core/test_logger.py",
        "tests/unit/services/test_audit_service.py",
        "-v", "--disable-warnings", "--tb=short"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    output = result.stdout + result.stderr

    # 查找失败和错误
    failed = []
    errors = []

    for line in output.split('\n'):
        if '::' in line:
            if 'FAILED' in line:
                failed.append(line.strip())
            elif 'ERROR' in line:
                errors.append(line.strip())

    print(f"\n失败的测试: {len(failed)}")
    for f in failed:
        print(f"  - {f}")

    print(f"\n错误的测试: {len(errors)}")
    for e in errors:
        print(f"  - {e}")

    # 分析具体错误
    if "fixture 'self' not found" in output:
        print("\n发现 fixture 错误:")
        for line in output.split('\n'):
            if "fixture 'self' not found" in line:
                print(f"  {line.strip()}")


if __name__ == "__main__":
    main()