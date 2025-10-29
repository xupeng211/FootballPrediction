#!/usr/bin/env python3
"""
简化的覆盖率基线工具
建立稳定、可重现的覆盖率统计方案
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime


def run_coverage_baseline():
    """运行覆盖率基线测试"""
    print("🔍 运行覆盖率基线测试...")

    # 定义稳定的基线测试套件
    baseline_tests = [
        "tests/unit/services/test_services_basic.py",
        "tests/unit/adapters/test_registry.py",
    ]

    print(f"📋 运行 {len(baseline_tests)} 个基线测试...")

    # 运行测试并生成覆盖率报告
    cmd = [
        "python",
        "-m",
        "pytest",
        *baseline_tests,
        "--cov=src",
        "--cov-report=json",
        "--cov-report=term",
        "--tb=short",
        "-q",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print("❌ 测试执行失败")
            return None

        # 读取覆盖率报告
        with open("coverage.json", "r") as f:
            coverage_data = json.load(f)

        totals = coverage_data.get("totals", {})
        coverage_percent = totals.get("percent_covered", 0)
        covered_lines = totals.get("covered_lines", 0)
        total_lines = totals.get("num_statements", 0)

        print("\n" + "=" * 50)
        print("📊 覆盖率基线报告")
        print("=" * 50)
        print(f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 总体覆盖率: {coverage_percent:.2f}%")
        print(f"📝 覆盖行数: {covered_lines:,}")
        print(f"📄 总代码行数: {total_lines:,}")
        print(f"🧪 测试文件: {len(baseline_tests)} 个")

        # 显示高覆盖率模块
        files = coverage_data.get("files", {})
        if files:
            print("\n🏆 高覆盖率模块:")
            high_coverage = [
                (file_path, file_data["summary"]["percent_covered"])
                for file_path, file_data in files.items()
                if file_data["summary"]["percent_covered"] > 50
            ]
            high_coverage.sort(key=lambda x: x[1], reverse=True)

            for file_path, percent in high_coverage[:10]:
                short_name = file_path.replace("/home/user/projects/FootballPrediction/src/", "")
                print(f"  📁 {short_name:<40} {percent:6.2f}%")

        print("=" * 50)

        # 保存基线数据
        baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "coverage_percent": coverage_percent,
            "covered_lines": covered_lines,
            "total_lines": total_lines,
            "test_files": baseline_tests,
        }

        baseline_file = Path("reports/coverage_baseline.json")
        baseline_file.parent.mkdir(exist_ok=True)

        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, indent=2, ensure_ascii=False)

        print(f"💾 基线数据已保存: {baseline_file}")
        return baseline_data

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return None


def analyze_coverage_drop():
    """分析覆盖率下降原因"""
    print("\n🔍 分析覆盖率下降原因...")

    # 从Issue #83-C最终报告中提取数据
    issue83c_report = Path("ISSUE_83C_FINAL_COMPLETION_REPORT.md")

    if issue83c_report.exists():
        with open(issue83c_report, "r") as f:
            content = f.read()

        # 查找覆盖率数据
        import re

        old_coverage_match = re.search(r"起始覆盖率: ([\d.]+)%", content)
        final_coverage_match = re.search(r"最终覆盖率: ([\d.]+)%", content)

        if old_coverage_match and final_coverage_match:
            start_coverage = float(old_coverage_match.group(1))
            final_coverage = float(final_coverage_match.group(1))
            print(f"📋 Issue #83-C起始覆盖率: {start_coverage:.2f}%")
            print(f"📋 Issue #83-C最终覆盖率: {final_coverage:.2f}%")
            print(f"📊 Issue #83-C期间变化: {final_coverage - start_coverage:+.2f}%")
        else:
            print("⚠️ 无法找到Issue #83-C的覆盖率数据")
            start_coverage = 17.30  # 从报告中手动提取
            final_coverage = 14.19
            print(f"📋 Issue #83-C起始覆盖率: {start_coverage:.2f}% (从报告提取)")
            print(f"📋 Issue #83-C最终覆盖率: {final_coverage:.2f}% (从报告提取)")
    else:
        print("⚠️ Issue #83-C报告文件不存在")
        start_coverage = 17.30  # 默认值
        final_coverage = 14.19

    # 运行当前覆盖率测试
    current_data = run_coverage_baseline()
    if not current_data:
        return False

    current_coverage = current_data["coverage_percent"]
    drop = old_coverage - current_coverage

    print("📊 覆盖率变化分析:")
    print(f"   Issue #83-C完成时: {old_coverage:.2f}%")
    print(f"   当前覆盖率:      {current_coverage:.2f}%")
    print(f"   变化:           {drop:+.2f}%")

    if drop > 1.0:
        print("⚠️ 覆盖率明显下降")
        print("🔍 可能原因:")
        print("   1. 模块导入修复改变了测试覆盖范围")
        print("   2. 某些模块的测试被跳过或失败")
        print("   3. 基线测试套件与之前测试不同")
        print("   4. 覆盖率统计方法变化")
    elif drop < -1.0:
        print("✅ 覆盖率有所提升")
    else:
        print("➡️ 覆盖率基本稳定")

    return True


def establish_stable_baseline():
    """建立稳定的基线测试套件"""
    print("🚀 建立稳定的覆盖率基线...")

    # 测试稳定性：运行3次取平均值
    results = []
    for i in range(3):
        print(f"\n第 {i+1}/3 次测试...")
        data = run_coverage_baseline()
        if data:
            results.append(data["coverage_percent"])
        else:
            print(f"❌ 第 {i+1} 次测试失败")
            return False

    if len(results) == 0:
        print("❌ 所有测试都失败")
        return False

    # 计算平均值和稳定性
    avg_coverage = sum(results) / len(results)
    max_diff = max(abs(r - avg_coverage) for r in results)

    print("\n📊 稳定性分析:")
    print(f"   平均覆盖率: {avg_coverage:.2f}%")
    print(f"   最大波动:   {max_diff:.2f}%")

    stable_baseline = {
        "timestamp": datetime.now().isoformat(),
        "coverage_percent": avg_coverage,
        "stability_variance": max_diff,
        "test_runs": results,
        "is_stable": max_diff < 0.5,
    }

    # 保存稳定基线
    stable_file = Path("reports/stable_coverage_baseline.json")
    with open(stable_file, "w", encoding="utf-8") as f:
        json.dump(stable_baseline, f, indent=2, ensure_ascii=False)

    print(f"💾 稳定基线已保存: {stable_file}")

    if stable_baseline["is_stable"]:
        print("✅ 覆盖率统计稳定，基线建立成功")
        return True
    else:
        print("⚠️ 覆盖率统计有波动，建议进一步调查")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="覆盖率基线工具")
    parser.add_argument("--analyze", action="store_true", help="分析覆盖率下降")
    parser.add_argument("--stable", action="store_true", help="建立稳定基线")

    args = parser.parse_args()

    if args.analyze:
        return analyze_coverage_drop()
    elif args.stable:
        return establish_stable_baseline()
    else:
        return run_coverage_baseline() is not None


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
