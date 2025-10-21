#!/usr/bin/env python3
"""
验证 Phase 2 目标：pytest 输出中 skipped 测试 < 100
"""

import subprocess
import re
import sys
import time


def count_skipped_tests_fast():
    """快速统计跳过的测试数量"""
    print("正在统计整个项目的跳过测试数量...")
    print("=" * 60)

    # 使用 pytest 的 --collect-only 来获取所有测试
    print("Step 1: 收集所有测试...")

    # 先运行收集模式获取总数
    collect_result = subprocess.run(
        ["pytest", "--collect-only", "-p", "no:warnings", "-q"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    total_tests = 0
    for line in collect_result.stdout.split("\n"):
        if "tests collected" in line:
            match = re.search(r"(\d+) tests collected", line)
            if match:
                total_tests = int(match.group(1))
                break

    print(f"总测试数: {total_tests}")

    # 运行测试但设置早期退出，只统计跳过的
    print("\nStep 2: 统计跳过的测试...")

    # 运行测试，使用 --maxfail 来快速停止
    cmd = [
        "pytest",
        "--tb=no",
        "-q",
        "--disable-warnings",
        "--maxfail=10",  # 遇到10个失败就停止
        "-rs",  # 显示跳过原因
        "tests/",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,  # 3分钟超时
    )

    # 统计结果
    output = result.stdout + result.stderr

    skipped_count = len(re.findall(r"SKIPPED", output))
    passed_count = len(re.findall(r"PASSED", output))
    failed_count = len(re.findall(r"FAILED", output))
    error_count = len(re.findall(r"ERROR", output))

    run_count = passed_count + failed_count + error_count

    print("\n统计结果:")
    print(f"  跳过 (SKIPPED): {skipped_count}")
    print(f"  通过 (PASSED): {passed_count}")
    print(f"  失败 (FAILED): {failed_count}")
    print(f"  错误 (ERROR): {error_count}")
    print(f"  运行总计: {run_count}")

    # 如果没有运行完所有测试，估算总数
    if run_count + skipped_count < total_tests:
        estimated_skipped = (
            int((skipped_count / (run_count + skipped_count)) * total_tests)
            if run_count + skipped_count > 0
            else 0
        )
        print("\n估算结果（基于样本）:")
        print(f"  估算跳过数: {estimated_skipped}")
        print(f"  估算运行数: {total_tests - estimated_skipped}")
        final_skipped = estimated_skipped
    else:
        final_skipped = skipped_count
        print("\n实际结果:")
        print(f"  实际跳过数: {final_skipped}")
        print(f"  实际运行数: {run_count}")

    # 显示跳过原因
    print("\n跳过原因分析:")
    skip_reasons = re.findall(r"SKIPPED.*?(\[.*\])", output)
    reason_counts = {}
    for reason in skip_reasons:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    # 显示前5个最常见的跳过原因
    sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    for reason, count in sorted_reasons[:5]:
        print(f"  {count}: {reason}")

    # 验证目标
    print("\n" + "=" * 60)
    print("Phase 2 目标验证:")
    print("  目标: skipped 测试 < 100")
    print(f"  实际: {final_skipped}")

    if final_skipped < 100:
        print("\n✅ Phase 2 目标达成！")
        print(f"   跳过测试数量 ({final_skipped}) < 100")
        return True
    else:
        print("\n❌ Phase 2 目标未达成")
        print(f"   跳过测试数量 ({final_skipped}) >= 100")

        # 分析哪些模块跳过最多
        print("\n建议重点优化的模块:")
        module_skips = {}
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "SKIPPED" in line:
                # 提取测试文件路径
                if i > 0:
                    prev_line = lines[i - 1]
                    if "tests/" in prev_line:
                        module = (
                            prev_line.split("tests/")[1].split("::")[0].split(".py")[0]
                        )
                        module_skips[module] = module_skips.get(module, 0) + 1

        sorted_modules = sorted(module_skips.items(), key=lambda x: x[1], reverse=True)
        for module, count in sorted_modules[:5]:
            print(f"  - {module}: {count} 个跳过")

        return False


def main():
    print("Phase 2 目标验证工具")
    print("目标：pytest 输出中 skipped 测试 < 100")
    print("=" * 60)

    success = count_skipped_tests_fast()

    if success:
        print("\n🎉 Phase 2 可以标记为完成！")
        sys.exit(0)
    else:
        print("\n⚠️  Phase 2 需要进一步优化")
        sys.exit(1)


if __name__ == "__main__":
    main()
