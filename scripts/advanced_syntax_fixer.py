#!/usr/bin/env python3
"""
高级语法错误修复工具
Advanced Syntax Error Fixer

使用多种策略批量修复Python语法错误
"""

import ast
import re
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('syntax_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AdvancedSyntaxFixer:
    """高级语法错误修复器"""

    def __init__(self, src_dir: str = 'src'):
        self.src_dir = Path(src_dir)
        self.fix_stats = {
            'total_files': 0,
            'fixed_files': 0,
            'failed_files': 0,
            'fixes_applied': defaultdict(int)
        }

    def analyze_errors(self) -> Dict[str, List[Tuple[Path, str]]]:
        """分析所有语法错误"""
        errors = defaultdict(list)

        for py_file in self.src_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                module = str(py_file.parent.relative_to(self.src_dir))
                errors[module].append((py_file, e.msg))

        return errors

    def fix_common_patterns(self, content: str) -> Tuple[str, List[str]]:
        """修复常见的语法错误模式"""
        fixes_applied = []
        original_content = content

        # 1. 修复连接的import语句
        import_patterns = [
            (r'import ([a-zA-Z_][a-zA-Z0-9_]*)import', r'import \1\nimport'),
            (r'from ([^.]+)import', r'from \1 import'),
            (r'import ([a-zA-Z_][a-zA-Z0-9_]*),([a-zA-Z_])', r'import \1,\n\2'),
        ]

        for pattern, replacement in import_patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                if content != original_content:
                    fixes_applied.append(f"修复import语句: {pattern}")
                    original_content = content

        # 2. 修复中文字符后的错误
        chinese_patterns = [
            (r'([。)！））])import', r'\1\nimport'),
            (r'([。）！））])def', r'\1\ndef'),
            (r'([。)！））])class', r'\1\nclass'),
            (r'([。）！））])#', r'\1\n#'),
            (r'([。）！））])([a-zA-Z_])', r'\1\n\2'),
        ]

        for pattern, replacement in chinese_patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                if content != original_content:
                    fixes_applied.append(f"修复中文标点后的问题: {pattern}")
                    original_content = content

        # 3. 修复未闭合的括号和引号
        bracket_fixes = self._fix_brackets(content)
        if bracket_fixes:
            content = bracket_fixes
            fixes_applied.append("修复括号匹配问题")
            original_content = content

        # 4. 修复f-string语法错误
        fstring_patterns = [
            (r'f"([^"]*)\{([^}]*)([^"]*)"', lambda m: self._fix_fstring_content(m.group(0))),
            (r"f'([^']*)\{([^}]*)([^']*)'", lambda m: self._fix_fstring_content(m.group(0))),
        ]

        for pattern, fixer in fstring_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                try:
                    fixed = fixer(match)
                    if fixed and fixed != match.group(0):
                        content = content.replace(match.group(0), fixed)
                        fixes_applied.append("修复f-string语法")
                except:
                    pass

        # 5. 修复无效字符
        invalid_chars = [
            ('（', '('),
            ('）', ')'),
            ('，', ','),
            ('：', ':'),
            ('；', ';'),
            ('\u3001', ','),  # 顿号
            ('\u201c', '"'),  # 左双引号
            ('\u201d', '"'),  # 右双引号
            ('\u2018', "'"),  # 左单引号
            ('\u2019', "'"),  # 右单引号
        ]

        for invalid, valid in invalid_chars:
            if invalid in content:
                content = content.replace(invalid, valid)
                fixes_applied.append(f"替换无效字符: {invalid} -> {valid}")

        # 6. 修复缩进问题
        content = self._fix_indentation(content)

        # 7. 修复未闭合的字符串
        content = self._fix_unclosed_strings(content)

        return content, fixes_applied

    def _fix_brackets(self, content: str) -> Optional[str]:
        """修复括号匹配问题"""
        stack = []
        lines = content.split('\n')
        fixed_lines = lines.copy()

        bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        reverse_pairs = {')': '(', ']': '[', '}': '{'}

        for i, line in enumerate(lines):
            for j, char in enumerate(line):
                if char in bracket_pairs:
                    stack.append((char, i, j))
                elif char in reverse_pairs:
                    if stack and stack[-1][0] == reverse_pairs[char]:
                        stack.pop()
                    else:
                        # 多余的闭合括号，删除
                        fixed_lines[i] = line[:j] + line[j+1:]
                        lines[i] = fixed_lines[i]

        # 添加缺失的闭合括号
        while stack:
            open_bracket, line_idx, _ = stack.pop()
            close_bracket = bracket_pairs[open_bracket]
            fixed_lines[line_idx] += close_bracket

        return '\n'.join(fixed_lines) if fixed_lines != lines else None

    def _fix_fstring_content(self, fstring: str) -> Optional[str]:
        """修复f-string内容"""
        try:
            # 测试f-string是否有效
            eval(fstring)
            return None
        except:
            # 尝试修复常见的f-string错误
            if '}{' in fstring:
                # 修复连续的{}
                return fstring.replace('}{', '} {')
            if '{:' in fstring and '}' not in fstring[fstring.find('{:')+2:]:
                # 修复未闭合的格式化
                return fstring + '}'
            return None

    def _fix_indentation(self, content: str) -> str:
        """修复缩进问题"""
        lines = content.split('\n')
        fixed_lines = []
        indent_stack = [0]

        for line in lines:
            if line.strip() == '':
                fixed_lines.append(line)
                continue

            # 计算当前缩进
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # 处理dedent
            while indent_stack and indent < indent_stack[-1]:
                indent_stack.pop()

            # 处理需要缩进的行
            if stripped.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'with ', 'finally:')):
                if indent <= indent_stack[-1]:
                    indent = indent_stack[-1] + 4
                    line = ' ' * indent + stripped
                    indent_stack.append(indent)
            elif stripped.startswith(('except ', 'elif ')) and indent == indent_stack[-1]:
                # except和elif应该与对应的if/try对齐
                if len(indent_stack) > 1:
                    indent = indent_stack[-2]
                    line = ' ' * indent + stripped

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_unclosed_strings(self, content: str) -> str:
        """修复未闭合的字符串"""
        lines = content.split('\n')
        fixed_lines = []

        in_string = False
        string_char = None
        escape_next = False

        for line in lines:
            fixed_line = []
            for char in line:
                if escape_next:
                    escape_next = False
                    fixed_line.append(char)
                    continue

                if char == '\\':
                    escape_next = True
                    fixed_line.append(char)
                elif char in ('"', "'") and not in_string:
                    in_string = True
                    string_char = char
                    fixed_line.append(char)
                elif char == string_char and in_string:
                    in_string = False
                    string_char = None
                    fixed_line.append(char)
                else:
                    fixed_line.append(char)

            # 行结束时如果字符串未闭合，添加闭合
            if in_string and string_char:
                fixed_line.append(string_char)
                in_string = False
                string_char = None

            fixed_lines.append(''.join(fixed_line))

        return '\n'.join(fixed_lines)

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            content, fixes = self.fix_common_patterns(content)

            # 尝试解析修复后的内容
            try:
                ast.parse(content)
                # 如果成功，写入文件
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    for fix in fixes:
                        self.fix_stats['fixes_applied'][fix] += 1

                    logger.info(f"✅ 修复文件: {file_path}")
                    for fix in fixes:
                        logger.info(f"   - {fix}")

                    self.fix_stats['fixed_files'] += 1
                    return True
            except SyntaxError as e:
                # 如果基础修复失败，尝试高级修复
                content = self._advanced_fix(content, e)
                try:
                    ast.parse(content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"✅ 高级修复文件: {file_path}")
                    self.fix_stats['fixed_files'] += 1
                    return True
                except:
                    pass

            self.fix_stats['failed_files'] += 1
            logger.warning(f"❌ 无法修复文件: {file_path}")
            return False

        except Exception as e:
            logger.error(f"处理文件时出错 {file_path}: {e}")
            self.fix_stats['failed_files'] += 1
            return False

    def _advanced_fix(self, content: str, error: SyntaxError) -> str:
        """高级修复策略"""
        lines = content.split('\n')
        error_line = error.lineno - 1 if error.lineno else 0

        # 根据错误类型应用不同的修复策略
        if 'invalid syntax' in str(error):
            # 尝试在错误行附近插入缺失的元素
            if error_line < len(lines):
                line = lines[error_line]

                # 检查是否缺少冒号
                if any(keyword in line for keyword in ['if ', 'def ', 'class ', 'for ', 'while ', 'try:', 'with ']) and ':' not in line:
                    lines[error_line] = line + ':'

                # 检查是否缺少括号
                open_count = line.count('(') + line.count('[') + line.count('{')
                close_count = line.count(')') + line.count(']') + line.count('}')
                if open_count > close_count:
                    # 添加缺失的闭合括号
                    lines[error_line] = line + ')' * (open_count - close_count)

        return '\n'.join(lines)

    def fix_module(self, module_path: str) -> int:
        """修复整个模块"""
        module_dir = self.src_dir / module_path
        if not module_dir.exists():
            logger.error(f"模块不存在: {module_path}")
            return 0

        fixed_count = 0
        py_files = list(module_dir.rglob('*.py'))

        logger.info(f"\n开始修复模块: {module_path} ({len(py_files)} 个文件)")

        for py_file in py_files:
            self.fix_stats['total_files'] += 1
            if self.fix_file(py_file):
                fixed_count += 1

        logger.info(f"模块 {module_path} 修复完成: {fixed_count}/{len(py_files)}")
        return fixed_count

    def fix_all(self, priority_modules: List[str] = None):
        """修复所有文件，按优先级模块排序"""
        errors = self.analyze_errors()

        # 按模块错误数量排序
        sorted_modules = sorted(errors.items(), key=lambda x: len(x[1]), reverse=True)

        # 如果指定了优先级模块，先处理这些模块
        if priority_modules:
            priority_set = set(priority_modules)
            priority_items = [(m, f) for m, f in sorted_modules if m in priority_set]
            other_items = [(m, f) for m, f in sorted_modules if m not in priority_set]
            sorted_modules = priority_items + other_items

        logger.info(f"开始批量修复，共 {len(sorted_modules)} 个模块")

        for module, files in sorted_modules:
            fixed = self.fix_module(module)
            logger.info(f"模块 {module}: {fixed}/{len(files)} 文件已修复")

        # 打印统计信息
        self.print_stats()

    def print_stats(self):
        """打印修复统计信息"""
        logger.info("\n" + "="*60)
        logger.info("修复统计")
        logger.info("="*60)
        logger.info(f"总文件数: {self.fix_stats['total_files']}")
        logger.info(f"成功修复: {self.fix_stats['fixed_files']}")
        logger.info(f"修复失败: {self.fix_stats['failed_files']}")
        logger.info(f"成功率: {(self.fix_stats['fixed_files']/self.fix_stats['total_files']*100):.1f}%")

        logger.info("\n应用的修复类型:")
        for fix_type, count in sorted(self.fix_stats['fixes_applied'].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {fix_type}: {count} 次")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='高级语法错误修复工具')
    parser.add_argument('--module', '-m', help='修复指定模块')
    parser.add_argument('--file', '-f', help='修复指定文件')
    parser.add_argument('--priority', '-p', nargs='+', default=['api', 'core', 'database', 'services'],
                       help='优先修复的模块列表')
    parser.add_argument('--dry-run', action='store_true', help='只分析，不修复')

    args = parser.parse_args()

    fixer = AdvancedSyntaxFixer()

    if args.file:
        # 修复单个文件
        file_path = Path(args.file)
        if file_path.exists():
            fixer.fix_file(file_path)
            fixer.print_stats()
        else:
            logger.error(f"文件不存在: {args.file}")
    elif args.module:
        # 修复指定模块
        fixer.fix_module(args.module)
        fixer.print_stats()
    else:
        # 修复所有文件
        if args.dry_run:
            errors = fixer.analyze_errors()
            logger.info(f"发现 {sum(len(files) for files in errors.values())} 个文件有语法错误")
            for module, files in sorted(errors.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                logger.info(f"  {module}: {len(files)} 个文件")
        else:
            fixer.fix_all(args.priority)


if __name__ == '__main__':
    main()