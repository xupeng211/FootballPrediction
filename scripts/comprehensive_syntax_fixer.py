#!/usr/bin/env python3
"""
全面语法修复工具
专门处理缩进、导入语句和语法结构问题
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class ComprehensiveSyntaxFixer:
    def __init__(self):
        self.files_fixed = 0
        self.errors_fixed = 0

    def fix_import_and_indentation(self, file_path: str) -> Dict[str, int]:
        """修复导入语句和缩进问题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 1. 分离导入语句和其他代码
            lines = content.split('\n')
            imports = []
            others = []
            in_import_section = True

            for line in lines:
                stripped = line.strip()

                # 跳过空行和注释
                if not stripped or stripped.startswith('#'):
                    if in_import_section:
                        imports.append(line)
                    else:
                        others.append(line)
                    continue

                # 检查是否是导入语句
                if stripped.startswith(('import ', 'from ')) and in_import_section:
                    # 修复缩进问题
                    fixed_import = stripped
                    imports.append(fixed_import)
                    fixes_count += 1
                else:
                    # 结束导入部分
                    if in_import_section and not stripped.startswith(('import ', 'from ', '#', '"""', "'''")):
                        in_import_section = False
                        # 添加空行分隔
                        if imports and imports[-1] != '':
                            imports.append('')

                    # 修复其他代码的缩进
                    if stripped.startswith(('class ', 'def ')) and line.startswith('    '):
                        # 修复类和函数定义的缩进
                        fixed_line = stripped
                        others.append(fixed_line)
                        fixes_count += 1
                    else:
                        others.append(line)

            # 2. 重新组合文件
            fixed_lines = imports + others
            content = '\n'.join(fixed_lines)

            # 3. 修复文档字符串问题
            content = self._fix_docstrings(content)

            # 4. 修复特殊字符问题
            content = content.replace('（', '(').replace('）', ')')
            content = content.replace('，', ',').replace('。', '.')
            content = content.replace('≤', '<=').replace('≥', '>=')
            content = content.replace('$', '')

            # 5. 清理多余的空行
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

            # 6. 确保文件以换行符结尾
            if content and not content.endswith('\n'):
                content += '\n'

            # 写入修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  ✅ 修复 {file_path}: {fixes_count} 个语法问题")
                self.errors_fixed += fixes_count

            return {"syntax_fixes": fixes_count}

        except Exception as e:
            print(f"  ❌ 处理文件 {file_path} 时出错: {e}")
            return {"syntax_fixes": 0}

    def _fix_docstrings(self, content: str) -> str:
        """修复文档字符串问题"""
        lines = content.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 处理三引号文档字符串
            if '"""' in line and not line.strip().startswith('"""'):
                # 尝试修复文档字符串格式
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    fixed_lines.append(f'    {stripped}')
                    fixes_count = 1
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

            i += 1

        return '\n'.join(fixed_lines)

    def fix_problematic_files(self):
        """修复有问题的文件"""
        print("🔧 全面语法修复工具")
        print("=" * 50)

        # 问题文件列表
        problematic_files = [
            "src/__init__.py",
            "src/adapters/__init__.py",
            "src/adapters/adapters/football_models.py",
            "src/bad_example.py",
            "src/app_enhanced.py",
            "src/app_legacy.py",
            "src/config/cors_config.py"
        ]

        total_fixes = 0

        for file_path in problematic_files:
            if Path(file_path).exists():
                print(f"🔧 修复文件: {file_path}")
                result = self.fix_import_and_indentation(file_path)
                total_fixes += result.get("syntax_fixes", 0)
                self.files_fixed += 1
            else:
                print(f"  ⚠️ 文件不存在: {file_path}")

        print(f"\n📊 修复统计:")
        print(f"  🔧 修复文件数: {self.files_fixed}")
        print(f"  ✅ 修复问题数: {self.errors_fixed}")
        print(f"  📈 总修复量: {total_fixes}")

    def quick_syntax_check(self) -> int:
        """快速语法检查"""
        try:
            import subprocess
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
    fixer = ComprehensiveSyntaxFixer()

    print("🔍 检查当前语法错误数量...")
    initial_errors = fixer.quick_syntax_check()
    print(f"  📊 初始语法错误: {initial_errors}")

    fixer.fix_problematic_files()

    print("\n🔍 验证修复效果...")
    final_errors = fixer.quick_syntax_check()
    print(f"  📊 修复后语法错误: {final_errors}")

    if initial_errors > 0 and final_errors >= 0:
        improvement = initial_errors - final_errors
        print(f"\n🎉 语法修复成果: 减少了 {improvement} 个语法错误")

if __name__ == "__main__":
    main()