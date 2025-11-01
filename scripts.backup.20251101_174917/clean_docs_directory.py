#!/usr/bin/env python3
"""
Docs目录清理脚本
删除重复、过时和不必要的文档文件
"""

import os
import shutil
from pathlib import Path
import hashlib
from collections import defaultdict


def calculate_file_hash(filepath):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def find_duplicate_files(directory):
    """查找重复文件"""
    file_hashes = defaultdict(list)

    for file_path in Path(directory).rglob("*.md"):
        if file_path.is_file():
            hash_value = calculate_file_hash(file_path)
            file_hashes[hash_value].append(file_path)

    # 返回有重复的文件列表
    duplicates = {hash_val: files for hash_val, files in file_hashes.items() if len(files) > 1}
    return duplicates


def clean_docs_directory():
    """清理docs目录"""
    docs_path = Path("docs")

    if not docs_path.exists():
        print("❌ docs目录不存在")
        return

    print("🔍 开始分析docs目录...")

    # 1. 查找重复文件
    print("\n1️⃣ 查找重复文件...")
    duplicates = find_duplicate_files(docs_path)

    removed_duplicates = 0
    for hash_val, files in duplicates.items():
        # 保留第一个文件，删除其余的
        for file_path in files[1:]:
            print(f"   删除重复文件: {file_path}")
            file_path.unlink()
            removed_duplicates += 1

    print(f"   ✅ 删除了 {removed_duplicates} 个重复文件")

    # 2. 删除存档目录（保留最新的）
    print("\n2️⃣ 清理存档目录...")
    archive_dirs = [
        docs_path / "archive",
        docs_path / "archives",
        docs_path / "old",
        docs_path / "backup",
    ]

    removed_archives = 0
    for archive_dir in archive_dirs:
        if archive_dir.exists():
            print(f"   删除存档目录: {archive_dir}")
            shutil.rmtree(archive_dir)
            removed_archives += 1

    print(f"   ✅ 删除了 {removed_archives} 个存档目录")

    # 3. 删除特定类型的文件
    print("\n3️⃣ 清理特定文件...")

    # 要删除的文件模式
    patterns_to_remove = [
        "**/README.md.bak",
        "**/*.md.bak",
        "**/*.md.old",
        "**/*.md.tmp",
        "**/DRAFT_*.md",
        "**/TODO_*.md",
        "**/draft_*.md",
        "**/temp_*.md",
        "**/test_*.md",
    ]

    removed_patterns = 0
    for pattern in patterns_to_remove:
        for file_path in docs_path.glob(pattern):
            if file_path.is_file():
                print(f"   删除临时文件: {file_path}")
                file_path.unlink()
                removed_patterns += 1

    print(f"   ✅ 删除了 {removed_patterns} 个临时文件")

    # 4. 清理空目录
    print("\n4️⃣ 清理空目录...")
    removed_empty_dirs = 0

    # 从最深层的目录开始，向上清理
    for root, dirs, files in os.walk(docs_path, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    print(f"   删除空目录: {dir_path}")
                    dir_path.rmdir()
                    removed_empty_dirs += 1
            except OSError:
                pass  # 目录不为空或权限问题

    print(f"   ✅ 删除了 {removed_empty_dirs} 个空目录")

    # 5. 列出大文件（可选）
    print("\n5️⃣ 大文件检查（>50KB）...")
    large_files = []

    for file_path in docs_path.rglob("*.md"):
        if file_path.is_file():
            size_kb = file_path.stat().st_size / 1024
            if size_kb > 50:
                large_files.append((file_path, size_kb))

    if large_files:
        large_files.sort(key=lambda x: x[1], reverse=True)
        print("   以下文件较大，请检查是否需要优化：")
        for file_path, size_kb in large_files[:10]:  # 只显示前10个
            print(f"   - {file_path.relative_to(docs_path)} ({size_kb:.1f}KB)")

    # 6. 统计结果
    print("\n📊 清理结果统计：")

    # 计算清理后的文件数和大小
    total_files = len(list(docs_path.rglob("*.md")))
    total_size_mb = sum(f.stat().st_size for f in docs_path.rglob("*") if f.is_file()) / (
        1024 * 1024
    )

    print(f"   - 剩余Markdown文件数: {total_files}")
    print(f"   - 剩余目录大小: {total_size_mb:.2f}MB")
    print(f"   - 删除重复文件: {removed_duplicates}")
    print(f"   - 删除存档目录: {removed_archives}")
    print(f"   - 删除临时文件: {removed_patterns}")
    print(f"   - 删除空目录: {removed_empty_dirs}")

    print("\n✅ docs目录清理完成！")


if __name__ == "__main__":
    clean_docs_directory()
