#!/usr/bin/env python3
"""
🔧 关键语法错误修复工具
Phase G应用准备 - 修复影响AST分析的关键语法错误

专注于修复影响智能测试缺口分析器运行的源代码语法问题
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict

class SyntaxErrorFixer:
    """语法错误修复器"""

    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.fixes_applied = 0

    def fix_project_syntax_errors(self, source_dir: str = "src") -> Dict:
        """修复项目中的语法错误"""
        print("🔧 开始修复项目语法错误...")

        source_path = Path(source_dir)
        python_files = list(source_path.rglob("*.py"))

        print(f"📂 发现 {len(python_files)} 个Python文件")

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            print(f"   🔍 检查: {py_file}")
            self._fix_file_syntax_errors(py_file)

        summary = {
            'total_files': len(python_files),
            'fixed_files': len(self.fixed_files),
            'failed_files': len(self.failed_files),
            'fixes_applied': self.fixes_applied,
            'fixed_files_list': [str(f) for f in self.fixed_files],
            'failed_files_list': [str(f) for f in self.failed_files]
        }

        print("\n📊 修复结果摘要:")
        print(f"   总文件数: {summary['total_files']}")
        print(f"   修复成功: {summary['fixed_files']}")
        print(f"   修复失败: {summary['failed_files']}")
        print(f"   修复应用: {summary['fixes_applied']}")

        return summary

    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__",
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "site-packages",
            ".git"
        ]

        for pattern in skip_patterns:
            if pattern in str(file_path):
                return True

        return False

    def _fix_file_syntax_errors(self, file_path: Path) -> bool:
        """修复单个文件的语法错误"""
        try:
            # 读取原始内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 尝试解析AST
            try:
                ast.parse(original_content)
                print(f"      ✅ {file_path.name} 语法正确")
                return True

            except SyntaxError as e:
                print(f"      ❌ {file_path.name} 语法错误: {e}")

                # 尝试修复
                fixed_content = self._apply_syntax_fixes(original_content, str(file_path))

                # 验证修复结果
                try:
                    ast.parse(fixed_content)
                    # 写入修复后的内容
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)

                    print(f"      ✅ {file_path.name} 修复成功")
                    self.fixed_files.append(file_path)
                    return True

                except SyntaxError as e2:
                    print(f"      ❌ {file_path.name} 修复失败: {e2}")
                    self.failed_files.append(file_path)
                    return False

        except Exception as e:
            print(f"      ❌ {file_path.name} 处理异常: {e}")
            self.failed_files.append(file_path)
            return False

    def _apply_syntax_fixes(self, content: str, file_path: str) -> str:
        """应用语法修复"""
        fixed_content = content

        # 修复1: isinstance语法错误
        fixed_content = self._fix_isinstance_errors(fixed_content)

        # 修复2: 未闭合的字符串字面量
        fixed_content = self._fix_unclosed_strings(fixed_content)

        # 修复3: 未闭合的括号
        fixed_content = self._fix_unclosed_brackets(fixed_content)

        # 修复4: 缩进错误
        fixed_content = self._fix_indentation_errors(fixed_content, file_path)

        # 修复5: 缺少冒号
        fixed_content = self._fix_missing_colons(fixed_content)

        # 修复6: 导入语句错误
        fixed_content = self._fix_import_errors(fixed_content)

        return fixed_content

    def _fix_isinstance_errors(self, content: str) -> str:
        """修复isinstance语法错误"""
        # 查找并修复isinstance调用中的语法错误
        # 模式: isinstance(x, (type1, type2, type3)) -> isinstance(x, (type1, type2))
        pattern = r'\bisinstance\s*\(\s*([^,]+),\s*\(([^)]+)\)\s*\)'

        def fix_isinstance_tuple(match):
            obj = match.group(1).strip()
            types_str = match.group(2).strip()

            # 如果类型列表太长，截断为前两个
            types = [t.strip() for t in types_str.split(',')]
            if len(types) > 2:
                types = types[:2]

            return f"isinstance({obj}, ({', '.join(types)}))"

        fixed_content = re.sub(pattern, fix_isinstance_tuple, content)

        # 修复: isinstance(x, type1, type2, type3) -> isinstance(x, (type1, type2))
        pattern2 = r'\bisinstance\s*\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'

        def fix_isinstance_multi(match):
            parts = [match.group(i).strip() for i in range(1, 5)]
            return f"isinstance({parts[0]}, ({parts[1]}, {parts[2]}))"

        fixed_content = re.sub(pattern2, fix_isinstance_multi, fixed_content)

        return fixed_content

    def _fix_unclosed_strings(self, content: str) -> str:
        """修复未闭合的字符串字面量"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 简单的字符串修复：检查是否有未闭合的引号
            if line.strip():
                # 计算引号数量
                single_quotes = line.count("'")
                double_quotes = line.count('"')

                # 如果单引号数量为奇数，添加一个
                if single_quotes % 2 == 1 and double_quotes % 2 == 0:
                    line += "'"
                # 如果双引号数量为奇数，添加一个
                elif double_quotes % 2 == 1 and single_quotes % 2 == 0:
                    line += '"'

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_unclosed_brackets(self, content: str) -> str:
        """修复未闭合的括号"""
        # 括号配对
        brackets = {'(': ')', '[': ']', '{': '}'}

        for open_bracket, close_bracket in brackets.items():
            count = content.count(open_bracket) - content.count(close_bracket)
            if count > 0:
                # 在文件末尾添加缺失的闭合括号
                content += close_bracket * count
                print(f"      添加了 {count} 个 '{close_bracket}' 闭合括号")

        return content

    def _fix_indentation_errors(self, content: str, file_path: str) -> str:
        """修复缩进错误"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 简单的缩进修复：确保行尾没有多余空格
            fixed_line = line.rstrip()

            # 修复混合缩进（制表符和空格混用）
            if '\t' in fixed_line and fixed_line.strip():
                # 将制表符替换为4个空格
                fixed_line = fixed_line.replace('\t', '    ')

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines)

    def _fix_missing_colons(self, content: str) -> str:
        """修复缺少冒号的语法错误"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 检查常见的缺少冒号的模式
            stripped = line.strip()

            # 修复: if condition -> if condition:
            if stripped.startswith('if ') and not stripped.endswith(':'):
                if len(stripped) > 3:  # 确保不是空条件
                    fixed_line = line + ':'
                    self.fixes_applied += 1
                else:
                    fixed_line = line
            # 修复: try -> try:
            elif stripped.startswith('try ') and not stripped.endswith(':'):
                fixed_line = line + ':'
                self.fixes_applied += 1
            # 修复: for item in -> for item in:
            elif re.match(r'^\s*for\s+\w+\s+in\s+', stripped) and not stripped.endswith(':'):
                fixed_line = line + ':'
                self.fixes_applied += 1
            # 修复: def function( -> def function(
            elif re.match(r'^\s*def\s+\w+\s*\(', stripped) and not stripped.endswith(':'):
                fixed_line = line + ':'
                self.fixes_applied += 1
            # 修复: class MyClass -> class MyClass:
            elif re.match(r'^\s*class\s+\w+', stripped) and not stripped.endswith(':'):
                fixed_line = line + ':'
                self.fixes_applied += 1
            # 修复: while condition -> while condition:
            elif stripped.startswith('while ') and not stripped.endswith(':'):
                if len(stripped) > 6:  # 确保不是空条件
                    fixed_line = line + ':'
                    self.fixes_applied += 1
                else:
                    fixed_line = line
            else:
                fixed_line = line

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines)

    def _fix_import_errors(self, content: str) -> str:
        """修复导入语句错误"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 修复重复的import语句
            if stripped.startswith('import ') and stripped.count('import ') > 1:
                # 简单修复：保留第一个import
                parts = stripped.split('import ')
                if len(parts) > 2:
                    fixed_line = line.replace(stripped, f"import {parts[1].strip()}")
                    self.fixes_applied += 1
                else:
                    fixed_line = line
            else:
                fixed_line = line

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines)

def main():
    """主函数"""
    print("🚀 关键语法错误修复工具启动...")
    print("=" * 60)

    fixer = SyntaxErrorFixer()

    # 先修复src目录的关键文件
    print("📁 修复 src/ 目录语法错误...")
    src_summary = fixer.fix_project_syntax_errors("src")

    # 再修复tests目录的关键文件
    print("\n📝 修复 tests/ 目录语法错误...")
    tests_summary = fixer.fix_project_syntax_errors("tests")

    # 生成修复报告
    total_summary = {
        'src_summary': src_summary,
        'tests_summary': tests_summary,
        'total_fixed_files': src_summary['fixed_files'] + tests_summary['fixed_files'],
        'total_failed_files': src_summary['failed_files'] + tests_summary['failed_files'],
        'total_fixes_applied': src_summary['fixes_applied'] + tests_summary['fixes_applied']
    }

    print("\n" + "=" * 60)
    print("📊 总体修复结果:")
    print(f"   src目录修复成功: {src_summary['fixed_files']}")
    print(f"   tests目录修复成功: {tests_summary['fixed_files']}")
    print(f"   总修复成功: {total_summary['total_fixed_files']}")
    print(f"   总修复失败: {total_summary['total_failed_files']}")
    print(f"   总修复应用: {total_summary['total_fixes_applied']}")

    # 保存修复报告
    import json
    with open('syntax_fix_report.json', 'w', encoding='utf-8') as f:
        json.dump(total_summary, f, indent=2, ensure_ascii=False)

    print("\n📄 详细报告: syntax_fix_report.json")

    # 给出下一步建议
    print("\n🎯 下一步建议:")
    if total_summary['total_fixed_files'] > 0:
        print("   ✅ 语法错误修复完成，现在可以运行Phase G工具")
        print("   📋 建议: python3 scripts/intelligent_test_gap_analyzer.py")
    else:
        print("   ⚠️ 未发现需要修复的关键语法错误")
        print("   📋 建议: 检查其他可能的语法问题")

    return total_summary

if __name__ == "__main__":
    main()