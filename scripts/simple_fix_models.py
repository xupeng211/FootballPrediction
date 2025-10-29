#!/usr/bin/env python3
"""
简单直接修复所有SQLAlchemy模型
"""

import re
from pathlib import Path


def fix_all_models():
    """修复所有模型文件"""
    print("🔧 简单修复所有SQLAlchemy模型...")

    model_files = [
        "src/database/models/league.py",
        "src/database/models/audit_log.py",
        "src/database/models/data_quality_log.py",
        "src/database/models/features.py",
        "src/database/models/user.py",
        "src/database/models/predictions.py",
        "src/database/models/raw_data.py",
        "src/database/models/odds.py",
        "src/database/models/team.py",
        "src/database/models/match.py",
    ]

    fixed_count = 0

    for file_path in model_files:
        path = Path(file_path)
        if not path.exists():
            print(f"    ⚠️ {file_path} 不存在")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否已经有extend_existing
            if "extend_existing=True" in content:
                print(f"    ✅ {file_path} 已经有 extend_existing")
                continue

            # 查找第一个BaseModel类定义
            lines = content.split("\n")
            new_lines = []
            modified = False

            for i, line in enumerate(lines):
                new_lines.append(line)

                # 如果找到BaseModel类定义
                if re.match(r"^\s*class\s+\w+\s*\(\s*BaseModel\s*\)\s*:", line):
                    # 在下一行添加__table_args__
                    next_line = i + 1
                    if next_line < len(lines):
                        current_indent = len(line) - len(line.lstrip())
                        table_args_line = (
                            " " * (current_indent + 4)
                            + "__table_args__ = {'extend_existing': True}"
                        )
                        new_lines.insert(next_line, table_args_line)
                        modified = True
                        print(f"    ✅ 修复了 {file_path}")
                        fixed_count += 1
                        break

            if modified:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines))

        except Exception as e:
            print(f"    ❌ 修复 {file_path} 时出错: {e}")

    print(f"\n✅ 修复完成！总共修复了 {fixed_count} 个文件")
    return fixed_count


if __name__ == "__main__":
    fix_all_models()
