#!/usr/bin/env python3
"""生成简洁的测试覆盖率报告"""

import json


def load_coverage_data():
    """加载覆盖率数据"""
    try:
        with open("htmlcov_local/status.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ 找不到覆盖率报告文件")
        return None


def calculate_summary(coverage_data):
    """计算总体覆盖率摘要"""
    if not coverage_data or "files" not in coverage_data:
        return None

    files = coverage_data["files"]
    total_statements = 0
    total_missing = 0
    total_excluded = 0

    file_details = []

    for file_path, file_data in files.items():
        nums = file_data["index"]["nums"]
        statements = nums["n_statements"]
        missing = nums["n_missing"]
        excluded = nums["n_excluded"]
        covered = statements - missing
        coverage_pct = (covered / statements * 100) if statements > 0 else 0

        total_statements += statements
        total_missing += missing
        total_excluded += excluded

        # 只显示覆盖率大于0%的文件
        if coverage_pct > 0:
            file_details.append(
                {
                    "file": file_data["index"]["file"],
                    "statements": statements,
                    "covered": covered,
                    "coverage": coverage_pct,
                }
            )

    # 按覆盖率排序
    file_details.sort(key=lambda x: x["coverage"], reverse=True)

    total_covered = total_statements - total_missing
    overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0

    return {
        "total_statements": total_statements,
        "total_covered": total_covered,
        "total_missing": total_missing,
        "total_excluded": total_excluded,
        "overall_coverage": overall_coverage,
        "files": file_details[:20],  # 只显示前20个文件
    }


def print_report(summary):
    """打印覆盖率报告"""
    if not summary:
        return

    print("\n" + "=" * 60)
    print("📊 测试覆盖率报告")
    print("=" * 60)

    # 总体覆盖率
    print(f"\n📈 总体覆盖率: {summary['overall_coverage']:.1f}%")
    print(f"   总代码行数: {summary['total_statements']}")
    print(f"   已覆盖行数: {summary['total_covered']}")
    print(f"   未覆盖行数: {summary['total_missing']}")
    print(f"   排除行数: {summary['total_excluded']}")

    # 覆盖率等级
    coverage = summary["overall_coverage"]
    if coverage >= 80:
        grade = "✅ 优秀"
    elif coverage >= 60:
        grade = "⚠️ 良好"
    elif coverage >= 40:
        grade = "❌ 一般"
    else:
        grade = "🚨 需要改进"

    print(f"   覆盖率等级: {grade}")

    # 各文件覆盖率详情
    if summary["files"]:
        print("\n📋 各模块覆盖率详情 (前20个):")
        print("-" * 60)
        print(f"{'模块':<35} {'覆盖率':<10} {'覆盖/总行数':<15}")
        print("-" * 60)

        for file_detail in summary["files"]:
            file_name = file_detail["file"].replace("src/", "")
            coverage_str = f"{file_detail['coverage']:.1f}%"
            lines_str = f"{file_detail['covered']}/{file_detail['statements']}"
            print(f"{file_name:<35} {coverage_str:<10} {lines_str:<15}")

    # Phase 覆盖率分析
    print("\n🎯 Phase 覆盖率分析:")

    # 检查 Phase 1 核心模块
    phase1_modules = [
        "src/api/health.py",
        "src/api/data.py",
        "src/api/features.py",
        "src/api/predictions.py",
    ]

    phase1_coverage = []
    for module in phase1_modules:
        for file_detail in summary["files"]:
            if file_detail["file"] == module:
                phase1_coverage.append(file_detail["coverage"])

    if phase1_coverage:
        avg_phase1 = sum(phase1_coverage) / len(phase1_coverage)
        print(f"   Phase 1 (API核心模块): {avg_phase1:.1f}%")
        print(f"   - 目标: 30% | 当前: {'✅' if avg_phase1 >= 30 else '❌'}")

    # 检查数据库相关模块
    db_modules = [f for f in summary["files"] if "database" in f["file"]]
    if db_modules:
        avg_db = sum(f["coverage"] for f in db_modules) / len(db_modules)
        print(f"   数据库模块: {avg_db:.1f}%")

    # 检查工具模块
    utils_modules = [f for f in summary["files"] if "utils" in f["file"]]
    if utils_modules:
        avg_utils = sum(f["coverage"] for f in utils_modules) / len(utils_modules)
        print(f"   工具模块: {avg_utils:.1f}%")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    coverage_data = load_coverage_data()
    summary = calculate_summary(coverage_data)
    print_report(summary)


if __name__ == "__main__":
    main()
