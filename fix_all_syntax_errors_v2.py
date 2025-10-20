#!/usr/bin/env python3
"""
批量修复Python语法错误 v2
"""

import os
import re
from pathlib import Path


def fix_bracket_errors(content):
    """修复各种括号相关的语法错误"""
    # 修复 ] = None -> = None
    content = re.sub(r"\s*]\s*=\s*None\s*$", " = None", content, flags=re.MULTILINE)

    # 修复 ]] -> ]
    content = re.sub(r"\]\]", "]", content)

    # 修复 ]] = None -> ] = None
    content = re.sub(r"\]\]\s*=\s*None", "] = None", content)

    # 修复 Optional[str = None -> Optional[str] = None
    content = re.sub(r"Optional\[(\w+)\s*=\s*(\w+)", r"Optional[\1] = \2", content)

    # 修复 Dict[str, Any = None -> Dict[str, Any] = None
    content = re.sub(r"Dict\[(\w+,\s*\w+)\s*=\s*(\w+)", r"Dict[\1] = \2", content)

    # 修复 Type[Any][T] -> Type[Any, T]
    content = re.sub(r"Type\[Any\]\[(\w+)\]", r"Type[Any, \1]", content)

    # 修复 Dict[str, Any][Type[Any]] -> Dict[Type[Any], ServiceDescriptor]
    content = re.sub(r"Dict\[str, Any\]\[(\w+)\]", r"Dict[\1", content)

    # 修复 Dict[str, Any][Type[Any], Any] -> Dict[Type[Any], Any]
    content = re.sub(r"Dict\[str, Any\]\[(\w+),\s*(\w+)\]", r"Dict[\1, \2]", content)

    return content


def fix_optional_syntax(content):
    """修复Optional类型注解语法"""
    # 修复 Optional[Callable = None -> Optional[Callable] = None
    content = re.sub(
        r"Optional\[([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\w+)", r"Optional[\1] = \2", content
    )

    # 修复 Optional[List[Type[Any]] = None -> Optional[List[Type[Any]]] = None
    content = re.sub(
        r"Optional\[List\[([^\]]+)\]\s*=\s*(\w+)", r"Optional[List[\1]] = \2", content
    )

    return content


def fix_typing_imports(content):
    """修复typing导入语句"""
    # 修复重复的Any
    content = re.sub(
        r"from typing import Any,.*?\bAny\b.*",
        lambda m: re.sub(r",\s*Any", "", m.group(0)),
        content,
    )

    # 修复 Dict[str, Any], Any -> Dict[str, Any], Any
    content = re.sub(r"Any,\s*Dict\[str, Any\],\s*Any", "Any, Dict[str, Any]", content)

    # 修复 Any, Dict[str], Any -> Any, Dict, Any
    content = re.sub(r"Any,\s*Dict\[str\],\s*Any", "Any, Dict, Any", content)

    # 修复 Any, Dict[str], Any, List[Any] -> Any, Dict, Any, List[Any]
    content = re.sub(
        r"from typing import Any, Dict\[str\], Any, List\[Any\]",
        "from typing import Any, Dict, List, Optional",
        content,
    )

    return content


def fix_missing_brackets(content):
    """修复缺失的右括号"""
    # 修复 Dict[str, Any = None
    content = re.sub(r"Dict\[str, Any\s*=\s*(\w+)", r"Dict[str, Any] = \1", content)

    return content


def fix_class_definition(content):
    """修复类定义中的语法错误"""
    # 修复 class X(BaseModel):\n    field: Optional[type = None
    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        # 检查是否是缺少右括号的类型注解
        if re.search(r"Optional\[[^\]]*=\s*\w+\s*$", line):
            # 修复类型注解
            line = re.sub(
                r"(Optional\[[^\]]*?)(\s*=\s*)(\w+)(\s*)$", r"\1]\2\3\4", line
            )
        new_lines.append(line)

    return "\n".join(new_lines)


def fix_file_syntax(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 应用各种修复
        content = fix_typing_imports(content)
        content = fix_bracket_errors(content)
        content = fix_optional_syntax(content)
        content = fix_missing_brackets(content)
        content = fix_class_definition(content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    src_dir = Path("src")

    fixed_count = 0
    total_count = 0

    # 遍历所有 Python 文件
    for py_file in src_dir.rglob("*.py"):
        total_count += 1
        if fix_file_syntax(py_file):
            fixed_count += 1

    print("\n修复完成！")
    print(f"总计检查文件: {total_count}")
    print(f"修复文件数: {fixed_count}")


if __name__ == "__main__":
    main()
