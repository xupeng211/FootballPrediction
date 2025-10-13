#!/usr/bin/env python3
"""
彻底清理Docs目录
删除所有不必要的文件和目录
"""

import os
import shutil
from pathlib import Path
import re


def clean_docs_complete():
    """彻底清理docs目录"""
    docs_path = Path("docs")

    print("🧹 开始彻底清理docs目录...")

    # 1. 删除所有archive目录
    print("\n1️⃣ 删除所有归档目录...")
    archive_dirs = list(docs_path.rglob("*archive*"))
    archive_dirs.extend(list(docs_path.rglob("*Archive*")))

    removed_archives = 0
    for archive_dir in archive_dirs:
        if archive_dir.is_dir():
            print(f"   删除归档目录: {archive_dir.relative_to(docs_path)}")
            shutil.rmtree(archive_dir)
            removed_archives += 1

    print(f"   ✅ 删除了 {removed_archives} 个归档目录")

    # 2. 删除测试相关的临时文档
    print("\n2️⃣ 删除测试相关临时文档...")
    test_files_to_remove = [
        "testing/E2E_TEST_RUNBOOK.md",
        "testing/INTEGRATION_TEST_RUNBOOK.md",
        "testing/EXECUTION_PLAN.md",
        "testing/COVERAGE_IMPROVEMENT_PLAN.md",
        "testing/CI_MIGRATION_COMPATIBILITY_REPORT.md",
        "testing/coverage_dashboard.html",
        "testing/test_execution_plan.md",
        "testing/TEST_EXECUTION_LOG.md",
        "testing/TEST_ACTIVATION_PLAN.md",
        "testing/TEST_OPTIMIZATION_REPORT.md",
        "testing/PERFORMANCE_TEST_REPORT.md",
        "testing/BLOCKED_TESTS_REPORT.md",
        "testing/TEST_STATUS_TRACKER.md",
        "testing/CI_TROUBLESHOOTING.md",
        "testing/LOCAL_TESTING.md",
        "testing/QUICK_TEST_RUN.md",
        "testing/TEST_CLEANUP.md",
    ]

    removed_test_files = 0
    for file_path in test_files_to_remove:
        full_path = docs_path / file_path
        if full_path.exists():
            print(f"   删除测试文件: {file_path}")
            full_path.unlink()
            removed_test_files += 1

    print(f"   ✅ 删除了 {removed_test_files} 个测试文件")

    # 3. 删除_reports目录下的无用文件
    print("\n3️⃣ 清理_reports目录...")
    reports_dir = docs_path / "_reports"

    if reports_dir.exists():
        # 删除HTML文件和模板
        html_files = list(reports_dir.rglob("*.html"))
        for html_file in html_files:
            print(f"   删除HTML文件: {html_file.relative_to(docs_path)}")
            html_file.unlink()

        # 删除templates目录
        templates_dir = reports_dir / "templates"
        if templates_dir.exists():
            print("   删除模板目录: templates")
            shutil.rmtree(templates_dir)

        # 删除其他临时报告
        temp_reports = [
            "TEST_COVERAGE_IMPROVEMENT.md",
            "COVERAGE_PROGRESS.md",
            "COVERAGE_OPTIMIZATION.md",
            "TEST_OPTIMIZATION.md",
            "PERFORMANCE_REPORT.md",
            "CLEANUP_REPORT.md",
            "DAILY_REPORT.md",
            "WEEKLY_REPORT.md",
            "scaffold_dashboard.html",
        ]

        removed_reports = 0
        for report in temp_reports:
            report_path = reports_dir / report
            if report_path.exists():
                print(f"   删除临时报告: {report}")
                report_path.unlink()
                removed_reports += 1

        print(f"   ✅ 删除了 {removed_reports} 个临时报告")

    # 4. 删除重复或过时的指南
    print("\n4️⃣ 删除重复或过时的指南...")
    duplicate_guides = [
        "how-to/DEPLOYMENT_ISSUES_LOG.md",
        "how-to/DEPLOYMENT_TROUBLESHOOTING.md",
        "how-to/MIGRATION_GUIDE_OLD.md",
        "how-to/SETUP_GUIDE_OLD.md",
        "how-to/LEGACY_DEPLOYMENT.md",
        "how-to/OLD_DEPLOYMENT_GUIDE.md",
        "project/OLD_README.md",
        "project/PROJECT_PLAN.md",
        "project/PROJECT_ROADMAP.md",
        "project/TIMELINE.md",
        "project/DEVELOPMENT_PLAN.md",
        "project/RELEASE_NOTES.md",
        "project/CHANGELOG_OLD.md",
    ]

    removed_guides = 0
    for guide in duplicate_guides:
        guide_path = docs_path / guide
        if guide_path.exists():
            print(f"   删除过时指南: {guide}")
            guide_path.unlink()
            removed_guides += 1

    print(f"   ✅ 删除了 {removed_guides} 个过时指南")

    # 5. 删除AI相关的测试文档
    print("\n5️⃣ 清理AI相关文档...")
    ai_dir = docs_path / "ai"
    if ai_dir.exists():
        # 保留主要文档，删除测试和示例
        ai_files_to_keep = ["README.md", "architecture.md", "integration.md"]
        removed_ai_files = 0

        for file_path in ai_dir.rglob("*.md"):
            if file_path.name not in ai_files_to_keep:
                print(f"   删除AI文档: {file_path.relative_to(docs_path)}")
                file_path.unlink()
                removed_ai_files += 1

        # 删除空的子目录
        for subdir in ai_dir.iterdir():
            if subdir.is_dir() and not any(subdir.iterdir()):
                subdir.rmdir()
                print(f"   删除空目录: {subdir.name}")

        print(f"   ✅ 删除了 {removed_ai_files} 个AI文档")

    # 6. 删除项目中的临时和草稿文件
    print("\n6️⃣ 删除临时和草稿文件...")
    temp_patterns = [
        "**/*DRAFT*",
        "**/*WIP*",
        "**/*TEMP*",
        "**/*TODO*",
        "**/*FIXME*",
        "**/*draft*",
        "**/*wip*",
        "**/*temp*",
        "**/*todo*",
        "**/*fixme*",
        "**/*_backup*",
        "**/*_old*",
        "**/*_deprecated*",
        "**/*_test*",
        "**/*_demo*",
        "**/*_example*",
    ]

    removed_temp = 0
    for pattern in temp_patterns:
        for file_path in docs_path.glob(pattern):
            if file_path.is_file() and file_path.suffix == ".md":
                print(f"   删除临时文件: {file_path.relative_to(docs_path)}")
                file_path.unlink()
                removed_temp += 1

    print(f"   ✅ 删除了 {removed_temp} 个临时文件")

    # 7. 清理空的README文件
    print("\n7️⃣ 清理空的或无用的README文件...")
    empty_readmes = 0

    for readme in docs_path.rglob("README.md"):
        if readme.stat().st_size < 100:  # 小于100字节的README
            content = readme.read_text(encoding="utf-8")
            if not content.strip() or len(content.split("\n")) < 3:
                print(f"   删除空README: {readme.relative_to(docs_path)}")
                readme.unlink()
                empty_readmes += 1

    print(f"   ✅ 删除了 {empty_readmes} 个空README文件")

    # 8. 清理空目录
    print("\n8️⃣ 清理所有空目录...")
    removed_empty_dirs = 0

    # 多次遍历，从最深层开始
    for _ in range(3):
        for root, dirs, files in os.walk(docs_path, topdown=False):
            for dir_name in dirs[:]:
                dir_path = Path(root) / dir_name
                try:
                    if dir_path.exists() and not any(dir_path.iterdir()):
                        print(f"   删除空目录: {dir_path.relative_to(docs_path)}")
                        dir_path.rmdir()
                        removed_empty_dirs += 1
                except OSError:
                    pass

    print(f"   ✅ 删除了 {removed_empty_dirs} 个空目录")

    # 9. 最终统计
    print("\n📊 最终统计：")

    total_files = len(list(docs_path.rglob("*.md")))
    total_dirs = len([d for d in docs_path.rglob("*") if d.is_dir()])
    total_size_mb = sum(
        f.stat().st_size for f in docs_path.rglob("*") if f.is_file()
    ) / (1024 * 1024)

    print(f"   - 最终文件数: {total_files}")
    print(f"   - 最终目录数: {total_dirs}")
    print(f"   - 最终大小: {total_size_mb:.2f}MB")
    print(f"   - 删除归档目录: {removed_archives}")
    print(f"   - 删除测试文件: {removed_test_files}")
    print(f"   - 删除过时指南: {removed_guides}")
    print(f"   - 删除临时文件: {removed_temp}")
    print(f"   - 删除空目录: {removed_empty_dirs}")

    # 10. 保留的核心文档列表
    print("\n📚 保留的核心文档：")
    core_docs = [
        "README.md",
        "INDEX_MINIMAL.md",
        "architecture/README.md",
        "project/README.md",
        "TESTING_GUIDE.md",
        "how-to/README.md",
    ]

    for doc in core_docs:
        if (docs_path / doc).exists():
            print(f"   ✅ {doc}")

    print("\n✅ Docs目录彻底清理完成！")


if __name__ == "__main__":
    clean_docs_complete()
