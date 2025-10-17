#!/usr/bin/env python3
"""
Fix all syntax errors in test files
"""

import re
from pathlib import Path


def fix_function_names(content: str) -> str:
    """Fix function names with slashes and other syntax issues"""
    # Fix function definitions with slashes
    content = re.sub(
        r"def test_([^/]+)/([^_\s]+)_functions", r"def test_\1_\2_functions", content
    )

    # Fix any remaining slashes in function names
    content = re.sub(r"def test_([^/]+)/([^\s(]+)", r"def test_\1_\2", content)

    # Fix indentation issues
    lines = content.split("\n")
    fixed_lines = []
    for line in lines:
        # Remove excessive indentation
        if line.strip().startswith("assert ") and line.startswith("        "):
            line = "    " + line.strip()
        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def process_file(file_path: Path):
    """Process a single test file"""
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Fix syntax errors
    new_content = fix_function_names(content)

    if new_content != original_content:
        file_path.write_text(new_content, encoding="utf-8")
        print(f"✅ Fixed: {file_path}")
        return True

    return False


def main():
    """Main function to fix all test files"""
    fixed_files = []

    # Process all test files
    for test_file in Path("tests").rglob("test_*.py"):
        if process_file(test_file):
            fixed_files.append(test_file)

    print("\n📊 Fix Summary:")
    print(f"✅ Fixed files: {len(fixed_files)}")


if __name__ == "__main__":
    main()
