#!/usr/bin/env python3
"""
Fix indentation issues in test_utils_comprehensive.py
"""


def fix_file():
    with open("tests/unit/test_utils_comprehensive.py", "r") as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("assert "):
            # All assert statements should be indented by 12 spaces (3 levels)
            fixed_lines.append("            " + stripped)
        else:
            fixed_lines.append(line)

    with open("tests/unit/test_utils_comprehensive.py", "w") as f:
        f.writelines(fixed_lines)

    print("File fixed")


if __name__ == "__main__":
    fix_file()
