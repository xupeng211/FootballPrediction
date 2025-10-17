#!/usr/bin/env python3
"""
Quick fix for remaining syntax errors in test_model_integration.py
"""

import re


def fix_model_integration_file():
    """Fix indentation issues in test_model_integration.py"""
    file_path = "tests/integration/models/test_model_integration.py"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix common indentation patterns
    fixes = [
        # Fix assertion statements that should be indented
        (r"^(\s*)assert (.+)$", r"        assert \2"),
        # Fix for loop indentation
        (r"^(\s*)for (.+):$", r"        for \2:"),
        # Fix if statements inside functions
        (r"^(\s*)if (.+):$", r"            if \2:"),
        # Fix variable assignments
        (r"^(\s*)(\w+ = .+)$", r"            \2"),
        # Fix method calls
        (r"^(\s*)(\w+\(.+)\)$", r"            \2)"),
    ]

    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        fixed_line = line
        for pattern, replacement in fixes:
            if re.match(pattern, line):
                fixed_line = re.sub(pattern, replacement, line)
                break
        fixed_lines.append(fixed_line)

    # Join and write back
    fixed_content = "\n".join(fixed_lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    return file_path


if __name__ == "__main__":
    fix_model_integration_file()
    print("Fixed test_model_integration.py")
