#!/usr/bin/env python3
"""运行全面的测试套件"""

import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime
import json


def run_command(cmd, description, check=True):
    """运行命令并处理结果"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)

    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print("Errors:")
            print(result.stderr)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def run_test_suite(test_type="all", coverage=True, verbose=False):
    """运行测试套件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*80}")
    print(f"FootballPrediction Test Suite")
    print(f"Started at: {timestamp}")
    print('='*80)

    # 基础命令
    python = sys.executable
    pytest_cmd = [python, "-m", "pytest"]

    # 测试配置
    if verbose:
        pytest_cmd.append("-v")

    results = {
        "timestamp": timestamp,
        "tests": {},
        "summary": {}
    }

    # 1. 单元测试
    if test_type in ["all", "unit"]:
        success = run_command(
            pytest_cmd + [
                "tests/unit/",
                "-m", "unit",
                "--tb=short",
                "--maxfail=10"
            ],
            "Unit Tests",
            check=False
        )
        results["tests"]["unit"] = success

    # 2. 集成测试
    if test_type in ["all", "integration"]:
        success = run_command(
            pytest_cmd + [
                "tests/integration/",
                "-m", "integration",
                "--tb=short",
                "--maxfail=5"
            ],
            "Integration Tests",
            check=False
        )
        results["tests"]["integration"] = success

    # 3. API测试
    if test_type in ["all", "api"]:
        success = run_command(
            pytest_cmd + [
                "tests/unit/api/",
                "-m", "api",
                "--tb=short",
                "--maxfail=10"
            ],
            "API Tests",
            check=False
        )
        results["tests"]["api"] = success

    # 4. 数据库测试
    if test_type in ["all", "database"]:
        success = run_command(
            pytest_cmd + [
                "tests/unit/database/",
                "-m", "database",
                "--tb=short",
                "--maxfail=5"
            ],
            "Database Tests",
            check=False
        )
        results["tests"]["database"] = success

    # 5. 覆盖率测试
    if coverage and test_type in ["all", "coverage"]:
        print(f"\n{'='*60}")
        print("Running Coverage Tests")
        print('='*60)

        # 生成覆盖率报告
        cov_cmd = pytest_cmd + [
            "tests/unit/utils/",
            "--cov=src.utils",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=20",  # 20%最低要求
            "--tb=short"
        ]

        success = run_command(cov_cmd, "Coverage Report", check=False)
        results["tests"]["coverage"] = success

        # 检查覆盖率文件
        coverage_file = Path("htmlcov/index.html")
        if coverage_file.exists():
            print(f"\nCoverage report generated: {coverage_file.absolute()}")

    # 6. 性能测试
    if test_type in ["all", "performance"]:
        success = run_command(
            pytest_cmd + [
                "tests/",
                "-m", "performance",
                "--tb=short",
                "--maxfail=3",
                "-v"
            ],
            "Performance Tests",
            check=False
        )
        results["tests"]["performance"] = success

    # 7. 代码质量检查
    if test_type in ["all", "quality"]:
        print(f"\n{'='*60}")
        print("Code Quality Checks")
        print('='*60)

        # Linting
        lint_success = run_command(
            [python, "-m", "ruff", "check", "src/"],
            "Ruff Linting",
            check=False
        )
        results["summary"]["lint"] = lint_success

        # Type checking (core modules only)
        type_check_success = run_command(
            [python, "-m", "mypy", "src/core", "src/services", "src/api"],
            "MyPy Type Checking",
            check=False
        )
        results["summary"]["type_check"] = type_check_success

    # 生成测试摘要
    total_tests = len(results["tests"])
    passed_tests = sum(1 for v in results["tests"].values() if v)

    results["summary"]["total"] = total_tests
    results["summary"]["passed"] = passed_tests
    results["summary"]["success_rate"] = f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"

    # 保存结果
    results_file = Path("test_results.json")
    with results_file.open("w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*80}")
    print("Test Suite Summary")
    print('='*80)
    print(f"Total test categories: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Success rate: {results['summary']['success_rate']}")

    if results_file.exists():
        print(f"\nDetailed results saved to: {results_file.absolute()}")

    return results["summary"]["success_rate"] == "100.0%"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "api", "database", "coverage", "performance", "quality"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage tests"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # 运行测试
    success = run_test_suite(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=args.verbose
    )

    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()