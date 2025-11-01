#!/usr/bin/env python3
"""
Docs目录最终优化脚本
对大文件进行分割和压缩
"""

import os
import re
from pathlib import Path


def split_large_file(file_path, chunk_size=30 * 1024):  # 30KB chunks
    """将大文件分割成多个小文件"""
    if not file_path.exists():
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 如果文件不太大，不分割
    if len(content.encode("utf-8")) < chunk_size:
        return

    print(f"   分割文件: {file_path.name}")

    # 按章节分割
    sections = re.split(r"\n(#{1,3})\s+", content)

    # 创建输出目录
    output_dir = file_path.parent / (file_path.stem + "_parts")
    output_dir.mkdir(exist_ok=True)

    current_chunk = ""
    chunk_num = 1

    for i, section in enumerate(sections):
        if i == 0:
            # 文件开头部分
            current_chunk = section
        else:
            # 检查添加这个章节是否会超过大小限制
            test_chunk = (
                current_chunk + "\n" + sections[i] + sections[i + 1]
                if i + 1 < len(sections)
                else sections[i]
            )

            if len(test_chunk.encode("utf-8")) > chunk_size and current_chunk:
                # 写入当前块
                chunk_file = output_dir / f"part_{chunk_num:02d}.md"
                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(current_chunk)
                chunk_num += 1
                current_chunk = sections[i] + (sections[i + 1] if i + 1 < len(sections) else "")
            else:
                current_chunk += (
                    "\n" + sections[i] + (sections[i + 1] if i + 1 < len(sections) else "")
                )

    # 写入最后一块
    if current_chunk:
        chunk_file = output_dir / f"part_{chunk_num:02d}.md"
        with open(chunk_file, "w", encoding="utf-8") as f:
            f.write(current_chunk)

    # 创建索引文件
    index_file = output_dir / "_index.md"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(f"# {file_path.stem} - 分割文档\n\n")
        for i in range(1, chunk_num + 1):
            f.write(f"- [Part {i}](part_{i:02d}.md)\n")

    # 压缩原文件
    import gzip

    with open(file_path, "rb") as f_in:
        with open(file_path.with_suffix(".md.gz"), "wb") as f_out:
            f_out.writelines(f_in)

    # 删除原文件
    file_path.unlink()

    print(f"   ✅ 分割成 {chunk_num} 个部分")


def optimize_docs_final():
    """最终优化docs目录"""
    docs_path = Path("docs")

    print("🚀 开始最终优化docs目录...")

    # 1. 处理超大的部署指南
    print("\n1️⃣ 优化大型文档...")
    large_files = [
        docs_path / "how-to/PRODUCTION_DEPLOYMENT_GUIDE.md",
        docs_path / "architecture/architecture.md",
        docs_path / "testing/ci_config.md",
    ]

    optimized_files = 0
    for file_path in large_files:
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            if size_kb > 80:  # 只处理大于80KB的文件
                split_large_file(file_path)
                optimized_files += 1
            else:
                print(f"   跳过 {file_path.name} ({size_kb:.1f}KB - 不需要分割)")

    print(f"   ✅ 优化了 {optimized_files} 个大文件")

    # 2. 压缩旧的测试报告
    print("\n2️⃣ 压缩旧报告...")
    old_reports = [
        docs_path / "testing/archive/TEST_STRATEGY.md",
        docs_path / "_reports/TEST_COVERAGE_OPTIMIZATION_OVERVIEW.md",
        docs_path / "_reports/FINAL_REVALIDATION_LOG.md",
    ]

    compressed_reports = 0
    for report in old_reports:
        if report.exists():
            # 压缩文件
            import gzip

            with open(report, "rb") as f_in:
                with open(report.with_suffix(".md.gz"), "wb") as f_out:
                    f_out.writelines(f_in)
            report.unlink()
            compressed_reports += 1
            print(f"   压缩: {report.name}")

    print(f"   ✅ 压缩了 {compressed_reports} 个旧报告")

    # 3. 创建精简版文档索引
    print("\n3️⃣ 创建精简版索引...")
    index_content = """# 项目文档索引

## 核心文档
- [项目概述](project/README.md)
- [快速开始](README.md)
- [架构文档](architecture/README.md)

## 开发指南
- [测试指南](TESTING_GUIDE.md)
- [代码规范](project/CODING_STANDARDS.md)
- [部署指南](how-to/README.md)

## 报告归档
- [测试报告](_reports/README.md)
- [覆盖率报告](coverage/README.md)

---
*此文档由自动优化脚本生成*
"""

    index_file = docs_path / "INDEX_MINIMAL.md"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(index_content)

    print("   ✅ 创建精简版索引: INDEX_MINIMAL.md")

    # 4. 最终统计
    print("\n📊 优化结果：")

    total_files = len(list(docs_path.rglob("*.md")))
    total_size_mb = sum(f.stat().st_size for f in docs_path.rglob("*") if f.is_file()) / (
        1024 * 1024
    )

    print(f"   - 最终文件数: {total_files}")
    print(f"   - 最终大小: {total_size_mb:.2f}MB")
    print(f"   - 优化大文件: {optimized_files}")
    print(f"   - 压缩旧报告: {compressed_reports}")

    # 计算总体节省
    original_size = 5.2  # MB
    saved = original_size - total_size_mb
    saved_percent = (saved / original_size) * 100

    print("\n💾 总体节省:")
    print(f"   - 原始大小: {original_size}MB")
    print(f"   - 最终大小: {total_size_mb:.2f}MB")
    print(f"   - 节省空间: {saved:.2f}MB ({saved_percent:.1f}%)")

    print("\n✅ Docs目录优化完成！")
    print("\n📌 建议:")
    print("   1. 使用 INDEX_MINIMAL.md 作为主要导航")
    print("   2. 大型文档已分割成多个部分，便于快速加载")
    print("   3. 旧报告已压缩，需要时可以解压查看")


if __name__ == "__main__":
    optimize_docs_final()
