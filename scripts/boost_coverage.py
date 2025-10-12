#!/usr/bin/env python3
"""
快速提升覆盖率脚本
通过运行现有测试快速提升覆盖率到30%
"""

import subprocess
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_test_suite(test_paths, description, timeout=60):
    """运行测试套件"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")

    cmd = [
        "python",
        "-m",
        "pytest",
        *test_paths,
        "--cov=src",
        "--cov-report=term-missing",
        "--tb=no",
        "-q",
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=project_root
        )

        elapsed = time.time() - start_time
        print(f"⏱️  耗时: {elapsed:.2f}秒")

        # 解析输出
        output = result.stdout + result.stderr

        # 查找测试统计
        for line in output.split("\n"):
            if "passed" in line and (
                "failed" in line or "error" in line or "skipped" in line
            ):
                print(f"📊 {line.strip()}")

        # 查找覆盖率
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                coverage = line.strip()
                print(f"🎯 覆盖率: {coverage}")
                return coverage

        return None

    except subprocess.TimeoutExpired:
        print("⏰ 超时！")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("📈 快速提升覆盖率到30%")
    print("=" * 60)

    coverage_history = []

    # 第一阶段：运行适配器测试（覆盖率最高）
    coverage = run_test_suite(
        ["tests/unit/adapters/"], "第一阶段：适配器模块测试（已知高覆盖率）"
    )
    if coverage:
        coverage_history.append(("适配器", coverage))

    # 第二阶段：运行API测试
    coverage = run_test_suite(
        ["tests/unit/api/test_health_check.py", "tests/unit/api/test_dependencies.py"],
        "第二阶段：API核心测试",
    )
    if coverage:
        coverage_history.append(("API核心", coverage))

    # 第三阶段：运行通过的测试
    passing_tests = [
        "tests/unit/database/test_connection.py",
        "tests/unit/domain/models/test_match.py",
        "tests/unit/domain/models/test_prediction.py",
        "tests/unit/domain/services/test_scoring_service.py",
        "tests/unit/services/test_data_processing.py",
        "tests/unit/tasks/test_error_logger.py",
        "tests/unit/cache/test_mock_redis_optimized.py",
        "tests/unit/data/quality/test_data_quality_monitor_simple.py",
    ]

    coverage = run_test_suite(passing_tests, "第三阶段：已通过的单元测试")
    if coverage:
        coverage_history.append(("单元测试", coverage))

    # 第四阶段：运行模型和核心测试
    model_tests = [
        "tests/unit/database/models/",
        "tests/unit/core/",
        "tests/unit/utils/",
    ]

    coverage = run_test_suite(model_tests, "第四阶段：模型和工具测试")
    if coverage:
        coverage_history.append(("模型工具", coverage))

    # 第五阶段：运行所有通过测试
    coverage = run_test_suite(
        ["tests/unit/"], "第五阶段：全部测试（排除已知失败的）", timeout=120
    )
    if coverage:
        coverage_history.append(("全部", coverage))

    # 总结
    print("\n" + "=" * 60)
    print("📊 覆盖率提升总结")
    print("=" * 60)

    for stage, cov in coverage_history:
        print(f"{stage:10} - {cov}")

    # 检查是否达到目标
    if coverage_history:
        last_coverage = coverage_history[-1][1]
        try:
            percent = float(last_coverage.split("%")[0].split()[-1])
            if percent >= 30:
                print(f"\n✅ 恭喜！已达到30%覆盖率目标！当前：{percent:.1f}%")
            else:
                print(
                    f"\n⚠️  当前覆盖率：{percent:.1f}%，目标30%，还需提升：{30-percent:.1f}%"
                )
                print("\n💡 建议：")
                print("1. 修复失败的测试")
                print("2. 为0%覆盖率模块创建测试")
                print("3. 运行集成测试提升覆盖率")
        except Exception:
            print(f"\n❓ 无法解析覆盖率：{last_coverage}")


if __name__ == "__main__":
    main()
