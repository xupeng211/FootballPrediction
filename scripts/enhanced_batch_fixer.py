#!/usr/bin/env python3
"""
增强版批量语法错误修复工具
Enhanced Batch Syntax Fixer

专门处理复杂的语法错误
"""

import ast
import re
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedBatchFixer:
    """增强版批量语法修复器"""

    def __init__(self, src_dir: str = 'src'):
        self.src_dir = Path(src_dir)
        self.fix_stats = defaultdict(int)

    def fix_all_errors(self):
        """修复所有错误"""
        # 首先处理invalid_character错误（最容易修复）
        self.fix_invalid_characters()

        # 然后处理unterminated_string错误
        self.fix_unterminated_strings()

        # 处理import语句连接问题
        self.fix_import_concatenation()

        # 处理invalid_syntax（需要更智能的修复）
        self.fix_invalid_syntax()

        # 最后处理mismatched_parentheses
        self.fix_mismatched_parentheses()

        self.print_statistics()

    def fix_invalid_characters(self):
        """修复无效字符错误"""
        char_replacements = {
            '（': '(',
            '）': ')',
            '，': ',',
            '：': ':',
            '；': ';',
            '：': ':',
            '！': '!',
            '？': '?',
            '。': '.',
            '、': ',',
            '【': '[',
            '】': ']',
            '｛': '{',
            '｝': '}',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '\u3001': ',',  # 顿号
            '\u3002': '.',  # 句号
            '\uff1a': ':',  # 冒号
            '\uff1b': ';',  # 分号
            '\uff1f': '?',  # 问号
            '\uff01': '!',  # 感叹号
            '\uff08': '(',  # 左圆括号
            '\uff09': ')',  # 右圆括号
        }

        fixed_count = 0
        for py_file in self.src_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                for invalid, valid in char_replacements.items():
                    if invalid in content:
                        content = content.replace(invalid, valid)
                        self.fix_stats[f'替换字符 {invalid}->{valid}'] += 1

                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
            except Exception as e:
                logger.error(f"处理文件 {py_file} 时出错: {e}")

        logger.info(f"修复无效字符错误: {fixed_count} 个文件")

    def fix_unterminated_strings(self):
        """修复未终止的字符串"""
        fixed_count = 0

        for py_file in self.src_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                modified = False
                new_lines = []
                in_string = False
                string_char = None
                escape_next = False

                for line in lines:
                    new_line = []
                    i = 0
                    while i < len(line):
                        char = line[i]

                        if escape_next:
                            new_line.append(char)
                            escape_next = False
                            i += 1
                            continue

                        if not in_string:
                            if char in ('"', "'"):
                                # 检查是否是三引号
                                if i + 2 < len(line) and line[i:i+3] in ('"""', "'''"):
                                    in_string = True
                                    string_char = line[i:i+3]
                                    new_line.append(line[i:i+3])
                                    i += 3
                                else:
                                    in_string = True
                                    string_char = char
                                    new_line.append(char)
                                    i += 1
                            else:
                                new_line.append(char)
                                i += 1
                        else:
                            # 在字符串中
                            if len(string_char) == 1:
                                if char == string_char and line[i-1] != '\\':
                                    in_string = False
                                    string_char = None
                            else:  # 三引号
                                if i + 2 < len(line) and line[i:i+3] == string_char:
                                    in_string = False
                                    string_char = None
                                    new_line.append(line[i:i+3])
                                    i += 3
                                    continue

                            new_line.append(char)
                            i += 1

                    # 行结束时如果字符串未闭合，添加闭合
                    if in_string and len(string_char) == 1:
                        new_line.append(string_char)
                        in_string = False
                        string_char = None
                        modified = True

                    new_lines.append(''.join(new_line))

                if modified:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    fixed_count += 1
                    self.fix_stats['修复未终止字符串'] += 1

            except Exception as e:
                logger.error(f"处理文件 {py_file} 时出错: {e}")

        logger.info(f"修复未终止字符串错误: {fixed_count} 个文件")

    def fix_import_concatenation(self):
        """修复import语句连接问题"""
        patterns = [
            (r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)import', r'import \1\nimport'),
            (r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)import', r'from \1 import'),
            (r'([a-zA-Z_][a-zA-Z0-9_]*)import\s+([a-zA-Z_])', r'\1\nimport \2'),
            (r'import\s+([a-zA-Z_][a-zA-Z0-9_]*),([a-zA-Z_])', r'import \1,\n\2'),
        ]

        fixed_count = 0
        for py_file in self.src_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                for pattern, replacement in patterns:
                    content = re.sub(pattern, replacement, content)

                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
                    self.fix_stats['修复import连接'] += 1
            except Exception as e:
                logger.error(f"处理文件 {py_file} 时出错: {e}")

        logger.info(f"修复import连接错误: {fixed_count} 个文件")

    def fix_invalid_syntax(self):
        """修复复杂的语法错误"""
        fixed_count = 0

        for py_file in self.src_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # 1. 修复缺失的冒号
                content = self.fix_missing_colons(content)

                # 2. 修复函数/类定义
                content = self.fix_function_class_definitions(content)

                # 3. 修复行尾的注释
                content = self.fix_line_comments(content)

                # 4. 修复字典语法
                content = self.fix_dict_syntax(content)

                # 5. 修复return语句
                content = self.fix_return_statements(content)

                # 6. 修复async/await语法
                content = self.fix_async_syntax(content)

                if content != original_content:
                    # 验证修复后的语法
                    try:
                        ast.parse(content)
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        fixed_count += 1
                        self.fix_stats['修复复杂语法'] += 1
                    except SyntaxError:
                        # 如果修复后仍有错误，记录但不保存
                        logger.warning(f"文件 {py_file} 修复后仍有语法错误")

            except Exception as e:
                logger.error(f"处理文件 {py_file} 时出错: {e}")

        logger.info(f"修复复杂语法错误: {fixed_count} 个文件")

    def fix_missing_colons(self, content: str) -> str:
        """修复缺失的冒号"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()
            # 需要冒号但缺少冒号的情况
            keywords = ['def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally', 'with ', 'async def']

            for keyword in keywords:
                if stripped.startswith(keyword) and ':' not in line and not stripped.startswith('#'):
                    # 确保不是注释或字符串
                    if not line.strip().startswith('#'):
                        line = line.rstrip() + ':'
                        self.fix_stats['添加缺失冒号'] += 1
                        break

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_function_class_definitions(self, content: str) -> str:
        """修复函数和类定义"""
        # 修复函数定义格式错误
        content = re.sub(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*([^{:\n])',
                        r'def \1(\2):\3', content)

        # 修复类定义格式错误
        content = re.sub(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(\([^)]*\))?\s*([^{:\n])',
                        r'class \1\2:\3', content)

        return content

    def fix_line_comments(self, content: str) -> str:
        """修复行注释"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 处理行尾缺少空格的注释
            if '#' in line and not line.strip().endswith('#'):
                # 查找代码和注释的分界
                parts = line.split('#', 1)
                if len(parts) == 2 and parts[0].strip() and not parts[0].endswith(' '):
                    line = parts[0] + '  #' + parts[1]
                    self.fix_stats['修复注释格式'] += 1

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_dict_syntax(self, content: str) -> str:
        """修复字典语法"""
        # 修复字典键值对之间缺少逗号
        content = re.sub(r'(".*?")\s*\n\s*(".*?")\s*:', r'\1,\n    \2:', content)
        content = re.sub(r"('.*?')\s*\n\s*('.*?')\s*:", r"\1,\n    \2:", content)

        return content

    def fix_return_statements(self, content: str) -> str:
        """修复return语句"""
        # 修复换行的return语句
        content = re.sub(r'return\s*\n\s+([a-zA-Z_])', r'return \1', content)

        return content

    def fix_async_syntax(self, content: str) -> str:
        """修复async/await语法"""
        # 修复async def换行
        content = re.sub(r'async\s*\n\s*def\s+([a-zA-Z_])', r'async def \1', content)

        # 修复await换行
        content = re.sub(r'await\s*\n\s+([a-zA-Z_])', r'await \1', content)

        return content

    def fix_mismatched_parentheses(self):
        """修复括号不匹配"""
        fixed_count = 0

        for py_file in self.src_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                lines = content.split('\n')
                fixed_lines = []

                for line in lines:
                    # 简单的括号平衡检查
                    open_parens = line.count('(') + line.count('[') + line.count('{')
                    close_parens = line.count(')') + line.count(']') + line.count('}')

                    if open_parens > close_parens:
                        # 添加缺失的闭合括号
                        line += ')' * (open_parens - close_parens)
                        self.fix_stats['修复括号匹配'] += 1
                    elif close_parens > open_parens:
                        # 删除多余的闭合括号
                        diff = close_parens - open_parens
                        for _ in range(diff):
                            for i in range(len(line)-1, -1, -1):
                                if line[i] in ')}]':
                                    line = line[:i] + line[i+1:]
                                    break

                    fixed_lines.append(line)

                content = '\n'.join(fixed_lines)

                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1

            except Exception as e:
                logger.error(f"处理文件 {py_file} 时出错: {e}")

        logger.info(f"修复括号不匹配错误: {fixed_count} 个文件")

    def print_statistics(self):
        """打印修复统计"""
        print("\n" + "="*80)
        print("修复统计")
        print("="*80)
        total_fixes = sum(self.fix_stats.values())
        print(f"总修复操作数: {total_fixes}")
        print("\n各类修复统计:")
        for fix_type, count in sorted(self.fix_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {fix_type}: {count} 次")


def main():
    """主函数"""
    print("开始增强版批量语法修复...")
    fixer = EnhancedBatchFixer()
    fixer.fix_all_errors()
    print("\n批量修复完成！")


if __name__ == '__main__':
    main()