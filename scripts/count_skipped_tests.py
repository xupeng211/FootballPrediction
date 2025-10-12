#!/usr/bin/env python3
"""
统计跳过测试的脚本
"""

import subprocess
import re


def count_skipped_tests():
    """统计被跳过的测试数量"""
    print("正在收集测试信息...")

    # 运行pytest收集测试
    result = subprocess.run(
        ["pytest", "--collect-only", "-p", "no:warnings", "-q"],
        capture_output=True,
        text=True,
    )

    # 提取测试数量
    test_count = 0
    for line in result.stdout.split("\n"):
        if "tests collected" in line:
            match = re.search(r"(\d+) tests collected", line)
            if match:
                test_count = int(match.group(1))
                break

    print(f"总测试数: {test_count}")

    # 运行一个小的测试样本来检查跳过情况
    test_modules = [
        "tests/unit/api/test_health.py",
        "tests/unit/cache/test_ttl_cache_enhanced.py",
        "tests/unit/core/test_logger.py",
    ]

    total_skipped = 0
    total_run = 0

    for module in test_modules:
        print(f"\n检查模块: {module}")
        result = subprocess.run(
            ["pytest", module, "-v", "--disable-warnings"],
            capture_output=True,
            text=True,
        )

        # 统计跳过的测试
        skipped = len(re.findall(r"SKIPPED", result.stdout))
        passed = len(re.findall(r"PASSED", result.stdout))
        failed = len(re.findall(r"FAILED", result.stdout))
        errors = len(re.findall(r"ERROR", result.stdout))

        run = passed + failed + errors
        total_skipped += skipped
        total_run += run

        print(f"  跳过: {skipped}, 运行: {run}")

    # 估算整体跳过数量
    if test_count > 0 and total_run > 0:
        estimated_skipped = int(
            (total_skipped / (total_skipped + total_run)) * test_count
        )
        skip_percentage = (estimated_skipped / test_count) * 100
        print("\n估算结果:")
        print(f"  总测试数: {test_count}")
        print(f"  估算跳过数: {estimated_skipped}")
        print(f"  跳过百分比: {skip_percentage:.2f}%")

        return estimated_skipped, skip_percentage

    return 0, 0


if __name__ == "__main__":
    count_skipped_tests()
