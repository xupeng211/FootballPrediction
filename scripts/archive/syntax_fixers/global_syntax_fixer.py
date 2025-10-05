#!/usr/bin/env python3
"""
Global syntax error fixer based on Phase 3 validated repair patterns.
Fixes common syntax errors automatically:
1. Dictionary access: result'key' -> result['key']
2. String quotes: "value": [value] -> "value": "value"
3. Function definitions: extra colons in docstrings
4. Simple statement separation: missing colons and commas
"""

import re
import sys
from pathlib import Path
from typing import Tuple


class GlobalSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.errors_files = []
        self.total_fixes = 0

        # 基于 Phase 3 验证的修复模式
        self.patterns = [
            # 模式1: 字典访问语法错误 result"key" -> result["key"]
            (r'(\w+)"([^"]+)"', r'\1["\2"]'),
            # 模式2: 字符串值语法错误 "key": [value] -> "key": "value"
            (r'":\s*\[([^\]]+)\](?=\s*[,}])', r': "\1"'),
            # 模式3: 缺少冒号的字典项 "key" value -> "key": value
            (r'"([^"]+)"\s+([a-zA-Z_]\w*)', r'"\1": \2'),
            # 模式4: 函数定义后多余冒号 def method():""" -> def method():"""
            (r'def\s+(\w+)\([^)]*\):"""', r'def \1(\n    """'),
            # 模式5: assert语句后多余冒号 assert condition: -> assert condition
            (r"assert\s+([^:\n]+):", r"assert \1"),
            # 模式6: 修复简单的括号不匹配
            (r"(\w+)\s*\[\s*([^\]]+)(?<!])$", r"\1[\2]"),
            # 模式7: 修复未闭合的字符串
            (r'"([^"]*?)(?=\n)', r'"\1"'),
            # 模式8: 修复常见的类型注解错误
            (r"(\w+):\s*([a-zA-Z_]\w*)\s*=", r"\1 = \2"),  # 简化类型注解
        ]

    def fix_file(self, file_path: Path) -> Tuple[bool, int]:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 应用所有修复模式
            for pattern, replacement in self.patterns:
                new_content, count = re.subn(pattern, replacement, content)
                if count > 0:
                    content = new_content
                    fixes_count += count

            # 如果有修复，写回文件
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True, fixes_count

            return False, 0

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False, 0

    def fix_directory(
        self, directory: Path, file_pattern: str = "*.py"
    ) -> Tuple[int, int]:
        """修复目录下所有匹配的文件"""
        fixed_count = 0
        total_fixes = 0

        # 递归查找所有Python文件
        for file_path in directory.rglob(file_pattern):
            if file_path.is_file():
                fixed, fixes = self.fix_file(file_path)
                if fixed:
                    fixed_count += 1
                    total_fixes += fixes
                    self.fixed_files.append(str(file_path))
                    print(f"Fixed {file_path} ({fixes} fixes)")
                else:
                    self.errors_files.append(str(file_path))

        return fixed_count, total_fixes

    def fix_tests_directory(self, tests_dir: str = "tests") -> Tuple[int, int]:
        """修复tests目录下的所有文件"""
        print(f"Starting global syntax fix for {tests_dir} directory...")

        tests_path = Path(tests_dir)
        if not tests_path.exists():
            print(f"Tests directory {tests_dir} not found!")
            return 0, 0

        fixed_count, total_fixes = self.fix_directory(tests_path)

        print("\n=== Global Syntax Fix Summary ===")
        print(f"Files fixed: {fixed_count}")
        print(f"Total fixes: {total_fixes}")
        print(f"Files processed: {len(self.fixed_files) + len(self.errors_files)}")

        if self.fixed_files:
            print("\nFixed files:")
            for file_path in self.fixed_files[:10]:  # 只显示前10个
                print(f"  - {file_path}")
            if len(self.fixed_files) > 10:
                print(f"  ... and {len(self.fixed_files) - 10} more files")

        return fixed_count, total_fixes


def main():
    if len(sys.argv) > 1:
        tests_dir = sys.argv[1]
    else:
        tests_dir = "tests"

    fixer = GlobalSyntaxFixer()
    fixed_count, total_fixes = fixer.fix_tests_directory(tests_dir)

    if fixed_count > 0:
        print(
            f"\n✅ Successfully fixed syntax errors in {fixed_count} files with {total_fixes} total fixes!"
        )
        return 0
    else:
        print("\n⚠️ No syntax errors were fixed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
