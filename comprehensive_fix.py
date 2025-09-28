#!/usr/bin/env python3
"""
Comprehensive fix for backup_tasks test file indentation
"""

import re

def comprehensive_fix():
    """Fix all indentation issues in the backup_tasks test file"""

    file_path = "tests/unit/tasks/test_backup_tasks.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            i += 1
            continue

        # Check if this is an assert statement with wrong indentation
        if stripped.startswith('assert ') or stripped.startswith('mock_') or stripped.startswith('def ') or stripped.startswith('@'):
            # Find the correct indentation level by looking at previous non-empty lines
            correct_indent = 0
            for j in range(i-1, -1, -1):
                if lines[j].strip():
                    if lines[j].strip().startswith('"""'):
                        # Skip docstring lines
                        continue
                    correct_indent = len(lines[j]) - len(lines[j].lstrip())
                    break

            current_indent = len(line) - len(line.lstrip())

            # Fix indentation if needed (use 8 spaces for test methods)
            if current_indent != correct_indent and correct_indent > 0:
                # Determine correct indentation - usually 8 spaces for test assertions
                if 'def test_' in ''.join(lines[max(0, i-10):i]):
                    # Inside test method, use 8 spaces
                    fixed_line = '        ' + stripped + '\n'
                elif stripped.startswith('def ') or stripped.startswith('@'):
                    # Method definition, use 4 spaces
                    fixed_line = '    ' + stripped + '\n'
                else:
                    # Use the detected correct indentation
                    fixed_line = ' ' * correct_indent + stripped + '\n'

                fixed_lines.append(fixed_line)
                print(f"Fixed line {i+1}: {line.strip()} -> {fixed_line.strip()}")
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

        i += 1

    # Write fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Comprehensively fixed indentation issues in {file_path}")

if __name__ == "__main__":
    comprehensive_fix()