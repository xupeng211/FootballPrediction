#!/usr/bin/env python3
"""
批量修复MyPy类型注解中的括号不匹配错误
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def find_and_fix_bracket_errors(file_path: Path) -> Tuple[int, List[str]]:
    """查找并修复括号不匹配错误"""
    errors = []
    fixes_count = 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        modified = False
        new_lines = []

        for i, line in enumerate(lines, 1):
            # 修复模式: Dict[str, Type] -> Dict[str, Type]]
            # 匹配: Dict[str, Union[str, Decimal]]  # 缺少右括号
            pattern1 = r"(\w+\[.*?)\](?=\s*(?:#|$|:|->|=))"
            if re.search(pattern1, line):
                # 检查是否缺少右括号
                open_brackets = line.count("[")
                close_brackets = line.count("]")

                # 特殊处理函数参数和返回值
                if ":" in line and "->" in line:
                    # 函数定义行
                    parts = line.split("->")
                    if len(parts) > 1:
                        param_part = parts[0]
                        return_part = parts[1]

                        # 修复参数部分
                        if param_part.count("[") > param_part.count("]"):
                            # 找到最后一个未闭合的括号位置
                            param_part = re.sub(
                                r"(\w+\[.*?)\s*($|:|,)", r"\1]\2", param_part
                            )
                            line = f"{param_part}->{return_part}"
                            modified = True
                            fixes_count += 1
                            errors.append(f"Line {i}: Fixed parameter type annotation")
                else:
                    # 普通行
                    if (
                        open_brackets > close_brackets
                        and open_brackets - close_brackets == 1
                    ):
                        # 需要添加一个右括号
                        line = re.sub(
                            r"(\w+\[.*?)\](?=\s*(?:#|$|:|->|=))", r"\1]]", line
                        )
                        modified = True
                        fixes_count += 1
                        errors.append(f"Line {i}: Fixed type annotation")

            # 另一种模式: Dict[str, Type] = None,  # 确保有正确的括号
            if "= None" in line or "= None," in line:
                # 检查类型注解
                before_equal = line.split("=")[0] if "=" in line else line
                if "[" in before_equal and "]" not in before_equal:
                    # 添加缺失的右括号
                    line = re.sub(r"(\w+\[.*?)\s*(?==)", r"\1] ", line)
                    modified = True
                    fixes_count += 1
                    errors.append(f"Line {i}: Fixed Optional type annotation")

            new_lines.append(line)

        # 写回文件
        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
            print(f"Fixed {fixes_count} errors in {file_path}")
            for error in errors:
                print(f"  - {error}")

        return fixes_count, errors

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, []


def main():
    """主函数"""
    src_dir = Path("src")

    total_fixes = 0
    files_processed = 0

    # 查找所有Python文件
    for py_file in src_dir.rglob("*.py"):
        if "migrations" in str(py_file) or "stubs" in str(py_file):
            continue

        fixes, errors = find_and_fix_bracket_errors(py_file)
        if fixes > 0:
            total_fixes += fixes
            files_processed += 1

    print("\n总计:")
    print(f"  修复文件数: {files_processed}")
    print(f"  修复错误数: {total_fixes}")


if __name__ == "__main__":
    main()
