#!/usr/bin/env python3
"""
F841未使用变量批量清理工具
F841 Unused Variable Batch Cleaner

专门用于批量清理F841未使用变量错误，通过：
1. AST分析变量使用情况
2. 智能分类：删除、重命名、保留
3. 安全批量处理
4. 验证修复效果

目标: 清理786个F841未使用变量错误
"""

import ast
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class F841VariableCleaner:
    """F841未使用变量清理器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

        # 需要保留的变量模式
        self.preserve_patterns = [
            r'^_',  # 下划线开头的变量（通常是故意未使用的）
            r'^test_',  # 测试变量
            r'^mock_',  # mock对象
            r'^dummy_',  # 哑变量
            r'^temp_',  # 临时变量
        ]

    def get_f841_errors(self) -> List[Dict]:
        """获取所有F841未使用变量错误"""
        logger.info("🔍 正在获取F841未使用变量错误...")

        errors = []

        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=F841', '--format=json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.stdout.strip():
                try:
                    error_data = json.loads(result.stdout)
                    for error in error_data:
                        if error.get('code') == 'F841':
                            errors.append({
                                'file': error['filename'],
                                'line': error['location']['row'],
                                'column': error['location']['column'],
                                'message': error['message'],
                                'code': 'F841',
                                'variable_name': self.extract_variable_name(error['message'])
                            })

                except json.JSONDecodeError:
                    logger.warning("无法解析Ruff JSON输出，使用文本解析")
                    # 备用文本解析方法
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'F841' in line and 'assigned but never used' in line:
                            parts = line.split(':')
                            if len(parts) >= 4:
                                message = ':'.join(parts[3:]).strip()
                                errors.append({
                                    'file': parts[0],
                                    'line': int(parts[1]),
                                    'column': int(parts[2]),
                                    'message': message,
                                    'code': 'F841',
                                    'variable_name': self.extract_variable_name(message)
                                })

            logger.info(f"📊 发现 {len(errors)} 个F841未使用变量错误")

        except Exception as e:
            logger.error(f"获取F841错误失败: {e}")

        return errors

    def extract_variable_name(self, message: str) -> str:
        """从错误消息中提取变量名"""
        # 消息格式通常是: "assigned but never used"
        # 尝试提取变量名
        match = re.search(r"'([^']+)' assigned but never used", message)
        if match:
            return match.group(1)

        # 备用模式
        match = re.search(r"variable '([^']+)'", message)
        if match:
            return match.group(1)

        return ""

    def analyze_variable_usage(self, file_path: str, variable_name: str, line_num: int) -> Dict:
        """分析变量的使用情况"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST分析变量使用情况
            try:
                tree = ast.parse(content)
                analyzer = VariableUsageAnalyzer(variable_name, line_num)
                analyzer.visit(tree)
                return analyzer.get_analysis()

            except SyntaxError:
                logger.warning(f"文件 {file_path} 存在语法错误，跳过AST分析")
                return {
                    'status': 'syntax_error',
                    'action': 'skip',
                    'confidence': 0.0
                }

        except Exception as e:
            logger.error(f"分析文件 {file_path} 失败: {e}")
            return {
                'status': 'analysis_error',
                'action': 'skip',
                'confidence': 0.0
            }

    def should_preserve_variable(self, variable_name: str) -> bool:
        """判断变量是否应该保留"""
        for pattern in self.preserve_patterns:
            if re.match(pattern, variable_name):
                return True
        return False

    def fix_unused_variable(self, file_path: str, line_num: int, variable_name: str, analysis: Dict) -> bool:
        """修复未使用变量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            if line_num <= len(lines):
                original_line = lines[line_num - 1]

                action = analysis.get('action', 'skip')

                if action == 'delete':
                    # 删除未使用的变量赋值
                    lines[line_num - 1] = f"# {original_line.rstrip()}  # Removed unused variable: {variable_name}"
                    modified = True
                    logger.info(f"删除变量: {file_path}:{line_num} - {variable_name}")

                elif action == 'rename':
                    # 重命名变量（添加下划线前缀）
                    renamed_line = original_line.replace(variable_name, f"_{variable_name}", 1)
                    lines[line_num - 1] = renamed_line
                    modified = True
                    logger.info(f"重命名变量: {file_path}:{line_num} - {variable_name} -> _{variable_name}")

                elif action == 'keep':
                    # 保留变量，添加注释
                    if '# TODO:' not in original_line:
                        lines[line_num - 1] = f"{original_line.rstrip()}  # TODO: Use this variable"
                        modified = True
                        logger.info(f"保留变量: {file_path}:{line_num} - {variable_name}")

                # 如果有修改，写回文件
                if 'modified' in locals() and modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    return True

        except Exception as e:
            logger.error(f"修复文件 {file_path} 失败: {e}")

        return False

    def run_batch_variable_cleanup(self) -> Dict:
        """运行批量变量清理"""
        logger.info("🧹 开始F841未使用变量批量清理...")

        errors = self.get_f841_errors()
        if not errors:
            logger.info("✅ 没有发现F841错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'files_fixed': 0,
                'message': '没有F841错误需要修复'
            }

        # 按文件分组错误
        errors_by_file = {}
        for error in errors:
            file_path = error['file']
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error)

        # 修复每个文件的未使用变量
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, file_errors in errors_by_file.items():
            logger.info(f"🔧 正在修复文件: {file_path} ({len(file_errors)}个未使用变量)")

            file_fixed = False
            for error in file_errors:
                variable_name = error['variable_name']
                line_num = error['line']

                # 检查是否应该保留
                if self.should_preserve_variable(variable_name):
                    logger.info(f"⚠️ 保留变量: {file_path}:{line_num} - {variable_name}")
                    continue

                # 分析变量使用情况
                analysis = self.analyze_variable_usage(file_path, variable_name, line_num)
                logger.info(f"📋 变量分析: {variable_name} -> {analysis['action']} (confidence: {analysis['confidence']})")

                # 只处理高置信度的修复
                if analysis['confidence'] >= 0.7:
                    if self.fix_unused_variable(file_path, line_num, variable_name, analysis):
                        total_errors_fixed += 1
                        file_fixed = True
                        self.fixes_applied += 1

            if file_fixed:
                files_fixed += 1

            self.files_processed += 1

        # 验证修复效果
        remaining_errors = len(self.get_f841_errors())
        errors_fixed = len(errors) - remaining_errors

        result = {
            'success': errors_fixed > 0,
            'initial_errors': len(errors),
            'remaining_errors': remaining_errors,
            'errors_fixed': errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'fix_rate': f"{(errors_fixed / max(len(errors), 1)) * 100:.1f}%",
            'message': f'清理了 {errors_fixed} 个未使用变量，{remaining_errors} 个剩余'
        }

        logger.info(f"🧹 F841批量清理完成: {result}")
        return result

    def generate_cleaner_report(self) -> Dict:
        """生成清理报告"""
        return {
            'cleaner_name': 'F841 Unused Variable Batch Cleaner',
            'timestamp': '2025-10-30T02:45:00.000000',
            'target_errors': '786 F841 unused variables',
            'strategy': 'AST analysis + intelligent classification + safe batch processing',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_step': 'Proceed to format error cleanup and quality gate verification'
        }


class VariableUsageAnalyzer(ast.NodeVisitor):
    """变量使用情况分析器"""

    def __init__(self, target_variable: str, target_line: int):
        self.target_variable = target_variable
        self.target_line = target_line
        self.is_used = False
        self.in_function_scope = False
        self.function_start_line = 0
        self.analysis = {
            'action': 'skip',
            'confidence': 0.0,
            'reason': ''
        }

    def visit_FunctionDef(self, node):
        """访问函数定义"""
        if self.function_start_line == 0:
            self.function_start_line = node.lineno
        self.in_function_scope = True
        self.generic_visit(node)

    def visit_FunctionDef_end(self, node):
        """离开函数定义"""
        self.in_function_scope = False

    def visit_Name(self, node):
        """访问名称节点"""
        if isinstance(node.ctx, ast.Load) and node.id == self.target_variable:
            self.is_used = True

    def visit_Assign(self, node):
        """访问赋值节点"""
        if isinstance(node.value, ast.Name) and node.value.id == self.target_variable:
            # 变量被赋值给其他变量，可能有使用
            self.analysis.update({
                'action': 'keep',
                'confidence': 0.8,
                'reason': 'Variable assigned to another variable'
            })

    def get_analysis(self) -> Dict:
        """获取分析结果"""
        if self.is_used:
            self.analysis.update({
                'action': 'keep',
                'confidence': 0.9,
                'reason': 'Variable is used in the code'
            })
        elif self.function_start_line == self.target_line:
            # 函数参数通常不应该删除
            self.analysis.update({
                'action': 'keep',
                'confidence': 0.85,
                'reason': 'Function parameter should not be deleted'
            })
        elif self.target_line == self.function_start_line + 1:
            # 函数内的第一行通常是重要的初始化
            self.analysis.update({
                'action': 'keep',
                'confidence': 0.7,
                'reason': 'First line in function may be important'
            })
        else:
            # 真正未使用的变量
            self.analysis.update({
                'action': 'delete',
                'confidence': 0.9,
                'reason': 'Variable is truly unused'
            })

        return self.analysis


def main():
    """主函数"""
    print("🧹 F841 未使用变量批量清理工具")
    print("=" * 60)
    print("🎯 目标: 786个F841未使用变量 → 清理完成")
    print("🛡️ 策略: AST分析 + 智能分类 + 安全批量处理")
    print("=" * 60)

    cleaner = F841VariableCleaner()

    # 运行批量变量清理
    result = cleaner.run_batch_variable_cleanup()

    # 生成报告
    report = cleaner.generate_cleaner_report()

    print("\n📊 变量清理摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 需要手动处理'}")

    # 保存清理报告
    report_file = Path('f841_variable_cleaner_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 变量清理报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n⚠️ 仍有 {result['remaining_errors']} 个未使用变量需要处理")
        print("🔧 建议: 检查具体的变量用途，确认是否可以安全删除")

    return result


if __name__ == '__main__':
    main()