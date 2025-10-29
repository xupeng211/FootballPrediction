#!/usr/bin/env python3
"""
Phase 5 语法错误专项修复器
Phase 5 Syntax Error Specialist Fixer

专门处理Phase 5 Week 1的语法错误修复任务
目标: 解决916个语法错误，为后续批量修复打好基础
"""

import ast
import subprocess
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase5SyntaxErrorFixer:
    """Phase 5 语法错误专项修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def get_syntax_errors(self) -> Dict[str, List]:
        """获取语法错误详细信息"""
        logger.info("🔍 获取语法错误详细信息...")

        try:
            # 使用Python编译器检查语法错误
            result = subprocess.run(
                ['find', 'src', '-name', '*.py', '-type', 'f'],
                capture_output=True,
                text=True,
                timeout=60
            )

            python_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            syntax_errors = defaultdict(list)

            for file_path in python_files:
                if not file_path:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 尝试编译检查语法
                    ast.parse(content)
                    logger.info(f"✅ 语法正确: {file_path}")

                except SyntaxError as e:
                    error_info = {
                        'file': file_path,
                        'line': e.lineno or 0,
                        'column': e.offset or 0,
                        'message': str(e),
                        'error_type': 'syntax_error'
                    }
                    syntax_errors[file_path].append(error_info)
                    logger.info(f"🔴 语法错误: {file_path}:{e.lineno} - {e.msg}")

                except Exception as e:
                    logger.warning(f"⚠️ 文件读取失败 {file_path}: {e}")

            # 也检查ruff报告的语法错误
            try:
                ruff_result = subprocess.run(
                    ['ruff', 'check', '--select=E999', '--format=json'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if ruff_result.stdout.strip():
                    try:
                        ruff_errors = json.loads(ruff_result.stdout)
                        for error in ruff_errors:
                            if error.get('code') == 'E999':
                                file_path = error['filename']
                                error_info = {
                                    'file': file_path,
                                    'line': error['location']['row'],
                                    'column': error['location']['column'],
                                    'message': error['message'],
                                    'error_type': 'ruff_e999'
                                }
                                syntax_errors[file_path].append(error_info)
                                logger.info(f"🔴 Ruff语法错误: {file_path}:{error['location']['row']} - {error['message']}")
                    except json.JSONDecodeError:
                        logger.warning("无法解析Ruff JSON输出")

            except Exception as e:
                logger.warning(f"Ruff检查失败: {e}")

            total_errors = sum(len(errors) for errors in syntax_errors.values())
            logger.info(f"📊 发现语法错误: {total_errors} 个，涉及 {len(syntax_errors)} 个文件")

            return dict(syntax_errors)

        except Exception as e:
            logger.error(f"获取语法错误失败: {e}")
            return {}

    def fix_syntax_error_in_file(self, file_path: str, errors: List[Dict]) -> int:
        """修复单个文件中的语法错误"""
        logger.info(f"🔧 修复文件: {file_path} ({len(errors)}个错误)")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            original_lines = lines.copy()
            fixes = 0

            for error in errors:
                line_num = error['line'] - 1
                if 0 <= line_num < len(lines):
                    original_line = lines[line_num]
                    fixed_line = self.fix_syntax_line(original_line, error['message'])

                    if fixed_line != original_line:
                        lines[line_num] = fixed_line
                        fixes += 1
                        logger.info(f"  修复: 第{line_num+1}行 - {error['message'][:50]}...")

            # 如果有修改，写回文件
            if lines != original_lines:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.files_fixed += 1
                logger.info(f"✅ 文件修复成功: {file_path}")

            return fixes

        except Exception as e:
            logger.error(f"❌ 修复文件失败 {file_path}: {e}")
            return 0

    def fix_syntax_line(self, line: str, error_message: str) -> str:
        """修复单行语法错误"""
        fixed_line = line

        # 修复未完成的字符串
        if 'unterminated string literal' in error_message.lower():
            # 检查字符串引号
            if line.count('"') % 2 == 1:
                fixed_line = line + '"'
            elif line.count("'") % 2 == 1:
                fixed_line = line + "'"

        # 修复未完成的括号
        elif 'unexpected EOF while parsing' in error_message.lower():
            # 计算括号匹配
            open_parens = line.count('(') - line.count(')')
            open_brackets = line.count('[') - line.count(']')
            open_braces = line.count('{') - line.count('}')

            if open_parens > 0:
                fixed_line = line + ')' * open_parens
            elif open_brackets > 0:
                fixed_line = line + ']' * open_brackets
            elif open_braces > 0:
                fixed_line = line + '}' * open_braces

        # 修复缩进问题
        elif 'unexpected indent' in error_message.lower():
            fixed_line = line.lstrip()

        # 修复缺少冒号
        elif 'expected \':\'' in error_message.lower():
            if line.strip().endswith(':') is False:
                if any(keyword in line for keyword in ['if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'def', 'class']):
                    fixed_line = line.rstrip() + ':'

        # 修复无效语法
        elif 'invalid syntax' in error_message.lower():
            # 常见的模式修复
            if 'pattern =' in line and not line.strip().endswith(('"', "'")):
                # 可能是未完成的正则表达式
                if '"' in line:
                    fixed_line = line.rstrip() + '"'
                elif "'" in line:
                    fixed_line = line.rstrip() + "'"

            # 修复return语句后的代码
            elif line.strip().startswith('return ') and 'async def test_async()' in line:
                # 这是特殊的async函数调用问题
                fixed_line = line.replace('async def test_async()', 'asyncio.run(test_async())')

        return fixed_line

    def run_phase5_syntax_fix(self) -> Dict:
        """运行Phase 5语法错误专项修复"""
        logger.info("🚀 开始Phase 5 Week 1语法错误专项修复...")

        # 1. 获取语法错误
        syntax_errors = self.get_syntax_errors()

        if not syntax_errors:
            logger.info("✅ 没有发现语法错误")
            return {
                'success': True,
                'total_errors': 0,
                'files_processed': 0,
                'files_fixed': 0,
                'errors_fixed': 0,
                'message': '没有语法错误需要修复'
            }

        # 2. 按优先级排序文件
        # 测试文件优先修复
        sorted_files = sorted(syntax_errors.keys(), key=lambda x: (
            0 if 'test' in x else 1,  # 测试文件优先
            len(syntax_errors[x]),     # 错误多的文件优先
            x
        ))

        # 3. 修复每个文件
        total_errors_fixed = 0

        for file_path in sorted_files:
            file_errors = syntax_errors[file_path]
            fixes = self.fix_syntax_error_in_file(file_path, file_errors)
            total_errors_fixed += fixes
            self.files_processed += 1

        # 4. 验证修复效果
        remaining_errors = self.get_syntax_errors()
        remaining_count = sum(len(errors) for errors in remaining_errors.values())

        # 5. 生成报告
        initial_count = sum(len(errors) for errors in syntax_errors.values())
        result = {
            'success': total_errors_fixed > 0,
            'initial_errors': initial_count,
            'remaining_errors': remaining_count,
            'errors_fixed': initial_count - remaining_count,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'fix_rate': f"{((initial_count - remaining_count) / max(initial_count, 1)) * 100:.1f}%",
            'message': f'修复了 {initial_count - remaining_count} 个语法错误，{remaining_count} 个剩余'
        }

        logger.info(f"🎉 Phase 5语法错误修复完成: {result}")
        return result

    def generate_phase5_report(self) -> Dict:
        """生成Phase 5报告"""
        return {
            'phase': 'Phase 5 Week 1',
            'focus': '语法错误专项修复',
            'target_errors': '916个语法错误',
            'strategy': '手动精确修复 + 验证测试',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'next_step': 'Week 2: E722批量修复 + 其他错误清理'
        }

def main():
    """主函数"""
    print("🚀 Phase 5 语法错误专项修复器")
    print("=" * 60)
    print("🎯 目标: Week 1 - 解决语法错误")
    print("🛠️ 策略: 手动精确修复 + 验证测试")
    print("📊 目标: 修复916个语法错误")
    print("=" * 60)

    fixer = Phase5SyntaxErrorFixer()
    result = fixer.run_phase5_syntax_fix()

    print("\n📊 Phase 5 Week 1修复摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

    # 生成报告
    report = fixer.generate_phase5_report()

    # 保存报告
    report_file = Path('phase5_syntax_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Phase 5修复报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n⚠️ 仍有 {result['remaining_errors']} 个语法错误需要处理")
        print("💡 建议: 检查复杂的语法问题，可能需要手动修复")

    return result

if __name__ == '__main__':
    main()