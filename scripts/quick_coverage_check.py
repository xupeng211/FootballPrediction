#!/usr/bin/env python3
"""
快速测试覆盖率检查工具
专门用于快速获取覆盖率数据
"""

import subprocess
import json
import sys
from pathlib import Path


def run_quick_coverage():
    """运行快速覆盖率检查"""
    print("🔍 开始快速测试覆盖率检查...")

    # 运行覆盖率测试，限制在单元测试范围内
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/",
        "--cov=src",
        "--cov-report=json",
        "--cov-report=term-missing",
        "--tb=short",
        "-q",  # 安静模式
    ]

    print("📊 运行测试套件...")
    subprocess.run(cmd, capture_output=True, text=True)

    # 读取覆盖率报告
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        try:
            with open(coverage_file, "r") as f:
                coverage_data = json.load(f)

            totals = coverage_data.get("totals", {})
            coverage_percent = totals.get("percent_covered", 0)
            lines_covered = totals.get("covered_lines", 0)
            total_lines = totals.get("num_statements", 0)

            print("\n📈 测试覆盖率报告")
            print("=" * 50)
            print(f"总体覆盖率: {coverage_percent:.2f}%")
            print(f"覆盖行数: {lines_covered}/{total_lines}")

            # 按模块显示覆盖率
            files = coverage_data.get("files", {})
            if files:
                print("\n📁 模块覆盖率 (Top 10):")
                # 按覆盖率排序
                sorted_files = sorted(
                    [(f["name"], f["summary"]["percent_covered"]) for f in files.values()],
                    key=lambda x: x[1],
                    reverse=True,
                )

                for i, (file_path, percent) in enumerate(sorted_files[:10], 1):
                    # 简化文件名
                    short_name = file_path.replace("/home/user/projects/FootballPrediction/", "")
                    print(f"  {i:2d}. {short_name:<50} {percent:6.2f}%")

            # 覆盖率等级评估
            if coverage_percent >= 90:
                grade = "A+ (优秀)"
            elif coverage_percent >= 80:
                grade = "A (良好)"
            elif coverage_percent >= 70:
                grade = "B (合格)"
            elif coverage_percent >= 60:
                grade = "C (需要改进)"
            else:
                grade = "D (不合格)"

            print(f"\n🎯 覆盖率等级: {grade}")

            # 改进建议
            if coverage_percent < 70:
                print("\n💡 改进建议:")
                print("  1. 重点测试核心业务逻辑")
                print("  2. 增加边界条件测试")
                print("  3. 提高异常处理测试覆盖")
            elif coverage_percent < 80:
                print("\n💡 优化建议:")
                print("  1. 补充缺失的测试用例")
                print("  2. 增加集成测试")
                print("  3. 完善错误处理测试")

            return coverage_percent, len(files)

        except Exception as e:
            print(f"❌ 读取覆盖率报告失败: {e}")
            return 0, 0
    else:
        print("❌ 未找到覆盖率报告文件")
        return 0, 0


def check_test_structure():
    """检查测试结构"""
    print("\n🔍 检查测试结构...")

    test_dirs = [
        "tests/unit/",
        "tests/integration/",
        "tests/e2e/",
        "tests/backup/",
        "tests/helpers/",
    ]

    print("📁 测试目录结构:")
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            # 统计测试文件数量
            test_files = list(Path(test_dir).glob("**/*.py"))
            print(f"  ✅ {test_dir:<20} {len(test_files):3d} 个测试文件")
        else:
            print(f"  ❌ {test_dir:<20} 不存在")


def main():
    """主函数"""
    print("🚀 启动测试覆盖率深度分析")
    print("=" * 60)

    # 检查测试结构
    check_test_structure()

    # 运行覆盖率检查
    coverage_percent, module_count = run_quick_coverage()

    print("\n📊 最终总结:")
    print(f"  • 测试覆盖率: {coverage_percent:.2f}%")
    print(f"  • 测试模块数: {module_count}")

    # 保存报告
    report = {
        "timestamp": "2025-10-21",
        "coverage_percent": coverage_percent,
        "module_count": module_count,
        "grade": (
            "A+"
            if coverage_percent >= 90
            else (
                "A"
                if coverage_percent >= 80
                else "B" if coverage_percent >= 70 else "C" if coverage_percent >= 60 else "D"
            )
        ),
    }

    reports_dir = Path("reports/quality")
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / "coverage_analysis.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 详细报告已保存: {report_file}")


if __name__ == "__main__":
    main()
