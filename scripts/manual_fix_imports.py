#!/usr/bin/env python3
"""
手动修复数据库模型文件中的重复导入
"""

import re
from pathlib import Path


def fix_file(file_path: Path):
    """修复单个文件的导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 合并所有 sqlalchemy 导入
    lines = content.split("\n")
    new_lines = []
    sqlalchemy_imports = []
    other_imports = []
    imports_done = False

    # 第一遍：收集所有导入
    for line in lines:
        if not imports_done and (
            line.startswith("from sqlalchemy") or line.startswith("import sqlalchemy")
        ):
            sqlalchemy_imports.append(line)
        elif not imports_done and (
            line.startswith("from ") or line.startswith("import ")
        ):
            other_imports.append(line)
        elif line.strip() == "" and not imports_done:
            continue
        else:
            imports_done = True

    # 合并 sqlalchemy 导入
    if sqlalchemy_imports:
        # 提取所有导入的符号
        symbols = set()
        base_imports = set()

        for imp in sqlalchemy_imports:
            if imp.startswith("from sqlalchemy import"):
                symbols.update(
                    [
                        s.strip()
                        for s in imp.replace("from sqlalchemy import", "").split(",")
                    ]
                )
            elif imp.startswith("from sqlalchemy.orm import"):
                symbols.update(
                    [
                        s.strip()
                        for s in imp.replace("from sqlalchemy.orm import", "").split(
                            ","
                        )
                    ]
                )
            elif imp.startswith("import sqlalchemy"):
                base_imports.add("sqlalchemy")

        # 生成新的导入
        new_imports = []
        if base_imports:
            new_imports.append(f"import {', '.join(sorted(base_imports))}")
        if symbols:
            # 分组符号
            core_symbols = [
                s
                for s in symbols
                if not s.endswith(" as ")
                and s not in ["relationship", "mapped_column", "Mapped"]
            ]
            orm_symbols = [
                s
                for s in symbols
                if s in ["relationship", "mapped_column", "Mapped"]
                or s.endswith(" as SQLEnum")
            ]

            if core_symbols:
                new_imports.append(
                    f"from sqlalchemy import {', '.join(sorted(core_symbols))}"
                )
            if orm_symbols:
                new_imports.append(
                    f"from sqlalchemy.orm import {', '.join(sorted(orm_symbols))}"
                )

        # 重新构建文件内容
        new_lines = []
        imports_added = False

        for line in lines:
            if not imports_added and line.strip() == "" and other_imports:
                # 添加其他导入
                for imp in other_imports:
                    new_lines.append(imp)
                new_lines.append("")
                # 添加新的 sqlalchemy 导入
                for imp in new_imports:
                    new_lines.append(imp)
                new_lines.append("")
                imports_added = True
            elif line.startswith("from sqlalchemy") or line.startswith(
                "import sqlalchemy"
            ):
                continue  # 跳过旧的 sqlalchemy 导入
            else:
                new_lines.append(line)

        new_content = "\n".join(new_lines)
    else:
        new_content = content

    # 写回文件
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✓ 修复: {file_path.relative_to('.')}")
        return True

    return False


def main():
    """主函数"""
    print("手动修复数据库模型文件的导入...")

    # 需要修复的文件
    files_to_fix = [
        "src/database/models/league.py",
        "src/database/models/audit_log.py",
        "src/database/models/data_collection_log.py",
        "src/database/models/data_quality_log.py",
        "src/database/models/features.py",
        "src/database/models/odds.py",
        "src/database/models/user.py",
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            if fix_file(path):
                fixed_count += 1

    print(f"\n修复完成！共修复 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
