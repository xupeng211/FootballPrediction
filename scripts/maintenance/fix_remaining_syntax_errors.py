#!/usr/bin/env python3
"""
修复剩余语法错误的精确脚本
"""

import re
from pathlib import Path


def fix_broken_try_except_blocks(file_path: Path) -> bool:
    """修复损坏的try-except块结构"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 移除无效的except块
        # 模式: 空行 + try: + 空行 + except ImportError:
        patterns = [
            r"\n\s*try:\s*\n\s*except ImportError:\s*\n\s*pass\s*\n",
            r"\n\s*try:\s*\n\s*except Exception:\s*\n\s*pass\s*\n",
        ]

        for pattern in patterns:
            content = re.sub(pattern, "\n", content)

        # 修复孤立的except ImportError:
        content = re.sub(r"\n\s*except ImportError:\s*\n\s*pass\s*\n", "\n", content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
            except Exception:
        return False


def fix_extra_indented_imports(file_path: Path) -> bool:
    """修复过度缩进的import语句"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        original_lines = lines[:]
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 如果是import语句但过度缩进（超过4个空格）
            if (
                (stripped.startswith("import ") or stripped.startswith("from "))
                and line.startswith("        ")
                and not line.strip().startswith("#")
            ):
                # 将缩进减少到合适的位置
                fixed_line = "    " + stripped + "\n"
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)

        if fixed_lines != original_lines:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(fixed_lines)
            return True

        return False
            except Exception:
        return False


def fix_unterminated_string(file_path: Path) -> bool:
    """修复未终止的三引号字符串"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 查找未终止的三引号字符串并修复
        lines = content.split("\n")
        fixed_lines = []
        in_triple_quote = False
        triple_quote_start = 0

        for i, line in enumerate(lines):
            if '"""' in line and not in_triple_quote:
                # 开始三引号字符串
                if line.count('"""') == 1:  # 只有一个开始引号
                    in_triple_quote = True
                    triple_quote_start = i
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            elif in_triple_quote:
                fixed_lines.append(line)
                # 检查是否结束
                if '"""' in line and i > triple_quote_start:
                    in_triple_quote = False
            else:
                fixed_lines.append(line)

        # 如果在三引号字符串中结束文件，添加结束引号
        if in_triple_quote:
            fixed_lines.append('"""')

        fixed_content = "\n".join(fixed_lines)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

        return False
            except Exception:
        return False


def main():
    print("🔧 精确修复剩余语法错误...")

    # 需要修复的文件列表
    files_to_fix = [
        "tests/unit/utils/test_error_handlers.py",
        "tests/unit/utils/test_data_collectors_v2.py",
        "tests/unit/utils/test_metadata_manager.py",
        "tests/unit/utils/test_core_config_extended.py",
        "tests/unit/utils/test_utils_complete.py",
        "tests/unit/utils/test_metrics_exporter.py",
        "tests/unit/utils/test_data_quality_extended.py",
        "tests/unit/utils/test_collectors_all.py",
        "tests/unit/repositories/test_lineage_reporter.py",
        "tests/unit/database/test_models_common.py",
        "tests/unit/mocks/mock_factory_phase4a_backup.py",
        "tests/unit/tasks/test_tasks_coverage_boost.py",
    ]

    fixed_count = 0

    for file_str in files_to_fix:
        file_path = Path(file_str)
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        was_fixed = False

        if fix_broken_try_except_blocks(file_path):
            was_fixed = True
            print(f"✅ 修复try-except块: {file_path}")

        if fix_extra_indented_imports(file_path):
            was_fixed = True
            print(f"✅ 修复缩进: {file_path}")

        if fix_unterminated_string(file_path):
            was_fixed = True
            print(f"✅ 修复字符串: {file_path}")

        if was_fixed:
            fixed_count += 1
        else:
            print(f"⚪ 跳过 {file_path}")

    print("\n📊 修复总结:")
    print(f"- 已修复: {fixed_count} 个文件")

    return fixed_count


if __name__ == "__main__":
    exit(main())
