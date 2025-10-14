#!/usr/bin/env python3
"""
Fix all type annotation syntax errors
"""

import re
from pathlib import Path


def fix_type_annotations(text: str) -> str:
    """Fix all type annotation syntax errors"""
    # Fix missing closing brackets in Optional
    text = re.sub(
        r"Optional\[(List|Dict)\[([^\]]*)\](?![\]])", r"Optional[\1[\2]]]", text
    )

    # Fix missing closing brackets in function return types
    text = re.sub(
        r"->\s*(Optional\[|List\[|Dict\[)([^\]]*)(?![\]])\s*:",
        lambda m: f"-> {m.group(1)}{m.group(2)}]:",
        text,
    )

    # Fix missing closing brackets in variable annotations
    text = re.sub(
        r":\s*(Optional\[|List\[|Dict\[)([^\]]*)(?![\]])\s*=",
        lambda m: f": {m.group(1)}{m.group(2)}] =",
        text,
    )

    # Fix specific common patterns
    patterns = [
        # Optional patterns
        (r"Optional\[List\[Type\](?![\]])", r"Optional[List[Type]]"),
        (r"Optional\[List\[str\](?![\]])", r"Optional[List[str]]"),
        (r"Optional\[Dict\[str,\s*Any\](?![\]])", r"Optional[Dict[str, Any]]"),
        (r"Optional\[Type\](?![\]])", r"Optional[Type]]"),
        # List patterns
        (r"List\[Type\](?![\]])", r"List[Type]]"),
        (r"List\[str\](?![\]])", r"List[str]]"),
        (
            r"List\[Callable\[\[DIContainer\],\s*None\]\](?![\]])",
            r"List[Callable[[DIContainer], None]]]",
        ),
        (r"List\[Dict\[str,\s*Any\]\](?![\]])", r"List[Dict[str, Any]]]"),
        (r"List\[PredictionStrategy\](?![\]])", r"List[PredictionStrategy]]"),
        (r"List\[Any\](?![\]])", r"List[Any]]"),
        (r"List\[BaseService\](?![\]])", r"List[BaseService]]"),
        (r"List\[AuditEvent\](?![\]])", r"List[AuditEvent]]"),
        (r"List\[Union\[.*?\]\](?![\]])", r"List[Union[\1]]]"),
        # Dict patterns
        (r"Dict\[Type,\s*List\[Type\](?![\]])", r"Dict[Type, List[Type]]]"),
        (r"Dict\[str,\s*Any\](?![\]])", r"Dict[str, Any]]"),
        (r"Dict\[Type,\s*Any\](?![\]])", r"Dict[Type, Any]]"),
        (r"Dict\[str,\s*ServiceConfig\](?![\]])", r"Dict[str, ServiceConfig]]"),
        (r"Dict\[str,\s*Dict\[Type,\s*Any\]\](?![\]])", r"Dict[str, Dict[Type, Any]]]"),
        (r"Dict\[str,\s*bool\](?![\]])", r"Dict[str, bool]]"),
        (r"Dict\[str,\s*int\](?![\]])", r"Dict[str, int]]"),
        (
            r"Dict\[str,\s*PredictionStrategy\](?![\]])",
            r"Dict[str, PredictionStrategy]]",
        ),
        (r"Dict\[str,\s*Dict\[str,\s*Any\]\](?![\]])", r"Dict[str, Dict[str, Any]]]"),
        # Union patterns
        (
            r"Union\[Dict\[str,\s*Any\],\s*List\[Dict\[str,\s*Any\]\]\](?![\]])",
            r"Union[Dict[str, Any], List[Dict[str, Any]]]]]",
        ),
        (
            r"Union\[Dict\[str,\s*Any\],\s*pd\.DataFrame\](?![\]])",
            r"Union[Dict[str, Any], pd.DataFrame]]]",
        ),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    # Fix double closing brackets
    text = re.sub(r"\]\]\]", r"]]", text)

    # Fix missing single bracket in complex cases
    text = re.sub(
        r"(\w+)\s*:\s*(Optional\[|List\[|Dict\[)([^\[\]]*)(?<!\])\s*([,=)])",
        r"\1: \2\3]\4",
        text,
    )

    return text


def main():
    """Fix all Python files"""
    src_dir = Path("src")
    fixed_count = 0

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                original = f.read()

            # Try to parse original
            try:
                compile(original, py_file, "exec")
                continue  # No error
            except SyntaxError:
                pass  # Has syntax error

            # Fix the content
            fixed = fix_type_annotations(original)

            # Try to parse fixed version
            try:
                compile(fixed, py_file, "exec")
                if fixed != original:
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    print(f"Fixed: {py_file}")
                    fixed_count += 1
            except SyntaxError as e:
                print(f"Could not fix {py_file}: {e}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
