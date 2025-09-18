#!/usr/bin/env python3
"""
Batch fix Python import issues, focusing on 'typing' and other common modules.
This script intelligently adds missing imports and merges them with existing import statements.
"""

import re
from pathlib import Path

# A comprehensive map of names to their required import statements.
IMPORT_MAP = {
    "Any": "typing",
    "Dict": "typing",
    "List": "typing",
    "Optional": "typing",
    "Union": "typing",
    "Sequence": "typing",
    "Set": "typing",
    "Generator": "typing",
    "AsyncGenerator": "typing",
    "Callable": "typing",
    "Tuple": "typing",
    "Type": "typing",
    "datetime": "datetime",
    "timedelta": "datetime",
    "timezone": "datetime",
    "asyncio": "asyncio",
    "patch": "unittest.mock",
    "Mock": "unittest.mock",
    "MagicMock": "unittest.mock",
    "AsyncMock": "unittest.mock",
    "pytest_asyncio": "pytest_asyncio",
}

# Group imports by their source module for consolidation.
MODULE_GROUP = {
    "typing": [k for k, v in IMPORT_MAP.items() if v == "typing"],
    "datetime": [k for k, v in IMPORT_MAP.items() if v == "datetime"],
    "unittest.mock": [k for k, v in IMPORT_MAP.items() if v == "unittest.mock"],
}


def fix_imports_in_file(file_path: Path):
    """Analyzes a single Python file and fixes its import statements."""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find all words in the file to check against our import map.
        words_in_file = set(re.findall(r"\b(\w+)\b", content))

        needed_modules = {
            IMPORT_MAP[word] for word in words_in_file if word in IMPORT_MAP
        }

        # Process grouped imports (typing, datetime, etc.)
        for module, names in MODULE_GROUP.items():
            if module in needed_modules:
                # Find what's needed vs. what's already imported from this module.
                needed_names = {name for name in names if name in words_in_file}

                for i, line in enumerate(lines):
                    match = re.match(rf"from {module} import (.+)", line)
                    if match:
                        imported_names = {
                            name.strip()
                            for name in match.group(1)
                            .replace("(", "")
                            .replace(")", "")
                            .split(",")
                        }
                        all_names = sorted(list(imported_names | needed_names))
                        new_import_line = f"from {module} import {', '.join(all_names)}"
                        if line != new_import_line:
                            lines[i] = new_import_line
                            print(f"🔧 Updated '{module}' import in {file_path}")
                        needed_modules.remove(module)
                        break

        # Add module imports for remaining needed modules (like 'import asyncio')
        if needed_modules:
            # Find the first non-docstring/comment line to insert new imports.
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip() and not (line.startswith(('"', "'", "#"))):
                    insert_pos = i
                    break

            for module in sorted(list(needed_modules)):
                import_statement = f"import {module}"
                if import_statement not in content:
                    lines.insert(insert_pos, import_statement)
                    print(f"➕ Added '{import_statement}' to {file_path}")

        new_content = "\n".join(lines)
        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")


def main():
    """Main function to scan 'src' and 'tests' directories and fix imports."""
    for target_dir in ["src", "tests"]:
        print(f"\n🔍 Scanning directory: {target_dir}")
        for py_file in Path(target_dir).rglob("*.py"):
            fix_imports_in_file(py_file)
    print("\n✅ Import fixing process complete.")


if __name__ == "__main__":
    main()
