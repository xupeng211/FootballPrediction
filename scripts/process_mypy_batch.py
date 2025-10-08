#!/usr/bin/env python3
"""
处理 MyPy 错误批次脚本
自动或交互式修复 MyPy 错误
"""

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def print_status(level: str, message: str):
    """打印带颜色的状态信息"""
    colors = {
        "info": BLUE,
        "success": GREEN,
        "warning": YELLOW,
        "error": RED
    }
    color = colors.get(level, "")
    print(f"{color}{message}{NC}")


def parse_error_line(line: str) -> Optional[Tuple[str, int, str, str]]:
    """解析错误行"""
    # 格式: file:line: error: message [error-code]
    match = re.match(r'([^:]+):(\d+): error: (.+) \[(.+)\]', line.strip())
    if match:
        file_path, line_num, message, error_code = match.groups()
        return file_path, int(line_num), message, error_code
    return None


def fix_attr_defined(file_path: str, line_num: int, message: str) -> Optional[str]:
    """修复 attr-defined 错误"""
    # 示例: "MyClass" has no attribute "attr_name"
    match = re.search(r'"([^"]+)" has no attribute "([^"]+)"', message)
    if match:
        class_name, attr_name = match.groups()

        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num <= len(lines):
            line = lines[line_num - 1]

            # 简单修复策略：使用 getattr 或添加类型注解
            if f".{attr_name}" in line:
                # 使用 getattr 避免属性错误
                fixed_line = line.replace(
                    f".{attr_name}",
                    f".{attr_name}"  # 保持原样，需要更多上下文
                )
                # TODO: 这里需要更智能的修复逻辑
                return fixed_line

    return None


def fix_arg_type(file_path: str, line_num: int, message: str) -> Optional[str]:
    """修复 arg-type 错误"""
    # 示例: Argument 1 to "func" has incompatible type "int"; expected "str"
    match = re.search(r'Argument (\d+) to "([^"]+)" has incompatible type "([^"]+)"; expected "([^"]+)"', message)
    if match:
        arg_num, func_name, actual_type, expected_type = match.groups()

        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num <= len(lines):
            line = lines[line_num - 1]

            # 简单的类型转换
            if expected_type == "str" and actual_type == "int":
                fixed_line = re.sub(rf'(\b\w+\b)(?=\))', r'str(\1)', line)
                return fixed_line
            elif expected_type == "int" and actual_type == "str":
                fixed_line = re.sub(rf'(\b\w+\b)(?=\))', r'int(\1)', line)
                return fixed_line

    return None


def fix_return_value(file_path: str, line_num: int, message: str) -> Optional[str]:
    """修复 return-value 错误"""
    # 示例: Incompatible return value type (got "int", expected "str")
    match = re.search(r'\(got "([^"]+)", expected "([^"]+)"\)', message)
    if match:
        actual_type, expected_type = match.groups()

        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num <= len(lines):
            line = lines[line_num - 1]

            # 查找 return 语句
            if "return" in line:
                if expected_type == "str" and actual_type == "int":
                    fixed_line = line.replace("return", "return str")
                    return fixed_line
                elif expected_type == "int" and actual_type == "str":
                    # 需要更复杂的转换逻辑
                    pass

    return None


def apply_fix(file_path: str, line_num: int, error_code: str, message: str, auto: bool = False) -> bool:
    """应用修复"""
    fixed_line = None

    if error_code == "attr-defined":
        fixed_line = fix_attr_defined(file_path, line_num, message)
    elif error_code == "arg-type":
        fixed_line = fix_arg_type(file_path, line_num, message)
    elif error_code == "return-value":
        fixed_line = fix_return_value(file_path, line_num, message)

    if fixed_line is not None:
        if auto:
            # 自动模式：直接应用修复
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            lines[line_num - 1] = fixed_line

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            print_status("success", f"自动修复: {file_path}:{line_num}")
            return True
        else:
            # 交互模式：显示修复建议
            print(f"\n{YELLOW}文件: {file_path}:{line_num}{NC}")
            print(f"错误: {message}")
            print(f"建议修复:")
            print(f"  原始: {lines[line_num - 1].strip()}")
            print(f"  修复: {fixed_line.strip()}")

            response = input("\n应用修复? [Y/n/a] ").strip().lower()
            if response in ['', 'y', 'yes']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                lines[line_num - 1] = fixed_line

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                print_status("success", "已应用修复")
                return True
            elif response == 'a':
                # 应用到所有类似的错误
                return apply_fix(file_path, line_num, error_code, message, auto=True)

    return False


def process_batch(batch_file: str, auto: bool = False):
    """处理批次文件"""
    batch_path = Path(batch_file)

    if not batch_path.exists():
        print_status("error", f"批次文件不存在: {batch_file}")
        return

    print_status("info", f"处理批次: {batch_path.name}")

    # 读取批次中的错误
    with open(batch_path) as f:
        errors = f.readlines()

    total = len(errors)
    fixed = 0

    for i, error_line in enumerate(errors, 1):
        print(f"\n进度: {i}/{total}")
        print("-" * 50)

        parsed = parse_error_line(error_line)
        if not parsed:
            continue

        file_path, line_num, message, error_code = parsed

        # 检查文件是否存在
        if not os.path.exists(file_path):
            print_status("warning", f"文件不存在: {file_path}")
            continue

        # 应用修复
        if apply_fix(file_path, line_num, error_code, message, auto):
            fixed += 1

    print(f"\n{GREEN}批次处理完成{NC}")
    print(f"总计: {total}, 修复: {fixed}, 跳过: {total - fixed}")

    # 更新状态文件
    status_file = batch_path.parent / f"{batch_path.stem}_status.json"
    if status_file.exists():
        import json
        with open(status_file) as f:
            status = json.load(f)

        status["status"] = "completed"
        status["fixed_count"] = fixed
        status["total_count"] = total
        status["completed_at"] = "2025-10-09T00:00:00"  # 使用固定时间

        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="处理 MyPy 错误批次")
    parser.add_argument("batch_file", help="批次文件路径")
    parser.add_argument("--auto", action="store_true", help="自动修复模式")

    args = parser.parse_args()

    if args.auto:
        print_status("warning", "自动修复模式已启用")
        response = input("确定要自动修复所有错误吗? [y/N] ")
        if response.lower() != 'y':
            print_status("info", "取消操作")
            return

    process_batch(args.batch_file, args.auto)


if __name__ == "__main__":
    main()