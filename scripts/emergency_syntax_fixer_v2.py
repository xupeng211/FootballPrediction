#!/usr/bin/env python3
"""
紧急语法修复工具
修复严重的语法错误，恢复代码可读性
"""

import re
from pathlib import Path


class EmergencySyntaxFixer:
    def __init__(self):
        self.files_fixed = 0
        self.errors_fixed = 0

    def fix_file_syntax(self, file_path: str) -> dict[str, int]:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 1. 修复导入语句的缩进问题
            lines = content.split('\n')
            fixed_lines = []

            for i, line in enumerate(lines):
                stripped = line.strip()

                # 修复多余的import语句和缩进问题
                if stripped.startswith('import ') or stripped.startswith('from '):
                    # 检查是否是不正确的缩进
                    if line.startswith('    ') and not self._is_inside_class_or_function(lines, i):
                        # 移到文件顶部
                        fixed_lines.append(stripped)
                        fixes_count += 1
                        continue

                # 修复空行和注释
                if stripped == '' or stripped.startswith('#'):
                    fixed_lines.append(line)
                    continue

                # 修复类和函数定义格式
                if stripped.startswith('class ') or stripped.startswith('def '):
                    # 确保类和函数定义没有多余缩进
                    if line.startswith('    ') and not self._is_inside_class_or_function(lines, i):
                        fixed_lines.append(stripped)
                        fixes_count += 1
                        continue

                # 修复重复的导入
                if 'import numpy as np' in stripped:
                    if stripped in fixed_lines[-5:] if fixed_lines else False:
                        continue  # 跳过重复的导入

                fixed_lines.append(line)

            # 2. 修复括号和引号匹配问题
            content = '\n'.join(fixed_lines)
            content = self._fix_bracket_issues(content)
            content = self._fix_quote_issues(content)

            # 3. 清理多余的空行
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

            # 4. 确保文件以换行符结尾
            if content and not content.endswith('\n'):
                content += '\n'

            # 写入修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.errors_fixed += fixes_count

            return {"syntax_fixes": fixes_count}

        except Exception:
            return {"syntax_fixes": 0}

    def _is_inside_class_or_function(self, lines: list[str], current_line: int) -> bool:
        """检查当前行是否在类或函数内部"""
        # 简单检查：查看前面的行是否有类或函数定义
        for i in range(max(0, current_line - 10), current_line):
            line = lines[i].strip()
            if line.startswith('class ') or line.startswith('def '):
                return True
        return False

    def _fix_bracket_issues(self, content: str) -> str:
        """修复括号匹配问题"""
        # 修复不匹配的中文括号
        content = content.replace('（', '(').replace('）', ')')
        content = content.replace('，', ',').replace('。', '.')
        content = content.replace('≤', '<=').replace('≥', '>=')
        content = content.replace('$', '')
        return content

    def _fix_quote_issues(self, content: str) -> str:
        """修复引号匹配问题"""
        # 修复不匹配的三引号
        lines = content.split('\n')
        fixed_lines = []
        in_docstring = False

        for line in lines:
            stripped = line.strip()

            # 处理三引号文档字符串
            if '"""' in stripped:
                if in_docstring:
                    in_docstring = False
                else:
                    in_docstring = True

            # 如果是空的文档字符串行，修复它
            if stripped == '"""' and in_docstring:
                continue

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_critical_files(self):
        """修复关键的语法错误文件"""

        # 高优先级文件列表
        critical_files = [
            "src/api/predictions_enhanced.py",
            "src/api/realtime_streaming.py",
            "src/api/auth_dependencies.py",
            "src/api/health.py",
            "src/config/config_manager.py",
            "src/config/openapi_config.py",
            "src/main.py",
            "src/main_simple.py"
        ]

        total_fixes = 0

        for file_path in critical_files:
            if Path(file_path).exists():
                result = self.fix_file_syntax(file_path)
                total_fixes += result.get("syntax_fixes", 0)
                self.files_fixed += 1
            else:
                pass


def main():
    """主函数"""
    fixer = EmergencySyntaxFixer()
    fixer.fix_critical_files()


if __name__ == "__main__":
    main()
