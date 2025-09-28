#!/usr/bin/env python3
"""
Fix indentation issues in backup_tasks test file
"""

import re

def fix_backup_tasks_indentation():
    """Fix indentation issues in the backup_tasks test file"""

    file_path = "tests/unit/tasks/test_backup_tasks.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix common patterns - move assert statements that are incorrectly indented
    # Pattern: assert at beginning of line should have same indentation as previous line
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines and non-assert lines
        if not stripped or not stripped.startswith('assert '):
            fixed_lines.append(line)
            continue

        # Check if this assert line needs to be fixed
        # Look at previous non-empty line to determine correct indentation
        prev_indent = 0
        for j in range(i-1, -1, -1):
            if lines[j].strip():
                prev_indent = len(lines[j]) - len(lines[j].lstrip())
                break

        current_indent = len(line) - len(line.lstrip())

        # If assert has less indentation than previous line, fix it
        if current_indent < prev_indent:
            fixed_line = ' ' * prev_indent + stripped
            fixed_lines.append(fixed_line)
            print(f"Fixed line {i+1}: {line.strip()} -> {fixed_line.strip()}")
        else:
            fixed_lines.append(line)

    # Write fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

    print(f"Fixed indentation issues in {file_path}")

if __name__ == "__main__":
    fix_backup_tasks_indentation()