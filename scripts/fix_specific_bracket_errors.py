#!/usr/bin/env python3
"""
Fix specific bracket syntax errors introduced by previous fixes
"""

import os
import re
from pathlib import Path


def fix_bracket_errors(file_path: Path) -> int:
    """Fix specific bracket syntax errors"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix 1: ]} -> ]
        content = re.sub(r"\]\}", "]", content)

        # Fix 2: ] = None -> ] = None
        content = re.sub(r"\]\s*=\s*None", "] = None", content)

        # Fix 3: ]] -> ]
        content = re.sub(r"\]\]", "]", content)

        # Fix 4: ]\] -> ]
        content = re.sub(r"\]\\\]", "]", content)

        # Fix 5: [^]]*] -> [ ... ] (malformed dict literals)
        content = re.sub(r"\{\}\s*\]", "{}]", content)

        # Fix 6: Specific patterns
        content = re.sub(r"List\[Any\]\s*=\s*\{\}", "List[Any] = []", content)
        content = re.sub(r"Dict\[str, Any\]\s*=\s*\{\}", "Dict[str, Any] = {}", content)

        # Fix 7: ]]] -> ]
        content = re.sub(r"\]\]\]", "]", content)

        # Fix 8: [str, str]] -> [str, str]
        content = re.sub(r"\[str,\s*str\]\]", "[str, str]", content)

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
                if fix_bracket_errors(py_file):
                    fixed_files += 1
                    print(f"  ✓ Fixed: {py_file}")

    print(f"\n✅ Fixed bracket syntax errors in {fixed_files} files")


if __name__ == "__main__":
    main()
