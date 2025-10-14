#!/usr/bin/env python3
"""
Fix missing closing brackets in type annotations
"""

import re
from pathlib import Path


def fix_missing_brackets(text: str) -> str:
    """Fix missing closing brackets in type annotations"""
    # Fix patterns with missing closing brackets
    fixes = [
        # Missing closing brackets for Dict
        (r"Dict\[str,\s*Any\](?!\])", r"Dict[str, Any]]"),
        (r"Dict\[Type,\s*List\[Type\](?!\])", r"Dict[Type, List[Type]]]"),
        (r"Dict\[str,\s*ServiceConfig\](?!\])", r"Dict[str, ServiceConfig]]"),
        (r"Dict\[Type,\s*Any\](?!\])", r"Dict[Type, Any]]"),
        (r"Dict\[str,\s*Dict\[Type,\s*Any\]\](?!\])", r"Dict[str, Dict[Type, Any]]]"),
        (r"Dict\[str,\s*bool\](?!\])", r"Dict[str, bool]]"),
        (r"Dict\[str,\s*int\](?!\])", r"Dict[str, int]]"),
        (r"Dict\[str,\s*PredictionStrategy\](?!\])", r"Dict[str, PredictionStrategy]]"),
        # Missing closing brackets for List
        (r"List\[Type\](?!\])", r"List[Type]]"),
        (r"List\[str\](?!\])", r"List[str]]"),
        (
            r"List\[Callable\[\[DIContainer\],\s*None\]\](?!\])",
            r"List[Callable[[DIContainer], None]]]",
        ),
        (r"List\[Dict\[str,\s*Any\]\](?!\])", r"List[Dict[str, Any]]]"),
        (r"List\[PredictionStrategy\](?!\])", r"List[PredictionStrategy]]"),
        (r"List\[Any\](?!\])", r"List[Any]]"),
        (r"List\[BaseService\](?!\])", r"List[BaseService]]"),
        (r"List\[AuditEvent\](?!\])", r"List[AuditEvent]]"),
        # Missing closing brackets for Optional
        (r"Optional\[List\[Type\]\](?!\])", r"Optional[List[Type]]]"),
        (r"Optional\[List\[str\]\](?!\])", r"Optional[List[str]]]"),
        (r"Optional\[Dict\[str,\s*Any\]\](?!\])", r"Optional[Dict[str, Any]]]"),
        (r"Optional\[Type\](?!\])", r"Optional[Type]]"),
        # Missing closing brackets for Union
        (
            r"Union\[Dict\[str,\s*Any\],\s*List\[Dict\[str,\s*Any\]\]\](?!\])",
            r"Union[Dict[str, Any], List[Dict[str, Any]]]]]",
        ),
        (
            r"Union\[Dict\[str,\s*Any\],\s*pd\.DataFrame\](?!\])",
            r"Union[Dict[str, Any], pd.DataFrame]]]",
        ),
        # Fix missing brackets in function signatures
        (
            r"def\s+\w+\([^)]*\)\s*->\s*Optional\[Dict\[str,\s*Any\](?!\]):",
            lambda m: m.group(0).replace(
                "Optional[Dict[str, Any]", "Optional[Dict[str, Any]]"
            ),
        ),
        (
            r"def\s+\w+\([^)]*\)\s*->\s*Dict\[str,\s*Any\](?!\]):",
            lambda m: m.group(0).replace("Dict[str, Any]", "Dict[str, Any]]"),
        ),
        (
            r"def\s+\w+\([^)]*\)\s*->\s*List\[Dict\[str,\s*Any\]\](?!\]):",
            lambda m: m.group(0).replace(
                "List[Dict[str, Any]]", "List[Dict[str, Any]]]"
            ),
        ),
        (
            r"def\s+\w+\([^)]*\)\s*->\s*List\[Type\](?!\]):",
            lambda m: m.group(0).replace("List[Type]", "List[Type]]"),
        ),
        (
            r"def\s+\w+\([^)]*\)\s*->\s*List\[str\](?!\]):",
            lambda m: m.group(0).replace("List[str]", "List[str]]"),
        ),
        (
            r"def\s+\w+\([^)]*\)\s*->\s*Dict\[Type,\s*Any\](?!\]):",
            lambda m: m.group(0).replace("Dict[Type, Any]", "Dict[Type, Any]]"),
        ),
        # Fix missing brackets in variable annotations
        (
            r":\s*Optional\[Dict\[str,\s*Any\](?!\])\s*=",
            r": Optional[Dict[str, Any]] =",
        ),
        (r":\s*Dict\[str,\s*Any\](?!\])\s*=", r": Dict[str, Any]] ="),
        (r":\s*List\[Type\](?!\])\s*=", r": List[Type]] ="),
        (r":\s*List\[str\](?!\])\s*=", r": List[str]] ="),
        (
            r":\s*List\[Callable\[\[DIContainer\],\s*None\]\](?!\])\s*=",
            r": List[Callable[[DIContainer], None]]] =",
        ),
        (r":\s*Dict\[Type,\s*List\[Type\]\](?!\])\s*=", r": Dict[Type, List[Type]]] ="),
        (
            r":\s*Dict\[str,\s*ServiceConfig\](?!\])\s*=",
            r": Dict[str, ServiceConfig]] =",
        ),
        (
            r":\s*Dict\[str,\s*Dict\[Type,\s*Any\]\](?!\])\s*=",
            r": Dict[str, Dict[Type, Any]]] =",
        ),
    ]

    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)

    return text


def main():
    """Fix all Python files in src"""
    src_dir = Path("src")
    fixed_files = []

    for py_file in src_dir.rglob("*.py"):
        try:
            original_content = py_file.read_text(encoding="utf-8")

            # Try to parse to check for syntax errors
            try:
                compile(original_content, py_file, "exec")
                continue  # No syntax error, skip
            except SyntaxError:
                pass  # Has syntax error, try to fix

            fixed_content = fix_missing_brackets(original_content)

            # Try to parse the fixed content
            try:
                compile(fixed_content, py_file, "exec")
                if fixed_content != original_content:
                    py_file.write_text(fixed_content, encoding="utf-8")
                    fixed_files.append(py_file)
            except SyntaxError:
                print(f"Could not fix: {py_file}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    if fixed_files:
        print(f"✅ Fixed {len(fixed_files)} files:")
        for f in fixed_files:
            print(f"  - {f}")
    else:
        print("✅ No files needed fixing")


if __name__ == "__main__":
    main()
