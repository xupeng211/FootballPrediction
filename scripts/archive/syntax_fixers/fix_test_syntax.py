#!/usr/bin/env python3
"""
Enhanced Test Syntax Fixer for FootballPrediction Project

Comprehensive syntax error detection and repair tool that:
1. Scans all test files for syntax errors
2. Applies automated fixes for common issues
3. Generates detailed reports of fixes applied
4. Provides a list of unfixable files for manual review
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FixResult:
    """Result of fixing a file"""

    file_path: Path
    original_valid: bool
    fixed_valid: bool
    fixes_applied: List[str]
    error: Optional[str] = None


class EnhancedTestSyntaxFixer:
    """Enhanced test syntax fixer with comprehensive error detection and repair"""

    def __init__(self):
        self.fixes_count = 0
        self.files_processed = 0
        self.total_fixes_applied = []

    def fix_indentation_error(self, content: str, line_num: int, error_msg: str) -> str:
        """Fix specific indentation errors"""
        lines = content.split("\n")
        if line_num <= len(lines):
            line = lines[line_num - 1]
            stripped = line.lstrip()

            # Common indentation fixes
            if "unexpected indent" in error_msg:
                # Remove excessive indentation
                current_indent = len(line) - len(stripped)
                if current_indent > 4:
                    lines[line_num - 1] = " " * 4 + stripped
                    return "\n".join(lines)

            elif "expected an indented block" in error_msg:
                # Add missing indentation
                current_indent = len(line) - len(stripped)
                if current_indent == 0 and stripped:
                    lines[line_num - 1] = " " * 4 + stripped
                    return "\n".join(lines)

        return content

    def fix_bracket_mismatch(self, content: str) -> str:
        """Fix unbalanced brackets, parentheses, and braces"""
        lines = content.split("\n")
        stack = []
        fixes = []

        for i, line in enumerate(lines):
            for j, char in enumerate(line):
                if char in "([{":
                    stack.append((char, i + 1, j + 1))
                elif char in ")]}":
                    if stack:
                        open_char, line_num, col_num = stack.pop()
                        if (
                            (char == ")" and open_char != "(")
                            or (char == "]" and open_char != "[")
                            or (char == "}" and open_char != "{")
                        ):
                            # Mismatch - add missing opening bracket
                            fixes.append((i + 1, f"Add missing {open_char}"))
                    else:
                        # Unmatched closing bracket - remove it
                        lines[i] = line[:j] + line[j + 1 :]
                        fixes.append((i + 1, f"Remove unmatched {char}"))

        # Check for unclosed brackets at EOF
        if stack:
            for open_char, line_num, col_num in stack[-3:]:  # Last 3 unclosed
                if line_num <= len(lines):
                    lines[line_num - 1] += {"(": ")", "[": "]", "{": "}"}[open_char]
                    fixes.append((line_num, f"Close unclosed {open_char}"))

        return "\n".join(lines), fixes

    def fix_try_except_blocks(self, content: str) -> Tuple[str, List[str]]:
        """Fix malformed try/except/finally blocks"""
        lines = content.split("\n")
        fixes = []
        try_stack = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("try:"):
                try_stack.append(i)
            elif line.startswith(("except ", "except:", "finally:")):
                if try_stack:
                    try_stack.pop()
            elif (
                line
                and not line.startswith("#")
                and not line.startswith(("except ", "except:", "finally:", "try:"))
            ):
                # Non-control line - check if we're in an incomplete try block
                if try_stack:
                    try_line = try_stack[-1]
                    indent = len(lines[try_line]) - len(lines[try_line].lstrip())

                    # Add except block
                    except_line = " " * (indent + 4) + "pass"
                    except_header = " " * indent + "except Exception as e:"

                    lines.insert(i, except_line)
                    lines.insert(i, except_header)
                    fixes.append(f"Added missing except block at line {try_line + 1}")
                    try_stack.pop()
                    i += 2

            i += 1

        # Close any remaining try blocks
        for try_line in try_stack:
            indent = len(lines[try_line]) - len(lines[try_line].lstrip())
            except_line = " " * (indent + 4) + "pass"
            except_header = " " * indent + "except Exception as e:"
            lines.append(except_header)
            lines.append(except_line)
            fixes.append(f"Closed incomplete try block at line {try_line + 1}")

        return "\n".join(lines), fixes

    def fix_function_definitions(self, content: str) -> Tuple[str, List[str]]:
        """Fix function and class definition issues"""
        lines = content.split("\n")
        fixes = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Fix async function definitions
            if re.match(r"async\s+def\s+\w+", stripped):
                # Ensure proper function body
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    if i + 2 < len(lines) and not lines[i + 2].startswith(
                        " " * (len(line) - len(stripped) + 4)
                    ):
                        # Add docstring or pass
                        indent = " " * (len(line) - len(stripped) + 4)
                        lines.insert(i + 1, indent + "pass")
                        fixes.append(f"Added pass to async function at line {i + 1}")

            # Fix class definitions
            elif stripped.startswith("class "):
                # Ensure class body
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    if i + 2 < len(lines) and not lines[i + 2].startswith(
                        " " * (len(line) - len(stripped) + 4)
                    ):
                        # Add docstring or pass
                        indent = " " * (len(line) - len(stripped) + 4)
                        lines.insert(i + 1, indent + "pass")
                        fixes.append(f"Added pass to class at line {i + 1}")

        return "\n".join(lines), fixes

    def fix_string_literals(self, content: str) -> str:
        """Fix unclosed string literals"""
        # Fix triple quotes
        triple_patterns = [
            (r'"""([^"]*|"(?!")|""(?!"))*$', '"""'),
            (r"'''([^']*|'(?!')|''(?!'))*$", "'''"),
        ]

        for pattern, closer in triple_patterns:
            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(
                    pattern, lambda m: m.group(0) + closer, content, flags=re.MULTILINE
                )

        # Fix single quotes
        single_quote_pattern = r"'([^']*|'(?!'))*$"
        if re.search(single_quote_pattern, content, re.MULTILINE):
            content = re.sub(
                single_quote_pattern,
                lambda m: m.group(0) + "'",
                content,
                flags=re.MULTILINE,
            )

        # Fix double quotes
        double_quote_pattern = r'"([^"]*|"(?!"))*$'
        if re.search(double_quote_pattern, content, re.MULTILINE):
            content = re.sub(
                double_quote_pattern,
                lambda m: m.group(0) + '"',
                content,
                flags=re.MULTILINE,
            )

        return content

    def fix_import_statements(self, content: str) -> Tuple[str, List[str]]:
        """Fix import statement issues"""
        lines = content.split("\n")
        fixes = []

        # Group consecutive imports
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("import ") or line.startswith("from "):
                # Find all consecutive imports
                import_block = [i]
                j = i + 1
                while j < len(lines) and (
                    lines[j].strip().startswith("import ") or lines[j].strip().startswith("from ")
                ):
                    import_block.append(j)
                    j += 1

                # Sort imports if they're not already sorted
                if len(import_block) > 1:
                    imports = [lines[k] for k in import_block]
                    sorted_imports = sorted(imports, key=lambda x: x.strip())
                    if imports != sorted_imports:
                        for k, idx in enumerate(import_block):
                            lines[idx] = sorted_imports[k]
                        fixes.append(f"Sorted imports at lines {i + 1}-{j}")

                i = j
            else:
                i += 1

        return "\n".join(lines), fixes

    def validate_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax and return error message if invalid"""
        try:
            ast.parse(content)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Unknown error: {str(e)}"

    def process_file(self, file_path: Path) -> FixResult:
        """Process a single test file"""
        try:
            original_content = file_path.read_text(encoding="utf-8")
            original_valid, original_error = self.validate_syntax(original_content)

            if original_valid:
                return FixResult(file_path, True, True, [], "File already valid")

            content = original_content
            all_fixes = []

            # Apply fixes
            if original_error:
                content = self.fix_indentation_error(
                    content,
                    (
                        int(original_error.split(":")[0].split()[-1])
                        if "Line" in original_error
                        else 1
                    ),
                    original_error,
                )

            # Fix bracket mismatches
            content, bracket_fixes = self.fix_bracket_mismatch(content)
            all_fixes.extend([f"Line {line}: {fix}" for line, fix in bracket_fixes])

            # Fix try/except blocks
            content, try_fixes = self.fix_try_except_blocks(content)
            all_fixes.extend(try_fixes)

            # Fix function definitions
            content, func_fixes = self.fix_function_definitions(content)
            all_fixes.extend(func_fixes)

            # Fix string literals
            content = self.fix_string_literals(content)
            if content != original_content:
                all_fixes.append("Fixed string literals")

            # Fix import statements
            content, import_fixes = self.fix_import_statements(content)
            all_fixes.extend(import_fixes)

            # Validate result
            fixed_valid, fixed_error = self.validate_syntax(content)

            if content != original_content and fixed_valid:
                file_path.write_text(content, encoding="utf-8")
                self.total_fixes_applied.extend(all_fixes)
                return FixResult(file_path, False, True, all_fixes)

            return FixResult(file_path, False, fixed_valid, [], fixed_error)

        except Exception as e:
            return FixResult(file_path, False, False, [], f"Processing error: {str(e)}")

    def scan_and_fix(self, test_dir: Path) -> Dict[str, List[FixResult]]:
        """Scan and fix all test files"""
        results = {"fixed": [], "failed": [], "already_valid": [], "unfixable": []}

        print(f"🔍 Scanning {test_dir} for test files...")

        test_files = list(test_dir.rglob("test_*.py"))
        if not test_files:
            test_files = list(test_dir.rglob("*.py"))

        print(f"📊 Found {len(test_files)} test files")

        for i, test_file in enumerate(test_files, 1):
            print(f"🔧 Processing [{i}/{len(test_files)}]: {test_file.name}")

            result = self.process_file(test_file)
            self.files_processed += 1

            if result.original_valid and result.fixed_valid:
                results["already_valid"].append(result)
                print("  ✅ Already valid")
            elif not result.original_valid and result.fixed_valid:
                results["fixed"].append(result)
                self.fixes_count += len(result.fixes_applied)
                print(f"  ✅ Fixed ({len(result.fixes_applied)} fixes)")
            elif not result.original_valid and not result.fixed_valid:
                results["unfixable"].append(result)
                print(f"  ❌ Could not fix: {result.error}")
            else:
                results["failed"].append(result)
                print("  ⚠️ Unexpected state")

        return results

    def generate_report(self, results: Dict[str, List[FixResult]], output_dir: Path):
        """Generate detailed report of fixes applied"""
        report_file = output_dir / "TEST_SYNTAX_FIX_REPORT.md"
        unfixed_file = output_dir / "UNFIXED_TESTS.md"

        # Main report
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Test Syntax Fix Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Files processed**: {self.files_processed}\n")
            f.write(f"- **Files fixed**: {len(results['fixed'])}\n")
            f.write(f"- **Files already valid**: {len(results['already_valid'])}\n")
            f.write(f"- **Files unfixable**: {len(results['unfixable'])}\n")
            f.write(f"- **Total fixes applied**: {self.fixes_count}\n\n")

            if results["fixed"]:
                f.write("## Fixed Files\n\n")
                for result in results["fixed"]:
                    f.write(f"### {result.file_path.name}\n")
                    for fix in result.fixes_applied:
                        f.write(f"- {fix}\n")
                    f.write("\n")

            if results["unfixable"]:
                f.write("## Unfixable Files\n\n")
                for result in results["unfixable"]:
                    f.write(f"### {result.file_path.name}\n")
                    f.write(f"- Error: {result.error}\n")
                    f.write("\n")

        # Unfixed files list
        if results["unfixable"]:
            with open(unfixed_file, "w", encoding="utf-8") as f:
                f.write("# Unfixable Test Files\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(
                    "These files could not be automatically fixed and require manual attention:\n\n"
                )

                for result in results["unfixable"]:
                    f.write(f"## {result.file_path}\n\n")
                    f.write(f"**Error**: {result.error}\n\n")
                    f.write("```python\n")
                    try:
                        content = result.file_path.read_text(encoding="utf-8")
                        f.write(content[:500])  # First 500 chars
                        if len(content) > 500:
                            f.write("\n...")
                        f.write("\n```\n\n")
                    except Exception:
                        f.write("Could not read file content\n")
                    f.write("---\n\n")

        print("📄 Reports generated:")
        print(f"   - {report_file}")
        if results["unfixable"]:
            print(f"   - {unfixed_file}")


def main():
    """Main function"""
    test_dir = Path("tests")
    output_dir = Path("docs/_reports")
    output_dir.mkdir(exist_ok=True)

    if not test_dir.exists():
        print("❌ Tests directory not found!")
        return 1

    fixer = EnhancedTestSyntaxFixer()
    results = fixer.scan_and_fix(test_dir)

    # Generate reports
    fixer.generate_report(results, output_dir)

    # Summary
    total_files = sum(len(files) for files in results.values())
    success_rate = len(results["fixed"]) / total_files * 100 if total_files > 0 else 0

    print("\n🎯 Summary:")
    print(f"📊 Total files: {total_files}")
    print(f"✅ Fixed: {len(results['fixed'])} ({success_rate:.1f}%)")
    print(f"🟡 Already valid: {len(results['already_valid'])}")
    print(f"🔴 Unfixable: {len(results['unfixable'])}")

    if results["unfixable"]:
        print(f"\n⚠️ Manual attention required for {len(results['unfixable'])} files")
        print(f"   See {output_dir}/UNFIXED_TESTS.md for details")

    return len(results["unfixable"]) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
