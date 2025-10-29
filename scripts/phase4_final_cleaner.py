#!/usr/bin/env python3
"""
Phase 4 最终清理器
Phase 4 Final Cleaner

直接执行剩余1,009个错误的最佳实践清理路径
采用快速、安全、批量化的策略
"""

import subprocess
import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase4FinalCleaner:
    """Phase 4 最终清理器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def get_current_errors(self) -> Dict[str, List]:
        """获取当前所有错误"""
        logger.info("🔍 获取当前错误状态...")

        try:
            result = subprocess.run(
                ['ruff', 'check', '--format=json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            errors_by_type = defaultdict(list)

            if result.stdout.strip():
                try:
                    error_data = json.loads(result.stdout)
                    for error in error_data:
                        code = error.get('code', 'unknown')
                        errors_by_type[code].append({
                            'file': error['filename'],
                            'line': error['location']['row'],
                            'col': error['location']['column'],
                            'message': error['message'],
                            'code': code
                        })
                except json.JSONDecodeError:
                    logger.warning("无法解析JSON输出，使用备用方法")
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if ':' in line and any(code in line for code in ['F541', 'E722', 'F841', 'F404', 'F823', 'F601', 'E712', 'F402', 'F632']):
                            parts = line.split(':')
                            if len(parts) >= 4:
                                file_path = parts[0]
                                line_num = int(parts[1])
                                message = ':'.join(parts[3:])
                                code = message.split()[0] if message.split() else 'unknown'
                                errors_by_type[code].append({
                                    'file': file_path,
                                    'line': line_num,
                                    'message': message,
                                    'code': code
                                })

            total_errors = sum(len(errors) for errors in errors_by_type.values())
            logger.info(f"📊 当前状态: {total_errors} 个错误，{len(errors_by_type)} 种错误类型")

            return dict(errors_by_type)

        except Exception as e:
            logger.error(f"获取错误状态失败: {e}")
            return {}

    def fix_f541_fstring_errors(self, errors: List[Dict]) -> int:
        """修复F541 f-string占位符缺失错误"""
        logger.info("🔧 修复F541 f-string占位符缺失错误...")

        fixes = 0
        files_by_path = defaultdict(list)
        for error in errors:
            files_by_path[error['file']].append(error)

        for file_path, file_errors in files_by_path.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                modified = False

                for error in file_errors:
                    line_num = error['line'] - 1
                    if 0 <= line_num < len(lines):
                        line = lines[line_num]

                        # 查找f-string
                        if 'f"' in line or "f'" in line:
                            # 检查是否没有占位符
                            fstring_match = re.search(r'f["\']([^"\']*)["\']', line)
                            if fstring_match and '{' not in fstring_match.group(1):
                                # 将f-string改为普通字符串
                                fixed_line = line.replace('f"', '"').replace("f'", "'")
                                if fixed_line != line:
                                    lines[line_num] = fixed_line
                                    modified = True
                                    fixes += 1
                                    logger.info(f"修复F541: {file_path}:{line_num + 1}")

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    self.files_fixed += 1

            except Exception as e:
                logger.error(f"修复文件失败 {file_path}: {e}")

        return fixes

    def fix_e722_bare_except(self, errors: List[Dict]) -> int:
        """修复E722 bare except错误"""
        logger.info("🔧 修复E722 bare except错误...")

        fixes = 0
        files_by_path = defaultdict(list)
        for error in errors:
            files_by_path[error['file']].append(error)

        for file_path, file_errors in files_by_path.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                modified = False

                for error in file_errors:
                    line_num = error['line'] - 1
                    if 0 <= line_num < len(lines):
                        line = lines[line_num].strip()

                        # 查找bare except
                        if line == 'except:':
                            # 替换为except Exception:
                            fixed_line = lines[line_num].replace('except:', 'except Exception:')
                            lines[line_num] = fixed_line
                            modified = True
                            fixes += 1
                            logger.info(f"修复E722: {file_path}:{line_num + 1}")

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    self.files_fixed += 1

            except Exception as e:
                logger.error(f"修复文件失败 {file_path}: {e}")

        return fixes

    def fix_f841_unused_variables(self, errors: List[Dict]) -> int:
        """修复F841未使用变量错误"""
        logger.info("🔧 修复F841未使用变量错误...")

        fixes = 0
        files_by_path = defaultdict(list)
        for error in errors:
            files_by_path[error['file']].append(error)

        for file_path, file_errors in files_by_path.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                modified = False

                for error in file_errors:
                    line_num = error['line'] - 1
                    if 0 <= line_num < len(lines):
                        line = lines[line_num]

                        # 提取变量名
                        message = error['message']
                        if "assigned but never used" in message:
                            var_match = re.search(r"`([^`]+)`", message)
                            if var_match:
                                var_name = var_match.group(1)

                                # 尝试重命名变量（添加下划线前缀）
                                if '=' in line:
                                    # 只在第一次出现时重命名
                                    original_line = line
                                    fixed_line = re.sub(
                                        rf'\b{re.escape(var_name)}\s*=',
                                        f'_{var_name} =',
                                        line,
                                        count=1
                                    )
                                    if fixed_line != original_line:
                                        lines[line_num] = fixed_line
                                        modified = True
                                        fixes += 1
                                        logger.info(f"修复F841: {file_path}:{line_num + 1} - {var_name} -> _{var_name}")

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    self.files_fixed += 1

            except Exception as e:
                logger.error(f"修复文件失败 {file_path}: {e}")

        return fixes

    def fix_syntax_errors(self, errors: List[Dict]) -> int:
        """修复语法错误"""
        logger.info("🔧 修复语法错误...")

        fixes = 0
        files_by_path = defaultdict(list)
        for error in errors:
            files_by_path[error['file']].append(error)

        for file_path, file_errors in files_by_path.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 尝试语法解析
                try:
                    ast.parse(content)
                    logger.info(f"文件语法正确: {file_path}")
                    continue
                except SyntaxError as e:
                    logger.info(f"语法错误 {file_path}:{e.lineno}: {e.msg}")

                    lines = content.split('\n')
                    if e.lineno and 1 <= e.lineno <= len(lines):
                        error_line = lines[e.lineno - 1]

                        # 常见语法错误修复
                        fixed_line = error_line

                        # 修复未完成的字符串
                        if 'unterminated string literal' in e.msg.lower():
                            if error_line.count('"') % 2 == 1:
                                fixed_line = error_line + '"'
                            elif error_line.count("'") % 2 == 1:
                                fixed_line = error_line + "'"

                        # 修复意外的缩进
                        elif 'unexpected indent' in e.msg.lower():
                            fixed_line = error_line.lstrip()

                        # 修复其他常见问题
                        elif 'invalid syntax' in e.msg.lower():
                            # 简单的括号匹配修复
                            if error_line.count('(') > error_line.count(')'):
                                fixed_line = error_line + ')'
                            elif error_line.count('[') > error_line.count(']'):
                                fixed_line = error_line + ']'

                        if fixed_line != error_line:
                            lines[e.lineno - 1] = fixed_line

                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines))

                            fixes += 1
                            logger.info(f"修复语法错误: {file_path}:{e.lineno}")
                            self.files_fixed += 1

            except Exception as e:
                logger.error(f"处理语法错误失败 {file_path}: {e}")

        return fixes

    def run_auto_fix(self) -> Dict:
        """运行ruff自动修复"""
        logger.info("🚀 运行ruff自动修复...")

        try:
            # 运行安全修复
            result = subprocess.run(
                ['ruff', 'check', '--fix'],
                capture_output=True,
                text=True,
                timeout=180
            )

            # 运行不安全修复
            result_unsafe = subprocess.run(
                ['ruff', 'check', '--fix', '--unsafe-fixes'],
                capture_output=True,
                text=True,
                timeout=180
            )

            fixed_count = result.stdout.count('Fixed') + result_unsafe.stdout.count('Fixed')

            logger.info(f"✅ ruff自动修复完成，修复了 {fixed_count} 个问题")

            return {
                'success': True,
                'fixed_count': fixed_count,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except Exception as e:
            logger.error(f"ruff自动修复失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def execute_phase4_cleaning(self) -> Dict:
        """执行Phase 4最终清理"""
        logger.info("🚀 开始Phase 4最终清理...")

        # 1. 运行ruff自动修复
        auto_fix_result = self.run_auto_fix()

        # 2. 获取当前错误状态
        current_errors = self.get_current_errors()
        total_errors = sum(len(errors) for errors in current_errors.values())

        if total_errors == 0:
            logger.info("🎉 所有错误已清理完成！")
            return {
                'success': True,
                'total_errors_before': 0,
                'total_errors_after': 0,
                'errors_fixed': 0,
                'message': '没有错误需要修复'
            }

        logger.info("📊 剩余错误分布:")
        for code, errors in sorted(current_errors.items()):
            logger.info(f"   {code}: {len(errors)} 个")

        # 3. 分类型修复错误
        total_fixes = 0

        # F541 f-string占位符缺失
        if 'F541' in current_errors:
            fixes = self.fix_f541_fstring_errors(current_errors['F541'])
            total_fixes += fixes
            logger.info(f"✅ F541修复: {fixes} 个")

        # E722 bare except
        if 'E722' in current_errors:
            fixes = self.fix_e722_bare_except(current_errors['E722'])
            total_fixes += fixes
            logger.info(f"✅ E722修复: {fixes} 个")

        # F841 未使用变量
        if 'F841' in current_errors:
            fixes = self.fix_f841_unused_variables(current_errors['F841'])
            total_fixes += fixes
            logger.info(f"✅ F841修复: {fixes} 个")

        # 语法错误
        syntax_errors = [e for errors in current_errors.values() for e in errors
                        if e.get('code', '').startswith('E') or 'syntax' in e.get('message', '').lower()]
        if syntax_errors:
            fixes = self.fix_syntax_errors(syntax_errors)
            total_fixes += fixes
            logger.info(f"✅ 语法错误修复: {fixes} 个")

        # 4. 再次运行ruff自动修复清理剩余问题
        self.run_auto_fix()

        # 5. 最终统计
        final_errors = self.get_current_errors()
        final_total = sum(len(errors) for errors in final_errors.values())

        result = {
            'success': total_fixes > 0 or auto_fix_result.get('success', False),
            'initial_errors': total_errors,
            'final_errors': final_total,
            'errors_fixed': total_errors - final_total,
            'auto_fix_count': auto_fix_result.get('fixed_count', 0),
            'manual_fix_count': total_fixes,
            'files_processed': len(set(e['file'] for errors in current_errors.values() for e in errors)),
            'error_distribution': {code: len(errors) for code, errors in final_errors.items()},
            'message': f'Phase 4清理完成: {total_errors} → {final_total} (-{total_errors - final_total})'
        }

        logger.info(f"🎉 Phase 4清理完成: {result}")
        return result

def main():
    """主函数"""
    print("🚀 Phase 4 最终清理器")
    print("=" * 60)
    print("🎯 目标: 1,009个错误 → 清理完成")
    print("🛠️ 策略: 自动修复 + 批量处理 + 直接执行")
    print("=" * 60)

    cleaner = Phase4FinalCleaner()
    result = cleaner.execute_phase4_cleaning()

    print("\n📊 Phase 4清理摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   最终错误数: {result['final_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   自动修复数: {result['auto_fix_count']}")
    print(f"   手动修复数: {result['manual_fix_count']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

    if result['final_errors'] > 0:
        print("\n📋 剩余错误分布:")
        for code, count in sorted(result['error_distribution'].items()):
            print(f"   {code}: {count} 个")

    # 保存报告
    report_file = Path('phase4_final_clean_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Phase 4清理报告已保存到: {report_file}")

    return result

if __name__ == '__main__':
    main()