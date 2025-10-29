#!/usr/bin/env python3
"""
最终缩进修复 - 处理剩余的语法错误
"""

import os
import re


def fix_specific_line_indentation(filepath, line_number):
    """修复特定行的缩进问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if line_number <= len(lines):
            line = lines[line_number - 1]
            if line.strip():
                # 检查当前缩进
                len(line) - len(line.lstrip())
                stripped = line.lstrip()

                # 根据内容决定正确的缩进
                if stripped.startswith(
                    ("if ", "for ", "while ", "try:", "except", "with ", "elif", "else:")
                ):
                    # 语句块开始，需要4个空格缩进
                    correct_indent = 4
                elif stripped.startswith(("def ", "class ", "@")):
                    # 函数/类定义，需要4个空格缩进
                    correct_indent = 4
                else:
                    # 语句块内容，需要8个空格缩进
                    correct_indent = 8

                # 修复缩进
                fixed_line = " " * correct_indent + stripped + "\n"
                lines[line_number - 1] = fixed_line

                # 写回文件
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                return True
        return False
    except Exception as e:
        print(f"修复文件 {filepath} 第{line_number}行时出错: {e}")
        return False


def main():
    """主函数"""
    # 需要修复的文件和行号
    fixes = [
        # phase3文件 - 修复第116行或第123行
        ("tests/unit/adapters/base_test_phase3.py", 116),
        ("tests/unit/api/data_router_test_phase3.py", 127),
        ("tests/unit/api/decorators_test_phase3.py", 127),
        ("tests/unit/utils/helpers_test_phase3.py", 125),
        ("tests/unit/utils/formatters_test_phase3.py", 125),
        ("tests/unit/utils/dict_utils_test_phase3.py", 125),
        ("tests/unit/utils/file_utils_test_phase3.py", 125),
        ("tests/unit/utils/time_utils_test_phase3.py", 125),
        ("tests/unit/cqrs/application_test_phase3.py", 116),
        ("tests/unit/cqrs/base_test_phase3.py", 116),
        ("tests/unit/cqrs/dto_test_phase3.py", 116),
        ("tests/unit/database/config_test_phase3.py", 123),
        ("tests/unit/database/definitions_test_phase3.py", 123),
        ("tests/unit/database/dependencies_test_phase3.py", 123),
        ("tests/unit/core/logging_test_phase3.py", 123),
        ("tests/unit/core/service_lifecycle_test_phase3.py", 123),
        ("tests/unit/core/auto_binding_test_phase3.py", 123),
        ("tests/unit/data/processing/football_data_cleaner_test_phase3.py", 115),
        ("tests/unit/data/quality/data_quality_monitor_test_phase3.py", 115),
        ("tests/unit/data/quality/exception_handler_test_phase3.py", 115),
        ("tests/unit/events/types_test_phase3.py", 115),
        ("tests/unit/events/base_test_phase3.py", 115),
        # 拆分文件 - 修复函数定义问题
        ("tests/unit/domain/test_prediction_algorithms_part_2.py", 74),
        ("tests/unit/domain/test_prediction_algorithms_part_3.py", 53),
        ("tests/unit/domain/test_prediction_algorithms_part_4.py", 24),
        ("tests/unit/domain/test_prediction_algorithms_part_5.py", 35),
    ]

    print("🔧 最终语法错误修复...")

    fixed_count = 0
    for filepath, line_num in fixes:
        if os.path.exists(filepath):
            filename = os.path.relpath(filepath, "tests")
            print(f"  修复: {filename} 第{line_num}行")
            if fix_specific_line_indentation(filepath, line_num):
                print("  ✅ 修复成功")
                fixed_count += 1
            else:
                print("  ❌ 修复失败")
        else:
            print(f"  ⚠️ 文件不存在: {filepath}")

    print(f"\n📊 最终修复总结: {fixed_count}/{len(fixes)} 个文件已修复")


if __name__ == "__main__":
    main()
