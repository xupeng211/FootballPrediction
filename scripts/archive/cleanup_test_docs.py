#!/usr/bin/env python3
"""
清理过时的测试文档
"""

import shutil
from pathlib import Path
from datetime import datetime


def create_archive_directory():
    """创建归档目录"""
    archive_dir = Path("docs/testing/archive")
    archive_dir.mkdir(exist_ok=True)

    # 创建归档说明
    readme = """# 测试文档归档

此目录包含已过时或被替代的测试文档。

归档时间：{}
归档原因：测试重构完成，新的文档体系已建立

## 新文档体系

请参考：
- `../TEST_GUIDE.md` - 完整的测试指南
- `../README.md` - 快速入门
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    with open(archive_dir / "README.md", "w") as f:
        f.write(readme)

    return archive_dir


def move_to_archive(files_to_move, archive_dir):
    """移动文件到归档目录"""
    moved = []
    for file_path in files_to_move:
        src = Path(file_path)
        if src.exists():
            dst = archive_dir / src.name
            shutil.move(src, dst)
            moved.append(str(src))
            print(f"  📦 已归档: {src}")
    return moved


def delete_files(files_to_delete):
    """删除文件"""
    deleted = []
    for file_path in files_to_delete:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            deleted.append(str(path))
            print(f"  🗑️  已删除: {path}")
    return deleted


def main():
    """主函数"""
    print("=" * 60)
    print("🧹 开始清理测试文档")
    print("=" * 60)

    # 需要归档的文件（可能还有历史价值）
    files_to_archive = [
        "docs/testing/COVERAGE_PROGRESS.md",
        "docs/testing/COVERAGE_PROGRESS_NEW.md",
        "docs/testing/COVERAGE_ROADMAP.md",
        "docs/testing/COVERAGE_BASELINE_REPORT.md",
        "docs/testing/TEST_STRATEGY.md",
        "docs/testing/TESTING_STRATEGY.md",
        "docs/testing/TESTING_OPTIMIZATION_REPORT.md",
        "docs/testing/CI_BLOCKERS.md",
        "docs/testing/CI_FIX_REPORT.md",
        "docs/testing/LOCAL_CI_REPORT.md",
        "docs/testing/FEATURE_STORE_TEST_FIXES.md",
    ]

    # 需要完全删除的文件（完全过时）
    files_to_delete = []

    # 创建归档目录
    print("\n📁 创建归档目录...")
    archive_dir = create_archive_directory()
    print(f"  ✅ 归档目录: {archive_dir}")

    # 归档文件
    print("\n📦 归档过时文档...")
    moved = move_to_archive(files_to_archive, archive_dir)

    # 删除文件
    if files_to_delete:
        print("\n🗑️  删除无用文档...")
        delete_files(files_to_delete)

    # 统计
    print("\n" + "=" * 60)
    print("📊 清理统计")
    print("=" * 60)
    print(f"  归档文件: {len(moved)} 个")
    print(f"  删除文件: {len(files_to_delete)} 个")
    print(f"  总计处理: {len(moved) + len(files_to_delete)} 个")

    print("\n✅ 清理完成！")
    print("\n📌 提示:")
    print("  - 归档文件在: docs/testing/archive/")
    print("  - 主要参考: docs/testing/TEST_GUIDE.md")
    print("  - 请更新相关链接")


if __name__ == "__main__":
    main()
