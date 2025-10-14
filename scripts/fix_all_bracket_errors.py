#!/usr/bin/env python3
"""
Fix all bracket syntax errors in the project
"""

import os
import re
from pathlib import Path


def fix_missing_brackets(file_path: Path) -> int:
    """Fix missing closing brackets in type annotations"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix pattern: Optional[List[Type] = None -> Optional[List[Type]] = None
        content = re.sub(
            r"Optional\[([A-Za-z0-9_\[\],\s]+)\]?\s*=\s*None",
            lambda m: f"Optional[{m.group(1)}] = None"
            if not m.group(1).endswith("]")
            else m.group(0),
            content,
        )

        # Fix pattern: Dict[str, Dict[Type, Any] = {} -> Dict[str, Dict[Type, Any]] = {}
        content = re.sub(
            r"([A-Z][a-zA-Z0-9_]*)\[([^\]]+)\]?\s*=\s*[{[]",
            lambda m: f"{m.group(1)}[{m.group(2)}] = "
            + ("{}" if m.group(1) in ["Dict", "List", "Set"] else "[]"),
            content,
        )

        # Fix pattern: List[Callable[[DIContainer], None] = [] -> List[Callable[[DIContainer], None]] = []
        content = re.sub(
            r"List\[([^\]]+)\]?\s*=\s*\[\]",
            lambda m: f"List[{m.group(1)}] = []",
            content,
        )

        # Fix pattern: Dict[Type, ServiceDescriptor] = {} with missing bracket
        content = re.sub(
            r"Dict\[([^\]]+)\]?\s*=\s*\{\}",
            lambda m: f"Dict[{m.group(1)}] = {{}}",
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


def check_syntax_errors(file_path: Path) -> bool:
    """Check if a Python file has syntax errors"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, str(file_path), "exec")
        return False
    except SyntaxError:
        return True


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

    # First pass: fix obvious bracket errors
    fixed_files = 0
    for core_dir in core_dirs:
        if os.path.exists(core_dir):
            for py_file in Path(core_dir).rglob("*.py"):
                if fix_missing_brackets(py_file):
                    fixed_files += 1
                    print(f"  ✓ Fixed: {py_file}")

    print(f"\n✅ Fixed bracket syntax errors in {fixed_files} files")

    # Second pass: check for remaining syntax errors
    print("\n🔍 Checking for remaining syntax errors...")
    files_with_errors = []
    for core_dir in core_dirs:
        if os.path.exists(core_dir):
            for py_file in Path(core_dir).rglob("*.py"):
                if check_syntax_errors(py_file):
                    files_with_errors.append(py_file)

    if files_with_errors:
        print(f"\n❌ Still found {len(files_with_errors)} files with syntax errors:")
        for f in files_with_errors[:10]:
            print(f"  - {f}")
    else:
        print("\n✅ No syntax errors found!")


if __name__ == "__main__":
    main()
