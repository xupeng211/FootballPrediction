#!/usr/bin/env python3
"""
批量修复导入问题的脚本
"""

import os
import re
import subprocess

# 常见的导入修复映射
IMPORT_FIXES = {
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "asyncio": "import asyncio",
    "patch": "from unittest.mock import patch",
    "time": "import time",
    "RedisError": "from redis import RedisError",
    "text": "from sqlalchemy import text",
    "TeamType": "from src.database.models.team import TeamType",
    "Match": "from src.database.models.match import Match",
    "MatchStatus": "from src.database.models.match import MatchStatus",
    "Odds": "from src.database.models.odds import Odds",
    "MarketType": "from src.database.models.odds import MarketType",
    "Predictions": "from src.database.models.predictions import Predictions",
    "DataQualityLog": "from src.database.models.data_quality import DataQualityLog",
    "DatabaseManager": "from src.database.connection import DatabaseManager",
    "DatabaseConfig": "from src.database.connection import DatabaseConfig",
    "DataLakeStorage": "from src.data.storage.data_lake_storage import DataLakeStorage",
    "FeatureStore": "from src.data.features.feature_store import FeatureStore",
    "FeatureDefinitions": "from src.data.features.feature_definitions import FeatureDefinitions",
    "FeatureExamples": "from src.data.features.feature_examples import FeatureExamples",
    "MagicMock": "from unittest.mock import MagicMock",
    "Dict": "from typing import Dict",
}


def get_lint_errors():
    """获取所有F821错误"""
    result = subprocess.run(["make", "lint"], capture_output=True, text=True)
    errors = []
    for line in result.stdout.split("\n"):
        if "F821 undefined name" in line:
            match = re.search(r"(.+):(\d+):\d+: F821 undefined name '(.+)'", line)
            if match:
                filepath, line_num, var_name = match.groups()
                errors.append((filepath, int(line_num), var_name))
    return errors


def read_file_lines(filepath):
    """读取文件所有行"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []


def write_file_lines(filepath, lines):
    """写入文件所有行"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def find_import_section_end(lines):
    """找到导入区域的结束位置"""
    in_docstring = False
    docstring_char = None
    import_end = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测文档字符串
        if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            in_docstring = True
            docstring_char = stripped[:3]
        elif in_docstring and docstring_char in stripped:
            in_docstring = False
            continue

        # 跳过文档字符串内容
        if in_docstring:
            continue

        # 找到导入语句
        if stripped.startswith(("import ", "from ")) and not stripped.startswith("from ."):
            import_end = max(import_end, i + 1)
        # 遇到非导入语句，非空行，非注释则停止
        elif stripped and not stripped.startswith("#") and "import" not in stripped:
            break

    return import_end


def add_missing_import(lines, var_name):
    """添加缺失的导入"""
    if var_name not in IMPORT_FIXES:
        return lines

    import_statement = IMPORT_FIXES[var_name] + "\n"

    # 检查是否已经存在该导入
    for line in lines:
        if import_statement.strip() in line.strip():
            return lines

    # 找到导入区域结束位置
    import_end = find_import_section_end(lines)

    # 插入导入语句
    lines.insert(import_end, import_statement)
    return lines


def fix_file_imports(filepath, errors_for_file):
    """修复单个文件的导入问题"""
    lines = read_file_lines(filepath)
    if not lines:
        return

    # 收集所有需要添加的导入
    vars_to_add = set()
    for _, _, var_name in errors_for_file:
        vars_to_add.add(var_name)

    # 逐个添加导入
    modified = False
    for var_name in vars_to_add:
        if var_name in IMPORT_FIXES:
            old_lines_len = len(lines)
            lines = add_missing_import(lines, var_name)
            if len(lines) > old_lines_len:
                modified = True

    # 写回文件
    if modified:
        if write_file_lines(filepath, lines):
            print(f"Fixed imports in {filepath}: {vars_to_add}")


def main():
    """主函数"""
    print("获取lint错误...")
    errors = get_lint_errors()

    if not errors:
        print("没有找到F821错误")
        return

    print(f"找到 {len(errors)} 个F821错误")

    # 按文件分组错误
    errors_by_file = {}
    for filepath, line_num, var_name in errors:
        if filepath not in errors_by_file:
            errors_by_file[filepath] = []
        errors_by_file[filepath].append((filepath, line_num, var_name))

    print(f"涉及 {len(errors_by_file)} 个文件")

    # 修复每个文件
    for filepath, file_errors in errors_by_file.items():
        if os.path.exists(filepath):
            fix_file_imports(filepath, file_errors)

    print("修复完成！")


if __name__ == "__main__":
    main()
