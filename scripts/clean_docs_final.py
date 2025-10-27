#!/usr/bin/env python3
"""
Docs目录最后一轮清理
清理根目录下的报告文件
"""

import os
import shutil
from pathlib import Path


def clean_docs_final():
    """最后一轮清理docs目录"""
    docs_path = Path("docs")

    print("🎯 开始最后一轮清理...")

    # 1. 清理根目录下的报告和总结文件
    print("\n1️⃣ 清理根目录报告文件...")
    report_files = [
        "CLEANUP_COMPLETED_REPORT.md",
        "COVERAGE_IMPROVEMENT_PHASE2_SUMMARY.md",
        "COVERAGE_IMPROVEMENT_SUMMARY.md",
        "COVERAGE_REPORT.md",
        "DEEP_CLEANUP_FINAL_REPORT.md",
        "DOCS_CLEANUP_ANALYSIS.md",
        "DOCS_CLEANUP_SUMMARY.md",
        "WEEKLY_IMPROVEMENT_LOG.md",
        "RUFF_ERROR_FIX_PLAN.md",
        "complexity_report.md",
        "daily_maintainability_report.json",
        "feature_calculator_modularization_summary.md",
        "football_data_cleaner_modularization_summary.md",
        "github-actions-optimization.md",
        "mypy_fix_report.md",
        "performance-monitoring.md",
        "phase3_completion_report.md",
        "phase3_final_report.md",
        "predictions_api_modularization_summary.md",
        "refactoring_plan.md",
        "system_monitor_modularization_summary.md",
        "technical_debt_completion_report.md",
    ]

    removed_reports = 0
    for report in report_files:
        report_path = docs_path / report
        if report_path.exists():
            size_kb = report_path.stat().st_size / 1024
            print(f"   删除报告: {report} ({size_kb:.1f}KB)")
            report_path.unlink()
            removed_reports += 1

    print(f"   ✅ 删除了 {removed_reports} 个报告文件")

    # 2. 移动一些文档到合适的位置
    print("\n2️⃣ 整理文档位置...")
    moves = [
        ("AI_DEVELOPER_GUIDE.md", "project/"),
        ("AI_DEVELOPMENT_DOCUMENTATION_RULES.md", "project/"),
        ("API_EXAMPLES.md", "reference/"),
        ("ARCHITECTURE.md", "architecture/"),
        ("CHANGES.md", "release/"),
        ("CODE_EXAMPLES.md", "reference/"),
        ("DEPENDENCY_BEST_PRACTICES.md", "maintenance/"),
        ("DEPENDENCY_MANAGEMENT.md", "maintenance/"),
        ("DEPLOYMENT.md", "how-to/"),
        ("DEPLOYMENT_GUIDE_V2.md", "how-to/"),
        ("DEVELOPMENT_WORKFLOW.md", "project/"),
        ("MIGRATION_GUIDE.md", "how-to/"),
        ("OPTIMIZATION_QUICKSTART.md", "improvements/"),
        ("PROJECT_MAINTENANCE_GUIDE.md", "maintenance/"),
        ("QUALITY_IMPROVEMENT_PLAN.md", "improvements/"),
        ("QUICK_START_FOR_DEVELOPERS.md", "project/"),
        ("TESTING_COMMANDS.md", "testing/"),
        ("TESTING_STANDARDS.md", "testing/"),
        ("TEST_IMPROVEMENT_GUIDE.md", "testing/"),
        ("TROUBLESHOOTING_GUIDE.md", "how-to/"),
        ("WORKFLOWS_GUIDE.md", "project/"),
    ]

    moved_files = 0
    for filename, target_dir in moves:
        source = docs_path / filename
        target = docs_path / target_dir / filename
        if source.exists():
            if not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
            print(f"   移动: {filename} → {target_dir}/")
            shutil.move(str(source), str(target))
            moved_files += 1

    print(f"   ✅ 移动了 {moved_files} 个文件")

    # 3. 删除空的目录
    print("\n3️⃣ 清理空目录...")
    removed_empty = 0
    for _ in range(2):  # 运行两次
        for root, dirs, files in os.walk(docs_path, topdown=False):
            for dir_name in dirs[:]:
                dir_path = Path(root) / dir_name
                try:
                    if dir_path.exists() and not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        removed_empty += 1
                except OSError:
                    pass

    print(f"   ✅ 删除了 {removed_empty} 个空目录")

    # 4. 创建简洁的README
    print("\n4️⃣ 创建简洁的README...")
    readme_content = """# Football Prediction System

足球预测系统文档

## 快速开始

- [项目说明](project/README.md)
- [快速开发指南](QUICK_START_FOR_DEVELOPERS.md)
- [架构文档](architecture/README.md)

## 文档索引

- [完整文档索引](INDEX_MINIMAL.md)
- [测试指南](TESTING_GUIDE.md)

## 开发指南

- [开发工作流](project/DEVELOPMENT_WORKFLOW.md)
- [部署指南](how-to/DEPLOYMENT.md)
- [测试命令](testing/TESTING_COMMANDS.md)

---

*文档自动生成于清理脚本*
"""

    readme_path = docs_path / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("   ✅ 更新了README.md")

    # 5. 最终统计
    print("\n📊 最终结果：")

    total_files = len(list(docs_path.rglob("*.md")))
    total_size_mb = sum(
        f.stat().st_size for f in docs_path.rglob("*") if f.is_file()
    ) / (1024 * 1024)

    print(f"   - 最终文件数: {total_files}")
    print(f"   - 最终大小: {total_size_mb:.2f}MB")
    print(f"   - 删除报告: {removed_reports}")
    print(f"   - 移动文件: {moved_files}")

    print("\n📁 保留的目录结构：")
    for item in sorted(docs_path.iterdir()):
        if item.is_dir():
            file_count = len(list(item.rglob("*.md")))
            print(f"   📁 {item.name}/ ({file_count} 文件)")
        elif item.is_file() and item.suffix == ".md":
            size_kb = item.stat().st_size / 1024
            print(f"   📄 {item.name} ({size_kb:.1f}KB)")

    print("\n✅ Docs目录完全清理完成！")
    print("\n🎉 清理总结：")
    print("   原始: 5.2MB (309文件)")
    print(f"   最终: {total_size_mb:.1f}MB ({total_files}文件)")
    print(
        f"   节省: {5.2 - total_size_mb:.1f}MB ({((5.2 - total_size_mb) / 5.2 * 100):.1f}%)"
    )


if __name__ == "__main__":
    clean_docs_final()
