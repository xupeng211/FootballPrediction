#!/usr/bin/env python3
"""
最终修复所有语法错误
"""

import os
from pathlib import Path
import re


def fix_imports(content: str) -> str:
    """修复导入语句"""
    # 修复重复的 Any
    content = re.sub(
        r"from typing import Any,.*?, Any", "from typing import Any", content
    )
    content = re.sub(r"from typing import Any,  Any", "from typing import Any", content)

    # 修复重复的 Dict
    content = re.sub(
        r"from typing import.*Dict\[str, Any\], Any",
        "from typing import Any, Dict",
        content,
    )

    # 修复语法错误
    content = re.sub(
        r"from typing import Any,  Dict\[str, Any\]",
        "from typing import Any, Dict",
        content,
    )
    content = re.sub(
        r"from typing import Any,  Any,", "from typing import Any,", content
    )
    content = re.sub(
        r"from typing import Any,  Any$", "from typing import Any", content
    )

    # 修复常见的类型注解错误
    content = re.sub(r"Dict\[str, Any\]\[str, Any\]", "Dict[str, Any]", content)
    content = re.sub(r"dict\[str, Any\]\[str, Any\]", "dict[str, Any]", content)
    content = re.sub(r"List\[Any\]\[str\]", "List[str]", content)
    content = re.sub(
        r"List\[Any\]\[Dict\[str, Any\]\]", "List[Dict[str, Any]]", content
    )
    content = re.sub(
        r"Dict\[str, Any\]\[str, ServiceInfo\]", "Dict[str, ServiceInfo]", content
    )
    content = re.sub(
        r"Dict\[str, Any\]\[str, ServiceConfig\]", "Dict[str, ServiceConfig]", content
    )
    content = re.sub(
        r"Dict\[Type\[Any\], List\[Any\]\[Type\[Any\]\]\]",
        "Dict[Type[Any], List[Type[Any]]]",
        content,
    )
    content = re.sub(r"List\[Any\]\[BindingRule\]", "List[BindingRule]", content)
    content = re.sub(r"List\[Any\]\[str\]", "List[str]", content)
    content = re.sub(r"List\[Any\]\[tuple\]", "List[tuple]", content)

    return content


def main():
    print("🔧 最终修复所有语法错误")

    # 遍历所有 Python 文件
    for py_file in Path("src").glob("**/*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            fixed = fix_imports(content)

            if fixed != content:
                py_file.write_text(fixed, encoding="utf-8")
                print(f"✓ 修复 {py_file.relative_to(Path.cwd())}")
        except Exception as e:
            print(f"✗ 错误 {py_file}: {e}")

    print("\n✅ 修复完成！")


if __name__ == "__main__":
    main()
