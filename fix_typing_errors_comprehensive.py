#!/usr/bin/env python3
"""
系统性修复typing语法错误脚本
修复常见的typing导入和类型注解错误
"""

import os
import re
from pathlib import Path


def fix_typing_imports(content):
    """修复typing导入语句"""
    # 修复常见的typing导入错误
    patterns = [
        # Dict相关错误
        (
            r"from typing import.*?Dict\[str\], Any",
            lambda m: m.group(0).replace("Dict[str], Any", "Dict, Any"),
        ),
        (
            r"from typing import.*?Dict\[str,\s*Any\], Any",
            lambda m: m.group(0).replace("Dict[str, Any], Any", "Dict, Any"),
        ),
        (
            r"from typing import.*?Dict\[str\]",
            lambda m: m.group(0).replace("Dict[str]", "Dict"),
        ),
        (
            r"from typing import.*?Dict\[str,\s*Any\]",
            lambda m: m.group(0).replace("Dict[str, Any]", "Dict"),
        ),
        # List相关错误
        (
            r"from typing import.*?List\[Any\]",
            lambda m: m.group(0).replace("List[Any]", "List"),
        ),
        (
            r"from typing import.*?List\[Any\], Optional",
            lambda m: m.group(0).replace("List[Any], Optional", "List, Optional"),
        ),
        # 组合错误
        (
            r"from typing import.*?Any,\s*Dict\[str\],\s*Any",
            lambda m: m.group(0).replace("Any, Dict[str], Any", "Any, Dict, Any"),
        ),
        (
            r"from typing import.*?Any,\s*Dict\[str,\s*Any\],\s*Any",
            lambda m: m.group(0).replace("Any, Dict[str, Any], Any", "Any, Dict, Any"),
        ),
        (
            r"from typing import.*?Dict\[str\],\s*Any,\s*Optional",
            lambda m: m.group(0).replace(
                "Dict[str], Any, Optional", "Dict, Any, Optional"
            ),
        ),
        (
            r"from typing import.*?Dict\[str,\s*Any\],\s*Optional",
            lambda m: m.group(0).replace("Dict[str, Any], Optional", "Dict, Optional"),
        ),
        (
            r"from typing import.*?Any,\s*Dict\[str,\s*Any\],\s*List\[Any\]",
            lambda m: m.group(0).replace(
                "Any, Dict[str, Any], List[Any]", "Any, Dict, List"
            ),
        ),
        (
            r"from typing import.*?Any,\s*Dict\[str,\s*Any\],\s*Any,\s*List\[Any\]",
            lambda m: m.group(0).replace(
                "Any, Dict[str, Any], Any, List[Any]", "Any, Dict, Any, List"
            ),
        ),
        (
            r"from typing import.*?Union,\s*Any,\s*Dict\[str,\s*Any\]",
            lambda m: m.group(0).replace(
                "Union, Any, Dict[str, Any]", "Union, Any, Dict"
            ),
        ),
        # 重复的类型
        (
            r"from typing import.*?\bAny,\s*[^,]*Any\b",
            lambda m: re.sub(r",\s*[^,]*Any\b", "", m.group(0)),
        ),
        (
            r"from typing import.*?\bDict\[str\],\s*[^,]*Dict\b",
            lambda m: re.sub(r",\s*[^,]*Dict\b", "", m.group(0)),
        ),
        (
            r"from typing import.*?\bList\[Any\],\s*[^,]*List\b",
            lambda m: re.sub(r",\s*[^,]*List\b", "", m.group(0)),
        ),
        (
            r"from typing import.*?\bOptional,\s*[^,]*Optional\b",
            lambda m: re.sub(r",\s*[^,]*Optional\b", "", m.group(0)),
        ),
        (
            r"from typing import.*?\bUnion,\s*[^,]*Union\b",
            lambda m: re.sub(r",\s*[^,]*Union\b", "", m.group(0)),
        ),
    ]

    for pattern, replacement in patterns:
        content = pattern.sub(replacement, content, flags=re.MULTILINE | re.DOTALL)

    # 清理多余的逗号和空格
    content = re.sub(r",\s*,", ", ", content)
    content = re.sub(r"\s*,\s*$", "", content)
    content = re.sub(r"\s*,\s*\)", ")", content)

    return content


