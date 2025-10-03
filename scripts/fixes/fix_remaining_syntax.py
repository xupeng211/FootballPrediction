#!/usr/bin/env python3
"""
Fix remaining syntax errors more comprehensively.

This script targets the most common syntax patterns found in the remaining errors.
"""

import re
from pathlib import Path
import sys

def fix_trailing_colons(file_path):
    """Fix trailing colons after various statements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            original = content

        # Fix colons after assert statements
        content = re.sub(r'assert (.+):', r'assert \1', content)

        # Fix colons after docstrings (single line)
        content = re.sub(r'(\"{3}[^"]*\"{3})\s*:\s*\n', r'\1\n', content)

        # Fix colons after return statements
        content = re.sub(r'return (.+):', r'return \1', content)

        # Fix colons after assignment statements
        content = re.sub(r'(\w+)\s*=\s*(.+):', r'\1 = \2', content)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_indentation_issues(file_path):
    """Fix indentation issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        changes = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Fix inconsistent indentation after except blocks
            if stripped.startswith('#') and i > 0:
                prev_line = lines[i-1].strip()
                if prev_line.startswith('pass  # Auto-fixed empty except block'):
                    # Ensure comment has same indentation as the pass statement
                    indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                    fixed_line = ' ' * indent + stripped + '\n'
                    if fixed_line != line:
                        fixed_lines.append(fixed_line)
                        changes = True
                        continue

            fixed_lines.append(line)

        if changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix remaining syntax errors."""
    project_root = Path(".")
    files_fixed = 0

    # Focus on test files first
    test_dirs = ['tests/', 'tests/unit/', 'tests/integration/', 'tests/e2e/']

    for test_dir in test_dirs:
        dir_path = project_root / test_dir
        if dir_path.exists():
            for py_file in dir_path.rglob("*.py"):
                if fix_trailing_colons(py_file):
                    files_fixed += 1
                    print(f"Fixed trailing colons: {py_file}")

                if fix_indentation_issues(py_file):
                    files_fixed += 1
                    print(f"Fixed indentation: {py_file}")

    print(f"\nFixed syntax errors in {files_fixed} files")
    return files_fixed

if __name__ == "__main__":
    files_fixed = main()
    sys.exit(0 if files_fixed >= 0 else 1)