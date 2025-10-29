#!/usr/bin/env python3
"""
批量修复所有语法错误的脚本
"""

import re
import os
from pathlib import Path
from typing import List, Tuple


def fix_future_import_placement(file_path: Path) -> bool:
    """修复__future__ import放置位置"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否有__future__ import不在文件开头
        if "from __future__ import annotations" in content:
            lines = content.split("\n")

            # 找到__future__ import的位置
            future_import_line = -1
            first_non_comment_line = -1

            for i, line in enumerate(lines):
                stripped = line.strip()

                # 跳过空行和注释
                if stripped == "" or stripped.startswith("#"):
                    continue

                # 如果这是__future__ import，记录位置
                if "from __future__ import" in stripped and future_import_line == -1:
                    future_import_line = i

                # 如果这是第一个非注释非__future__行
                if first_non_comment_line == -1 and "from __future__ import" not in stripped:
                    first_non_comment_line = i
                    break

            # 如果__future__ import不在正确位置，移动它
            if future_import_line > first_non_comment_line:
                future_import = lines[future_import_line]
                lines.pop(future_import_line)
                lines.insert(first_non_comment_line, future_import)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

                return True

        return False
    except Exception:
        return False


def fix_pytest_import_in_try(file_path: Path) -> bool:
    """修复try块中的pytest导入问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复 "import pytest" 在try块中的问题
        # 查找模式：try: ... import pytest ... except:
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检查是否是try块内的import pytest
            if "import pytest" in line and i > 0:
                # 检查是否在try块内
                j = i - 1
                in_try = False
                try_indent = 0

                while j >= 0:
                    prev_line = lines[j].strip()
                    if prev_line.startswith("try:"):
                        in_try = True
                        try_indent = len(lines[j]) - len(lines[j].lstrip())
                        break
                    elif prev_line and not prev_line.startswith("#"):
                        # 遇到其他代码块，停止搜索
                        break
                    j -= 1

                if in_try:
                    # 将import pytest移动到try块之前
                    len(line) - len(line.lstrip())

                    # 移除当前行的import
                    new_lines.append(" " * try_indent + "import pytest")
                    i += 1
                    continue

            new_lines.append(line)
            i += 1

        fixed_content = "\n".join(new_lines)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

        return False
    except Exception:
        return False


def fix_duplicate_function_args(file_path: Path) -> bool:
    """修复重复的函数参数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复重复的client参数
        patterns = [
            (r"def test_db\(,\s*client,\s*client\):", "def test_db(client):"),
            (r"def test_client\(,\s*client,\s*client\):", "def test_client(client):"),
            (r"def test_env\(,\s*client,\s*client\):", "def test_env(client):"),
            (
                r"def test_intentional_failure\(client,\s*client,\s*client,\s*client,\s*client,\s*client\):",
                "def test_intentional_failure(client):",
            ),
            (
                r"def test_db_session\(test_database_engine,\s*client,\s*client\):",
                "def test_db_session(test_database_engine, client):",
            ),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception:
        return False


def fix_missing_except_block(file_path: Path) -> bool:
    """修复缺少except块的try语句"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            new_lines.append(line)

            # 检查是否是没有except的try块
            if "try:" in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                stripped_next = next_line.strip()

                # 如果下一行是import语句或其他不是异常处理的代码
                if (
                    stripped_next.startswith("import ")
                    or stripped_next.startswith("from ")
                    or (
                        stripped_next
                        and not any(x in stripped_next for x in ["except", "finally", "pass", "#"])
                    )
                ):

                    # 添加except块
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(" " * (indent + 4) + "pass")
                    new_lines.append(" " * indent + "except Exception:")
                    new_lines.append(" " * (indent + 4) + "pass")

            i += 1

        fixed_content = "\n".join(new_lines)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

        return False
    except Exception:
        return False


