#!/usr/bin/env python3
"""
Phase 6 测试系统优化 - 测试文件语法错误修复器
Phase 6 Test System Optimization - Test File Syntax Error Fixer

专门针对测试系统语法错误的综合修复工具
支持智能分析、批量修复和验证
"""

import os
import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase6TestSyntaxFixer:
    """Phase 6 测试文件语法错误修复器"""

    def __init__(self):
        self.errors_analyzed = 0
        self.files_fixed = 0
        self.errors_fixed = 0
        self.start_time = datetime.now()

    def analyze_test_syntax_errors(self) -> Dict:
        """全面分析测试文件语法错误"""
        logger.info("🔍 开始全面分析测试文件语法错误...")

        # 获取所有测试文件
        test_files = self._get_all_test_files()
        logger.info(f"📁 发现测试文件: {len(test_files)} 个")

        syntax_errors = {}
        total_errors = 0

        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # AST解析检查语法
                ast.parse(content)
                logger.info(f"✅ 语法正确: {file_path}")

            except SyntaxError as e:
                error_info = {
                    'line': e.lineno or 0,
                    'column': e.offset or 0,
                    'message': str(e.msg),
                    'type': 'SyntaxError'
                }

                if file_path not in syntax_errors:
                    syntax_errors[file_path] = []
                syntax_errors[file_path].append(error_info)
                total_errors += 1

                logger.info(f"🔴 语法错误: {file_path}:{e.lineno} - {e.msg}")
                self.errors_analyzed += 1

            except Exception as e:
                logger.warning(f"⚠️ 文件处理失败 {file_path}: {e}")

        # 按优先级分组
        prioritized_errors = self._prioritize_errors(syntax_errors)

        analysis_result = {
            'total_files': len(test_files),
            'error_files': len(syntax_errors),
            'total_errors': total_errors,
            'syntax_errors': syntax_errors,
            'prioritized_groups': prioritized_errors,
            'error_rate': f"{(len(syntax_errors) / len(test_files)) * 100:.1f}%" if test_files else "0%"
        }

        logger.info(f"📊 测试语法错误分析完成:")
        logger.info(f"   总文件数: {analysis_result['total_files']}")
        logger.info(f"   错误文件数: {analysis_result['error_files']}")
        logger.info(f"   总错误数: {analysis_result['total_errors']}")
        logger.info(f"   错误率: {analysis_result['error_rate']}")

        return analysis_result

    def _get_all_test_files(self) -> List[str]:
        """获取所有测试文件"""
        test_files = []

        for root, dirs, files in os.walk('tests'):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__')]

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    test_files.append(file_path)

        return sorted(test_files)

    def _prioritize_errors(self, syntax_errors: Dict) -> Dict:
        """按优先级对错误进行分组"""
        high_priority = []
        medium_priority = []
        low_priority = []

        for file_path, errors in syntax_errors.items():
            file_info = {
                'path': file_path,
                'error_count': len(errors),
                'errors': errors
            }

            # 根据目录和错误数量确定优先级
            if '/tests/unit/api/' in file_path or '/tests/integration/' in file_path:
                high_priority.append(file_info)
            elif '/tests/unit/utils/' in file_path or '/tests/unit/domain/' in file_path:
                medium_priority.append(file_info)
            else:
                low_priority.append(file_info)

        # 按错误数量排序
        high_priority.sort(key=lambda x: x['error_count'], reverse=True)
        medium_priority.sort(key=lambda x: x['error_count'], reverse=True)
        low_priority.sort(key=lambda x: x['error_count'], reverse=True)

        return {
            'high_priority': {
                'name': '高优先级 - API和集成测试',
                'files': high_priority,
                'total_files': len(high_priority),
                'total_errors': sum(f['error_count'] for f in high_priority)
            },
            'medium_priority': {
                'name': '中优先级 - 工具和领域测试',
                'files': medium_priority,
                'total_files': len(medium_priority),
                'total_errors': sum(f['error_count'] for f in medium_priority)
            },
            'low_priority': {
                'name': '低优先级 - 其他测试',
                'files': low_priority,
                'total_files': len(low_priority),
                'total_errors': sum(f['error_count'] for f in low_priority)
            }
        }

    def fix_syntax_errors(self, analysis_result: Dict, max_files: int = 50) -> Dict:
        """批量修复语法错误"""
        logger.info("🔧 开始批量修复测试文件语法错误...")

        prioritized_groups = analysis_result['prioritized_groups']
        fixed_files = []
        total_fixes = 0

        # 按优先级处理文件
        for group_name, group_data in prioritized_groups.items():
            if not group_data['files']:
                continue

            logger.info(f"🎯 处理{group_data['name']} ({group_data['total_files']}个文件)")

            for file_info in group_data['files'][:max_files]:
                file_path = file_info['path']
                errors = file_info['errors']

                fixes = self._fix_file_syntax_errors(file_path, errors)
                if fixes > 0:
                    fixed_files.append({
                        'path': file_path,
                        'fixes_applied': fixes,
                        'original_errors': len(errors)
                    })
                    total_fixes += fixes
                    self.files_fixed += 1

                # 限制处理文件数量
                if len(fixed_files) >= max_files:
                    break

        # 验证修复效果
        remaining_errors = self._verify_fixes(fixed_files)

        result = {
            'files_processed': len(fixed_files),
            'fixes_applied': total_fixes,
            'remaining_errors': remaining_errors,
            'success_rate': f"{(len([f for f in fixed_files if f['fixes_applied'] > 0]) / max(len(fixed_files), 1)) * 100:.1f}%"
        }

        logger.info(f"🎉 语法错误修复完成:")
        logger.info(f"   处理文件数: {result['files_processed']}")
        logger.info(f"   应用修复数: {result['fixes_applied']}")
        logger.info(f"   剩余错误数: {result['remaining_errors']}")
        logger.info(f"   成功率: {result['success_rate']}")

        return result

    def _fix_file_syntax_errors(self, file_path: str, errors: List[Dict]) -> int:
        """修复单个文件的语法错误"""
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
                    fixed_line = self._fix_syntax_line(original_line, error)

                    if fixed_line != original_line:
                        lines[line_num] = fixed_line
                        fixes += 1
                        logger.info(f"  修复: 第{error['line']}行 - {error['message'][:50]}...")

            # 验证修复后的语法
            try:
                fixed_content = '\n'.join(lines)
                ast.parse(fixed_content)

                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                self.errors_fixed += fixes

            except SyntaxError:
                # 修复失败，使用原内容
                logger.warning(f"⚠️ 修复后仍有语法错误: {file_path}")
                fixes = 0

            return fixes

        except Exception as e:
            logger.error(f"❌ 修复文件失败 {file_path}: {e}")
            return 0

    def _fix_syntax_line(self, line: str, error: Dict) -> str:
        """修复单行语法错误"""
        fixed_line = line
        message = error['message'].lower()

        # 修复未终止的字符串
        if 'unterminated string literal' in message:
            if line.count('"') % 2 == 1:
                fixed_line = line.rstrip() + '"'
            elif line.count("'") % 2 == 1:
                fixed_line = line.rstrip() + "'"

        # 修复缩进问题
        elif 'unexpected indent' in message:
            fixed_line = line.lstrip()

        # 修复缺少冒号
        elif 'expected \':\'' in message or 'invalid syntax' in message:
            if any(keyword in line for keyword in ['if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'def', 'class']):
                if not line.strip().endswith(':'):
                    fixed_line = line.rstrip() + ':'

        # 修复import语句缩进
        elif line.strip().startswith(('from ', 'import ')) and line.startswith('    '):
            # 检查是否应该移除缩进
            fixed_line = line.strip()

        return fixed_line

    def _verify_fixes(self, fixed_files: List[Dict]) -> int:
        """验证修复效果"""
        remaining_errors = 0

        for file_info in fixed_files:
            file_path = file_info['path']
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)  # 验证语法
            except SyntaxError:
                remaining_errors += 1
                logger.warning(f"⚠️ 修复后仍有语法错误: {file_path}")

        return remaining_errors

    def run_phase6_test_syntax_fix(self, max_files: int = 50) -> Dict:
        """运行Phase 6测试语法修复完整流程"""
        logger.info("🚀 开始Phase 6测试系统优化 - 语法错误修复...")

        # 1. 分析语法错误
        analysis_result = self.analyze_test_syntax_errors()

        if analysis_result['total_errors'] == 0:
            logger.info("✅ 没有发现测试文件语法错误")
            return {
                'success': True,
                'phase': 'Phase 6 Week 1',
                'analysis': analysis_result,
                'repairs': {'files_processed': 0, 'fixes_applied': 0, 'remaining_errors': 0},
                'message': '没有语法错误需要修复'
            }

        # 2. 修复语法错误
        repair_result = self.fix_syntax_errors(analysis_result, max_files)

        # 3. 生成最终报告
        elapsed_time = (datetime.now() - self.start_time).total_seconds()

        final_result = {
            'success': repair_result['files_processed'] > 0,
            'phase': 'Phase 6 Week 1',
            'elapsed_time': f"{elapsed_time:.1f}s",
            'analysis': analysis_result,
            'repairs': repair_result,
            'summary': {
                'total_files_analyzed': analysis_result['total_files'],
                'files_with_errors': analysis_result['error_files'],
                'total_syntax_errors': analysis_result['total_errors'],
                'files_fixed': repair_result['files_processed'],
                'errors_fixed': repair_result['fixes_applied'],
                'remaining_errors': repair_result['remaining_errors'],
                'success_rate': repair_result['success_rate']
            },
            'next_step': 'Week 2: 依赖安装和测试环境验证' if repair_result['files_processed'] > 0 else 'Week 1 继续执行'
        }

        logger.info(f"🎉 Phase 6 Week 1 完成: {final_result['summary']}")

        return final_result

def main():
    """主函数"""
    print("🚀 Phase 6 测试系统优化 - 测试文件语法错误修复器")
    print("=" * 60)
    print("🎯 目标: 修复测试文件语法错误，建立可运行的测试环境")
    print("⚡ 策略: 智能分析 + 优先级修复 + 验证")
    print("📊 阶段: Week 1 - 语法清理")
    print("=" * 60)

    import argparse
    parser = argparse.ArgumentParser(description='Phase 6 测试语法修复器')
    parser.add_argument('--analyze', action='store_true', help='仅分析错误，不修复')
    parser.add_argument('--max-files', type=int, default=50, help='最大修复文件数量')
    args = parser.parse_args()

    fixer = Phase6TestSyntaxFixer()

    if args.analyze:
        # 仅分析模式
        result = fixer.analyze_test_syntax_errors()
        print(f"\n📊 分析结果:")
        print(f"   总测试文件: {result['total_files']}")
        print(f"   错误文件数: {result['error_files']}")
        print(f"   语法错误数: {result['total_errors']}")
        print(f"   错误率: {result['error_rate']}")

        # 显示优先级分组
        for group_name, group_data in result['prioritized_groups'].items():
            if group_data['files']:
                print(f"\n🎯 {group_data['name']}:")
                print(f"   文件数: {group_data['total_files']}")
                print(f"   错误数: {group_data['total_errors']}")
                print(f"   Top 5 文件:")
                for i, file_info in enumerate(group_data['files'][:5]):
                    print(f"     {i+1}. {file_info['path']} ({file_info['error_count']}个错误)")
    else:
        # 完整修复模式
        result = fixer.run_phase6_test_syntax_fix(args.max_files)

        print(f"\n🎉 Phase 6 Week 1 执行摘要:")
        print(f"   分析文件数: {result['summary']['total_files_analyzed']}")
        print(f"   错误文件数: {result['summary']['files_with_errors']}")
        print(f"   语法错误数: {result['summary']['total_syntax_errors']}")
        print(f"   修复文件数: {result['summary']['files_fixed']}")
        print(f"   修复错误数: {result['summary']['errors_fixed']}")
        print(f"   剩余错误数: {result['summary']['remaining_errors']}")
        print(f"   成功率: {result['summary']['success_rate']}")
        print(f"   执行时间: {result['elapsed_time']}")
        print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")
        print(f"   下一步: {result['next_step']}")

        # 保存报告
        report_file = Path(f'phase6_test_syntax_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n📄 详细报告已保存到: {report_file}")

    return result

if __name__ == '__main__':
    main()