#!/usr/bin/env python3
"""
Fix bracket syntax errors like List[str]] -> List[str], Dict[str, Any]] -> Dict[str, Any]
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def fix_bracket_syntax(file_path: Path) -> int:
    """Fix bracket syntax errors in a file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Pattern 1: List[str]] -> List[str]
        content = re.sub(r"List\[(.*?)\]\]", r"List[\1]", content)

        # Pattern 2: Dict\[str, Any\]\] -> Dict\[str, Any\]
        content = re.sub(r"Dict\[(.*?)\]\]", r"Dict[\1]", content)

        # Pattern 3: Optional\[.*?\]\] -> Optional\[.*?\]
        content = re.sub(r"Optional\[(.*?)\]\]", r"Optional[\1]", content)

        # Pattern 4: Union\[.*?\]\] -> Union\[.*?\]
        content = re.sub(r"Union\[(.*?)\]\]", r"Union[\1]", content)

        # Pattern 5: Tuple\[(.*?)\]\] -> Tuple\[(.*?)\]
        content = re.sub(r"Tuple\[(.*?)\]\]", r"Tuple[\1]", content)

        # Pattern 6: Any\]\] -> Any\]
        content = re.sub(r"Any\]\]", r"Any]", content)

        # Pattern 7: Generic pattern with any type
        content = re.sub(r"([A-Z][a-zA-Z0-9_]*)\[(.*?)\]\]", r"\1[\2]", content)

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
            print(f"\n🔧 Fixing bracket syntax errors in {core_dir}/...")

            for py_file in Path(core_dir).rglob("*.py"):
                if fix_bracket_syntax(py_file):
                    fixed_files += 1
                    print(f"  ✓ Fixed: {py_file}")

    print(f"\n✅ Fixed bracket syntax errors in {fixed_files} files")

    # Now run mypy to check remaining errors
    print("\n🔍 Running MyPy to check remaining errors...")
    os.system(
        "mypy src/core src/services src/api src/domain src/repositories src/database/repositories --strict 2>&1 | head -20"
    )


if __name__ == "__main__":
    main()
