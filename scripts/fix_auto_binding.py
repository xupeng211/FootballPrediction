#!/usr/bin/env python3
"""
Fix syntax errors in auto_binding.py
"""

import re
from pathlib import Path


def fix_auto_binding_file():
    """Fix all syntax errors in auto_binding.py"""
    file_path = Path("/home/user/projects/FootballPrediction/src/core/auto_binding.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix all the syntax errors
    fixes = [
        # Fix Optional[callable]] -> Optional[callable]
        (r"Optional\[callable\]\]", r"Optional[callable]"),
        # Fix ff"..." -> f"..."
        (r'ff"([^"]*)"', r'f"\1"'),
        # Fix f-string with extra }
        (r'f"([^"]*)}([^"]*)"', r'f"\1\2"'),
        # Fix f-string with missing }
        (r'f"([^"]*?)\{([^}]*)$', r'f"\1{\2}"'),
        # Fix .py} -> .py
        (r"\.py}", r".py"),
        # Fix __name__} -> __name__
        (r"__name__}", r"__name__"),
        # Fix .__name__} -> .__name__
        (r"\.__name__}", r".__name__"),
        # Fix __name__}} -> __name__
        (r"__name__}}", r"__name__"),
        # Fix f-string at beginning of line
        (r'^\s*f"([^"]*?)\}([^"]*)"', r'    f"\1\2"'),
        # Fix other double braces
        (r"}}", "}"),
        (r"{{", "{"),
    ]

    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Write the fixed content back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ Fixed auto_binding.py")


if __name__ == "__main__":
    fix_auto_binding_file()
