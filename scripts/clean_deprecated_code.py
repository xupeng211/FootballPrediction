#!/usr/bin/env python3
"""
清理废弃代码脚本
物理删除所有_v2, _old, _mock, _simple后缀的文件
"""

import os
import sys
from pathlib import Path
from typing import List

def find_deprecated_files() -> List[Path]:
    """查找需要删除的废弃文件"""
    project_root = Path(__file__).parent.parent
    deprecated_files = []

    # 需要删除的文件模式
    patterns = [
        "*_v2.py",
        "*_old.py",
        "*_mock.py",
        "*_simple.py"
    ]

    # 搜索所有Python文件
    for py_file in project_root.rglob("*.py"):
        # 跳过虚拟环境
        if "venv" in str(py_file) or ".venv" in str(py_file):
            continue

        # 检查文件名是否匹配废弃模式
        for pattern in patterns:
            if py_file.match(pattern):
                deprecated_files.append(py_file)
                break

    return sorted(deprecated_files)

def main():
    """主函数"""
    print("🗑️ 废弃代码清理工具")
    print("=" * 50)

    # 查找废弃文件
    deprecated_files = find_deprecated_files()

    if not deprecated_files:
        print("✅ 没有找到需要删除的废弃文件")
        return

    print(f"📋 找到 {len(deprecated_files)} 个废弃文件:")
    for i, file_path in enumerate(deprecated_files, 1):
        relative_path = file_path.relative_to(Path.cwd())
        print(f"  {i:2d}. {relative_path}")

    # 确认删除
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        print(f"\n🗑️ 开始删除 {len(deprecated_files)} 个文件...")
        deleted_count = 0
        error_count = 0

        for file_path in deprecated_files:
            try:
                relative_path = file_path.relative_to(Path.cwd())
                print(f"  删除: {relative_path}")
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败 {file_path}: {e}")
                error_count += 1

        print(f"\n✅ 删除完成: {deleted_count} 个文件成功, {error_count} 个文件失败")

    else:
        print(f"\n💡 要删除这些文件，请运行:")
        print(f"  python {__file__} --delete")
        print(f"\n⚠️ 注意: 删除是不可逆的，请确保已备份重要代码")

if __name__ == "__main__":
    main()