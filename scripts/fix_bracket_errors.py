#!/usr/bin/env python3
"""
Fix specific bracket errors in type annotations
"""

import subprocess
import re
from pathlib import Path


def get_files_with_syntax_errors():
    """Get files that have syntax errors"""
    cmd = [
        "python",
        "-c",
        "import ast, sys; "
        "errors = []; "
        "for f in sys.argv[1:]: "
        "  try: ast.parse(open(f).read()); "
        "  except SyntaxError: errors.append(f); "
        "print('\\n'.join(errors))",
    ]

    # Get all Python files
    src_dir = Path("src")
    py_files = [str(f) for f in src_dir.rglob("*.py")]

    result = subprocess.run(cmd + py_files, capture_output=True, text=True)
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def fix_file(file_path):
    """Fix bracket errors in a file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Fix specific patterns
    fixes = [
        # Missing closing brackets in type annotations
        (r":\s*(Optional\[|List\[|Dict\[)[^]]*$", lambda m: m.group(0) + "]"),
        (r"->\s*(Optional\[|List\[|Dict\[)[^]]*:$", lambda m: m.group(0) + "]"),
        # Specific common patterns
        (r"Optional\[List\[Type\]$", r"Optional[List[Type]]"),
        (r"Optional\[List\[str\]$", r"Optional[List[str]]"),
        (r"Optional\[Dict\[str,\s*Any\]$", r"Optional[Dict[str, Any]]"),
        (r"Dict\[Type,\s*List\[Type\]$", r"Dict[Type, List[Type]]"),
        (r"Dict\[str,\s*Any\]$", r"Dict[str, Any]]"),
        (r"Dict\[Type,\s*Any\]$", r"Dict[Type, Any]]"),
        (r"Dict\[str,\s*ServiceConfig\]$", r"Dict[str, ServiceConfig]]"),
        (r"Dict\[str,\s*Dict\[Type,\s*Any\]\]$", r"Dict[str, Dict[Type, Any]]]"),
        (r"Dict\[str,\s*bool\]$", r"Dict[str, bool]]"),
        (r"Dict\[str,\s*int\]$", r"Dict[str, int]]"),
        (r"List\[Type\]$", r"List[Type]]"),
        (r"List\[str\]$", r"List[str]]"),
        (
            r"List\[Callable\[\[DIContainer\],\s*None\]\]$",
            r"List[Callable[[DIContainer], None]]]",
        ),
        (r"List\[Dict\[str,\s*Any\]\]$", r"List[Dict[str, Any]]]"),
        (r"List\[PredictionStrategy\]$", r"List[PredictionStrategy]]"),
        (r"List\[Any\]$", r"List[Any]]"),
        (r"List\[BaseService\]$", r"List[BaseService]]"),
        (r"List\[AuditEvent\]$", r"List[AuditEvent]]"),
    ]

    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Write back if changed
    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def main():
    """Fix all files with syntax errors"""
    error_files = get_files_with_syntax_errors()

    if not error_files or error_files == [""]:
        print("✅ No syntax errors found!")
        return

    print(f"Found {len(error_files)} files with syntax errors")

    fixed = 0
    for file_path in error_files:
        if not Path(file_path).exists():
            continue

        print(f"Fixing: {file_path}")
        if fix_file(file_path):
            fixed += 1

    print(f"\n✅ Fixed {fixed} files")


if __name__ == "__main__":
    main()
