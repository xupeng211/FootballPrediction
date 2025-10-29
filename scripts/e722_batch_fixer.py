#!/usr/bin/env python3
"""
E722 批量修复器
E722 Batch Fixer

专门用于批量修复E722 bare except错误的高效工具
采用智能模式识别和安全的替换策略
"""

import re
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class E722BatchFixer:
    """E722批量修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def find_e722_errors(self) -> Dict[str, List[Tuple[int, str]]]:
        """查找所有E722错误"""
        logger.info("🔍 查找E722 bare except错误...")

        try:
            # 使用ruff查找E722错误
            result = subprocess.run(
                ['ruff', 'check', '--select=E722', '--format=json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            e722_errors = {}

            if result.stdout.strip():
                import json
                try:
                    errors = json.loads(result.stdout)
                    for error in errors:
                        if error.get('code') == 'E722':
                            file_path = error['filename']
                            line_num = error['location']['row']

                            if file_path not in e722_errors:
                                e722_errors[file_path] = []

                            e722_errors[file_path].append((line_num, error['message']))
                            logger.info(f"🔴 发现E722错误: {file_path}:{line_num}")

                except json.JSONDecodeError:
                    logger.warning("无法解析ruff JSON输出")
                    return self.find_e722_fallback()

            total_errors = sum(len(errors) for errors in e722_errors.values())
            logger.info(f"📊 发现E722错误: {total_errors} 个，涉及 {len(e722_errors)} 个文件")

            return e722_errors

        except Exception as e:
            logger.error(f"查找E722错误失败: {e}")
            return self.find_e722_fallback()

    def find_e722_fallback(self) -> Dict[str, List[Tuple[int, str]]]:
        """备用方法：使用正则表达式查找E722错误"""
        logger.info("🔄 使用备用方法查找E722错误...")

        e722_errors = {}
        pattern = r'^(\s*)except:\s*$'

        # 遍历所有Python文件
        for root, dirs, files in os.walk('.'):
            # 跳过一些目录
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        for i, line in enumerate(lines, 1):
                            if re.match(pattern, line):
                                if file_path not in e722_errors:
                                    e722_errors[file_path] = []
                                e722_errors[file_path].append((i, line.strip()))
                                logger.info(f"🔴 发现E722错误: {file_path}:{i}")

                    except Exception as e:
                        logger.warning(f"读取文件失败 {file_path}: {e}")

        total_errors = sum(len(errors) for errors in e722_errors.values())
        logger.info(f"📊 备用方法发现E722错误: {total_errors} 个，涉及 {len(e722_errors)} 个文件")

        return e722_errors

    def fix_e722_in_file(self, file_path: str, errors: List[Tuple[int, str]]) -> int:
        """修复单个文件中的E722错误"""
        logger.info(f"🔧 修复文件: {file_path} ({len(errors)}个E722错误)")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            original_lines = lines.copy()
            fixes = 0

            for line_num, error_msg in errors:
                line_index = line_num - 1

                if 0 <= line_index < len(lines):
                    original_line = lines[line_index]
                    fixed_line = self.fix_e722_line(original_line, line_index, lines)

                    if fixed_line != original_line:
                        lines[line_index] = fixed_line
                        fixes += 1
                        logger.info(f"  修复: 第{line_num}行 - bare except → except Exception")

            # 如果有修改，写回文件
            if lines != original_lines:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.files_fixed += 1
                logger.info(f"✅ 文件修复成功: {file_path}, 修复了 {fixes} 个错误")

            return fixes

        except Exception as e:
            logger.error(f"❌ 修复文件失败 {file_path}: {e}")
            return 0

    def fix_e722_line(self, line: str, line_index: int, all_lines: List[str]) -> str:
        """修复单行的E722错误"""
        stripped = line.strip()

        # 基本的bare except修复
        if stripped == 'except:':
            indent = line[:len(line) - len(stripped)]
            return f"{indent}except Exception:"

        # 带注释的bare except
        if stripped.startswith('except:') and '#' in stripped:
            indent = line[:len(line) - len(stripped)]
            comment_part = stripped[7:]  # 去掉 'except:'
            return f"{indent}except Exception:{comment_part}"

        return line

    def run_e722_batch_fix(self) -> Dict:
        """运行E722批量修复"""
        logger.info("🚀 开始E722批量修复...")

        # 1. 查找所有E722错误
        e722_errors = self.find_e722_errors()

        if not e722_errors:
            logger.info("✅ 没有发现E722错误")
            return {
                'success': True,
                'initial_errors': 0,
                'remaining_errors': 0,
                'errors_fixed': 0,
                'files_processed': 0,
                'files_fixed': 0,
                'fix_rate': "0.0%",
                'message': '没有E722错误需要修复'
            }

        # 2. 按文件类型排序优先级
        sorted_files = sorted(e722_errors.keys(), key=lambda x: (
            0 if 'test' in x else 1,  # 测试文件优先
            0 if x.startswith('scripts/') else 1,  # 脚本文件优先
            len(e722_errors[x]),     # 错误多的文件优先
            x
        ))

        # 3. 修复每个文件
        total_errors_fixed = 0

        for file_path in sorted_files:
            file_errors = e722_errors[file_path]
            fixes = self.fix_e722_in_file(file_path, file_errors)
            total_errors_fixed += fixes
            self.files_processed += 1

        # 4. 验证修复效果
        remaining_errors = self.find_e722_errors()
        remaining_count = sum(len(errors) for errors in remaining_errors.values())

        # 5. 生成报告
        initial_count = sum(len(errors) for errors in e722_errors.values())
        result = {
            'success': total_errors_fixed > 0,
            'initial_errors': initial_count,
            'remaining_errors': remaining_count,
            'errors_fixed': initial_count - remaining_count,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'fix_rate': f"{((initial_count - remaining_count) / max(initial_count, 1)) * 100:.1f}%",
            'message': f'修复了 {initial_count - remaining_count} 个E722错误，{remaining_count} 个剩余'
        }

        logger.info(f"🎉 E722批量修复完成: {result}")
        return result

    def generate_fix_report(self) -> Dict:
        """生成修复报告"""
        return {
            'tool': 'E722 Batch Fixer',
            'version': '1.0',
            'phase': 'Phase 5 Week 2',
            'focus': 'E722 bare except错误批量修复',
            'strategy': '智能模式识别 + 安全替换 + 批量处理',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_step': '其他错误类型清理 + 验证测试'
        }

def main():
    """主函数"""
    print("🚀 E722 批量修复器")
    print("=" * 50)
    print("🎯 目标: 批量修复E722 bare except错误")
    print("⚡ 策略: 智能模式识别 + 安全替换")
    print("📊 影响: 异常处理规范化")
    print("=" * 50)

    fixer = E722BatchFixer()
    result = fixer.run_e722_batch_fix()

    print("\n📊 E722批量修复摘要:")
    print(f"   初始错误数: {result['initial_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

    # 生成报告
    report = fixer.generate_fix_report()

    # 保存报告
    import json
    from datetime import datetime

    report_file = Path(f'e722_batch_fix_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 E722批量修复报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n⚠️ 仍有 {result['remaining_errors']} 个E722错误需要处理")
        print("💡 建议: 检查复杂的异常处理模式，可能需要手动修复")

    return result

if __name__ == '__main__':
    main()