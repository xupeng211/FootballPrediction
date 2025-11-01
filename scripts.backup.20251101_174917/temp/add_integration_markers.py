#!/usr/bin/env python3
"""
为集成测试文件添加pytest.mark.integration标记
"""

import os
from pathlib import Path


def add_integration_marker_to_file(file_path: Path) -> bool:
    """为单个文件添加integration标记"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 如果已经有integration标记，跳过
        if "@pytest.mark.integration" in content:
            return False

        # 找到第一个测试类或函数
        lines = content.split("\n")
        insert_index = -1

        for i, line in enumerate(lines):
            if line.strip().startswith("class Test") or line.strip().startswith("def test_"):
                insert_index = i
                break

        if insert_index == -1:
            return False

        # 插入integration标记
        lines.insert(insert_index, "@pytest.mark.integration")
        lines.insert(insert_index + 1, "")

        # 写回文件
        new_content = "\n".join(lines)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """主函数"""
    integration_dir = Path("tests/integration")

    if not integration_dir.exists():
        print("Integration tests directory not found")
        return

    # 递归处理所有Python文件
    processed = 0
    for file_path in integration_dir.rglob("*.py"):
        if file_path.name in ["__init__.py", "conftest.py"]:
            continue

        if add_integration_marker_to_file(file_path):
            processed += 1
            print(f"Added integration marker to: {file_path}")

    print(f"\n✅ 添加了integration标记到 {processed} 个文件")


if __name__ == "__main__":
    main()
