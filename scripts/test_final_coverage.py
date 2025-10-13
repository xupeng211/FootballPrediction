#!/usr/bin/env python3
"""
Final coverage test script
"""
import subprocess
import sys
import os

def run_command(cmd, timeout=180):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def main():
    """主函数"""
    print("🚀 Running final coverage test...")

    # 运行一个更快的测试子集
    test_files = [
        "tests/unit/utils/test_config_loader_comprehensive.py",
        "tests/unit/utils/test_low_coverage_boost.py",
        "tests/unit/api/test_comprehensive.py",
        "tests/unit/tasks/test_tasks_basic.py",
        "tests/unit/core/test_di.py",
        "tests/unit/utils/test_dict_utils.py"
    ]

    cmd = f"pytest {' '.join(test_files)} --cov=src --cov-report=term-missing -q"
    print(f"Running: {cmd}")

    ret, out, err = run_command(cmd, timeout=120)

    if ret == 0:
        print("\n✅ Coverage test completed successfully!")
        print(out)

        # 提取覆盖率数字
        lines = out.split('\n')
        for line in lines:
            if "TOTAL" in line and "%" in line:
                print(f"\n📊 Final coverage: {line}")
                break
    else:
        print("\n❌ Coverage test failed")
        print(f"Error: {err}")

        # 尝试提取部分信息
        if "TOTAL" in out:
            lines = out.split('\n')
            for line in lines:
                if "TOTAL" in line and "%" in line:
                    print(f"\n📊 Partial coverage: {line}")
                    break

if __name__ == "__main__":
    main()