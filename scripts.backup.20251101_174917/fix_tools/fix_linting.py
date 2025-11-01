#!/usr/bin/env python3
"""
Script to fix common linting issues automatically
"""

import glob
import os
import re


def fix_unused_imports(file_path):
    """Remove unused imports based on common patterns"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Common unused imports to remove
    unused_patterns = [
        r"from typing import.*Optional.*\n",
        r"from typing import.*Tuple.*\n",
        r"from typing import.*Union.*\n",
        r"import asyncio\n(?!.*asyncio)",
        r"from datetime import.*timedelta.*\n(?!.*timedelta)",
        r"from unittest\.mock import.*MagicMock.*\n(?!.*MagicMock)",
        r"import pytest_asyncio\n(?!.*pytest_asyncio)",
    ]

    for pattern in unused_patterns:
        content = re.sub(pattern, "", content, flags=re.MULTILINE)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def fix_unused_variables(file_path):
    """Comment out or fix unused variables"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    for i, line in enumerate(lines):
        # Fix unused variables by prefixing with underscore
        if "F841" in line or "assigned to but never used" in line:
            # This is just a placeholder - actual fixing would need AST parsing
            pass

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)


def main():
    """Fix linting issues in Python files"""
    python_files = glob.glob("src/**/*.py", recursive=True) + glob.glob(
        "tests/**/*.py", recursive=True
    )

    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                fix_unused_imports(file_path)
                fix_unused_variables(file_path)
                print(f"Processed: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
