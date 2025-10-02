#!/usr/bin/env python3
"""
Fix syntax errors created by batch_syntax_fixer.py
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

class BatchSyntaxErrorFixer:
    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.fixed_files = set()
        self.total_fixes = 0

    def fix_file(self, file_path: Path) -> Tuple[int, List[str]]:
        """Fix syntax errors in a single file"""
        fixes = []
        fix_count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return 0, [f"Error reading {file_path}: {e}"]

        original_content = content

        # Fix 1: Convert malformed lists back to strings in dictionary values
        content = self.fix_malformed_lists(content)
        if content != original_content:
            fixes.append("Fixed malformed lists")
            fix_count += 1

        # Fix 2: Fix missing quotes around string values
        content = self.fix_missing_quotes(content)
        if content != original_content:
            fixes.append("Fixed missing quotes")
            fix_count += 1

        # Fix 3: Fix dictionary syntax with missing commas
        content = self.fix_dictionary_syntax(content)
        if content != original_content:
            fixes.append("Fixed dictionary syntax")
            fix_count += 1

        # Fix 4: Fix malformed function calls
        content = self.fix_function_calls(content)
        if content != original_content:
            fixes.append("Fixed function calls")
            fix_count += 1

        # Only write if changes were made
        if fix_count > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixed_files.add(str(file_path))
                self.total_fixes += fix_count
            except Exception as e:
                fixes.append(f"Error writing {file_path}: {e}")

        return fix_count, fixes

    def fix_malformed_lists(self, content: str) -> str:
        """Fix lists that should be strings"""
        # Pattern: ["value"] -> "value"
        content = re.sub(r'\["([^"]+)"\]', r'"\1"', content)
        # Pattern: [value] -> "value" (for strings without quotes)
        content = re.sub(r'\[([a-zA-Z_][a-zA-Z0-9_]*)\]', r'"\1"', content)
        # Pattern: [1.0] -> "1.0"
        content = re.sub(r'\[([0-9]+\.[0-9]+)\]', r'"\1"', content)
        # Pattern: [7d] -> "7d"
        content = re.sub(r'\[([0-9]+[a-zA-Z])\]', r'"\1"', content)
        return content

    def fix_missing_quotes(self, content: str) -> str:
        """Fix missing quotes around string values"""
        # Fix missing quotes in dictionary values
        content = re.sub(r'(\w+):\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])', r'\1: "\2"\3', content)
        return content

    def fix_dictionary_syntax(self, content: str) -> str:
        """Fix dictionary syntax issues"""
        # Fix missing commas in dictionaries
        content = re.sub(r'("\w+":\s*"[^"]*")\s*("\w+":)', r'\1, \2', content)
        return content

    def fix_function_calls(self, content: str) -> str:
        """Fix malformed function calls"""
        # Fix function calls with malformed arguments (simplified)
        content = re.sub(r'(\w+)\(\s*([^)]*)\s*([^{]*})', r'\1(\2)', content)
        return content

    def process_directory(self):
        """Process all Python files in the directory"""
        python_files = list(self.directory.rglob('*.py'))
        print(f"🔍 Found {len(python_files)} Python files to process")

        for file_path in python_files:
            print(f"📄 Processing {file_path.relative_to(self.directory)}...")
            fix_count, fixes = self.fix_file(file_path)
            if fix_count > 0:
                print(f"  ✅ Fixed {fix_count} issues: {', '.join(fixes)}")

        print(f"\n🎯 Summary:")
        print(f"📊 Files processed: {len(python_files)}")
        print(f"🔧 Files fixed: {len(self.fixed_files)}")
        print(f"✨ Total fixes: {self.total_fixes}")

def main():
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "tests/unit"

    fixer = BatchSyntaxErrorFixer(directory)
    fixer.process_directory()

if __name__ == "__main__":
    main()