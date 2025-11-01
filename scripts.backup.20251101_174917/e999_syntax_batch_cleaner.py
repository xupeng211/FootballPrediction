#!/usr/bin/env python3
"""
E999语法错误批量清理工具
E999 Syntax Error Batch Cleaner

专门用于批量清理E999语法错误，通过：
1. 智能识别语法错误类型
2. 分类修复策略
3. 安全批量处理
4. 验证修复效果

目标: 清理140个E999语法错误
"""

import ast
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from src.core.config import *
from src.core.config import *
class E999SyntaxCleaner:
    """E999语法错误清理器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def get_e999_errors(self) -> List[Dict]:
        """获取所有E999语法错误"""
        print("🔍 正在获取E999语法错误...")

        errors = []
        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=E999', '--format=json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.stdout.strip():
                error_data = json.loads(result.stdout)
                for error in error_data:
                    if error.get('code') == 'E999':
                        errors.append({
                            'file': error['filename'],
                            'line': error['location']['row'],
                            'column': error['location']['column'],
                            'message': error['message'],
                            'code': 'E999'
                        })

        except Exception as e:
            print(f"获取E999错误失败: {e}")

        print(f"📊 发现 {len(errors)} 个E999语法错误")
        return errors

    def analyze_syntax_error(self, file_path: str, line_num: int) -> Dict:
        """分析语法错误的具体类型"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                error_line = lines[line_num - 1]
                error_content = error_line.strip()

                # 分析错误类型
                analysis = {
                    'type': 'unknown',
                    'strategy': 'manual',
                    'context': error_content,
                    'suggestions': []
                }

                # 缩进错误
                if any(keyword in error_line.lower() for keyword in ['indentationerror', 'unexpected indent']):
                    analysis.update({
                        'type': 'indentation_error',
                        'strategy': 'fix_indentation',
                        'suggestions': ['检查缩进级别', '统一使用4个空格', '检查混合空格和制表符']
                    })

                # 导入语句错误
                if 'import' in error_line and any(keyword in error_line.lower() for keyword in ['invalid syntax', 'syntaxerror']):
                    analysis.update({
                        'type': 'import_syntax_error',
                        'strategy': 'fix_import_syntax',
                        'suggestions': ['检查import语句格式', '验证模块路径', '修复语法结构']
                    })

                # 括号匹配错误
                if any(char in error_line for char in ['(', ')', '[', ']', '{', '}']) and 'invalid syntax' in error_line.lower():
                    analysis.update({
                        'type': 'bracket_mismatch',
                        'strategy': 'fix_brackets',
                        'suggestions': ['检查括号匹配', '验证语法结构', '修复嵌套问题']
                    })

                # 一般语法错误
                if 'invalid syntax' in error_line.lower():
                    analysis.update({
                        'type': 'general_syntax_error',
                        'strategy': 'try_auto_fix',
                        'suggestions': ['检查语法结构', '验证关键字使用', '检查特殊字符']
                    })

                return analysis

        except Exception as e:
            print(f"分析文件 {file_path} 失败: {e}")
            return {'type': 'analysis_error', 'strategy': 'manual', 'error': str(e)}

        return {'type': 'line_not_found', 'strategy': 'skip'}

    def fix_indentation_error(self, file_path: str, line_num: int) -> bool:
        """修复缩进错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                error_line = lines[line_num - 1]
                stripped_line = error_line.lstrip()

                if not stripped_line:  # 空行，跳过
                    return False

                # 计算正确的缩进
                current_indent = len(error_line) - len(stripped_line)

                # 查找上一行的缩进级别作为参考
                prev_indent = 0
                for i in range(line_num - 2, -1, -1):
                    if lines[i].strip():
                        prev_indent = len(lines[i]) - len(lines[i].lstrip())
                        break

                # 根据代码行内容确定缩进
                target_indent = prev_indent

                # 函数/类定义在顶层
                if stripped_line.startswith(('def ', 'class ')):
                    target_indent = 0
                # if/elif/else/for/while/try/except/finally/with 语句
                elif any(stripped_line.startswith(keyword) for keyword in [
                    'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'finally:', 'with '
                ]):
                    target_indent = prev_indent + 4
                # return/break/continue语句
                elif any(stripped_line.startswith(keyword) for keyword in ['return ', 'break', 'continue', 'pass']):
                    target_indent = prev_indent + 4

                # 修复缩进
                if current_indent != target_indent:
                    fixed_line = ' ' * target_indent + stripped_line + '\n'
                    lines[line_num - 1] = fixed_line

                    # 写回文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    print(f"✅ 修复缩进错误: {file_path}:{line_num} - 缩进从{current_indent}改为{target_indent}")
                    return True

        except Exception as e:
            print(f"修复缩进错误失败 {file_path}:{line_num}: {e}")

        return False

    def fix_import_syntax_error(self, file_path: str, line_num: int) -> bool:
        """修复导入语句语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                error_line = lines[line_num - 1]

                # 常见导入问题修复
                fixed_line = error_line

                # 修复多余的逗号或句号
                fixed_line = re.sub(r',\s*$', '', fixed_line)
                fixed_line = re.sub(r'\.\s*$', '', fixed_line)

                # 修复不完整的导入语句
                if fixed_line.strip().endswith(('import ', 'from ')):
                    fixed_line = fixed_line.rstrip() + '\n'
                    lines[line_num - 1] = fixed_line
                    print(f"⚠️ 标记不完整导入语句: {file_path}:{line_num}")
                    return False

                # 修复明显的语法问题
                fixed_line = re.sub(r'\s+', ' ', fixed_line)  # 合并多余空格
                fixed_line = fixed_line.strip() + '\n'

                if fixed_line != error_line:
                    lines[line_num - 1] = fixed_line

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    print(f"✅ 修复导入语法: {file_path}:{line_num}")
                    return True

        except Exception as e:
            print(f"修复导入语法错误失败 {file_path}:{line_num}: {e}")

        return False

    def fix_bracket_mismatch(self, file_path: str, line_num: int) -> bool:
        """修复括号匹配错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST检查语法
            try:
                ast.parse(content)
                print(f"✅ 文件语法正确: {file_path}")
                return True
            except SyntaxError as e:
                # 获取语法错误的位置
                error_line_num = e.lineno if hasattr(e, 'lineno') else line_num
                if error_line_num == line_num:
                    lines = content.split('\n')
                    error_line = lines[line_num - 1]

                    # 尝试简单的括号修复
                    if '(' in error_line or ')' in error_line:
                        # 检查括号平衡
                        open_count = error_line.count('(')
                        close_count = error_line.count(')')

                        if open_count > close_count:
                            fixed_line = error_line + ')' * (open_count - close_count)
                        elif close_count > open_count:
                            fixed_line = error_line[:-(close_count - open_count)]

                        lines[line_num - 1] = fixed_line

                        # 尝试重新解析
                        try:
                            ast.parse('\n'.join(lines))
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines))
                            print(f"✅ 修复括号错误: {file_path}:{line_num}")
                            return True
                        except SyntaxError:
                            print(f"⚠️ 括号修复失败: {file_path}:{line_num}")

        except Exception as e:
            print(f"修复括号错误失败 {file_path}: {e}")

        return False

    def try_auto_fix(self, file_path: str, line_num: int) -> bool:
        """尝试自动修复一般语法错误"""
        try:
            # 尝试使用Ruff的自动修复功能
            result = subprocess.run(
                ['ruff', 'check', '--select=E999', '--fix', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"✅ Ruff自动修复语法错误: {file_path}")
                return True
            else:
                print(f"⚠️ Ruff无法自动修复: {file_path} - {result.stderr}")
                return False

        except Exception as e:
            print(f"一般语法错误修复失败 {file_path}: {e}")

        return False

    def apply_syntax_fix(self, file_path: str, line_num: int, error_analysis: Dict) -> bool:
        """应用语法修复"""
        strategy = error_analysis['strategy']

        if strategy == 'fix_indentation':
            return self.fix_indentation_error(file_path, line_num)
        elif strategy == 'fix_import_syntax':
            return self.fix_import_syntax_error(file_path, line_num)
        elif strategy == 'fix_brackets':
            return self.fix_bracket_mismatch(file_path, line_num)
        elif strategy == 'try_auto_fix':
            return self.try_auto_fix(file_path, line_num)
        else:
            print(f"未知修复策略: {strategy} for {file_path}:{line_num}")
            return False

    def run_batch_syntax_clean(self) -> Dict:
        """运行批量语法清理"""
        print("🔧 开始E999语法错误批量清理...")

        errors = self.get_e999_errors()
        if not errors:
            print("✅ 没有发现E999语法错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'files_fixed': 0,
                'message': '没有E999语法错误需要修复'
            }

        # 按文件分组错误
        errors_by_file = {}
        for error in errors:
            file_path = error['file']
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error)

        # 修复每个文件的语法错误
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, file_errors in errors_by_file.items():
            print(f"🔧 正在修复文件: {file_path} ({len(file_errors)}个语法错误)")

            file_fixed = False
            for error in file_errors:
                line_num = error['line']

                # 分析错误类型
                error_analysis = self.analyze_syntax_error(file_path, line_num)
                print(f"📋 错误分析: {file_path}:{line_num} - {error_analysis['type']}")

                # 应用修复
                if self.apply_syntax_fix(file_path, line_num, error_analysis):
                    total_errors_fixed += 1
                    file_fixed = True

            if file_fixed:
                files_fixed += 1

            self.files_processed += 1

        # 验证修复效果
        remaining_errors = len(self.get_e999_errors())
        errors_fixed = len(errors) - remaining_errors

        result = {
            'success': errors_fixed > 0,
            'initial_errors': len(errors),
            'remaining_errors': remaining_errors,
            'errors_fixed': errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'fix_rate': f"{(errors_fixed / max(len(errors), 1)) * 100:.1f}%",
            'message': f'修复了 {errors_fixed} 个语法错误，{remaining_errors} 个剩余'
        }

        print(f"✅ E999语法错误批量清理完成: {result}")
        return result

    def generate_cleaner_report(self) -> Dict:
        """生成清理报告"""
        return {
            'cleaner_name': 'E999 Syntax Error Batch Cleaner',
            'timestamp': '2025-10-30T02:15:00.000000',
            'target_errors': '140 E999 syntax errors',
            'strategy': 'Intelligent analysis + classified fix + safety validation',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_step': 'Proceed to F841 unused variable cleanup'
        }


def main():
    """主函数"""
    print("🔧 E999 语法错误批量清理工具")
    print("=" * 60)
    print("🎯 目标: 140个E999语法错误 → 清理完成")
    print("🛡️ 策略: 智能分析 + 分类修复 + 安全验证")
    print("=" * 60)

    cleaner = E999SyntaxCleaner()

    # 运行批量语法清理
    result = cleaner.run_batch_syntax_clean()

    # 生成报告
    report = cleaner.generate_cleaner_report()

    print("\n📊 语法清理摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 需要手动处理'}")

    # 保存清理报告
    report_file = Path('e999_syntax_cleaner_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 语法清理报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n⚠️ 仍有 {result['remaining_errors']} 个语法错误需要手动处理")
        print("🔧 建议: 检查具体错误文件，手动修复复杂的语法问题")

    return result


if __name__ == '__main__':
    main()