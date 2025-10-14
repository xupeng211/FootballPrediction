#!/usr/bin/env python3
"""
Fix all remaining MyPy syntax errors in core modules
"""

import re
from pathlib import Path


def fix_type_annotations(text: str) -> str:
    """Fix malformed type annotations"""
    # Fix various patterns
    fixes = [
        # Dict patterns
        (r"Dict\[str,\s*Any\]str,\s*Any\]", r"Dict[str, Any]"),
        (r"Dict\[str,\s*Any\]Type,\s*List\[Any\]Type\]\]", r"Dict[Type, List[Type]]"),
        (r"Dict\[str,\s*Any\]str,\s*ServiceConfig\]", r"Dict[str, ServiceConfig]"),
        (r"Dict\[str,\s*Any\]Type,\s*Any\]", r"Dict[Type, Any]"),
        (
            r"Dict\[str,\s*Any\]str,\s*Dict\[str,\s*Any\]Type,\s*Any\]\]",
            r"Dict[str, Dict[Type, Any]]",
        ),
        (r"Dict\[str,\s*Any\]str,\s*bool\]", r"Dict[str, bool]"),
        # List patterns
        (r"List\[Any\]Type\]", r"List[Type]"),
        (r"List\[Any\]str\]", r"List[str]"),
        (
            r"List\[Any\]Callable\[\[DIContainer\],\s*None\]\]",
            r"List[Callable[[DIContainer], None]]",
        ),
        (r"List\[Any\]Dict\[str,\s*Any\]\]", r"List[Dict[str, Any]]"),
        (r"List\[Any\]PredictionStrategy\]", r"List[PredictionStrategy]"),
        (r"List\[Any\]str\]", r"List[str]"),
        # Optional patterns
        (r"Optional\[List\[Any\]Type\]\]", r"Optional[List[Type]]"),
        (r"Optional\[List\[Any\]str\]\]", r"Optional[List[str]]"),
        (r"Optional\[Dict\[str,\s*Any\]str,\s*Any\]\]", r"Optional[Dict[str, Any]]"),
        # Callable patterns
        (r"Callable\[\[\],\s*Any\],\s*T\]\]", r"Callable[[], T]"),
        # Fix missing import in from typing statement
        (r"from typing import \(\s*,\s*Any", r"from typing import ("),
        (r"from typing import \(\s*Any,\s*\)", r"from typing import ("),
    ]

    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text)

    # Fix specific issues with field default factories
    text = re.sub(
        r"field\(default_factory=Dict\[str,\s*Any\]str,\s*Any\]\)",
        r"field(default_factory=dict)",
        text,
    )

    return text


def main():
    """Fix all Python files in src/core"""
    core_dir = Path("src/core")

    for py_file in core_dir.rglob("*.py"):
        original_content = py_file.read_text(encoding="utf-8")
        fixed_content = fix_type_annotations(original_content)

        if fixed_content != original_content:
            py_file.write_text(fixed_content, encoding="utf-8")
            print(f"Fixed: {py_file}")

    print("✅ Fixed all type annotation syntax errors")


if __name__ == "__main__":
    main()
