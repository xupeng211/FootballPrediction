#!/usr/bin/env python3
"""
批量修复 MyPy 类型错误 v2
Batch fix MyPy type errors v2
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set

# 项目根目录
ROOT_DIR = Path(__file__).parent

# 需要进行的修复类型映射
TYPE_FIXES = {
    "callable": "typing.Callable",
    "dict": "Dict",
    "list": "List",
    "tuple": "Tuple",
    "set": "Set",
}

# 需要添加 typing 导入的文件
NEEDS_TYPING_IMPORT = set()

def run_mypy_get_errors() -> List[str]:
    """运行 MyPy 获取所有错误"""
    print("🔍 运行 MyPy 检查...")
    result = subprocess.run(
        ["mypy", "src"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR
    )

    errors = []
    for line in result.stderr.split('\n'):
        if ': error:' in line:
            errors.append(line.strip())

    print(f"   找到 {len(errors)} 个错误")
    return errors

def fix_callable_type(file_path: Path, content: str) -> str:
    """修复 callable 类型错误"""
    # 检查是否需要添加 typing.Callable
    if "callable" in content.lower() and "typing.Callable" not in content:
        if "from typing import" in content:
            # 添加到现有的导入
            content = re.sub(
                r"(from typing import .+)",
                r"\1, Callable",
                content
            )
        else:
            # 添加新的导入
            content = "from typing import Callable\n" + content

    # 替换 callable 为 Callable
    content = re.sub(r"\bcallable\b", "Callable", content)

    NEEDS_TYPING_IMPORT.add(file_path)
    return content

def fix_var_annotated(file_path: Path, content: str, error_line: str) -> str:
    """修复变量类型注解错误"""
    # 提取变量名
    match = re.search(r'Need type annotation for "(\w+)"', error_line)
    if not match:
        return content

    var_name = match.group(1)

    # 在文件中查找该变量的定义
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if f"{var_name} = " in line:
            # 尝试推断类型
            if "= {}" in line or "= []" in line:
                # 空字典或列表
                if "dict" in line.lower() or "{}" in line:
                    type_hint = "Dict[str, Any]"
                elif "list" in line.lower() or "[]" in line:
                    type_hint = "List[Any]"
                else:
                    type_hint = "Any"
            else:
                # 默认使用 Any
                type_hint = "Any"

            # 在变量定义前添加类型注解
            lines[i] = f"{var_name}: {type_hint} = " + line.split(" = ", 1)[1]
            break

    content = '\n'.join(lines)
    return content

def fix_missing_logger(file_path: Path, content: str) -> str:
    """修复缺失的 logger 定义"""
    if "Name \"logger\" is not defined" in content and "import logging" not in content:
        content = "import logging\n" + content

    # 在类或模块顶部添加 logger
    lines = content.split('\n')
    logger_added = False

    for i, line in enumerate(lines):
        if line.startswith('class ') and not logger_added:
            # 在类的第一个方法前添加 logger
            j = i + 1
            while j < len(lines) and (lines[j].startswith('"""') or lines[j].startswith('"""') or not lines[j].strip()):
                j += 1
            if j < len(lines) and 'def ' in lines[j]:
                lines.insert(j, "    logger = logging.getLogger(__name__)\n")
                logger_added = True
        elif not logger_added and (line.startswith('def ') or line.startswith('async def ')):
            # 在模块级函数前添加 logger
            lines.insert(i, "logger = logging.getLogger(__name__)\n")
            logger_added = True

    return '\n'.join(lines)

def fix_sqlalchemy_error_imports(file_path: Path, content: str) -> str:
    """修复 SQLAlchemy 错误类型导入"""
    if "SQLAlchemyError" in content or "DatabaseError" in content:
        if "from sqlalchemy" in content and "exc" not in content:
            content = re.sub(
                r"(from sqlalchemy import .+)",
                r"\1, exc",
                content
            )
        elif "from sqlalchemy" not in content:
            content = "from sqlalchemy import exc\n" + content

        # 替换错误类型
        content = content.replace("SQLAlchemyError", "exc.SQLAlchemyError")
        content = content.replace("DatabaseError", "exc.DatabaseError")

    return content

def fix_none_callable(file_path: Path, content: str) -> str:
    """修复 None not callable 错误"""
    lines = content.split('\n')

    for i, line in enumerate(lines):
        if "None" in line and "callable" in line.lower():
            # 查找可能的 None 赋值给 callable 变量的情况
            if re.search(r'\w+\s*=\s*None\s*$', line):
                var_name = line.split('=')[0].strip()
                # 检查该变量是否应该是 callable
                if 'callback' in var_name.lower() or 'handler' in var_name.lower():
                    lines[i] = line.replace('None', 'lambda: None')

    return '\n'.join(lines)

def process_errors(errors: List[str]):
    """处理所有错误"""
    fixed_files = set()

    for error in errors:
        # 解析错误信息
        parts = error.split(':', 3)
        if len(parts) < 4:
            continue

        file_path = Path(parts[0])
        line_num = int(parts[1])
        error_type = parts[2].strip()
        error_msg = parts[3].strip()

        if not file_path.exists():
            continue

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 根据错误类型进行修复
        if 'Function "builtins.callable" is not valid as a type' in error_msg:
            content = fix_callable_type(file_path, content)
            print(f"   ✓ 修复 callable 类型错误: {file_path}")

        elif 'Need type annotation for' in error_msg:
            content = fix_var_annotated(file_path, content, error_msg)
            print(f"   ✓ 修复变量类型注解: {file_path}")

        elif 'Name "logger" is not defined' in error_msg:
            content = fix_missing_logger(file_path, content)
            print(f"   ✓ 修复 logger 导入: {file_path}")

        elif 'SQLAlchemyError" is not defined' in error_msg or 'DatabaseError" is not defined' in error_msg:
            content = fix_sqlalchemy_error_imports(file_path, content)
            print(f"   ✓ 修复 SQLAlchemy 错误导入: {file_path}")

        elif '"None" not callable' in error_msg:
            content = fix_none_callable(file_path, content)
            print(f"   ✓ 修复 None callable 错误: {file_path}")

        # 如果内容有修改，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_files.add(file_path)

    return fixed_files

def main():
    """主函数"""
    print("🚀 开始批量修复 MyPy 类型错误 v2\n")

    # 获取所有错误
    errors = run_mypy_get_errors()

    if not errors:
        print("✅ 没有 MyPy 错误需要修复！")
        return

    # 处理错误
    print("\n🔧 开始修复错误...")
    fixed_files = process_errors(errors)

    print(f"\n✅ 修复完成！共修复了 {len(fixed_files)} 个文件")

    # 再次运行 MyPy 检查
    print("\n🔍 再次运行 MyPy 检查...")
    result = subprocess.run(
        ["mypy", "src"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR
    )

    remaining_errors = [line for line in result.stderr.split('\n') if ': error:' in line]

    if remaining_errors:
        print(f"⚠️  还有 {len(remaining_errors)} 个错误需要手动修复：")
        for error in remaining_errors[:10]:
            print(f"   • {error}")
        if len(remaining_errors) > 10:
            print(f"   ... 还有 {len(remaining_errors) - 10} 个错误")
    else:
        print("🎉 所有错误都已修复！")

if __name__ == "__main__":
    main()