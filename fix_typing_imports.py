#!/usr/bin/env python3
"""
系统性修复typing导入语法错误
"""

import os
import re
from pathlib import Path


def fix_typing_imports_line(line):
    """修复单行typing导入"""
    # 基础修复规则
    fixes = [
        # 重复的类型
        (
            r"\bAny,\s*[^,]*Any\b",
            lambda m: m.group(0).replace(
                re.search(r",\s*[^,]*Any\b", m.group(0)).group(), ""
            ),
        ),
        # 错误的Dict语法
        (r"Dict\[str\]", "Dict"),
        (r"Dict\[str,\s*Any\]", "Dict"),
        # 错误的List语法
        (r"List\[Any\]", "List"),
        # 错误的Union语法
        (r"Union,\s*Any,\s*Dict", "Union, Any, Dict"),
        (r"Union,\s*Any,\s*Dict,\s*Any,\s*List", "Union, Any, Dict, List"),
        # 修复重复的Union
        (r"Union,\s*Union", "Union"),
        # 修复重复的Optional
        (r"Optional,\s*Optional", "Optional"),
        # 修复其他常见错误
        (r"Any,\s*Dict\[str\],\s*Any", "Any, Dict, Any"),
        (r"Any,\s*Dict\[str,\s*Any\],\s*Any", "Any, Dict, Any"),
        (r"Dict\[str\],\s*Any", "Dict, Any"),
        (r"Dict\[str,\s*Any\],\s*Any", "Dict, Any"),
        (r"Dict\[str,\s*Any\],\s*Optional", "Dict, Optional"),
        (r"List\[Any\],\s*Optional", "List, Optional"),
        (r"Dict\[str,\s*Any\],\s*Any,\s*List\[Any\]", "Dict, Any, List"),
        (r"Any,\s*Dict\[str,\s*Any\],\s*List\[Any\]", "Any, Dict, List"),
        (r"Any,\s*Dict\[str,\s*Any\],\s*Any,\s*List\[Any\]", "Any, Dict, Any, List"),
        (
            r"Any,\s*Dict\[str,\s*Any\],\s*Any,\s*List\[Any\],\s*Optional",
            "Any, Dict, Any, List, Optional",
        ),
        (r"Dict\[str\],\s*Any,\s*Optional", "Dict, Any, Optional"),
        # 修复复杂的导入
        (
            r"from typing import Union, Any, Dict\[str\], Any, Optional",
            "from typing import Union, Any, Dict, Optional",
        ),
        (
            r"from typing import Union, Any, Dict\[str,\s*Any\], Any, Optional",
            "from typing import Union, Any, Dict, Optional",
        ),
        (
            r"from typing import Union, Any, Dict\[str,\s*Any\], Any, List\[Any\], Optional",
            "from typing import Union, Any, Dict, List, Optional",
        ),
    ]

    for pattern, replacement in fixes:
        if callable(replacement):
            line = pattern.sub(replacement, line)
        else:
            line = re.sub(pattern, replacement, line)

    # 清理多余的逗号和空格
    line = re.sub(r",\s*,", ", ", line)
    line = re.sub(r"\s*,\s*$", "", line)

    return line


def fix_file_typing_imports(file_path):
    """修复单个文件的typing导入"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        new_lines = []

        in_typing_import = False
        for line in lines:
            if "from typing import" in line:
                in_typing_import = True
                fixed_line = fix_typing_imports_line(line)
                new_lines.append(fixed_line)
            elif in_typing_import and line.strip().startswith("("):
                # 多行导入，继续处理
                fixed_line = fix_typing_imports_line(line)
                new_lines.append(fixed_line)
            elif in_typing_import and ")" in line:
                # 结束多行导入
                fixed_line = fix_typing_imports_line(line)
                new_lines.append(fixed_line)
                in_typing_import = False
            else:
                new_lines.append(line)

        fixed_content = "\n".join(new_lines)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✓ Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    src_dir = Path("src")

    # 首先修复最关键的文件
    critical_files = [
        "src/utils/__init__.py",
        "src/utils/dict_utils.py",
        "src/utils/file_utils.py",
        "src/utils/helpers.py",
        "src/utils/validators.py",
        "src/utils/response.py",
        "src/utils/string_utils.py",
        "src/utils/data_validator.py",
        "src/utils/config_loader.py",
        "src/api/predictions/models.py",
        "src/api/__init__.py",
        "src/core/__init__.py",
        "src/database/models/__init__.py",
    ]

    print("修复关键文件...")
    fixed_count = 0
    for file_path in critical_files:
        if Path(file_path).exists():
            if fix_file_typing_imports(file_path):
                fixed_count += 1

    print(f"\n关键文件修复完成，修复了 {fixed_count} 个文件")

    # 然后修复所有文件
    print("\n开始修复所有文件...")
    total_fixed = 0
    total_files = 0

    for py_file in src_dir.rglob("*.py"):
        total_files += 1
        if fix_file_typing_imports(py_file):
            total_fixed += 1

    print("\n修复完成！")
    print(f"总计检查文件: {total_files}")
    print(f"修复文件数: {total_fixed}")


if __name__ == "__main__":
    main()
