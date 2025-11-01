#!/usr/bin/env python3
"""
Batch syntax fixer for tests/unit module
Target: Fix common syntax errors automatically
"""

import re
from pathlib import Path
from typing import List, Tuple


class SyntaxFixer:
    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.fixed_files = set()
        self.total_fixes = 0

    def fix_file(self, file_path: Path) -> Tuple[int, List[str]]:
        """Fix syntax errors in a single file"""
        fixes = []
        fix_count = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return 0, [f"Error reading {file_path}: {e}"]

        original_content = content

        # Fix 1: Missing quotes in strings
        content = self.fix_missing_quotes(content)
        if content != original_content:
            fixes.append("Fixed missing quotes")
            fix_count += 1

        # Fix 2: Mismatched brackets
        content = self.fix_bracket_mismatches(content)
        if content != original_content and content != original_content:
            fixes.append("Fixed bracket mismatches")
            fix_count += 1

        # Fix 3: Missing colons after function/class definitions
        content = self.fix_missing_colons(content)
        if content != original_content:
            fixes.append("Fixed missing colons")
            fix_count += 1

        # Fix 4: Fix trailing commas in function calls
        content = self.fix_trailing_commas(content)
        if content != original_content:
            fixes.append("Fixed trailing commas")
            fix_count += 1

        # Only write if changes were made
        if fix_count > 0:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixed_files.add(str(file_path))
                self.total_fixes += fix_count
            except Exception as e:
                fixes.append(f"Error writing {file_path}: {e}")

        return fix_count, fixes

    def fix_missing_quotes(self, content: str) -> str:
        """Fix missing quotes around string literals"""
        # Pattern: missing opening quote after [ or {
        content = re.sub(r"(\[|\{)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,", r'\1"\2",', content)
        content = re.sub(r"(\[|\{)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\]", r'\1"\2"', content)
        return content

    def fix_bracket_mismatches(self, content: str) -> str:
        """Fix common bracket mismatches"""
        # Fix missing closing bracket
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "]" in line and "[" not in line and i > 0:
                # Check if previous line has unmatched opening bracket
                prev_line = lines[i - 1]
                if prev_line.count("[") > prev_line.count("]"):
                    lines[i] = line.replace("]", "]")
        return "\n".join(lines)

    def fix_missing_colons(self, content: str) -> str:
        """Fix missing colons after function/class definitions"""
        # Pattern: def/class without colon
        content = re.sub(r"(def\s+\w+\([^)]*\))\s*$", r"\1:", content, flags=re.MULTILINE)
        content = re.sub(r"(class\s+\w+\([^)]*\))\s*$", r"\1:", content, flags=re.MULTILINE)
        return content

    def fix_trailing_commas(self, content: str) -> str:
        """Fix trailing commas in function calls and lists"""
        # Remove trailing commas before closing brackets
        content = re.sub(r",\s*([)\]}])", r"\1", content)
        return content

    def process_directory(self):
        """Process all Python files in the directory"""
        python_files = list(self.directory.rglob("*.py"))
        print(f"🔍 Found {len(python_files)} Python files to process")

        for file_path in python_files:
            print(f"📄 Processing {file_path.relative_to(self.directory)}...")
            fix_count, fixes = self.fix_file(file_path)
            if fix_count > 0:
                print(f"  ✅ Fixed {fix_count} issues: {', '.join(fixes)}")

        print("\n🎯 Summary:")
        print(f"📊 Files processed: {len(python_files)}")
        print(f"🔧 Files fixed: {len(self.fixed_files)}")
        print(f"✨ Total fixes: {self.total_fixes}")


def main():
    import sys

    directory = sys.argv[1] if len(sys.argv) > 1 else "tests/unit"

    fixer = SyntaxFixer(directory)
    fixer.process_directory()


if __name__ == "__main__":
    main()
