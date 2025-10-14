#!/usr/bin/env python3
"""
Find all Python files with syntax errors
"""

import ast
from pathlib import Path


def main():
    """Find all files with syntax errors"""
    src_dir = Path("src")
    error_files = []

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            error_files.append((py_file, str(e)))
            print(f"Syntax error in {py_file}: {e}")

    print(f"\nFound {len(error_files)} files with syntax errors")


if __name__ == "__main__":
    main()