def fix_async_function_error(file_path: Path) -> bool:
    """修复async/await在非异步函数中的错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检查是否有await在非async函数中
            if "await " in line and "async def" not in line:
                # 找到函数定义
                j = i - 1
                while j >= 0:
                    if "def " in lines[j]:
                        # 如果函数定义没有async标记，添加它
                        if not lines[j].strip().startswith("async def"):
                            lines[j] = lines[j].replace("def ", "async def ")
                        break
                    j -= 1

            new_lines.append(line)
            i += 1

        fixed_content = "\n".join(new_lines)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

        return False
    except Exception:
        return False


def fix_missing_comma(file_path: Path) -> bool:
    """修复缺少逗号的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复常见的缺少逗号问题
        patterns = [
            (
                r"return_value\{([^\}]+)\}",
                r"return_value{\1}",
            ),  # return_value{...} -> return_value({...})
            (
                r"AsyncMock\(return_value\{",
                r"AsyncMock(return_value={",
            ),  # AsyncMock(return_value{ -> AsyncMock(return_value={
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception:
        return False


def fix_indentation_errors(file_path: Path) -> bool:
    """修复缩进错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        new_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 如果是空行或注释，保持原样
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue

            # 检查是否需要缩进
            if i > 0:
                prev_line = lines[i - 1].strip()

                # 如果上一行以:结尾，当前行需要缩进
                if (
                    prev_line.endswith(":")
                    and not line.startswith(" ")
                    and not line.startswith("\t")
                    and not stripped.startswith("except")
                    and not stripped.startswith("finally")
                ):
                    # 添加4个空格缩进
                    new_lines.append("    " + line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        fixed_content = "\n".join(new_lines)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

        return False
    except Exception:
        return False


def fix_single_file(file_path: Path) -> Tuple[bool, List[str]]:
    """修复单个文件的语法错误"""
    fixes_applied = []

    if fix_future_import_placement(file_path):
        fixes_applied.append("修复__future__ import位置")

    if fix_pytest_import_in_try(file_path):
        fixes_applied.append("修复try块中的pytest导入")

    if fix_duplicate_function_args(file_path):
        fixes_applied.append("修复重复函数参数")

    if fix_missing_except_block(file_path):
        fixes_applied.append("添加缺失的except块")

    if fix_async_function_error(file_path):
        fixes_applied.append("修复async函数标记")

    if fix_missing_comma(file_path):
        fixes_applied.append("修复缺失逗号")

    if fix_indentation_errors(file_path):
        fixes_applied.append("修复缩进错误")

    return len(fixes_applied) > 0, fixes_applied


def main():
    print("🔧 批量修复所有语法错误文件...")

    # 找到所有语法错误的文件
    syntax_error_files = [
        "tests/test_conftest_old.py",
        "tests/test_conftest_final.py",
        "tests/test_conftest_containers.py",
        "tests/test_failure_demo.py",
        "tests/test_conftest_original.py",
        "tests/test_conftest_new.py",
        "tests/unit/test_lineage_basic.py",
        "tests/unit/test_utils_complete.py",
        "tests/unit/test_monitoring_complete.py",
        "tests/unit/test_cache_complete.py",
        "tests/unit/test_data_collectors_all.py",
        "tests/unit/test_streaming_basic.py",
        "tests/unit/test_database_connections.py",
        "tests/unit/test_tasks_basic.py",
        "tests/unit/config/test_cors_config.py",
        "tests/unit/api/test_app_infrastructure.py",
        "tests/unit/utils/test_middleware_simple.py",
        "tests/unit/utils/test_i18n.py",
        "tests/unit/utils/test_error_handlers.py",
        "tests/unit/utils/test_security_simple.py",
        "tests/unit/utils/test_data_collectors_v2.py",
        "tests/unit/utils/test_metadata_manager.py",
        "tests/unit/utils/test_core_config_extended.py",
        "tests/unit/utils/test_utils_complete.py",
        "tests/unit/utils/test_realtime_simple.py",
        "tests/unit/utils/test_metrics_exporter.py",
        "tests/unit/utils/test_config_loader.py",
        "tests/unit/utils/test_config_functionality.py",
        "tests/unit/utils/test_data_quality_extended.py",
        "tests/unit/utils/test_data_quality_simple.py",
        "tests/unit/utils/test_ml_simple.py",
        "tests/unit/utils/test_linter.py",
        "tests/unit/utils/test_low_coverage_boost.py",
        "tests/unit/utils/test_observers_simple.py",
        "tests/unit/utils/test_async_handling.py",
        "tests/unit/utils/test_data_flow.py",
        "tests/unit/repositories/test_lineage_reporter.py",
        "tests/unit/middleware/test_middleware_phase4b.py",
        "tests/unit/middleware/test_cors_middleware.py",
        "tests/unit/middleware/test_api_routers_simple.py",
        "tests/unit/middleware/test_cors_middleware_simple.py",
        "tests/unit/database/test_config.py",
        "tests/unit/database/test_models_common.py",
        "tests/unit/database/test_connection.py",
        "tests/unit/database/test_db_models_basic.py",
        "tests/unit/mocks/mock_factory_phase4a_simple.py",
        "tests/unit/mocks/mock_factory_phase4a_backup.py",
        "tests/unit/collectors/test_fixtures_collector.py",
        "tests/unit/collectors/test_scores_collector.py",
        "tests/unit/core/test_config_full.py",
        "tests/unit/core/test_di_setup_improved.py",
        "tests/unit/core/test_config.py",
        "tests/unit/core/test_di_setup_real.py",
        "tests/unit/core/test_di_setup_functional.py",
        "tests/unit/services/test_services_basic.py",
        "tests/unit/services/test_prediction_algorithms.py",
        "tests/unit/tasks/test_tasks_coverage_boost.py",
        "tests/unit/tasks/test_tasks_basic.py",
        "tests/unit/security/test_key_manager.py",
    ]

    fixed_files = 0
    total_files = len(syntax_error_files)

    for file_str in syntax_error_files:
        file_path = Path(file_str)
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        was_fixed, fixes = fix_single_file(file_path)

        if was_fixed:
            fixed_files += 1
            print(f"✅ 修复 {file_path}: {', '.join(fixes)}")
        else:
            print(f"⚪ 跳过 {file_path}: 无需修复")

    print("\n📊 修复总结:")
    print(f"- 总文件数: {total_files}")
    print(f"- 已修复: {fixed_files}")
    print(f"- 成功率: {(fixed_files/total_files)*100:.1f}%")

    return fixed_files


if __name__ == "__main__":
    exit(main())
