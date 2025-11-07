#!/usr/bin/env python3
"""
API语法错误批量修复工具 - Issue #345专用

专门用于修复API文件中的HTTPException语法错误和其他常见语法问题。
"""

import ast
import os
import re
from pathlib import Path


class APISyntaxFixer:
    """API语法错误修复器"""

    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.fix_patterns = [
            # HTTPException 重复括号修复
            (r'raise HTTPException\((.*?)\)\)\s*from\s+(\w+)',
             r'raise HTTPException(\1) from \2'),

            # HTTPException 缺失括号修复
            (r'raise HTTPException\((.*?)\s*from\s+(\w+)(?!\))',
             r'raise HTTPException(\1) from \2'),

            # 缩进错误修复 - 需要手动处理
            # 这里主要是标记文件需要手动检查
        ]

    def check_syntax_errors(self, file_path: Path) -> list[str]:
        """检查文件的语法错误"""
        errors = []
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # 尝试解析AST
            ast.parse(content)

            # 检查常见的HTTPException语法模式
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'raise HTTPException' in line:
                    # 检查重复括号
                    if ')) from' in line:
                        errors.append(f"Line {i}: 重复括号 ')) from e'")

                    # 检查缺失括号
                    if 'from e' in line and not line.strip().endswith(')'):
                        errors.append(f"Line {i}: 可能缺失括号")

                    # 检查语法结构
                    if 'raise HTTPException(' in line and line.count('(') > line.count(')'):
                        errors.append(f"Line {i}: 括号不匹配")

        except SyntaxError as e:
            errors.append(f"Line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"解析错误: {str(e)}")

        return errors

    def fix_http_exception_syntax(self, content: str) -> tuple[str, int]:
        """修复HTTPException语法错误"""
        original_content = content
        fixes_count = 0

        for pattern, replacement in self.fix_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
                fixes_count += len(matches)

        return content, fixes_count

    def fix_indentation_issues(self, content: str) -> tuple[str, int]:
        """尝试修复简单的缩进问题"""
        lines = content.split('\n')
        fixed_lines = []
        fixes_count = 0

        for line in lines:
            # 检查明显的缩进问题
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # 如果行不是空的，且不以空格或tab开始，可能是缩进错误
                # 这里做保守修复，只标记
                pass

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes_count

    def fix_file(self, file_path: Path) -> dict[str, any]:
        """修复单个文件"""
        result = {
            'file': str(file_path),
            'original_errors': [],
            'fixes_applied': 0,
            'success': False,
            'message': ''
        }

        try:
            # 检查原始错误
            result['original_errors'] = self.check_syntax_errors(file_path)

            if not result['original_errors']:
                result['success'] = True
                result['message'] = '文件语法正确，无需修复'
                return result

            # 读取文件内容
            with open(file_path, encoding='utf-8') as f:
                original_content = f.read()

            # 应用修复
            fixed_content = original_content
            total_fixes = 0

            # HTTPException语法修复
            fixed_content, http_fixes = self.fix_http_exception_syntax(fixed_content)
            total_fixes += http_fixes

            # 缩进修复（保守）
            fixed_content, indent_fixes = self.fix_indentation_issues(fixed_content)
            total_fixes += indent_fixes

            # 验证修复结果
            try:
                ast.parse(fixed_content)

                # 保存修复后的文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                result['fixes_applied'] = total_fixes
                result['success'] = True
                result['message'] = f'成功修复，应用了{total_fixes}个修复'

            except SyntaxError as e:
                result['success'] = False
                result['message'] = f'修复后仍有语法错误: Line {e.lineno}: {e.msg}'

                # 恢复原始内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

        except Exception as e:
            result['success'] = False
            result['message'] = f'处理文件时出错: {str(e)}'

        return result

    def scan_api_directory(self, api_dir: Path = None) -> list[dict[str, any]]:
        """扫描API目录中的所有Python文件"""
        if api_dir is None:
            api_dir = Path('src/api')

        python_files = []

        # 递归查找所有Python文件
        for py_file in api_dir.rglob('*.py'):
            if py_file.is_file():
                python_files.append(py_file)

        return python_files

    def fix_all_api_files(self) -> dict[str, any]:
        """修复所有API文件"""
        print("🔧 开始扫描API文件...")
        python_files = self.scan_api_directory()

        print(f"📁 发现 {len(python_files)} 个Python文件")

        results = []

        for file_path in python_files:
            try:
                rel_path = file_path.relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path
            print(f"🔍 检查文件: {rel_path}")

            # 检查是否有语法错误
            errors = self.check_syntax_errors(file_path)

            if errors:
                print(f"  ❌ 发现 {len(errors)} 个语法错误:")
                for error in errors:
                    print(f"    - {error}")

                # 尝试修复
                print("  🔧 尝试修复...")
                result = self.fix_file(file_path)
                results.append(result)

                if result['success']:
                    print(f"  ✅ {result['message']}")
                    self.fixed_files.append(file_path)
                else:
                    print(f"  ❌ {result['message']}")
                    self.failed_files.append(file_path)
            else:
                print("  ✅ 文件语法正确")

        return {
            'total_files': len(python_files),
            'files_with_errors': len([r for r in results if r['original_errors']]),
            'successfully_fixed': len(self.fixed_files),
            'failed_to_fix': len(self.failed_files),
            'results': results
        }

    def generate_report(self, results: dict[str, any]) -> str:
        """生成修复报告"""
        report = []
        report.append("# API语法错误修复报告")
        report.append(f"生成时间: {os.popen('date').read().strip()}")
        report.append("")

        # 汇总信息
        report.append("## 📊 修复汇总")
        report.append(f"- 总文件数: {results['total_files']}")
        report.append(f"- 有错误文件数: {results['files_with_errors']}")
        report.append(f"- 成功修复: {results['successfully_fixed']}")
        report.append(f"- 修复失败: {results['failed_to_fix']}")
        report.append("")

        # 成功修复的文件
        if self.fixed_files:
            report.append("## ✅ 成功修复的文件")
            for file_path in self.fixed_files:
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    rel_path = file_path
                report.append(f"- {rel_path}")
            report.append("")

        # 修复失败的文件
        if self.failed_files:
            report.append("## ❌ 需要手动修复的文件")
            for file_path in self.failed_files:
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    rel_path = file_path
                report.append(f"- {rel_path}")
            report.append("")

        # 详细结果
        report.append("## 📋 详细修复结果")
        for result in results['results']:
            if result['original_errors']:
                try:
                    rel_path = Path(result['file']).relative_to(Path.cwd())
                except ValueError:
                    rel_path = result['file']
                report.append(f"### {rel_path}")
                report.append(f"**状态**: {'✅ 成功' if result['success'] else '❌ 失败'}")
                report.append(f"**消息**: {result['message']}")
                report.append(f"**修复数**: {result['fixes_applied']}")

                if result['original_errors']:
                    report.append("**原始错误**:")
                    for error in result['original_errors']:
                        report.append(f"- {error}")
                report.append("")

        return "\n".join(report)


def main():
    """主函数"""
    print("🔧 API语法错误批量修复工具 - Issue #345")
    print("=" * 50)
    print()

    fixer = APISyntaxFixer()

    # 修复所有API文件
    results = fixer.fix_all_api_files()

    print()
    print("📊 修复完成统计:")
    print(f"  总文件数: {results['total_files']}")
    print(f"  有错误文件: {results['files_with_errors']}")
    print(f"  成功修复: {results['successfully_fixed']}")
    print(f"  修复失败: {results['failed_to_fix']}")

    # 生成报告
    report = fixer.generate_report(results)

    # 保存报告
    report_path = Path('docs/API_SYNTAX_FIX_REPORT.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"📝 详细报告已保存到: {report_path}")

    # 返回状态码
    if fixer.failed_files:
        print(f"\n⚠️  有 {len(fixer.failed_files)} 个文件需要手动修复")
        return 1
    else:
        print("\n✅ 所有语法错误已成功修复！")
        return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
