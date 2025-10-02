#!/usr/bin/env python3
"""
Fix docstring colon syntax errors across the codebase.

This script fixes the pattern where colons appear after docstrings in class/function definitions.
"""

import re
from pathlib import Path
import sys

def fix_docstring_colons(file_path):
    """Fix docstring colon syntax errors in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern: docstring followed by colon on next line
        # Example:
        # def func():
        #     """Docstring."""
        pattern = r'(\"{3}.*?\"{3})\s*:\s*\n'
        replacement = r'\1\n'

        fixed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix docstring colon errors."""
    project_root = Path(".")
    files_fixed = 0

    # Process all Python files
    for py_file in project_root.rglob("*.py"):
        if fix_docstring_colons(py_file):
            files_fixed += 1
            print(f"Fixed: {py_file}")

    print(f"\nFixed docstring colon errors in {files_fixed} files")
    return files_fixed

if __name__ == "__main__":
    files_fixed = main()
    sys.exit(0 if files_fixed >= 0 else 1)