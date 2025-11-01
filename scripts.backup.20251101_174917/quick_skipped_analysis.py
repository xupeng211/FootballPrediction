#!/usr/bin/env python3
"""
快速分析 skipped 测试
"""

import subprocess
import re
import sys
import os


def quick_analysis():
    """快速分析 skipped 测试"""
    print("\n🔍 快速分析 skipped 测试...")
    print("=" * 60)

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 使用 --collect-only 快速收集
    cmd = ["pytest", "--collect-only", "-q", "tests"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    output = result.stdout + result.stderr

    # 简单统计
    total_tests = len(re.findall(r"test_", output))
    print(f"\n收集到测试总数: {total_tests}")

    # 现在运行实际的测试来获取 skipped 信息
    print("\n运行测试获取 skipped 信息...")
    cmd = [
        "pytest",
        "-v",
        "--disable-warnings",
        "--tb=no",
        "--maxfail=5",
        "-x",  # 第一个失败就停止
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    output = result.stdout + result.stderr

    # 统计各种结果
    passed = len(re.findall(r"PASSED", output))
    failed = len(re.findall(r"FAILED", output))
    errors = len(re.findall(r"ERROR", output))
    skipped = len(re.findall(r"SKIPPED", output))

    print("\n测试结果统计:")
    print(f"  ✓ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  💥 错误: {errors}")
    print(f"  ⏭️  跳过: {skipped}")

    # 收集 skipped 测试的详细信息
    skipped_tests = []
    lines = output.split("\n")

    for i, line in enumerate(lines):
        if "SKIPPED" in line and "::" in line:
            test_name = line.split("::")[1].split()[0] if "::" in line else line.strip()
            skip_reason = "未知原因"

            # 查找跳过原因
            for j in range(max(0, i - 5), min(len(lines), i + 5)):
                if any(
                    keyword in lines[j].lower()
                    for keyword in ["skip", "reason", "[skipped]", "condition"]
                ):
                    skip_reason = lines[j].strip()
                    break

            skipped_tests.append({"name": test_name, "reason": skip_reason})

    print(f"\n📋 Skipped 测试详情 ({len(skipped_tests)} 个):")

    # 分类
    placeholder = []
    dependency = []
    config = []
    other = []

    for test in skipped_tests:
        reason = test["reason"].lower()
        if any(k in reason for k in ["placeholder", "占位", "not implemented"]):
            placeholder.append(test)
        elif any(k in reason for k in ["not available", "不可用", "missing", "依赖"]):
            dependency.append(test)
        elif any(k in reason for k in ["config", "配置", "env", "环境"]):
            config.append(test)
        else:
            other.append(test)

    print(f"\n  📌 占位测试: {len(placeholder)} 个")
    for t in placeholder[:3]:
        print(f"    - {t['name']}: {t['reason'][:80]}...")

    print(f"\n  ⚠️  依赖缺失: {len(dependency)} 个")
    for t in dependency[:3]:
        print(f"    - {t['name']}: {t['reason'][:80]}...")

    print(f"\n  🔧 配置相关: {len(config)} 个")
    for t in config[:3]:
        print(f"    - {t['name']}: {t['reason'][:80]}...")

    print(f"\n  ❓ 其他原因: {len(other)} 个")
    for t in other[:3]:
        print(f"    - {t['name']}: {t['reason'][:80]}...")

    # 生成简单的修复建议
    print("\n🔧 修复建议:")
    if dependency:
        print(f"  1. 依赖缺失的测试 ({len(dependency)} 个) - 可以通过添加 mock 修复")
    if config:
        print(f"  2. 配置相关的测试 ({len(config)} 个) - 可以通过设置环境变量修复")

    return {
        "total": skipped,
        "categories": {
            "placeholder": len(placeholder),
            "dependency": len(dependency),
            "config": len(config),
            "other": len(other),
        },
    }


if __name__ == "__main__":
    quick_analysis()
