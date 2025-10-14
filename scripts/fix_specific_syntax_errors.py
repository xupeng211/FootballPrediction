#!/usr/bin/env python3
"""
Fix specific syntax errors in core modules
"""

import re
from pathlib import Path


def fix_cache_manager(content: str) -> str:
    """Fix syntax errors in cache_manager.py"""
    # Fix f-string syntax: f"{__name__}".{self.__class__.__name__} -> f"{__name__}.{self.__class__.__name__}"
    content = re.sub(r'f"([^"]+)"\.(\{[^}]+\})', r'f"\1.\2"', content)

    # Fix Optional[Dict[str, Any]: -> Optional[Dict[str, Any]]
    content = re.sub(
        r"Optional\[Dict\[str,\s*Any\]:", r"Optional[Dict[str, Any]]:", content
    )

    # Fix Optional[int] ] -> Optional[int]
    content = re.sub(r"Optional\[int\]\s*\]", r"Optional[int]]", content)

    return content


def fix_generic_syntax(content: str) -> str:
    """Fix generic syntax errors"""
    # Fix missing closing brackets in type annotations
    content = re.sub(r"(\w+)\[([^\]]+)(?=\s*[:,\)])", r"\1[\2]", content)

    # Fix double brackets
    content = re.sub(r"\]\]", "]", content)

    # Fix missing opening brackets
    content = re.sub(r"Optional\s+(\w+)", r"Optional[\1]", content)

    return content


def main():
    """Main function to fix syntax errors"""
    base_dir = Path("/home/user/projects/FootballPrediction")

    # Fix specific files
    files_to_fix = [
        "src/core/prediction/cache_manager.py",
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"Fixing {file_path}...")

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            content = fix_cache_manager(content)
            content = fix_generic_syntax(content)

            if content != original_content:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✓ Fixed {file_path}")
                total_fixes += 1
            else:
                print(f"  - No changes needed for {file_path}")

    print(f"\n✅ Fixed {total_fixes} files")


if __name__ == "__main__":
    main()
