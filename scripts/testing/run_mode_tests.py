#!/usr/bin/env python3
"""
运行不同模式的测试
支持minimal和full两种模式
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: List[str], env: Optional[dict] = None) -> int:
    """运行命令并返回退出码"""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    result = subprocess.run(
        cmd, env=env or os.environ, cwd=project_root, capture_output=False
    )

    print("-" * 50)
    print(f"Exit code: {result.returncode}")
    return result.returncode


def run_minimal_tests():
    """运行minimal模式测试（快速）"""
    print("\n🔥 Running Minimal Mode Tests (Fast)...")

    # 使用.env.test配置
    env = os.environ.copy()
    env["DOTENV"] = ".env.test"

    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/api/test_health.py::TestHealthAPI",
        "-v",
        "--tb=short",
        "-x",
    ]

    return run_command(cmd, env)


def run_full_tests():
    """运行full模式测试（完整）"""
    print("\n✨ Running Full Mode Tests (Complete)...")

    # 使用.env.test.full配置
    env = os.environ.copy()
    env["DOTENV"] = ".env.test.full"

    # 先运行健康检查
    health_cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/api/test_health.py",
        "-v",
        "--tb=short",
    ]

    if run_command(health_cmd, env) != 0:
        print("❌ Health check tests failed")
        return 1

    # 运行预测API测试
    prediction_cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/api/test_predictions.py",
        "-v",
        "--tb=short",
    ]

    if run_command(prediction_cmd, env) != 0:
        print("❌ Prediction API tests failed")
        return 1

    print("✅ All full mode tests passed")
    return 0


def run_unit_tests():
    """运行所有单元测试"""
    print("\n🧪 Running All Unit Tests...")

    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/",
        "-v",
        "--tb=short",
        "--durations=10",
        "-x",
    ]

    return run_command(cmd)


def run_coverage_tests():
    """运行覆盖率测试"""
    print("\n📊 Running Coverage Tests...")

    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=60",  # 本地测试60%即可
        "-v",
    ]

    return run_command(cmd)


def run_integration_tests():
    """运行集成测试"""
    print("\n🔗 Running Integration Tests...")

    cmd = ["python", "-m", "pytest", "tests/integration/", "-v", "--tb=short"]

    return run_command(cmd)


def run_e2e_tests():
    """运行端到端测试"""
    print("\n🎯 Running E2E Tests...")

    cmd = ["python", "-m", "pytest", "tests/e2e/", "-v", "--tb=short"]

    return run_command(cmd)


def main():
    parser = argparse.ArgumentParser(description="Run tests in different modes")
    parser.add_argument(
        "mode",
        choices=["minimal", "full", "unit", "coverage", "integration", "e2e", "all"],
        help="Test mode to run",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running tests even if some fail",
    )

    args = parser.parse_args()

    exit_code = 0

    if args.mode == "minimal":
        exit_code = run_minimal_tests()
    elif args.mode == "full":
        exit_code = run_full_tests()
    elif args.mode == "unit":
        exit_code = run_unit_tests()
    elif args.mode == "coverage":
        exit_code = run_coverage_tests()
    elif args.mode == "integration":
        exit_code = run_integration_tests()
    elif args.mode == "e2e":
        exit_code = run_e2e_tests()
    elif args.mode == "all":
        # 运行所有测试套件
        tests = [
            ("Minimal", run_minimal_tests),
            ("Unit", run_unit_tests),
            ("Integration", run_integration_tests),
            ("E2E", run_e2e_tests),
        ]

        for name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"Running {name} Tests")
            print("=" * 60)

            code = test_func()
            if code != 0 and not args.continue_on_error:
                print(f"❌ {name} tests failed with exit code {code}")
                sys.exit(code)
            exit_code = max(exit_code, code)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
