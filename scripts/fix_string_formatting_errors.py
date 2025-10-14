#!/usr/bin/env python3
"""
Fix string formatting errors (f-strings and regular strings)
"""

import os
import re
from pathlib import Path


def fix_string_errors(file_path: Path) -> int:
    """Fix string formatting errors"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix 1: f"{var}" -> f"{var}"
        content = re.sub(r'f"\{([^}]+)\}"', r'f"{\1}"', content)

        # Fix 2: f"{var}text" -> f"{var}text"
        content = re.sub(r'f"\{([^}]+)([^"]*)"', r'f"{\1\2}"', content)

        # Fix 3: "text{var}" -> f"text{var}"
        content = re.sub(r'"([^"]*)\{([^}]+)\}"', r'f"\1{\2}"', content)

        # Fix 4: f"text{var" -> f"text{var}"
        content = re.sub(r'f"([^"]*)\{([^"]*)"', r'f"\1{\2}"', content)

        # Fix 5: missing quotes in f-strings
        content = re.sub(r'f"([^"]*?)\{([^}]+)\}([^"]*?)"', r'f"\1{\2}\3"', content)

        # Fix 6: fix common patterns
        content = re.sub(r'\{([^}]+)\}"([^"]*)"', r'{\1}"\2"', content)

        # Fix 7: f"{var} -> f"{var}"
        content = re.sub(r'f"\{([^}]*)$', r'f"{\1}"', content)

        # Fix 8: "{var}"text -> f"{var}text"
        content = re.sub(
            r'^"\{([^}]+)\}([^"]*)"', r'f"{\1}\2"', content, flags=re.MULTILINE
        )

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return 1

        return 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0


def main():
    """Main function"""
    core_dirs = [
        "src/core",
        "src/services",
        "src/api",
        "src/domain",
        "src/repositories",
        "src/database/repositories",
    ]

    fixed_files = 0
    for core_dir in core_dirs:
        if os.path.exists(core_dir):
            for py_file in Path(core_dir).rglob("*.py"):
                if fix_string_errors(py_file):
                    fixed_files += 1
                    print(f"  ✓ Fixed: {py_file}")

    print(f"\n✅ Fixed string formatting errors in {fixed_files} files")


if __name__ == "__main__":
    main()
