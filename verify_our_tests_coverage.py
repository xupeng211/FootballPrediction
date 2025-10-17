#!/usr/bin/env python3
"""
验证我们创建的综合测试的覆盖率
"""

import subprocess
import json
import os

def run_coverage():
    """运行覆盖率测试"""
    print("=" * 60)
    print("🔍 验证我们创建的综合测试的覆盖率")
    print("=" * 60)

    # 我们创建的测试文件列表
    test_files = [
        "tests/unit/test_validators_comprehensive.py",
        "tests/unit/test_crypto_utils_comprehensive.py",
        "tests/unit/test_file_utils_comprehensive.py",
        "tests/unit/test_string_utils_comprehensive.py",
        "tests/unit/test_time_utils_comprehensive.py"
    ]

    # 运行pytest获取覆盖率
    cmd = [
        "python", "-m", "pytest",
        "--cov=src.utils",
        "--cov-report=json:our_coverage.json",
        "--cov-report=term-missing",
        "--tb=no",
        "-q"
    ] + test_files

    print(f"\n运行命令: {' '.join(cmd)}\n")

    # 运行测试
    result = subprocess.run(cmd, capture_output=True, text=True)

    print("测试输出:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    # 如果生成了JSON报告，分析它
    if os.path.exists("our_coverage.json"):
        print("\n" + "=" * 60)
        print("📊 我们的测试覆盖率详情")
        print("=" * 60)

        with open("our_coverage.json", "r") as f:
            coverage = json.load(f)

        # 获取utils模块的覆盖率
        files = coverage.get("files", {})

        # 我们关注的文件
        target_files = {
            "validators.py": 0,
            "crypto_utils.py": 0,
            "file_utils.py": 0,
            "string_utils.py": 0,
            "time_utils.py": 0
        }

        # 提取每个文件的覆盖率
        for file_path, data in files.items():
            if "/src/utils/" in file_path:
                file_name = file_path.split("/")[-1]
                if file_name in target_files:
                    summary = data.get("summary", {})
                    covered = summary.get("covered_lines", 0)
                    total = summary.get("num_statements", 0)
                    percent = summary.get("percent_covered", 0)
                    target_files[file_name] = percent

                    # 计算缺失的行
                    missing = total - covered
                    status = "✅" if percent == 100 else "⚠️" if percent >= 80 else "❌"

                    print(f"{status} {file_name:20} | {percent:5.1f}% | {covered:3d}/{total:3d} 行覆盖")
                    if missing > 0:
                        print(f"{'':24}   缺失 {missing} 行")

        # 计算平均覆盖率
        avg_coverage = sum(target_files.values()) / len(target_files)
        print(f"\n平均覆盖率: {avg_coverage:.1f}%")

        # 对比之前的覆盖率
        print("\n" + "=" * 60)
        print("📈 覆盖率提升对比")
        print("=" * 60)

        previous = {
            "validators.py": 23,
            "crypto_utils.py": 32,
            "file_utils.py": 31,
            "string_utils.py": 48,
            "time_utils.py": 39
        }

        print(f"{'文件':20} | {'之前':>6} | {'现在':>6} | {'提升':>6}")
        print("-" * 50)

        for file_name in target_files:
            before = previous.get(file_name, 0)
            after = target_files.get(file_name, 0)
            improvement = after - before
            arrow = "↑" if improvement > 0 else "→" if improvement == 0 else "↓"

            print(f"{file_name:20} | {before:6.1f}% | {after:6.1f}% | {arrow}{abs(improvement):5.1f}%")

    else:
        print("\n❌ 未生成覆盖率报告")

if __name__ == "__main__":
    run_coverage()