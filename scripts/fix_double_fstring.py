#!/usr/bin/env python3
"""
Fix double f-string issues
"""

import re
from pathlib import Path


def fix_double_fstrings(content: str) -> str:
    """Fix double f-string patterns like f"f"text"}"""
    # Pattern: f"f"text}" -> f"text"
    content = re.sub(r'f"f"([^"]*)}""', r'f"\1"', content)
    return content


def fix_file():
    """Fix config_di.py"""
    file_path = Path("/home/user/projects/FootballPrediction/src/core/config_di.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    content = fix_double_fstrings(content)

    # Also fix remaining single f-strings with extra braces
    content = re.sub(r'f"([^"]*?)}}', r'f"\1}"', content)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Fixed double f-string issues")


if __name__ == "__main__":
    fix_file()
