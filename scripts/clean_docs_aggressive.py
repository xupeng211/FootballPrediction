#!/usr/bin/env python3
"""
Docs目录深度清理脚本
更激进地清理不必要的文件
"""

import os
import shutil
from pathlib import Path
import tarfile


def clean_docs_aggressive():
    """激进地清理docs目录"""
    docs_path = Path("docs")

    print("🔥 开始深度清理docs目录...")

    # 1. 删除旧的归档文件
    print("\n1️⃣ 清理归档文件...")
    archive_files = [
        docs_path / "_reports/archive/legacy_archive_2025-10-04.tar.gz",
        docs_path / "_reports/archive/legacy_archive.tar.gz",
        docs_path / "_reports/archive/old_docs.tar.gz",
    ]

    removed_archives = 0
    for archive_file in archive_files:
        if archive_file.exists():
            size_mb = archive_file.stat().st_size / (1024 * 1024)
            print(f"   删除归档文件: {archive_file.name} ({size_mb:.1f}MB)")
            archive_file.unlink()
            removed_archives += 1

    print(f"   ✅ 删除了 {removed_archives} 个归档文件")

    # 2. 删除示例和测试文档
    print("\n2️⃣ 清理示例和测试文档...")
    example_patterns = [
        "testing/examples.md",
        "testing/sample_*.md",
        "testing/test_*.md",
        "how-to/examples/",
        "samples/",
        "examples/",
        "demo/",
        "test_docs/",
    ]

    removed_examples = 0
    for pattern in example_patterns:
        for path in docs_path.glob(pattern):
            if path.is_file():
                print(f"   删除示例文件: {path.relative_to(docs_path)}")
                path.unlink()
                removed_examples += 1
            elif path.is_dir():
                print(f"   删除示例目录: {path.relative_to(docs_path)}")
                shutil.rmtree(path)
                removed_examples += 1

    print(f"   ✅ 删除了 {removed_examples} 个示例文件/目录")

    # 3. 清理过时的报告
    print("\n3️⃣ 清理过时的报告...")
    report_dir = docs_path / "_reports/archive/2025-09"
    if report_dir.exists():
        old_reports = ["cleanup", "deployment", "migration", "performance"]

        removed_reports = 0
        for report_type in old_reports:
            report_path = report_dir / report_type
            if report_path.exists():
                print(f"   删除过时报告: {report_path.relative_to(docs_path)}")
                shutil.rmtree(report_path)
                removed_reports += 1

        print(f"   ✅ 删除了 {removed_reports} 个过时报告目录")

    # 4. 删除冗余的大型文档
    print("\n4️⃣ 检查大型文档...")
    large_files_to_check = [
        ("architecture/DATA_DESIGN.md", "架构设计文档"),
        ("how-to/PRODUCTION_DEPLOYMENT_GUIDE.md", "生产部署指南"),
        ("testing/ci_config.md", "CI配置文档"),
        ("testing/performance_tests.md", "性能测试文档"),
    ]

    for file_path, description in large_files_to_check:
        full_path = docs_path / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            print(f"   {description}: {file_path} ({size_kb:.1f}KB)")

    # 5. 清理空的索引文件
    print("\n5️⃣ 清理空或无用的索引文件...")
    index_files = [
        docs_path / "_sidebar.md",
        docs_path / "_navbar.md",
        docs_path / "summary.md",
    ]

    removed_indices = 0
    for index_file in index_files:
        if index_file.exists():
            # 检查文件是否很小或内容很少
            if index_file.stat().st_size < 100:
                print(f"   删除小型索引文件: {index_file.name}")
                index_file.unlink()
                removed_indices += 1

    print(f"   ✅ 删除了 {removed_indices} 个小型索引文件")

    # 6. 压缩特别大的文件
    print("\n6️⃣ 压缩大文件...")
    very_large_files = [docs_path / "architecture/DATA_DESIGN.md"]

    compressed_files = 0
    for file_path in very_large_files:
        if file_path.exists() and file_path.stat().st_size > 150 * 1024:  # >150KB
            # 创建压缩版本
            gz_path = file_path.with_suffix(file_path.suffix + ".gz")
            if not gz_path.exists():
                print(f"   压缩大文件: {file_path.name}")
                with open(file_path, "rb") as f_in:
                    with open(gz_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                # 删除原文件
                file_path.unlink()
                compressed_files += 1

    print(f"   ✅ 压缩了 {compressed_files} 个大文件")

    # 7. 最终统计
    print("\n📊 最终统计：")

    # 计算清理后的文件数和大小
    total_files = len(list(docs_path.rglob("*.md")))
    total_size_mb = sum(
        f.stat().st_size for f in docs_path.rglob("*") if f.is_file()
    ) / (1024 * 1024)

    print(f"   - 剩余Markdown文件数: {total_files}")
    print(f"   - 剩余目录大小: {total_size_mb:.2f}MB")
    print(f"   - 删除归档文件: {removed_archives}")
    print(f"   - 删除示例文件: {removed_examples}")
    print(
        f"   - 删除过时报告: {removed_reports if 'removed_reports' in locals() else 0}"
    )
    print(f"   - 删除索引文件: {removed_indices}")
    print(
        f"   - 压缩大文件: {compressed_files if 'compressed_files' in locals() else 0}"
    )

    # 8. 提供进一步优化建议
    print("\n💡 进一步优化建议：")
    print("   1. 考虑将大型文档拆分成多个小文档")
    print("   2. 使用图片压缩工具优化docs中的图片")
    print("   3. 考虑将不常用的文档移动到wiki或单独的仓库")

    print("\n✅ docs目录深度清理完成！")


if __name__ == "__main__":
    clean_docs_aggressive()
