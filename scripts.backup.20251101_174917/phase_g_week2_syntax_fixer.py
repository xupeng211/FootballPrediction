#!/usr/bin/env python3
"""
Phase G Week 2: 复杂语法错误批量修复工具
专门处理括号不匹配和类型注解错误
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple

class ComplexSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.fixes_applied = []

    def fix_bracket_mismatches(self, content: str) -> str:
        """修复括号不匹配问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复多层嵌套括号问题
            if '((((((((' in line:
                line = line.replace('((((((((', 'isinstance(')
            if '))))))' in line:
                line = line.replace('))))))', ', dict)')

            # 修复其他括号模式
            if '((((((' in line:
                line = line.replace('((((((', 'isinstance(')
            if ')))))' in line:
                line = line.replace(')))))', ', dict)')

            # 修复三重括号
            if '(((' in line and ')))' in line:
                line = line.replace('(((', 'isinstance(')
                line = line.replace(')))', ', dict)')

            # 修复isinstance语法模式
            isinstance_pattern = r'isinstance\(([^,]+)\s*\)\s*and\s*\([^)]+$'
            if re.search(isinstance_pattern, line):
                line = re.sub(r'isinstance\(([^,]+)\)\s*\)\s*and\s*\(([^)]+)\)',
                           r'isinstance(\1, \2)', line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_type_annotations(self, content: str) -> str:
        """修复类型注解错误"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复Dict[str]))模式
            if 'Dict[str]))' in line:
                line = line.replace('Dict[str]))', 'Dict[str, Any])')

            # 修复Dict[str))模式
            if 'Dict[str))' in line:
                line = line.replace('Dict[str))', 'Dict[str, Any]')

            # 修复List[Dict[str]))模式
            if 'List[Dict[str]))' in line:
                line = line.replace('List[Dict[str]))', 'List[Dict[str, Any]]')

            # 修复不完整的函数参数
            if 'def ' in line and '->' in line and '):' not in line and line.rstrip().endswith(':'):
                # 检查是否缺少右括号
                if line.count('(') > line.count(')'):
                    line = line.rstrip() + '):'

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_exception_handling(self, content: str) -> str:
        """修复异常处理语法错误"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复except (KeyError)):模式
            if 'except (KeyError)):' in line:
                line = line.replace('except (KeyError)):', 'except (KeyError, TypeError, IndexError):')

            # 修复其他不完整的except语句
            except_pattern = r'except\s*\(\s*([^)]+)\s*\)\s*\)\s*:'
            if re.search(except_pattern, line):
                line = re.sub(except_pattern, r'except (\1):', line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_unclosed_strings(self, content: str) -> str:
        """修复未闭合字符串"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复末尾的未闭合字符串
            if line.count('"') % 2 == 1 and not line.rstrip().endswith('"'):
                # 如果是字符串字面量但未闭合，添加闭合引号
                if '"' in line and not line.rstrip().endswith(','):
                    line = line.rstrip() + '"'

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_single_file(self, file_path: str) -> bool:
        """修复单个文件的语法错误"""
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

            # 应用各种修复
            content = self.fix_bracket_mismatches(content)
            content = self.fix_type_annotations(content)
            content = self.fix_exception_handling(content)
            content = self.fix_unclosed_strings(content)

            # 验证修复结果
            try:
                ast.parse(content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"✅ {file_path}: 修复成功")
                self.fixed_files.append(file_path)
                return True

            except SyntaxError as e:
                print(f"❌ {file_path}: 修复失败 - {e}")
                self.failed_files.append(file_path)
                return False

        except Exception as e:
            print(f"❌ {file_path}: 处理异常 - {e}")
            self.failed_files.append(file_path)
            return False

    def fix_directory(self, directory: str) -> None:
        """修复目录下的所有Python文件"""
        python_files = list(Path(directory).rglob("*.py"))

        print(f"🚀 开始修复 {len(python_files)} 个Python文件...")
        print("=" * 60)

        for file_path in python_files:
            self.fix_single_file(str(file_path))

        self.print_summary()

    def print_summary(self) -> None:
        """打印修复摘要"""
        print("=" * 60)
        print("📊 Phase G Week 2 语法修复摘要")
        print("=" * 60)
        print(f"✅ 修复成功: {len(self.fixed_files)} 个文件")
        print(f"❌ 修复失败: {len(self.failed_files)} 个文件")

        if self.fixed_files:
            print("\n🎯 成功修复的文件:")
            for file_path in self.fixed_files[:10]:  # 只显示前10个
                print(f"   ✅ {file_path}")
            if len(self.fixed_files) > 10:
                print(f"   ... 还有 {len(self.fixed_files) - 10} 个文件")

        if self.failed_files:
            print("\n⚠️ 修复失败的文件:")
            for file_path in self.failed_files[:5]:  # 只显示前5个
                print(f"   ❌ {file_path}")
            if len(self.failed_files) > 5:
                print(f"   ... 还有 {len(self.failed_files) - 5} 个文件")

        success_rate = len(self.fixed_files) / (len(self.fixed_files) + len(self.failed_files)) * 100
        print(f"\n📈 修复成功率: {success_rate:.1f}%")

        if success_rate >= 80:
            print("🎉 修复效果良好！语法健康度显著提升！")
        elif success_rate >= 60:
            print("👍 修复效果中等，部分复杂问题需要手动处理")
        else:
            print("⚠️ 修复效果有限，建议检查复杂语法问题")

def main():
    import sys

    fixer = ComplexSyntaxFixer()

    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "src"  # 默认修复src目录

    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return

    print("🔧 Phase G Week 2: 复杂语法错误批量修复")
    print(f"📁 目标目录: {directory}")
    print()

    fixer.fix_directory(directory)

if __name__ == "__main__":
    main()