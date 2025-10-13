#!/usr/bin/env python3
"""
冲刺30%覆盖率脚本
运行所有可能的测试以达到目标
"""

import subprocess
import sys
import os
from pathlib import Path

# 所有可能的测试文件
test_patterns = [
    # 运行所有utils测试
    "tests/unit/utils/test_*.py",
    # 运行config测试
    "tests/unit/config/test_*.py",
    # 运行comprehensive测试
    "tests/unit/test_comprehensive_parametrized.py",
    # 运行集成测试（部分）
    "tests/integration/test_*.py",
]

# 排除的文件/目录
excludes = [
    "--ignore=tests/unit/cache",
    "--ignore=tests/unit/core",
    "--ignore=tests/unit/database",
    "--ignore=tests/unit/services",
    "--ignore=tests/unit/api",
    "--ignore=tests/unit/data",
]


def main():
    print("=" * 60)
    print("🏃 冲刺30%覆盖率目标")
    print("=" * 60)

    # 构建命令
    cmd = [
        "pytest",
        "-v",
        "--tb=no",
        "--disable-warnings",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_final",
        "-x",  # 首次失败时停止
    ]

    # 添加测试模式
    cmd.append("-m")
    cmd.append("unit or integration")

    # 添加测试文件
    for pattern in test_patterns:
        cmd.extend(["--glob", pattern])

    # 添加排除项
    cmd.extend(excludes)

    print(f"运行命令: {' '.join(cmd)}\n")

    # 运行测试
    _result = subprocess.run(cmd, capture_output=True, text=True)

    # 分析结果
    output = result.stdout + result.stderr
    lines = output.split("\n")

    # 查找覆盖率
    coverage_found = False
    for line in lines:
        if "TOTAL" in line and "%" in line:
            coverage = line.strip()
            print(f"\n最终覆盖率: {coverage}")

            # 提取覆盖率数字
            parts = coverage.split()
            for part in parts:
                if part.endswith("%"):
                    cov_num = float(part.rstrip("%"))
                    coverage_found = True

                    if cov_num >= 30:
                        print("\n🎉 恭喜！成功达到30%覆盖率目标！")
                        print(f"✅ 最终覆盖率: {cov_num}%")
                    elif cov_num >= 25:
                        print(f"\n📈 非常接近了！覆盖率: {cov_num}%")
                        print("再添加一些简单的测试就能达到目标")
                    elif cov_num >= 20:
                        print(f"\n📊 进展不错！覆盖率: {cov_num}%")
                        print("继续添加更多测试")
                    else:
                        print(f"\n💪 还有提升空间！覆盖率: {cov_num}%")
                        print("需要大幅增加测试覆盖")

                    # 显示报告位置
                    print("\n📊 详细报告: htmlcov_final/index.html")
                    break

    if not coverage_found:
        print("\n⚠️  未能获取覆盖率信息")

    # 显示通过/失败统计
    for line in lines:
        if "passed" in line.lower() and (
            "failed" in line.lower() or "error" in line.lower()
        ):
            print(f"\n测试统计: {line.strip()}")
            break

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
