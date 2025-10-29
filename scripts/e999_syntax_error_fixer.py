#!/usr/bin/env python3
"""
E999语法错误最后清理工具
E999 Syntax Error Final Cleaner

专门用于清理剩余的E999语法错误，包括：
1. 缩进问题
2. 括号匹配问题
3. 字符串终止符问题
4. 其他语法错误
"""

import ast
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E999SyntaxErrorFixer:
    """E999语法错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def get_e999_errors(self) -> List[Dict]:
        """获取所有E999错误"""
        logger.info("正在获取E999错误列表...")
        errors = []

        try:
            result = subprocess.run(
                ['make', 'lint'],
                capture_output=True,
                text=True,
                timeout=60
            )

            for line in result.stdout.split('\n'):
                if 'E999' in line:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        col_num = int(parts[2])
                        error_msg = parts[3].strip()

                        errors.append({
                            'file': file_path,
                            'line': line_num,
                            'column': col_num,
                            'message': error_msg,
                            'full_line': line
                        })
        except Exception as e:
            logger.error(f"获取E999错误失败: {e}")

        logger.info(f"发现 {len(errors)} 个E999错误")
        return errors

    def fix_syntax_errors(self, file_path: str) -> bool:
        """修复语法错误"""
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            modified = False

            # 修复1: 常见的缩进问题
            content = self.fix_indentation_issues(content)
            if content != original_content:
                modified = True

            # 修复2: 字符串终止符问题
            if self.has_unterminated_strings(content):
                content = self.fix_unterminated_strings(content)
                if content != original_content:
                    modified = True

            # 修复3: 括号匹配问题
            if self.has_unmatched_brackets(content):
                content = self.fix_unmatched_brackets(content)
                if content != original_content:
                    modified = True

            # 修复4: 其他常见语法问题
            content = self.fix_common_syntax_issues(content)
            if content != original_content:
                modified = True

            # 验证修复后的语法
            try:
                ast.parse(content)
            except SyntaxError as e:
                logger.warning(f"文件 {file_path} 仍有语法错误: {e}")
                return False

            # 如果有修改，写回文件
            if modified:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"修复语法错误: {file_path}")
                return True

        except Exception as e:
            logger.error(f"修复文件 {file_path} 失败: {e}")

        return False

    def fix_indentation_issues(self, content: str) -> str:
        """修复缩进问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复过度缩进的import语句
            if line.strip().startswith(('import ', 'from ')):
                # 去除多余缩进
                fixed_line = '    ' + line.strip() if line.strip() else line
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def has_unterminated_strings(self, content: str) -> bool:
        """检查是否有未终止的字符串"""
        try:
            ast.parse(content)
            return False
        except SyntaxError:
            # 简单检查
            return '"""' in content and content.count('"""') % 2 != 0

    def fix_unterminated_strings(self, content: str) -> str:
        """修复未终止的字符串"""
        # 简单的三引号字符串修复
        if '"""' in content and content.count('"""') % 2 != 0:
            content += '"""'
        return content

    def has_unmatched_brackets(self, content: str) -> bool:
        """检查是否有不匹配的括号"""
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []

        for char in content:
            if char in brackets.keys():
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    return True
                expected = brackets[stack.pop()]
                if char != expected:
                    return True

        return len(stack) != 0

    def fix_unmatched_brackets(self, content: str) -> str:
        """修复不匹配的括号"""
        # 简单的括号修复
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复常见的多余括号
            line = re.sub(r'\)\s*\)', ')', line)
            line = re.sub(r'\]\s*\]', ']', line)
            line = re.sub(r'\}\s*\}', '}', line)
            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_common_syntax_issues(self, content: str) -> str:
        """修复常见语法问题"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 修复多余的逗号
            line = re.sub(r',\s*\)', ')', line)
            line = re.sub(r',\s*\]', ']', line)
            line = re.sub(r',\s*\}', '}', line)

            # 修复函数定义中的空参数列表
            line = re.sub(r'def\s+\w+\(\s*,\s*\)', 'def \\1()', line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def run_batch_fix(self) -> Dict:
        """运行批量修复"""
        logger.info("🔧 开始E999语法错误批量修复...")

        errors = self.get_e999_errors()
        if not errors:
            logger.info("没有发现E999错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'message': '没有E999错误需要修复'
            }

        # 获取需要修复的文件列表
        files_to_fix = set(error['file'] for error in errors)

        # 修复每个文件
        files_fixed = 0
        total_errors_fixed = 0

        for file_path in files_to_fix:
            if self.fix_syntax_errors(file_path):
                files_fixed += 1
                # 估算修复的错误数
                file_errors = [e for e in errors if e['file'] == file_path]
                total_errors_fixed += len(file_errors)

            self.files_processed += 1

        result = {
            'success': True,
            'errors_fixed': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'message': f'修复了 {files_fixed} 个文件中的 {total_errors_fixed} 个E999错误'
        }

        logger.info(f"E999批量修复完成: {result}")
        return result

    def generate_report(self) -> Dict:
        """生成修复报告"""
        return {
            'fixer_name': 'E999 Syntax Error Fixer',
            'timestamp': '2025-10-30T01:50:00.000000',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'success_rate': f"{(self.fixes_applied / max(self.files_processed, 1)) * 100:.1f}%"
        }


def main():
    """主函数"""
    fixer = E999SyntaxErrorFixer()

    print("🔧 E999 语法错误批量修复工具")
    print("=" * 50)

    # 运行批量修复
    result = fixer.run_batch_fix()

    # 生成报告
    report = fixer.generate_report()

    print("\n📊 修复摘要:")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   成功率: {report['success_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 失败'}")

    # 保存报告
    report_file = Path('e999_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_file}")

    return result


if __name__ == '__main__':
    main()