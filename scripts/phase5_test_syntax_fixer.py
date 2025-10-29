#!/usr/bin/env python3
"""
Phase 5 测试文件语法错误批量修复器
Phase 5 Test Files Syntax Error Batch Fixer

专门处理测试文件中的语法错误，这是当前最大的错误源
采用智能分析和安全修复策略
"""

import ast
import subprocess
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase5TestSyntaxFixer:
    """Phase 5 测试文件语法错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def get_test_syntax_errors(self) -> Dict[str, List]:
        """获取测试文件中的语法错误"""
        logger.info("🔍 获取测试文件语法错误...")

        try:
            # 查找所有测试文件
            result = subprocess.run(
                ['find', 'tests', '-name', '*.py', '-type', 'f'],
                capture_output=True,
                text=True,
                timeout=60
            )

            test_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            syntax_errors = defaultdict(list)

            for file_path in test_files:
                if not file_path or not Path(file_path).exists():
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
                        'error_type': 'syntax_error',
                        'raw_content': content
                    }
                    syntax_errors[file_path].append(error_info)
                    logger.info(f"🔴 语法错误: {file_path}:{e.lineno} - {e.msg}")

                except Exception as e:
                    logger.warning(f"⚠️ 文件读取失败 {file_path}: {e}")

            total_errors = sum(len(errors) for errors in syntax_errors.values())
            logger.info(f"📊 发现测试文件语法错误: {total_errors} 个，涉及 {len(syntax_errors)} 个文件")

            return dict(syntax_errors)

        except Exception as e:
            logger.error(f"获取测试文件语法错误失败: {e}")
            return {}

    def analyze_test_file_structure(self, content: str) -> Dict:
        """分析测试文件结构"""
        try:
            tree = ast.parse(content)
            analyzer = TestFileAnalyzer()
            analyzer.visit(tree)
            return analyzer.get_analysis()
        except SyntaxError:
            return {'status': 'syntax_error', 'structure': 'invalid'}
        except Exception as e:
            return {'status': 'analysis_error', 'error': str(e)}

    def fix_test_syntax_errors(self, file_path: str, errors: List[Dict]) -> int:
        """修复测试文件中的语法错误"""
        logger.info(f"🔧 修复测试文件: {file_path} ({len(errors)}个错误)")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            lines.copy()
            fixes = 0

            for error in errors:
                line_num = error['line'] - 1
                if 0 <= line_num < len(lines):
                    original_line = lines[line_num]
                    fixed_line = self.fix_test_syntax_line(
                        original_line,
                        error['message'],
                        line_num,
                        lines
                    )

                    if fixed_line != original_line:
                        lines[line_num] = fixed_line
                        fixes += 1
                        logger.info(f"  修复: 第{line_num+1}行 - {error['message'][:50]}...")

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
                # 如果修复后仍有错误，可能需要更复杂的处理
                fixes = 0  # 不计算为成功修复

            return fixes

        except Exception as e:
            logger.error(f"❌ 修复测试文件失败 {file_path}: {e}")
            return 0

    def fix_test_syntax_line(self, line: str, error_message: str, line_num: int, all_lines: List[str]) -> str:
        """修复测试文件中的单行语法错误"""
        fixed_line = line

        # 修复未完成的字符串
        if 'unterminated string literal' in error_message.lower():
            if line.count('"') % 2 == 1:
                fixed_line = line + '"'
            elif line.count("'") % 2 == 1:
                fixed_line = line + "'"

        # 修复未完成的正则表达式
        if 'pattern =' in line and not line.strip().endswith(('"', "'")):
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
        elif 'expected \':\'' in error_message.lower():
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

    def run_test_syntax_fix(self) -> Dict:
        """运行测试文件语法错误批量修复"""
        logger.info("🚀 开始Phase 5测试文件语法错误批量修复...")

        # 1. 获取测试文件语法错误
        test_errors = self.get_test_syntax_errors()

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
        remaining_errors = self.get_test_syntax_errors()
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
            'message': f'修复了 {initial_count - remaining_count} 个测试文件语法错误，{remaining_count} 个剩余'
        }

        logger.info(f"🎉 Phase 5测试文件语法错误修复完成: {result}")
        return result

    def generate_test_fix_report(self) -> Dict:
        """生成测试修复报告"""
        return {
            'phase': 'Phase 5 Week 1',
            'focus': '测试文件语法错误批量修复',
            'target_errors': '921个测试文件语法错误',
            'strategy': '智能分析 + 批量处理 + 安全修复',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_step': 'E722手动修复 + 其他错误清理'
        }

def main():
    """主函数"""
    print("🚀 Phase 5 测试文件语法错误批量修复器")
    print("=" * 70)
    print("🎯 目标: Week 1 - 批量修复测试文件语法错误")
    print("🛠️ 策略: 智能分析 + 批量处理 + 安全修复")
    print("📊 目标: 修复921个测试文件语法错误")
    print("=" * 70)

    fixer = Phase5TestSyntaxFixer()
    result = fixer.run_test_syntax_fix()

    print("\n📊 测试文件语法错误修复摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

    # 生成报告
    report = fixer.generate_test_fix_report()

    # 保存报告
    report_file = Path('phase5_test_syntax_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 测试文件语法错误修复报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n⚠️ 仍有 {result['remaining_errors']} 个测试文件语法错误需要处理")
        print("💡 建议: 检查复杂的语法问题，可能需要更深入的修复")

    return result

class TestFileAnalyzer(ast.NodeVisitor):
    """测试文件结构分析器"""

    def __init__(self):
        self.analysis = {
            'status': 'analyzed',
            'structure': 'valid',
            'imports': [],
            'functions': [],
            'classes': [],
            'tests': []
        }

    def visit_Import(self, node):
        """访问导入节点"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.analysis['imports'].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            self.analysis['imports'].append(f"from {node.module}")

    def visit_FunctionDef(self, node):
        """访问函数定义节点"""
        self.analysis['functions'].append(node.name)

    def visit_AsyncFunctionDef(self, node):
        """访问异步函数定义节点"""
        self.analysis['functions'].append(f"async {node.name}")

    def visit_ClassDef(self, node):
        """访问类定义节点"""
        self.analysis['classes'].append(node.name)

    def visit_Call(self, node):
        """访问函数调用节点"""
        if isinstance(node.func, ast.Name):
            if node.func.id.startswith('test_'):
                self.analysis['tests'].append(node.func.id)

    def get_analysis(self) -> Dict:
        """获取分析结果"""
        return self.analysis

if __name__ == '__main__':
    main()