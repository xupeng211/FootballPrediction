#!/usr/bin/env python3
"""
目标化语法错误修复工具
专注于修复invalid-syntax错误，目标是从276个减少到200个以下
"""

import subprocess
from pathlib import Path


class TargetedSyntaxFixer:
    def __init__(self):
        self.files_fixed = 0
        self.errors_fixed = 0
        self.target_files = []

    def get_syntax_error_files(self) -> list[tuple[str, int]]:
        """获取有语法错误的文件列表"""
        try:
            result = subprocess.run([
                "ruff", "check", "src/",
                "--output-format=concise"
            ], capture_output=True, text=True, timeout=30)

            error_files = {}
            for line in result.stdout.split('\n'):
                if 'invalid-syntax' in line and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        file_path = parts[0]
                        error_files[file_path] = error_files.get(file_path, 0) + 1

            # 按错误数量排序，优先处理错误最多的文件
            sorted_files = sorted(error_files.items(), key=lambda x: x[1], reverse=True)
            return sorted_files

        except Exception:
            return []

    def fix_file_critical_syntax_errors(self, file_path: str) -> dict[str, int]:
        """修复单个文件的关键语法错误"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 1. 修复未闭合的三引号字符串 (最常见的问题)
            content = self._fix_triple_quotes(content)
            if content != original_content:
                fixes_count += 1

            # 2. 修复未闭合的括号
            content = self._fix_brackets(content)
            if content != original_content:
                fixes_count += 1

            # 3. 修复类和函数定义格式问题
            content = self._fix_definitions(content)
            if content != original_content:
                fixes_count += 1

            # 4. 修复导入语句问题
            content = self._fix_imports(content)
            if content != original_content:
                fixes_count += 1

            # 5. 修复缩进问题
            content = self._fix_indentation(content)
            if content != original_content:
                fixes_count += 1

            # 写入修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.errors_fixed += 1

            return {"syntax_fixes": fixes_count}

        except Exception:
            return {"syntax_fixes": 0}

    def _fix_triple_quotes(self, content: str) -> str:
        """修复三引号字符串问题"""
        # 计算三引号的数量
        triple_quote_count = content.count('"""')

        # 如果数量是奇数，说明有未闭合的三引号
        if triple_quote_count % 2 == 1:
            # 在文件末尾添加闭合的三引号
            content = content.rstrip() + '\n"""\n'

        return content

    def _fix_brackets(self, content: str) -> str:
        """修复括号匹配问题"""
        # 计算括号数量
        open_parens = content.count('(') - content.count(')')
        open_brackets = content.count('[') - content.count(']')
        open_braces = content.count('{') - content.count('}')

        # 修复未闭合的括号
        if open_parens > 0:
            content += ')' * open_parens
        if open_brackets > 0:
            content += ']' * open_brackets
        if open_braces > 0:
            content += '}' * open_braces

        return content

    def _fix_definitions(self, content: str) -> str:
        """修复类和函数定义问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 修复缺少冒号的类和函数定义
            if (stripped.startswith(('class ', 'def ', 'async def ')) and
                ':' not in stripped and
                not stripped.endswith(':')):
                fixed_lines.append(line + ':')
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_imports(self, content: str) -> str:
        """修复导入语句问题"""
        lines = content.split('\n')
        fixed_lines = []
        in_import_section = True

        for line in lines:
            stripped = line.strip()

            # 检查是否是导入语句
            if stripped.startswith(('import ', 'from ')):
                # 修复缩进错误的导入语句
                if line.startswith('    ') and in_import_section:
                    fixed_lines.append(stripped)
                else:
                    fixed_lines.append(line)
            elif stripped and not stripped.startswith('#') and in_import_section:
                # 遇到非空非注释行，导入部分结束
                in_import_section = False
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_indentation(self, content: str) -> str:
        """修复缩进问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 修复顶级类和函数的错误缩进
            if stripped.startswith(('class ', 'def ', 'async def ')):
                if line.startswith('    ') and not self._is_nested_class_or_function(lines, line):
                    # 移除多余的缩进
                    fixed_lines.append(stripped)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _is_nested_class_or_function(self, lines: list[str], current_line: str) -> bool:
        """检查当前类或函数是否是嵌套的"""
        # 简单检查：如果前面有相同或更多缩进的类/函数定义，可能是嵌套的
        current_line_index = lines.index(current_line)
        current_indent = len(current_line) - len(current_line.lstrip())

        # 检查前面的行
        for i in range(max(0, current_line_index - 10), current_line_index):
            line = lines[i]
            if line.strip().startswith(('class ', 'def ', 'async def ')):
                line_indent = len(line) - len(line.lstrip())
                if line_indent >= current_indent:
                    return True

        return False

    def batch_fix_syntax_errors(self, target_limit: int = 20):
        """批量修复语法错误到目标数量以下"""

        # 获取有语法错误的文件
        error_files = self.get_syntax_error_files()
        if not error_files:
            return


        # 显示前10个错误最多的文件
        for file_path, _error_count in error_files[:10]:
            pass

        # 获取当前语法错误数量
        initial_errors = self.get_current_syntax_error_count()

        # 优先处理错误最多的文件
        files_to_process = error_files[:target_limit]

        total_fixes = 0
        for file_path, _error_count in files_to_process:
            if Path(file_path).exists():
                result = self.fix_file_critical_syntax_errors(file_path)
                total_fixes += result.get("syntax_fixes", 0)
                self.files_fixed += 1
            else:
                pass

        # 验证修复效果
        final_errors = self.get_current_syntax_error_count()
        initial_errors - final_errors


        if final_errors < 200:
            pass
        else:
            final_errors - 199

    def get_current_syntax_error_count(self) -> int:
        """获取当前语法错误数量"""
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
    fixer = TargetedSyntaxFixer()
    fixer.batch_fix_syntax_errors(20)

if __name__ == "__main__":
    main()
