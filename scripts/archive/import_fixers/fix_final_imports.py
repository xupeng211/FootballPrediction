#!/usr/bin/env python3
"""
最终导入修复脚本 - 专门处理剩余的F821错误
"""

import os
import re
import subprocess
from collections import defaultdict


def get_f821_errors():
    """获取所有F821错误"""
    result = subprocess.run(["make", "lint"], capture_output=True, text=True, cwd=".")
    errors = []
    for line in result.stdout.split("\n"):
        if "F821 undefined name" in line:
            match = re.search(r"(.+):(\d+):\d+: F821 undefined name '(.+)'", line)
            if match:
                filepath, line_num, var_name = match.groups()
                errors.append((filepath, int(line_num), var_name))
    return errors


def add_import_after_docstring(filepath, import_statement):
    """在文档字符串后添加导入语句"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 检查是否已存在该导入
        for line in lines:
            if import_statement.strip() in line.strip():
                return False

        # 找到第一个文档字符串的结束位置
        in_docstring = False
        docstring_end = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            if not in_docstring and stripped.startswith('"""'):
                in_docstring = True
                continue
            elif in_docstring and '"""' in stripped:
                docstring_end = i + 1
                break

        # 如果找不到文档字符串，在文件开头添加
        if docstring_end == 0:
            # 找到第一个非注释、非空行
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    docstring_end = i
                    break

        # 寻找合适的导入位置（在已有导入之后）
        import_pos = docstring_end
        for i in range(docstring_end, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith(("import ", "from ")):
                import_pos = i + 1
            elif stripped and not stripped.startswith("#") and "import" not in stripped:
                break

        # 添加空行（如果需要）
        if import_pos < len(lines) and lines[import_pos].strip():
            lines.insert(import_pos, "\n")
            import_pos += 1

        # 插入导入语句
        lines.insert(import_pos, import_statement + "\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """主函数"""
    print("获取F821错误...")
    errors = get_f821_errors()

    if not errors:
        print("没有发现F821错误！")
        return

    print(f"发现 {len(errors)} 个F821错误")

    # 按变量名和文件分组
    error_stats = defaultdict(lambda: defaultdict(list))
    for filepath, line_num, var_name in errors:
        error_stats[var_name][filepath].append(line_num)

    # 定义导入映射
    import_mapping = {
        "asyncio": "import asyncio",
        "time": "import time",
        "patch": "from unittest.mock import patch",
        "datetime": "from datetime import datetime",
        "timedelta": "from datetime import timedelta",
        "MagicMock": "from unittest.mock import MagicMock",
        "Mock": "from unittest.mock import Mock",
        "AsyncMock": "from unittest.mock import AsyncMock",
    }

    # 修复每种类型的错误
    total_fixed = 0
    for var_name, files_dict in error_stats.items():
        if var_name in import_mapping:
            import_statement = import_mapping[var_name]
            files_to_fix = list(files_dict.keys())

            print(f"\n修复 '{var_name}' 导入问题 ({len(files_to_fix)} 个文件)...")

            fixed_count = 0
            for filepath in files_to_fix:
                if os.path.exists(filepath) and filepath.startswith("tests/"):
                    if add_import_after_docstring(filepath, import_statement):
                        fixed_count += 1
                        total_fixed += 1
                        print(f"  ✓ {filepath}")

            print(f"已修复 {fixed_count} 个文件")

    print(f"\n总计修复了 {total_fixed} 个文件")

    # 再次检查错误数量
    print("\n重新检查错误数量...")
    new_errors = get_f821_errors()
    print(f"修复后剩余 {len(new_errors)} 个F821错误")

    if len(new_errors) < len(errors):
        print(f"✅ 成功减少了 {len(errors) - len(new_errors)} 个错误")


if __name__ == "__main__":
    main()
