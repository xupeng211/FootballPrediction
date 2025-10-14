#!/usr/bin/env python3
"""
Fix complex syntax errors in type annotations
"""

import os
import re
from pathlib import Path


def fix_syntax_errors(file_path: Path) -> int:
    """Fix complex syntax errors"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix 1: List[Any] = []] -> List[Any] = []
        content = re.sub(r"List\[Any\]\s*=\s*\[\]\]", "List[Any] = []", content)

        # Fix 2: Dict[str, Any] = {}} -> Dict[str, Any] = {}
        content = re.sub(
            r"Dict\[str,\s*Any\]\s*=\s*\{\}\}", "Dict[str, Any] = {}", content
        )

        # Fix 3: List[str] = {}} -> List[str] = []
        content = re.sub(r"List\[str\]\s*=\s*\{\}\]", "List[str] = []", content)

        # Fix 4: Dict[str, List[str]] = {}} -> Dict[str, List[str]] = {}
        content = re.sub(
            r"Dict\[str,\s*List\[str\]\]\s*=\s*\{\}\}",
            "Dict[str, List[str]] = {}",
            content,
        )

        # Fix 5: List[Callable[[DIContainer], None] = [] -> List[Callable[[DIContainer], None]] = []
        content = re.sub(
            r"List\[Callable\[\[DIContainer\],\s*None\]\s*=\s*\[\]",
            "List[Callable[[DIContainer], None]] = []",
            content,
        )

        # Fix 6: Dict[str, Any]str, List[str]] -> Dict[str, Union[str, List[str]]]
        content = re.sub(
            r"Dict\[str,\s*Any\]str,\s*List\[str\]\]",
            "Dict[str, Union[str, List[str]]]",
            content,
        )

        # Fix 7: missing brackets in Union types
        content = re.sub(r"List\[Any\]\s*=\s*\{\}", "List[Any] = []", content)
        content = re.sub(
            r"Dict\[str,\s*Any\]\s*=\s*\{\}", "Dict[str, Any] = {}", content
        )

        # Fix 8: malformed dict literals with quotes
        content = re.sub(r'\{\}\s*"', '{}"', content)
        content = re.sub(r"\{\}\s*\]", "{}]", content)

        # Fix 9: List[Type] = {}} -> List[Type] = []
        content = re.sub(
            r"List\[([A-Za-z0-9_]+)\]\s*=\s*\{\}\]", r"List[\1] = []", content
        )

        # Fix 10: Dict[str, Any]] -> Dict[str, Any]
        content = re.sub(r"Dict\[str,\s*Any\]\]", "Dict[str, Any]", content)

        # Fix 11: Dict[str, Any] = {}} -> Dict[str, Any] = {}
        content = re.sub(
            r"Dict\[str,\s*Any\]\s*=\s*\{\}\}", "Dict[str, Any] = {}", content
        )

        # Fix 12: missing closing bracket in Dict[Type, List[Type]
        content = re.sub(
            r"Dict\[Type,\s*List\[Type\]\s*=\s*\{\}",
            "Dict[Type, List[Type]] = {}",
            content,
        )

        # Fix 13: Dict[str, Any]str, Dict[str, Any] = {} -> Dict[str, Union[str, Dict[str, Any]]] = {}
        content = re.sub(
            r"Dict\[str,\s*Any\]str,\s*Dict\[str,\s*Any\]\s*=\s*\{\}",
            "Dict[str, Union[str, Dict[str, Any]]] = {}",
            content,
        )

        # Fix 14: current[keys[-1] = value -> current[keys[-1]] = value
        content = re.sub(
            r"current\[keys\[-1\]\s*=\s*value", "current[keys[-1]] = value", content
        )

        # Fix 15: missing quotes in strings
        content = re.sub(r'"\{[^}]*\}', lambda m: '"' + m.group(0)[1:-1] + '"', content)

        # Fix 16: f"{local[:3]***@{domain}" -> f"{local[:3]}***@{domain}"
        content = re.sub(
            r'f"\{[^}]*\]\*\*\*@',
            lambda m: m.group(0).replace("]***@", "]}***@"),
            content,
        )

        # Fix 17: List[Type] = {} -> List[Type] = []
        content = re.sub(
            r"List\[[^\]]+\]\s*=\s*\{\}",
            lambda m: m.group(0).replace("{}", "[]"),
            content,
        )

        # Fix 18: missing closing bracket in function signatures
        content = re.sub(
            r"List\[Dict\[str,\s*Any\]\s*=\s*None",
            "List[Dict[str, Any]] = None",
            content,
        )

        # Fix 19: Optional[Type] = None with missing bracket
        content = re.sub(
            r"Optional\[([A-Za-z0-9_\[\],\s]+)\]\s*=\s*None",
            r"Optional[\1] = None",
            content,
        )

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return 1

        return 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0


def main():
    """Main function"""
    core_dirs = [
        "src/core",
        "src/services",
        "src/api",
        "src/domain",
        "src/repositories",
        "src/database/repositories",
    ]

    fixed_files = 0
    for core_dir in core_dirs:
        if os.path.exists(core_dir):
            for py_file in Path(core_dir).rglob("*.py"):
                if fix_syntax_errors(py_file):
                    fixed_files += 1
                    print(f"  ✓ Fixed: {py_file}")

    print(f"\n✅ Fixed syntax errors in {fixed_files} files")


if __name__ == "__main__":
    main()
