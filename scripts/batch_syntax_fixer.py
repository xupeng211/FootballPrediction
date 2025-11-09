#!/usr/bin/env python3
"""
批量语法修复工具
专门处理大量语法错误的批量修复
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

class BatchSyntaxFixer:
    def __init__(self):
        self.files_fixed = 0
        self.errors_fixed = 0

    def get_top_error_files(self, limit: int = 20) -> List[Tuple[str, int]]:
        """获取语法错误最多的文件列表"""
        try:
            result = subprocess.run([
                "ruff", "check", "src/",
                "--output-format=concise"
            ], capture_output=True, text=True, timeout=30)

            error_counts = {}
            for line in result.stdout.split('\n'):
                if 'invalid-syntax' in line and ':' in line:
                    file_path = line.split(':')[0]
                    error_counts[file_path] = error_counts.get(file_path, 0) + 1

            # 按错误数量排序
            sorted_files = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_files[:limit]

        except Exception as e:
            print(f"获取错误文件列表失败: {e}")
            return []

    def fix_file_syntax_errors(self, file_path: str) -> Dict[str, int]:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 1. 修复未闭合的三引号字符串
            content = self._fix_triple_quotes(content)

            # 2. 修复未闭合的括号
            content = self._fix_unclosed_brackets(content)

            # 3. 修复缩进问题
            content = self._fix_indentation_issues(content)

            # 4. 修复导入语句问题
            content = self._fix_import_issues(content)

            # 5. 修复类和函数定义问题
            content = self._fix_class_function_definitions(content)

            # 6. 清理特殊字符
            content = self._fix_special_characters(content)

            # 7. 确保文件结构完整
            content = self._ensure_file_structure(content)

            # 写入修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                fixes_count = self._count_fixes(original_content, content)
                print(f"  ✅ 修复 {file_path}: {fixes_count} 个问题")
                self.errors_fixed += fixes_count

            return {"syntax_fixes": fixes_count}

        except Exception as e:
            print(f"  ❌ 处理文件 {file_path} 时出错: {e}")
            return {"syntax_fixes": 0}

    def _fix_triple_quotes(self, content: str) -> str:
        """修复未闭合的三引号字符串"""
        lines = content.split('\n')
        fixed_lines = []
        in_docstring = False
        quote_count = 0

        for line in lines:
            stripped = line.strip()

            # 计算三引号数量
            triple_quotes = line.count('"""')
            if triple_quotes > 0:
                quote_count += triple_quotes
                if quote_count % 2 == 1:
                    in_docstring = True
                else:
                    in_docstring = False

            # 如果是空行且在文档字符串中，添加占位符
            if in_docstring and stripped == '':
                line = '        '  # 添加适当缩进

            fixed_lines.append(line)

        # 如果最后有未闭合的文档字符串，添加闭合
        if quote_count % 2 == 1:
            fixed_lines.append('"""\n')

        return '\n'.join(fixed_lines)

    def _fix_unclosed_brackets(self, content: str) -> str:
        """修复未闭合的括号"""
        # 简单的括号平衡检查
        open_parens = content.count('(') - content.count(')')
        if open_parens > 0:
            content += ')' * open_parens

        open_brackets = content.count('[') - content.count(']')
        if open_brackets > 0:
            content += ']' * open_brackets

        open_braces = content.count('{') - content.count('}')
        if open_braces > 0:
            content += '}' * open_braces

        return content

    def _fix_indentation_issues(self, content: str) -> str:
        """修复缩进问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 修复类和函数定义的缩进
            if stripped.startswith(('class ', 'def ', 'async def ')) and line.startswith('    '):
                # 检查是否应该是一级缩进
                fixed_lines.append(stripped)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_import_issues(self, content: str) -> str:
        """修复导入语句问题"""
        lines = content.split('\n')
        fixed_lines = []
        in_import_section = True

        for line in lines:
            stripped = line.strip()

            if stripped.startswith(('import ', 'from ')):
                # 修复导入语句的缩进
                if line.startswith('    ') and in_import_section:
                    fixed_lines.append(stripped)
                else:
                    fixed_lines.append(line)
            elif stripped and not stripped.startswith('#') and in_import_section:
                # 导入部分结束
                in_import_section = False
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_class_function_definitions(self, content: str) -> str:
        """修复类和函数定义问题"""
        # 修复未闭合的类和函数定义
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 检查是否有未闭合的类或函数定义
            if (stripped.startswith(('class ', 'def ', 'async def ')) and
                ':' not in line and not stripped.endswith(':')):
                fixed_lines.append(line + ':')
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_special_characters(self, content: str) -> str:
        """修复特殊字符问题"""
        # 替换特殊字符
        content = content.replace('（', '(').replace('）', ')')
        content = content.replace('，', ',').replace('。', '.')
        content = content.replace('≤', '<=').replace('≥', '>=')
        content = content.replace('$', '')
        return content

    def _ensure_file_structure(self, content: str) -> str:
        """确保文件结构完整"""
        # 确保文件以换行符结尾
        if content and not content.endswith('\n'):
            content += '\n'

        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        return content

    def _count_fixes(self, original: str, fixed: str) -> int:
        """计算修复数量"""
        # 简单的修复计数：基于行数差异
        original_lines = len(original.split('\n'))
        fixed_lines = len(fixed.split('\n'))
        return abs(fixed_lines - original_lines) + 1  # 至少修复了1个问题

    def batch_fix_syntax_errors(self, file_limit: int = 20):
        """批量修复语法错误"""
        print("🔧 批量语法修复工具")
        print("=" * 50)

        # 获取错误最多的文件
        error_files = self.get_top_error_files(file_limit)

        if not error_files:
            print("  📊 没有发现需要修复的语法错误文件")
            return

        print(f"📋 发现 {len(error_files)} 个需要修复的文件:")
        for file_path, error_count in error_files[:5]:
            print(f"  - {file_path}: {error_count} 个错误")

        print(f"\n🔧 开始批量修复...")

        total_fixes = 0
        for file_path, error_count in error_files:
            if Path(file_path).exists():
                result = self.fix_file_syntax_errors(file_path)
                total_fixes += result.get("syntax_fixes", 0)
                self.files_fixed += 1
            else:
                print(f"  ⚠️ 文件不存在: {file_path}")

        print(f"\n📊 修复统计:")
        print(f"  🔧 修复文件数: {self.files_fixed}")
        print(f"  ✅ 修复问题数: {self.errors_fixed}")
        print(f"  📈 总修复量: {total_fixes}")

    def verify_improvement(self) -> int:
        """验证修复效果"""
        try:
            result = subprocess.run([
                "ruff", "check", "src/",
                "--output-format=concise"
            ], capture_output=True, text=True, timeout=30)

            syntax_errors = 0
            for line in result.stdout.split('\n'):
                if 'invalid-syntax' in line:
                    syntax_errors += 1

            return syntax_errors
        except:
            return -1

def main():
    """主函数"""
    fixer = BatchSyntaxFixer()

    print("🔍 检查当前语法错误数量...")
    initial_errors = fixer.verify_improvement()
    print(f"  📊 初始语法错误: {initial_errors}")

    fixer.batch_fix_syntax_errors(20)

    print("\n🔍 验证修复效果...")
    final_errors = fixer.verify_improvement()
    print(f"  📊 修复后语法错误: {final_errors}")

    if initial_errors > 0 and final_errors >= 0:
        improvement = initial_errors - final_errors
        print(f"\n🎉 语法修复成果: 减少了 {improvement} 个语法错误")
        if improvement > 0:
            print(f"📈 改善率: {improvement/initial_errors*100:.1f}%")

if __name__ == "__main__":
    main()