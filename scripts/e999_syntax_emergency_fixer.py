#!/usr/bin/env python3
"""
E999语法错误紧急修复工具
E999 Syntax Error Emergency Fixer

专门用于快速修复E999语法错误，采用多策略方法：
1. 智能缩进修复
2. 导入语句修复
3. 语法结构重建
4. 批量验证机制

优先级：最高 - 语法错误阻塞所有开发活动
"""

import ast
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E999SyntaxFixer:
    """E999语法错误紧急修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0
        self.critical_errors = 0

    def get_e999_errors(self) -> List[Dict]:
        """获取所有E999语法错误"""
        logger.info("🚨 正在获取E999语法错误列表...")
        errors = []

        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=E999', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.stdout.strip():
                try:
                    error_data = json.loads(result.stdout)
                    for error in error_data:
                        if error.get('code') == 'E999':
                            errors.append({
                                'file': error['filename'],
                                'line': error['location']['row'],
                                'column': error['location']['column'],
                                'message': error['message'],
                                'code': 'E999',
                                'fixable': error.get('fix', {}).get('applicability') == 'automatic'
                            })
                except json.JSONDecodeError:
                    logger.warning("无法解析Ruff JSON输出，使用文本解析")
                    # 备用文本解析方法
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'E999' in line and 'IndentationError' in line:
                            parts = line.split(':')
                            if len(parts) >= 4:
                                errors.append({
                                    'file': parts[0],
                                    'line': int(parts[1]),
                                    'column': int(parts[2]),
                                    'message': ':'.join(parts[3:]).strip(),
                                    'code': 'E999',
                                    'fixable': False
                                })

        except Exception as e:
            logger.error(f"获取E999错误失败: {e}")

        logger.info(f"🚨 发现 {len(errors)} 个E999语法错误")
        self.critical_errors = len(errors)
        return errors

    def analyze_syntax_error(self, file_path: str, line_num: int) -> Dict:
        """分析语法错误的具体类型和修复策略"""
        path = Path(file_path)
        if not path.exists():
            return {'type': 'file_not_found', 'strategy': 'skip'}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                error_line = lines[line_num - 1]

                # 分析错误类型
                analysis = {
                    'type': 'unknown',
                    'strategy': 'manual',
                    'context': error_line.strip(),
                    'suggestions': []
                }

                # 缩进错误
                if 'unexpected indent' in error_line.lower() or 'IndentationError' in str(error_line):
                    analysis['type'] = 'indentation_error'
                    analysis['strategy'] = 'fix_indentation'
                    analysis['suggestions'] = ['检测缩进级别', '统一使用4个空格', '检查混合空格和制表符']

                # 导入语句错误
                if 'import' in error_line and any(keyword in error_line.lower() for keyword in ['invalid syntax', 'syntaxerror']):
                    analysis['type'] = 'import_syntax_error'
                    analysis['strategy'] = 'fix_import_syntax'
                    analysis['suggestions'] = ['检查import语句格式', '验证模块路径', '修复语法结构']

                # 一般语法错误
                if 'invalid syntax' in error_line.lower():
                    analysis['type'] = 'general_syntax_error'
                    analysis['strategy'] = 'fix_general_syntax'
                    analysis['suggestions'] = ['检查括号匹配', '验证语法结构', '修复关键字使用']

                return analysis

        except Exception as e:
            logger.error(f"分析文件 {file_path} 失败: {e}")
            return {'type': 'analysis_error', 'strategy': 'manual', 'error': str(e)}

        return {'type': 'line_not_found', 'strategy': 'skip'}

    def fix_indentation_error(self, file_path: str, line_num: int) -> bool:
        """修复缩进错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                error_line = lines[line_num - 1]

                # 计算正确的缩进级别
                stripped_line = error_line.lstrip()
                if not stripped_line:  # 空行
                    return False

                # 查找上一行的缩进级别
                len(error_line) - len(stripped_line)
                prev_indent = 0

                for i in range(line_num - 2, -1, -1):
                    if lines[i].strip():
                        prev_indent = len(lines[i]) - len(lines[i].lstrip())
                        break

                # 确定正确的缩进
                if 'def ' in stripped_line or 'class ' in stripped_line:
                    correct_indent = 0
                elif stripped_line.startswith(('if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
                    correct_indent = prev_indent
                else:
                    correct_indent = prev_indent + 4

                # 修复缩进
                fixed_line = ' ' * correct_indent + stripped_line
                lines[line_num - 1] = fixed_line

                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                logger.info(f"✅ 修复缩进错误: {file_path}:{line_num} - 修正为{correct_indent}空格缩进")
                return True

        except Exception as e:
            logger.error(f"修复缩进错误失败 {file_path}:{line_num}: {e}")

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
                if 'import' in fixed_line and not fixed_line.strip().endswith(('import', 'from')):
                    if fixed_line.strip().endswith(('import ', 'from ')):
                        fixed_line = fixed_line.rstrip() + '\n'
                        lines[line_num - 1] = fixed_line
                        logger.info(f"⚠️ 标记不完整导入语句: {file_path}:{line_num}")
                        return False

                # 修复明显的语法问题
                fixed_line = re.sub(r'\s+', ' ', fixed_line)  # 合并多余空格
                fixed_line = fixed_line.strip() + '\n'

                if fixed_line != error_line:
                    lines[line_num - 1] = fixed_line

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    logger.info(f"✅ 修复导入语法: {file_path}:{line_num}")
                    return True

        except Exception as e:
            logger.error(f"修复导入语法错误失败 {file_path}:{line_num}: {e}")

        return False

    def fix_general_syntax_error(self, file_path: str, line_num: int) -> bool:
        """修复一般语法错误"""
        try:
            # 使用Ruff的自动修复功能
            result = subprocess.run(
                ['ruff', 'check', '--select=E999', '--fix', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"✅ Ruff自动修复语法错误: {file_path}")
                return True
            else:
                logger.warning(f"⚠️ Ruff无法自动修复: {file_path} - {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"一般语法错误修复失败 {file_path}: {e}")

        return False

    def apply_syntax_fix(self, file_path: str, line_num: int, error_analysis: Dict) -> bool:
        """根据错误分析应用相应的修复策略"""
        strategy = error_analysis.get('strategy', 'manual')

        if strategy == 'fix_indentation':
            return self.fix_indentation_error(file_path, line_num)
        elif strategy == 'fix_import_syntax':
            return self.fix_import_syntax_error(file_path, line_num)
        elif strategy == 'fix_general_syntax':
            return self.fix_general_syntax_error(file_path)
        else:
            logger.warning(f"未知修复策略: {strategy} for {file_path}:{line_num}")
            return False

    def run_emergency_syntax_fix(self) -> Dict:
        """运行紧急语法错误修复"""
        logger.info("🚨 开始E999语法错误紧急修复...")

        errors = self.get_e999_errors()
        if not errors:
            logger.info("✅ 没有发现E999语法错误")
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
            logger.info(f"🔧 正在修复文件: {file_path} ({len(file_errors)}个错误)")

            file_fixed = False
            for error in file_errors:
                line_num = error['line']

                # 分析错误类型
                error_analysis = self.analyze_syntax_error(file_path, line_num)
                logger.info(f"📋 错误分析: {file_path}:{line_num} - {error_analysis['type']}")

                # 应用修复
                if self.apply_syntax_fix(file_path, line_num, error_analysis):
                    total_errors_fixed += 1
                    file_fixed = True
                    self.fixes_applied += 1

            if file_fixed:
                files_fixed += 1

            self.files_processed += 1

        # 验证修复效果
        remaining_errors = len(self.get_e999_errors())
        errors_fixed = self.critical_errors - remaining_errors

        result = {
            'success': errors_fixed > 0,
            'initial_errors': self.critical_errors,
            'remaining_errors': remaining_errors,
            'errors_fixed': errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'fix_rate': f"{(errors_fixed / max(self.critical_errors, 1)) * 100:.1f}%",
            'message': f'修复了 {errors_fixed} 个语法错误，{remaining_errors} 个剩余'
        }

        logger.info(f"🚨 E999语法错误修复完成: {result}")
        return result

    def generate_emergency_report(self) -> Dict:
        """生成紧急修复报告"""
        return {
            'fixer_name': 'E999 Syntax Error Emergency Fixer',
            'timestamp': '2025-10-30T02:15:00.000000',
            'priority': 'CRITICAL',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'recommendation': '语法错误修复后应立即运行测试验证功能完整性'
        }


def main():
    """主函数"""
    print("🚨 E999 语法错误紧急修复工具")
    print("=" * 60)
    print("⚠️  优先级: CRITICAL - 语法错误阻塞所有开发活动")
    print("=" * 60)

    fixer = E999SyntaxFixer()

    # 运行紧急语法修复
    result = fixer.run_emergency_syntax_fix()

    # 生成报告
    report = fixer.generate_emergency_report()

    print("\n📊 紧急修复摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 需要手动处理'}")

    # 保存紧急修复报告
    report_file = Path('e999_emergency_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 紧急修复报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n⚠️  注意: 仍有 {result['remaining_errors']} 个语法错误需要手动处理")
        print("🔧 建议: 查看具体错误文件，手动修复复杂的语法问题")

    return result


if __name__ == '__main__':
    main()