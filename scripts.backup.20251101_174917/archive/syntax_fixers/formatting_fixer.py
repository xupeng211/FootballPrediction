#!/usr/bin/env python3
"""
Formatting fixer for Phase 4 Batch 3.

Fixes I001 (import order) and E501 (line length) errors.
"""

from pathlib import Path
from typing import List


class FormattingFixer:
    """Fixer for formatting issues."""

    def __init__(self, tests_dir: str = "tests"):
        self.tests_dir = Path(tests_dir)
        self.files_fixed = 0
        self.total_fixes = 0

    def fix_file(self, file_path: Path) -> int:
        """Fix formatting issues in a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            fixes_made = 0

            # Fix line length issues (break long lines)
            content = self._fix_line_length(content)
            fixes_made += len(original_content.split("\n")) - len(content.split("\n"))

            # Fix import order
            content = self._fix_import_order(content)
            if content != original_content:
                fixes_made += 1

            if fixes_made > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return fixes_made

            return 0

        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
            return 0

    def _fix_line_length(self, content: str, max_length: int = 88) -> str:
        """Fix line length issues."""
        lines = content.split("\n")
        result_lines = []

        for line in lines:
            if len(line) <= max_length:
                result_lines.append(line)
            else:
                # Break long lines at logical points
                broken_lines = self._break_long_line(line, max_length)
                result_lines.extend(broken_lines)

        return "\n".join(result_lines)

    def _break_long_line(self, line: str, max_length: int) -> List[str]:
        """Break a long line into multiple lines."""
        # Try to break at common break points
        break_points = [
            "assert ",
            "with ",
            "return ",
            "from ",
            "import ",
            "elif ",
            "if ",
            "for ",
            ", ",
            " + ",
            " == ",
            " != ",
            " >= ",
            " <= ",
            " > ",
            " < ",
            " and ",
            " or ",
        ]

        for break_point in break_points:
            if break_point in line and len(line) > max_length:
                # Find the best break position
                for i in range(max_length - 10, max_length + 10):
                    if i < len(line) and line[i : i + len(break_point)] == break_point:
                        # Break here
                        if i > 0 and i < len(line):
                            first_line = line[:i].rstrip()
                            second_line = " " * 8 + line[i:].lstrip()
                            return [first_line, second_line] + self._break_long_line(
                                second_line, max_length
                            )[1:]

        # If no good break point found, break at max_length
        if len(line) > max_length:
            first_line = line[:max_length]
            second_line = " " * 8 + line[max_length:]
            return [first_line, second_line] + self._break_long_line(second_line, max_length)[1:]

        return [line]

    def _fix_import_order(self, content: str) -> str:
        """Fix import order issues."""
        lines = content.split("\n")
        import_section = []
        other_lines = []
        in_import_section = True

        # Separate imports from other code
        for line in lines:
            stripped = line.strip()
            if in_import_section:
                if stripped.startswith(("import ", "from ")) or stripped == "":
                    import_section.append(line)
                else:
                    in_import_section = False
                    other_lines.append(line)
            else:
                other_lines.append(line)

        # Sort imports (basic approach)
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for line in import_section:
            stripped = line.strip()
            if stripped.startswith("import "):
                module = stripped.replace("import ", "").split(".")[0]
            elif stripped.startswith("from "):
                module = stripped.replace("from ", "").split(".")[0].split(" import")[0]
            else:
                other_lines.append(line)
                continue

            if module in [
                "os",
                "sys",
                "pathlib",
                "json",
                "datetime",
                "random",
                "asyncio",
                "typing",
                "re",
                "math",
                "time",
            ]:
                stdlib_imports.append(line)
            elif module in ["pytest", "tests"]:
                local_imports.append(line)
            else:
                third_party_imports.append(line)

        # Rebuild content with sorted imports
        sorted_imports = (
            sorted(stdlib_imports)
            + [""]
            + sorted(third_party_imports)
            + [""]
            + sorted(local_imports)
        )
        sorted_imports = [line for line in sorted_imports if line != ""]

        return "\n".join(sorted_imports + other_lines)

    def fix_all_files(self) -> None:
        """Fix all files in the tests directory."""
        print("Starting formatting fix for tests directory...")

        python_files = list(self.tests_dir.rglob("*.py"))

        for file_path in python_files:
            if file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
                fixes = self.fix_file(file_path)
                if fixes > 0:
                    self.files_fixed += 1
                    self.total_fixes += fixes
                    print(f"Fixed {file_path} ({fixes} fixes)")

        print("\n=== Formatting Fix Summary ===")
        print(f"Files fixed: {self.files_fixed}")
        print(f"Total fixes: {self.total_fixes}")
        print(f"✅ Successfully fixed formatting issues in {self.files_fixed} files!")


if __name__ == "__main__":
    fixer = FormattingFixer()
    fixer.fix_all_files()
