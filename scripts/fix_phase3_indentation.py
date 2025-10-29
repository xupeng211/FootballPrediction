#!/usr/bin/env python3
"""
批量修复phase3文件的缩进错误
"""

import os
import re


def fix_phase3_file(filepath):
    """修复phase3文件的缩进问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            line_num = i + 1

            # 修复第114-116行附近的缩进问题
            if 114 <= line_num <= 116:
                if line.strip():
                    # 检查是否是过深缩进
                    if line.startswith("            "):  # 12个空格或更多
                        stripped = line.lstrip()
                        # 判断是否应该是正常缩进
                        if stripped.startswith(
                            (
                                "try:",
                                "except",
                                "def ",
                                "class ",
                                "@",
                                "if ",
                                "for ",
                                "while ",
                                "with ",
                            )
                        ):
                            fixed_lines.append("        " + stripped)  # 8个空格
                        elif stripped.startswith(("#",)):
                            fixed_lines.append("        " + stripped)  # 注释也减少缩进
                        else:
                            fixed_lines.append("    " + stripped)  # 4个空格
                    elif line.startswith("        ") and not line.strip().startswith("#"):
                        # 检查是否需要进一步减少缩进
                        stripped = line.lstrip()
                        if stripped.startswith(("try:", "except", "def ", "class ", "@")):
                            fixed_lines.append("    " + stripped)  # 4个空格
                        else:
                            fixed_lines.append(line)  # 保持8个空格
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # 写回文件
        fixed_content = "\n".join(fixed_lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        return True
    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False


def main():
    """主函数"""
    # 需要修复的phase3文件
    phase3_files = [
        "tests/unit/adapters/base_test_phase3.py",
        "tests/unit/api/data_router_test_phase3.py",
        "tests/unit/api/decorators_test_phase3.py",
        "tests/unit/utils/helpers_test_phase3.py",
        "tests/unit/utils/formatters_test_phase3.py",
        "tests/unit/utils/dict_utils_test_phase3.py",
        "tests/unit/utils/file_utils_test_phase3.py",
        "tests/unit/utils/time_utils_test_phase3.py",
        "tests/unit/cqrs/application_test_phase3.py",
        "tests/unit/cqrs/base_test_phase3.py",
        "tests/unit/cqrs/dto_test_phase3.py",
        "tests/unit/database/config_test_phase3.py",
        "tests/unit/database/definitions_test_phase3.py",
        "tests/unit/database/dependencies_test_phase3.py",
        "tests/unit/core/logging_test_phase3.py",
        "tests/unit/core/service_lifecycle_test_phase3.py",
        "tests/unit/core/auto_binding_test_phase3.py",
        "tests/unit/data/processing/football_data_cleaner_test_phase3.py",
        "tests/unit/data/quality/data_quality_monitor_test_phase3.py",
        "tests/unit/data/quality/exception_handler_test_phase3.py",
        "tests/unit/events/types_test_phase3.py",
        "tests/unit/events/base_test_phase3.py",
    ]

    print("🔧 批量修复phase3文件缩进错误...")

    fixed_count = 0
    for filepath in phase3_files:
        if os.path.exists(filepath):
            print(f"  修复: {os.path.relpath(filepath, 'tests')}")
            if fix_phase3_file(filepath):
                print("  ✅ 修复成功")
                fixed_count += 1
            else:
                print("  ❌ 修复失败")
        else:
            print(f"  ⚠️ 文件不存在: {filepath}")

    print(f"\n📊 修复总结: {fixed_count}/{len(phase3_files)} 个文件已修复")


if __name__ == "__main__":
    main()