def fix_type_annotations(content):
    """修复类型注解中的语法错误"""
    # 修复函数参数类型注解
    content = re.sub(
        r"(\w+):\s*Optional\[Dict\[str,\s*Any\]\s*=\s*None",
        r"\1: Optional[Dict[str, Any]] = None",
        content,
    )
    content = re.sub(
        r"(\w+):\s*Dict\[str,\s*Any\]\s*=\s*None", r"\1: Dict[str, Any] = None", content
    )
    content = re.sub(
        r"(\w+):\s*List\[Any\]\s*=\s*None", r"\1: List[Any] = None", content
    )
    content = re.sub(
        r"(\w+):\s*Optional\[List\[Any\]\]\s*=\s*None",
        r"\1: Optional[List[Any]] = None",
        content,
    )

    # 修复类属性类型注解
    content = re.sub(
        r"(\w+):\s*Optional\[Dict\[str,\s*Any\]\s*$",
        r"\1: Optional[Dict[str, Any]]",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r"(\w+):\s*Dict\[str,\s*Any\]\s*$",
        r"\1: Dict[str, Any]",
        content,
        flags=re.MULTILINE,
    )

    # 修复泛型类型注解
    content = re.sub(r"Type\[Any\]\[(\w+)\]", r"Type[Any, \1]", content)
    content = re.sub(r"Dict\[str,\s*Any\]\[(\w+)\]", r"Dict[\1", content)
    content = re.sub(r"Dict\[str,\s*Any\]\[(\w+),\s*(\w+)\]", r"Dict[\1, \2]", content)

    # 修复Optional类型注解
    content = re.sub(r"Optional\[(\w+)\s*=\s*(\w+)\]", r"Optional[\1] = \2", content)

    return content


def fix_bracket_mismatches(content):
    """修复括号不匹配的问题"""
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        # 修复常见的括号不匹配
        if "Optional[Dict[str, Any" in line and not line.endswith("]"):
            line = line.replace("Optional[Dict[str, Any", "Optional[Dict[str, Any]]")
        elif "Dict[str, Any" in line and not line.endswith("]"):
            line = line.replace("Dict[str, Any", "Dict[str, Any]")
        elif "List[Any" in line and not line.endswith("]"):
            line = line.replace("List[Any", "List[Any]")
        elif "Union[str, Path" in line and not line.endswith("]"):
            line = line.replace("Union[str, Path", "Union[str, Path]")

        new_lines.append(line)

    return "\n".join(new_lines)


def fix_file(file_path):
    """修复单个文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 应用所有修复
        content = fix_typing_imports(content)
        content = fix_type_annotations(content)
        content = fix_bracket_mismatches(content)

        # 写回文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    # 定义需要优先修复的核心模块
    core_modules = [
        "src/core/__init__.py",
        "src/core/config.py",
        "src/core/exceptions.py",
        "src/core/di.py",
        "src/core/di_setup.py",
        "src/core/auto_binding.py",
        "src/core/logging.py",
        "src/utils/__init__.py",
        "src/utils/dict_utils.py",
        "src/utils/helpers.py",
        "src/utils/validators.py",
        "src/utils/response.py",
        "src/utils/string_utils.py",
        "src/utils/data_validator.py",
        "src/utils/config_loader.py",
        "src/utils/file_utils.py",
        "src/adapters/__init__.py",
        "src/adapters/base.py",
        "src/adapters/factory.py",
        "src/database/__init__.py",
        "src/database/models/__init__.py",
        "src/database/session.py",
        "src/api/__init__.py",
        "src/api/app.py",
        "src/api/schemas.py",
        "src/api/predictions/models.py",
    ]

    print("开始修复核心模块...")
    fixed_count = 0
    total_count = 0

    # 先修复核心模块
    for module_path in core_modules:
        if Path(module_path).exists():
            total_count += 1
            if fix_file(module_path):
                print(f"✓ Fixed: {module_path}")
                fixed_count += 1

    print(f"\n核心模块修复完成: {fixed_count}/{total_count}")

    # 再修复所有Python文件
    print("\n开始修复所有Python文件...")
    all_fixed = 0
    all_total = 0

    for py_file in Path("src").rglob("*.py"):
        all_total += 1
        if fix_file(py_file):
            all_fixed += 1

    print(f"\n总计修复: {all_fixed}/{all_total} 个文件")


if __name__ == "__main__":
    main()
