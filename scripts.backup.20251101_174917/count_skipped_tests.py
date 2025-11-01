#!/usr/bin/env python3
"""
统计 skipped测试数量
"""

import subprocess
import re
import sys
import os


def count_skipped_tests():
    """统计 skipped测试数量"""
    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 运行测试
    cmd = ["pytest", "-v", "--disable-warnings", "--tb=no"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
    output = result.stdout + result.stderr

    # 统计
    skipped = len(re.findall(r"SKIPPED", output))
    total = len(re.findall(r"(PASSED|FAILED|ERROR|SKIPPED)", output))

    print("\n跳过测试统计:")
    print(f"  跳过: {skipped}")
    print(f"  总计: {total}")
    print(f"  跳过率: {skipped/total*100:.1f}%" if total > 0 else "0.0%")

    # 如果设置阈值
    if len(sys.argv) > 1 and sys.argv[1] == "--fail-threshold":
        threshold = int(sys.argv[2])
        if skipped > threshold:
            print(f"\n❌ 跳过测试数 ({skipped}) 超过阈值 ({threshold})")
            sys.exit(1)
        else:
            print(f"\n✅ 跳过测试数 ({skipped}) 在阈值范围内 ({threshold})")

    return skipped


if __name__ == "__main__":
    count_skipped_tests()
