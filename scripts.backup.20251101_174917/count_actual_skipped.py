#!/usr/bin/env python3
"""
统计实际跳过的测试数量（运行 pytest 查看）
"""

import subprocess
import re
import os


def count_skipped_in_output(output):
    """从 pytest 输出中统计跳过的数量"""
    # 查找 "SKIPPED" 的数量
    skipped_matches = re.findall(r"SKIPPED", output)
    return len(skipped_matches)


def main():
    print("=" * 60)
    print("统计实际跳过的测试数量")
    print("=" * 60)

    # 获取一些有代表性的测试目录
    test_dirs = [
        "tests/unit/api/",
        "tests/unit/cache/",
        "tests/unit/core/",
        "tests/unit/services/",
        "tests/unit/utils/",
        "tests/unit/database/",
        "tests/unit/monitoring/",
        "tests/unit/models/",
        "tests/unit/streaming/",
        "tests/unit/data/",
        "tests/unit/collectors/",
    ]

    total_skipped = 0
    total_run = 0
    total_files = 0

    results = []

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\n检查目录: {test_dir}")

            # 使用 pytest 运行并收集结果
            cmd = ["pytest", test_dir, "-v", "--disable-warnings", "--tb=no", "-x"]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30秒超时
                )

                # 统计各种结果
                skipped = count_skipped_in_output(result.stdout)
                passed = len(re.findall(r"PASSED", result.stdout))
                failed = len(re.findall(r"FAILED", result.stdout))
                errors = len(re.findall(r"ERROR", result.stdout))

                run = passed + failed + errors
                total = skipped + run

                total_skipped += skipped
                total_run += run
                total_files += 1

                skip_rate = (skipped / total * 100) if total > 0 else 0

                results.append(
                    {
                        "dir": test_dir,
                        "total": total,
                        "skipped": skipped,
                        "run": run,
                        "skip_rate": skip_rate,
                    }
                )

                print(f"  总计: {total}, 跳过: {skipped}, 运行: {run}, 跳过率: {skip_rate:.1f}%")

            except subprocess.TimeoutExpired:
                print("  超时，跳过此目录")
            except Exception as e:
                print(f"  错误: {e}")

    # 显示汇总
    print("\n" + "=" * 60)
    print("汇总结果:")
    print(f"  检查目录数: {total_files}")
    print(f"  总测试数: {total_skipped + total_run}")
    print(f"  跳过数: {total_skipped}")
    print(f"  运行数: {total_run}")

    if total_skipped + total_run > 0:
        overall_skip_rate = (total_skipped / (total_skipped + total_run)) * 100
        print(f"  总跳过率: {overall_skip_rate:.2f}%")

    # 估算整个项目的跳过数量
    if total_run > 0:
        # 假设总测试数为 6919
        estimated_total_tests = 6919
        estimated_skipped = int(
            (total_skipped / (total_skipped + total_run)) * estimated_total_tests
        )
        print("\n估算整个项目:")
        print(f"  估算跳过数: {estimated_skipped}")
        print(f"  估算运行数: {estimated_total_tests - estimated_skipped}")

    # 按跳过率排序显示
    print("\n按跳过率排序:")
    results.sort(key=lambda x: x["skip_rate"], reverse=True)
    for result in results[:5]:
        print(
            f"  {result['dir']}: {result['skip_rate']:.1f}% ({result['skipped']}/{result['total']})"
        )

    print("\n" + "=" * 60)
    if total_skipped < 100:
        print("✅ Phase 2 目标可能达成：估算跳过数 < 100")
    else:
        print(f"⚠️  Phase 2 需要继续优化：估算跳过数 {total_skipped} >= 100")
    print("=" * 60)


if __name__ == "__main__":
    main()
