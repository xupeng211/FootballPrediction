#!/usr/bin/env python3
"""
Phase G Week 3: 高级语法修复器
专门处理复杂语法错误，冲击90%+健康度目标
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

class AdvancedSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.complex_fixes_applied = []

    def fix_isinstance_errors(self, content: str) -> str:
        """修复isinstance语法错误"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复isinstance参数错误
            if 'isinstance expected 2 arguments, got 3' in line:
                continue  # 跳过错误消息行

            # 修复isinstance语法模式
            if 'isinstance(' in line and '))' in line:
                # 处理isinstance(...))模式
                line = re.sub(r'isinstance\(([^,]+)\)\)\)', r'isinstance(\1, dict)', line)

            # 修复多重isinstance嵌套
            if 'isinstance(' in line:
                # 确保isinstance有两个参数
                isinstance_match = re.search(r'isinstance\(([^,]+)(?:,\s*([^)]+))?\)', line)
                if isinstance_match:
                    param1 = isinstance_match.group(1)
                    param2 = isinstance_match.group(2)
                    if not param2:
                        # 缺少第二个参数，根据上下文推断
                        if 'dict' in line or '{' in line:
                            line = line.replace(isinstance_match.group(0), f'isinstance({param1}, dict)')
                        elif 'list' in line or '[' in line:
                            line = line.replace(isinstance_match.group(0), f'isinstance({param1}, list)')
                        elif 'str' in line or '"' in line:
                            line = line.replace(isinstance_match.group(0), f'isinstance({param1}, str)')
                        else:
                            line = line.replace(isinstance_match.group(0), f'isinstance({param1}, object)')

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_bracket_mismatches_advanced(self, content: str) -> str:
        """高级括号匹配修复"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复复杂的括号不匹配
            line = self._fix_parenthesis_balance(line)
            line = self._fix_bracket_balance(line)
            line = self._fix_brace_balance(line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_parenthesis_balance(self, line: str) -> str:
        """修复圆括号平衡"""
        open_count = line.count('(')
        close_count = line.count(')')

        if open_count > close_count:
            # 缺少右括号
            line = line + ')' * (open_count - close_count)
        elif close_count > open_count:
            # 多余右括号，移除多余的
            excess = close_count - open_count
            for _ in range(excess):
                last_paren = line.rfind(')')
                if last_paren != -1:
                    line = line[:last_paren] + line[last_paren+1:]

        return line

    def _fix_bracket_balance(self, line: str) -> str:
        """修复方括号平衡"""
        open_count = line.count('[')
        close_count = line.count(']')

        if open_count > close_count:
            line = line + ']' * (open_count - close_count)
        elif close_count > open_count:
            excess = close_count - open_count
            for _ in range(excess):
                last_bracket = line.rfind(']')
                if last_bracket != -1:
                    line = line[:last_bracket] + line[last_bracket+1:]

        return line

    def _fix_brace_balance(self, line: str) -> str:
        """修复大括号平衡"""
        open_count = line.count('{')
        close_count = line.count('}')

        if open_count > close_count:
            line = line + '}' * (open_count - close_count)
        elif close_count > open_count:
            excess = close_count - open_count
            for _ in range(excess):
                last_brace = line.rfind('}')
                if last_brace != -1:
                    line = line[:last_brace] + line[last_brace+1:]

        return line

    def fix_string_literals(self, content: str) -> str:
        """修复字符串字面量问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复未闭合的字符串
            if 'unterminated string literal' in line:
                continue  # 跳过错误消息

            # 检查引号平衡
            quote_count = line.count('"')
            if quote_count % 2 == 1:
                # 奇数个引号，添加闭合引号
                if line.strip().endswith(','):
                    line = line.rstrip() + '",'
                else:
                    line = line.rstrip() + '"'

            # 修复十进制字面量错误
            if 'invalid decimal literal' in line:
                continue

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_indentation_issues(self, content: str) -> str:
        """修复缩进问题"""
        lines = content.split('\n')
        fixed_lines = []

        indent_stack = [0]  # 缩进栈

        for line in lines:
            if line.strip() == '':
                fixed_lines.append(line)
                continue

            # 计算当前缩进
            current_indent = len(line) - len(line.lstrip())

            # 处理缩进不匹配
            if 'unindent does not match' in line:
                continue  # 跳过错误消息

            # 检查是否需要调整缩进
            if line.strip().startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
                # 需要增加缩进的语句
                if current_indent <= indent_stack[-1]:
                    # 缩进不足，添加缩进
                    indent = indent_stack[-1] + 4
                    line = ' ' * indent + line.strip()
                    indent_stack.append(indent)
            elif line.strip().startswith(('return', 'pass', 'break', 'continue')):
                # 保持当前缩进
                pass
            elif current_indent < indent_stack[-1]:
                # 减少缩进
                while indent_stack and current_indent < indent_stack[-1]:
                    indent_stack.pop()

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_complex_patterns(self, content: str) -> str:
        """修复复杂语法模式"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复invalid syntax
            if 'invalid syntax' in line:
                continue

            # 修复expected indented block
            if 'expected an indented block' in line:
                continue

            # 修复其他常见模式
            line = self._fix_function_definitions(line)
            line = self._fix_class_definitions(line)
            line = self._fix_import_statements(line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_function_definitions(self, line: str) -> str:
        """修复函数定义"""
        if 'def ' in line and '->' in line and not line.strip().endswith(':'):
            if line.count('(') > line.count(')'):
                line = line.rstrip() + '):'
            else:
                line = line.rstrip() + ':'
        return line

    def _fix_class_definitions(self, line: str) -> str:
        """修复类定义"""
        if 'class ' in line and not line.strip().endswith(':'):
            line = line.rstrip() + ':'
        return line

    def _fix_import_statements(self, line: str) -> str:
        """修复导入语句"""
        if line.strip().startswith('import ') and not line.strip().endswith(','):
            # 检查是否是完整的导入语句
            if '"' in line and line.count('"') % 2 == 1:
                line = line.rstrip() + '"'
        return line

    def fix_single_file(self, file_path: str) -> bool:
        """修复单个文件的复杂语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 尝试解析AST
            try:
                ast.parse(original_content)
                print(f"✅ {file_path}: 语法正确，无需修复")
                return True
            except SyntaxError:
                pass

            content = original_content

            # 应用各种高级修复
            content = self.fix_isinstance_errors(content)
            content = self.fix_bracket_mismatches_advanced(content)
            content = self.fix_string_literals(content)
            content = self.fix_indentation_issues(content)
            content = self.fix_complex_patterns(content)

            # 验证修复结果
            try:
                ast.parse(content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"✅ {file_path}: 高级修复成功")
                self.fixed_files.append(file_path)
                return True

            except SyntaxError as e:
                print(f"❌ {file_path}: 高级修复失败 - {e}")
                self.failed_files.append(file_path)
                return False

        except Exception as e:
            print(f"❌ {file_path}: 处理异常 - {e}")
            self.failed_files.append(file_path)
            return False

    def fix_directory(self, directory: str) -> None:
        """修复目录下的所有Python文件"""
        python_files = list(Path(directory).rglob("*.py"))

        print("🚀 Phase G Week 3: 开始高级语法修复")
        print(f"📁 目标目录: {directory}")
        print(f"📂 发现 {len(python_files)} 个Python文件")
        print("=" * 60)

        for file_path in python_files:
            self.fix_single_file(str(file_path))

        self.print_summary()

    def print_summary(self) -> None:
        """打印修复摘要"""
        print("=" * 60)
        print("📊 Phase G Week 3 高级语法修复摘要")
        print("=" * 60)
        print(f"✅ 修复成功: {len(self.fixed_files)} 个文件")
        print(f"❌ 修复失败: {len(self.failed_files)} 个文件")

        total_files = len(self.fixed_files) + len(self.failed_files)
        if total_files > 0:
            success_rate = len(self.fixed_files) / total_files * 100
            print(f"📈 修复成功率: {success_rate:.1f}%")

        if self.fixed_files:
            print("\n🎯 成功修复的文件:")
            for file_path in self.fixed_files[:10]:
                print(f"   ✅ {file_path}")
            if len(self.fixed_files) > 10:
                print(f"   ... 还有 {len(self.fixed_files) - 10} 个文件")

        if self.failed_files:
            print("\n⚠️ 修复失败的文件:")
            for file_path in self.failed_files[:5]:
                print(f"   ❌ {file_path}")
            if len(self.failed_files) > 5:
                print(f"   ... 还有 {len(self.failed_files) - 5} 个文件")

        print("=" * 60)

def main():
    import sys

    fixer = AdvancedSyntaxFixer()

    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "src"  # 默认修复src目录

    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return

    fixer.fix_directory(directory)

if __name__ == "__main__":
    main()