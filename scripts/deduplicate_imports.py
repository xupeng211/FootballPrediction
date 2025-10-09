#!/usr/bin/env python3
"""
去除重复的导入语句
"""

from pathlib import Path


def deduplicate_imports(file_path: Path):
    """去除单个文件中的重复导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    seen_imports = set()
    new_lines = []
    skip_next_blank = False

    for line in lines:
        stripped = line.strip()
        # 检查是否是导入语句
        if stripped.startswith("from ") or stripped.startswith("import "):
            # 标准化导入语句
            normalized = stripped
            if normalized not in seen_imports:
                seen_imports.add(normalized)
                new_lines.append(line)
                skip_next_blank = True
            else:
                print(f"  跳过重复导入: {stripped}")
                continue
        elif stripped == "" and skip_next_blank:
            skip_next_blank = False
            continue
        else:
            new_lines.append(line)
            skip_next_blank = False

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def main():
    """主函数"""
    files = [
        "src/database/models/league.py",
        "src/database/models/audit_log.py",
        "src/database/models/data_collection_log.py",
        "src/database/models/data_quality_log.py",
        "src/database/models/features.py",
        "src/database/models/odds.py",
        "src/database/models/user.py",
    ]

    for file_path in files:
        path = Path(file_path)
        if path.exists():
            print(f"清理文件: {file_path}")
            deduplicate_imports(path)

    print("\n清理完成！")


if __name__ == "__main__":
    main()
