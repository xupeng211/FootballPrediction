#!/usr/bin/env python3
"""
为单元测试文件添加pytest.mark.unit标记
"""

import os
from pathlib import Path

def add_unit_marker_to_file(file_path: Path) -> bool:
    """为单个文件添加unit标记"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 如果已经有unit标记，跳过
        if "@pytest.mark.unit" in content:
            return False

        # 找到第一个测试类
        lines = content.split('\n')
        insert_index = -1

        for i, line in enumerate(lines):
            if line.strip().startswith('class Test'):
                insert_index = i
                break

        if insert_index == -1:
            return False

        # 插入unit标记
        lines.insert(insert_index, "@pytest.mark.unit")
        lines.insert(insert_index + 1, "")

        # 写回文件
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """主函数"""
    unit_dir = Path("tests/unit")

    if not unit_dir.exists():
        print("Unit tests directory not found")
        return

    # 递归处理所有Python文件
    processed = 0
    for file_path in unit_dir.rglob("*.py"):
        if file_path.name in ["__init__.py", "conftest.py"]:
            continue

        if add_unit_marker_to_file(file_path):
            processed += 1
            print(f"Added unit marker to: {file_path}")

    print(f"\n✅ 添加了unit标记到 {processed} 个文件")

if __name__ == "__main__":
    main()