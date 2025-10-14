#!/usr/bin/env python3
"""
Fix f-string syntax errors in core modules
"""

import re
from pathlib import Path


def fix_fstring_dot_syntax(content: str) -> str:
    """Fix f-string with dot syntax errors"""
    # Pattern: f"{__name__}".{self.__class__.__name__} -> f"{__name__}.{self.__class__.__name__}
    patterns = [
        (r'f"([^"]+)"\.(\{[^}]+\})', r'f"\1.\2"'),
        (r'f"\{(__name__)\}"\.(\{[^}]+\})', r'f"\1.\2"'),
        (r'f"([^"]+)"\.(\{[^}]+\}\})', r'f"\1.\2"'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def main():
    """Main function"""
    base_dir = Path("/home/user/projects/FootballPrediction/src/core")

    fixed_files = 0

    for py_file in base_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            content = fix_fstring_dot_syntax(content)

            if content != original_content:
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write(content)
                fixed_files += 1
                print(
                    f"Fixed: {py_file.relative_to('/home/user/projects/FootballPrediction')}"
                )

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"\n✅ Fixed {fixed_files} files")


if __name__ == "__main__":
    main()
