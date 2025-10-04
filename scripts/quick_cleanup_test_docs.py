#!/usr/bin/env python3
"""
快速清理过时的测试文档
"""

import os
import shutil
from pathlib import Path

def cleanup_test_docs():
    """清理测试相关的过时文档"""
    docs_dir = Path("docs")

    # 需要删除的文件模式
    patterns_to_remove = [
        "TEST_*.md",
        "test_*.md",
        "*test_report_*.md",
        "*_TEST_*.md",
        "integration_test_report_*.md",
        "e2e_test_report_*.md",
        "unit_test_failure_*.md"
    ]

    # 需要删除的特定文件
    files_to_remove = [
        "docs/testing/TEST_TOOLS_USER_GUIDE.md",
        "docs/testing/TEST_STRATEGY.md",
        "docs/testing/TEST_LAYERING_STRATEGY.md",
        "docs/testing/TEST_QUALITY_IMPROVEMENT_SUMMARY.md",
        "docs/guides/TEST_IMPROVEMENT_GUIDE.md",
        "docs/legacy/reports/TEST_ARCHITECTURE_REFACTOR_REPORT.md",
        "docs/project/ISSUES.md",
        "docs/legacy/README.md",
        "docs/ops/runbooks/README.md",
        "docs/README.md"
    ]

    deleted_count = 0
    total_size = 0

    print("开始清理测试文档...")

    # 按模式删除
    for pattern in patterns_to_remove:
        for file_path in docs_dir.rglob(pattern):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    print(f"  删除: {file_path.relative_to(docs_dir)} ({size} bytes)")
                    deleted_count += 1
                    total_size += size
                except Exception as e:
                    print(f"  删除失败: {file_path} - {e}")

    # 删除特定文件
    for file_path_str in files_to_remove:
        file_path = docs_dir / file_path_str
        if file_path.exists():
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                print(f"  删除: {file_path.relative_to(docs_dir)} ({size} bytes)")
                deleted_count += 1
                total_size += size
            except Exception as e:
                print(f"  删除失败: {file_path} - {e}")

    # 清理空目录
    print("\n清理空目录...")
    dirs_to_check = sorted(
        [d for d in docs_dir.rglob("*") if d.is_dir()],
        key=lambda x: len(x.parts),
        reverse=True
    )

    empty_dirs = 0
    for dir_path in dirs_to_check:
        try:
            if not any(dir_path.iterdir()):
                dir_path.rmdir()
                print(f"  删除空目录: {dir_path.relative_to(docs_dir)}")
                empty_dirs += 1
        except OSError:
            pass

    print(f"\n清理完成!")
    print(f"删除文件: {deleted_count} 个")
    print(f"释放空间: {total_size / 1024:.2f} KB")
    print(f"删除空目录: {empty_dirs} 个")

if __name__ == "__main__":
    cleanup_test_docs()