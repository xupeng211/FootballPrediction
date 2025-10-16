#!/usr/bin/env python3
"""
针对性语法错误修复工具
Targeted Syntax Error Fixer

针对特定的语法错误模式进行精确修复
"""

import ast
import re
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TargetedSyntaxFixer:
    """针对性语法错误修复器"""

    def __init__(self, src_dir: str = 'src'):
        self.src_dir = Path(src_dir)
        self.fixes_count = 0

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用针对性修复
            content = self.fix_docstring_issues(content)
            content = self.fix_import_concatenation(content)
            content = self.fix_chinese_punctuation(content)
            content = self.fix_missing_colons(content)
            content = self.fix_bracket_issues(content)
            content = self.fix_string_issues(content)

            # 验证修复结果
            try:
                ast.parse(content)
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"✅ 修复: {file_path}")
                    self.fixes_count += 1
                return True
            except SyntaxError as e:
                # 如果仍然有错误，打印错误信息
                logger.warning(f"⚠️  文件仍有错误: {file_path} - {e.msg}")
                return False

        except Exception as e:
            logger.error(f"❌ 处理文件失败 {file_path}: {e}")
            return False

    def fix_docstring_issues(self, content: str) -> str:
        """修复文档字符串问题"""
        # 修复开头缺少引号的文档字符串
        content = re.sub(r'^"([^"\n]*\n)', r'"""\1', content)
        content = re.sub(r"^'([^'\n]*\n)", r"'''\1", content)

        # 修复连接到文档字符串后的代码
        content = re.sub(r'"""([^"]*)"""([a-zA-Z_])', r'"""\1\n\2', content)
        content = re.sub(r"'''([^']*)'''([a-zA-Z_])", r"'''\1\n\2", content)

        # 处理特殊情况：文档字符串后直接跟import
        content = re.sub(r'("[^"]*\n\s*)import', r'\1\nimport', content)
        content = re.sub(r"('[^']*\n\s*)import", r"\1\nimport", content)

        return content

    def fix_import_concatenation(self, content: str) -> str:
        """修复import语句连接问题"""
        # 修复各种import连接情况
        patterns = [
            (r'([a-zA-Z_])import\s+([a-zA-Z_])', r'\1\nimport \2'),
            (r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)import', r'import \1\nimport'),
            (r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)import', r'from \1 import'),
            (r'([a-zA-Z_][a-zA-Z0-9_]*),([a-zA-Z_])', r'\1,\n\2'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        return content

    def fix_chinese_punctuation(self, content: str) -> str:
        """修复中文标点符号问题"""
        # 中文字符后跟代码的情况
        patterns = [
            (r'([。)！））;；])import', r'\1\nimport'),
            (r'([。)！））;；])def', r'\1\ndef'),
            (r'([。)！））;；])class', r'\1\nclass'),
            (r'([。)！））;；])#', r'\1\n#'),
            (r'([。)！））;；])([a-zA-Z_])', r'\1\n\2'),
            (r'([。）！））])\s*$', r'\1'),  # 行尾的中文标点
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        return content

    def fix_missing_colons(self, content: str) -> str:
        """修复缺失的冒号"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()
            # 检查需要冒号但缺少冒号的情况
            if any(stripped.startswith(kw) for kw in ['def ', 'class ', 'if ', 'elif ', 'for ', 'while ', 'with ', 'try:', 'except', 'else', 'finally']):
                if ':' not in line and not stripped.endswith('#'):
                    # 确保不是注释或字符串
                    if not line.strip().startswith('#'):
                        line = line.rstrip() + ':'
            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_bracket_issues(self, content: str) -> str:
        """修复括号问题"""
        # 简单的括号平衡修复
        open_brackets = '([{'
        close_brackets = ')]}'
        stack = []
        lines = content.split('\n')
        result = []

        for line in lines:
            for i, char in enumerate(line):
                if char in open_brackets:
                    stack.append((char, len(result), i))
                elif char in close_brackets:
                    if stack:
                        stack.pop()
                    else:
                        # 删除多余的闭合括号
                        line = line[:i] + line[i+1:]
                        break

            result.append(line)

        # 在文件末尾添加未闭合的括号
        if stack:
            close_map = {'(': ')', '[': ']', '{': '}'}
            result[-1] += ''.join(close_map[b[0]] for b in reversed(stack))

        return '\n'.join(result)

    def fix_string_issues(self, content: str) -> str:
        """修复字符串问题"""
        # 修复未闭合的字符串
        lines = content.split('\n')
        in_string = False
        string_char = None
        result = []

        for line in lines:
            fixed_line = []
            i = 0
            while i < len(line):
                char = line[i]

                if not in_string:
                    if char in ('"', "'"):
                        # 检查是否是三引号
                        if i + 2 < len(line) and line[i:i+3] in ('"""', "'''"):
                            in_string = True
                            string_char = line[i:i+3]
                            fixed_line.append(line[i:i+3])
                            i += 3
                        else:
                            in_string = True
                            string_char = char
                            fixed_line.append(char)
                            i += 1
                    else:
                        fixed_line.append(char)
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
                            fixed_line.append(line[i:i+3])
                            i += 3
                            continue

                    fixed_line.append(char)
                    i += 1

            # 如果行结束时字符串未闭合，添加闭合
            if in_string and len(string_char) == 1:
                fixed_line.append(string_char)
                in_string = False
                string_char = None

            result.append(''.join(fixed_line))

        return '\n'.join(result)

    def fix_module(self, module_name: str):
        """修复整个模块"""
        module_path = self.src_dir / module_name
        if not module_path.exists():
            logger.error(f"模块不存在: {module_name}")
            return

        logger.info(f"\n开始修复模块: {module_name}")
        py_files = list(module_path.rglob('*.py'))

        for py_file in py_files:
            self.fix_file(py_file)

        logger.info(f"模块 {module_name} 修复完成")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='针对性语法错误修复工具')
    parser.add_argument('path', help='要修复的文件或模块路径')

    args = parser.parse_args()

    fixer = TargetedSyntaxFixer()
    path = Path(args.path)

    if path.is_file():
        fixer.fix_file(path)
    elif path.is_dir():
        # 修复目录中的所有Python文件
        for py_file in path.rglob('*.py'):
            fixer.fix_file(py_file)
    else:
        # 假设是模块名
        fixer.fix_module(args.path)

    logger.info(f"\n总计修复了 {fixer.fixes_count} 个文件")


if __name__ == '__main__':
    main()