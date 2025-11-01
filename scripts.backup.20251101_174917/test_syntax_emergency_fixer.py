#!/usr/bin/env python3
"""
测试文件语法错误紧急修复器
Test Files Syntax Error Emergency Fixer

专门用于快速修复测试文件中常见语法错误的工具
采用模式识别和批量修复策略
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSyntaxEmergencyFixer:
    """测试文件语法错误紧急修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def find_test_syntax_errors(self) -> Dict[str, List[Tuple[int, str]]]:
        """查找测试文件中的语法错误"""
        logger.info("🔍 查找测试文件语法错误...")

        test_errors = {}

        # 遍历所有测试文件
        for root, dirs, files in os.walk('tests'):
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 尝试编译检查语法
                        ast.parse(content)
                        logger.info(f"✅ 语法正确: {file_path}")

                    except SyntaxError as e:
                        error_info = (e.lineno or 0, str(e.msg))
                        if file_path not in test_errors:
                            test_errors[file_path] = []
                        test_errors[file_path].append(error_info)
                        logger.info(f"🔴 语法错误: {file_path}:{e.lineno} - {e.msg}")

                    except Exception as e:
                        logger.warning(f"⚠️ 文件处理失败 {file_path}: {e}")

        total_errors = sum(len(errors) for errors in test_errors.values())
        logger.info(f"📊 发现测试文件语法错误: {total_errors} 个，涉及 {len(test_errors)} 个文件")

        return test_errors

    def fix_test_syntax_errors(self, file_path: str, errors: List[Tuple[int, str]]) -> int:
        """修复单个测试文件中的语法错误"""
        logger.info(f"🔧 修复测试文件: {file_path} ({len(errors)}个错误)")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            lines.copy()
            fixes = 0

            for line_num, error_msg in errors:
                line_index = line_num - 1

                if 0 <= line_index < len(lines):
                    original_line = lines[line_index]
                    fixed_line = self.fix_syntax_line(original_line, error_msg, line_index, lines)

                    if fixed_line != original_line:
                        lines[line_index] = fixed_line
                        fixes += 1
                        logger.info(f"  修复: 第{line_num}行 - {error_msg[:50]}...")

            # 特殊处理：修复常见的测试文件模式
            lines = self.fix_common_test_patterns(lines)

            # 检查修复后的语法
            try:
                fixed_content = '\n'.join(lines)
                ast.parse(fixed_content)
                logger.info(f"✅ 修复后语法正确: {file_path}")

                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                self.files_fixed += 1

            except SyntaxError as e:
                logger.warning(f"⚠️ 修复后仍有语法错误: {file_path}:{e.lineno} - {e.msg}")
                fixes = 0  # 不计算为成功修复

            return fixes

        except Exception as e:
            logger.error(f"❌ 修复测试文件失败 {file_path}: {e}")
            return 0

    def fix_syntax_line(self, line: str, error_message: str, line_num: int, all_lines: List[str]) -> str:
        """修复单行语法错误"""
        fixed_line = line

        # 修复未完成的字符串
        if 'unterminated string literal' in error_message.lower():
            if line.count('"') % 2 == 1:
                fixed_line = line + '"'
            elif line.count("'") % 2 == 1:
                fixed_line = line + "'"

        # 修复未完成的正则表达式
        elif 'pattern =' in line and not line.strip().endswith(('"', "'")):
            # 查找下一行是否是字符串
            if line_num + 1 < len(all_lines):
                next_line = all_lines[line_num + 1]
                if next_line.strip().startswith('"'):
                    fixed_line = line.rstrip() + ' ' + next_line.strip()
                    all_lines[line_num + 1] = ''  # 删除下一行
                    logger.info("  修复: 合并未完成的正则表达式")

        # 修复缩进问题
        elif 'unexpected indent' in error_message.lower():
            fixed_line = line.lstrip()

        # 修复缺少冒号
        elif "expected ':'" in error_message.lower():
            if line.strip().endswith(':') is False:
                if any(keyword in line for keyword in ['if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'def', 'class', 'async def']):
                    fixed_line = line.rstrip() + ':'

        # 修复import语句缩进
        elif line.strip().startswith('from ') and line.startswith('    ') and line_num > 0:
            if not all_lines[line_num - 1].strip().startswith('from ') and not all_lines[line_num - 1].strip().startswith('import '):
                fixed_line = line.strip()  # 移除缩进

        # 修复函数定义缩进
        elif 'def ' in line and line.startswith('    ') and line_num > 0:
            if not all_lines[line_num - 1].strip().startswith(('def ', 'class ', 'async def ')):
                # 可能是顶层函数被错误缩进
                prev_line = all_lines[line_num - 1].strip()
                if prev_line and not prev_line.startswith('#'):
                    fixed_line = line.strip()  # 移除缩进

        # 修复无效语法中的pattern定义
        elif 'invalid syntax' in error_message.lower() and 'pattern =' in line:
            if not line.strip().endswith(('"', "'")):
                # 可能是未完成的字符串定义
                if '"' in line and line.count('"') % 2 == 1:
                    fixed_line = line.rstrip() + '"'
                elif "'" in line and line.count("'") % 2 == 1:
                    fixed_line = line.rstrip() + "'"

        return fixed_line

    def fix_common_test_patterns(self, lines: List[str]) -> List[str]:
        """修复测试文件中的常见模式错误"""
        fixed_lines = lines.copy()

        for i, line in enumerate(fixed_lines):
            # 修复导入语句缩进错误
            if line.strip().startswith('from ') and line.startswith('    '):
                # 检查是否应该移除缩进
                if i == 0:
                    fixed_lines[i] = line.lstrip()
                elif i > 0:
                    prev_line = fixed_lines[i - 1].strip()
                    if not prev_line.startswith(('from ', 'import ')) and not prev_line.startswith('#'):
                        fixed_lines[i] = line.lstrip()

            # 修复函数定义缩进错误
            if line.strip().startswith('def ') and line.startswith('    '):
                if i == 0:
                    fixed_lines[i] = line.lstrip()
                elif i > 0:
                    prev_line = fixed_lines[i - 1].strip()
                    if not prev_line.startswith(('def ', 'class ', 'async def ')) and not prev_line.startswith('#'):
                        fixed_lines[i] = line.lstrip()

            # 修复类定义缩进错误
            if line.strip().startswith('class ') and line.startswith('    '):
                if i == 0:
                    fixed_lines[i] = line.lstrip()
                elif i > 0:
                    prev_line = fixed_lines[i - 1].strip()
                    if not prev_line.startswith(('class ', 'def ', 'async def ')) and not prev_line.startswith('#'):
                        fixed_lines[i] = line.lstrip()

        return fixed_lines

    def run_emergency_fix(self) -> Dict:
        """运行紧急语法错误修复"""
        logger.info("🚀 开始测试文件语法错误紧急修复...")

        # 1. 获取测试文件语法错误
        test_errors = self.find_test_syntax_errors()

        if not test_errors:
            logger.info("✅ 没有发现测试文件语法错误")
            return {
                'success': True,
                'total_errors': 0,
                'files_processed': 0,
                'files_fixed': 0,
                'errors_fixed': 0,
                'message': '没有测试文件语法错误需要修复'
            }

        # 2. 按优先级排序文件
        sorted_files = sorted(test_errors.keys(), key=lambda x: (
            0 if 'test_' in x else 1,  # 测试文件优先
            len(test_errors[x]),     # 错误多的文件优先
            x
        ))

        # 3. 修复每个测试文件
        total_errors_fixed = 0

        for file_path in sorted_files:
            file_errors = test_errors[file_path]
            fixes = self.fix_test_syntax_errors(file_path, file_errors)
            total_errors_fixed += fixes
            self.files_processed += 1

        # 4. 验证修复效果
        remaining_errors = self.find_test_syntax_errors()
        remaining_count = sum(len(errors) for errors in remaining_errors.values())

        # 5. 生成报告
        initial_count = sum(len(errors) for errors in test_errors.values())
        result = {
            'success': total_errors_fixed > 0,
            'initial_errors': initial_count,
            'remaining_errors': remaining_count,
            'errors_fixed': initial_count - remaining_count,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'fix_rate': f"{((initial_count - remaining_count) / max(initial_count, 1)) * 100:.1f}%",
            'message': f'紧急修复了 {initial_count - remaining_count} 个测试文件语法错误，{remaining_count} 个剩余'
        }

        logger.info(f"🎉 测试文件语法错误紧急修复完成: {result}")
        return result

def main():
    """主函数"""
    print("🚀 测试文件语法错误紧急修复器")
    print("=" * 60)
    print("🎯 目标: 紧急修复测试文件语法错误")
    print("⚡ 策略: 模式识别 + 批量修复")
    print("📊 目标: 大幅减少测试文件语法错误")
    print("=" * 60)

    fixer = TestSyntaxEmergencyFixer()
    result = fixer.run_emergency_fix()

    print("\n📊 测试文件语法错误紧急修复摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

    return result

if __name__ == '__main__':
    main()