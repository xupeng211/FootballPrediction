#!/usr/bin/env python3
"""
快速生成覆盖率报告
"""

import subprocess
import os
import json


def main():
    print("生成快速覆盖率报告...")

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 只测试核心模块
    test_modules = [
        "tests/unit/core/",
        "tests/unit/api/test_health.py",
        "tests/unit/services/test_audit_service.py",
    ]

    cmd = [
        "pytest",
        "--cov=src",
        "--cov-report=json",
        "--cov-report=term-missing",
        "--disable-warnings",
        "--maxfail=3",
    ] + test_modules

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
    output = result.stdout

    print("\n覆盖率结果:")
    # 提取TOTAL行
    for line in output.split("\n"):
        if "TOTAL" in line or line.startswith("src/"):
            print(line)

    # 如果生成了JSON文件，分析它
    if os.path.exists("coverage.json"):
        with open("coverage.json", "r") as f:
            data = json.load(f)

        print("\n详细统计:")
        print(f"  总覆盖率: {data['totals']['percent_covered']:.1f}%")
        print(f"  覆盖语句: {data['totals']['covered_lines']}/{data['totals']['num_statements']}")

        # 找出0%覆盖率的模块
        zero_modules = []
        for path, info in data["files"].items():
            if path.startswith("src/") and info["summary"]["percent_covered"] == 0:
                module = path.replace("src/", "").replace(".py", "")
                zero_modules.append(module)

        if zero_modules:
            print("\n0%覆盖率模块:")
            for m in zero_modules[:10]:
                print(f"  - {m}")


if __name__ == "__main__":
    main()
