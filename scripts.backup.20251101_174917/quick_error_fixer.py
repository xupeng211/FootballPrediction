#!/usr/bin/env python3
"""
快速错误修复器
Quick Error Fixer

专门处理E722 bare except等常见错误的快速修复
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickErrorFixer:
    """快速错误修复器"""

    def __init__(self):
        self.fixes_applied = 0

    def fix_bare_except_in_file(self, file_path: str) -> int:
        """修复单个文件中的bare except错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            fixes = 0
            modified = False

            for i, line in enumerate(lines):
                stripped = line.strip()
                # 查找bare except
                if stripped == 'except:':
                    # 替换为except Exception:
                    indent = line[:len(line) - len(stripped)]
                    lines[i] = f"{indent}except Exception:"
                    fixes += 1
                    modified = True
                    logger.info(f"修复bare except: {file_path}:{i+1}")

            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.fixes_applied += fixes

            return fixes

        except Exception as e:
            logger.error(f"修复文件失败 {file_path}: {e}")
            return 0

    def fix_syntax_error_in_file(self, file_path: str) -> int:
        """修复单个文件中的语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            fixes = 0
            modified = False

            for i, line in enumerate(lines):
                # 修复常见的语法错误

                # 修复未完成的字符串
                if 'pattern =' in line and not line.strip().endswith(('"', "'")):
                    # 查找下一行是否是字符串
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('"'):
                        lines[i] = line.rstrip() + ' ' + lines[i + 1].strip()
                        lines[i + 1] = ''  # 删除下一行
                        fixes += 1
                        modified = True
                        logger.info(f"修复未完成字符串: {file_path}:{i+1}")

                # 修复意外缩进
                if line.strip() and not line.startswith(' ') and i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line and not prev_line.startswith('#'):
                        # 检查是否需要缩进
                        if any(line.strip().startswith(keyword) for keyword in ['assert', 'return', 'if', 'for', 'while', 'try', 'except', 'finally', 'with', 'def', 'class']):
                            if not line.startswith('    '):
                                lines[i] = '    ' + line
                                fixes += 1
                                modified = True
                                logger.info(f"修复缩进: {file_path}:{i+1}")

                # 修复import语句缩进
                if line.strip().startswith('from ') and line.startswith('    ') and i > 0:
                    if not lines[i-1].strip().startswith('from ') and not lines[i-1].strip().startswith('import '):
                        lines[i] = line.strip()  # 移除缩进
                        fixes += 1
                        modified = True
                        logger.info(f"修复import缩进: {file_path}:{i+1}")

            if modified:
                # 清理空行
                lines = [line for line in lines if line.strip() != '']
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.fixes_applied += fixes

            return fixes

        except Exception as e:
            logger.error(f"修复语法错误失败 {file_path}: {e}")
            return 0

    def get_files_with_errors(self) -> Dict[str, List[str]]:
        """获取有错误的文件列表"""
        try:
            result = subprocess.run(
                ['ruff', 'check', '--format=text'],
                capture_output=True,
                text=True,
                timeout=60
            )

            files_with_errors = {}
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if ':' in line and ('E722' in line or 'invalid-syntax' in line):
                        parts = line.split(':')
                        if len(parts) >= 2:
                            file_path = parts[0]
                            error_type = 'E722' if 'E722' in line else 'syntax'

                            if file_path not in files_with_errors:
                                files_with_errors[file_path] = []
                            if error_type not in files_with_errors[file_path]:
                                files_with_errors[file_path].append(error_type)

            return files_with_errors

        except Exception as e:
            logger.error(f"获取错误文件失败: {e}")
            return {}

    def run_quick_fix(self) -> Dict:
        """运行快速修复"""
        logger.info("🚀 开始快速错误修复...")

        # 获取有错误的文件
        files_with_errors = self.get_files_with_errors()

        if not files_with_errors:
            logger.info("✅ 没有发现需要快速修复的错误")
            return {
                'success': True,
                'files_processed': 0,
                'fixes_applied': 0,
                'message': '没有错误需要修复'
            }

        logger.info(f"📊 发现 {len(files_with_errors)} 个文件需要修复")

        files_processed = 0
        total_fixes = 0

        for file_path, error_types in files_with_errors.items():
            logger.info(f"🔧 修复文件: {file_path} ({error_types})")

            file_fixes = 0

            # 修复E722错误
            if 'E722' in error_types:
                fixes = self.fix_bare_except_in_file(file_path)
                file_fixes += fixes
                logger.info(f"   E722修复: {fixes} 个")

            # 修复语法错误
            if 'syntax' in error_types:
                fixes = self.fix_syntax_error_in_file(file_path)
                file_fixes += fixes
                logger.info(f"   语法修复: {fixes} 个")

            if file_fixes > 0:
                files_processed += 1
                total_fixes += file_fixes

        result = {
            'success': total_fixes > 0,
            'files_found': len(files_with_errors),
            'files_processed': files_processed,
            'fixes_applied': total_fixes,
            'message': f'修复了 {files_processed} 个文件中的 {total_fixes} 个错误'
        }

        logger.info(f"✅ 快速修复完成: {result}")
        return result

def main():
    """主函数"""
    print("🚀 快速错误修复器")
    print("=" * 50)
    print("🎯 目标: 快速修复E722和语法错误")
    print("⚡ 策略: 直接修复 + 批量处理")
    print("=" * 50)

    fixer = QuickErrorFixer()
    result = fixer.run_quick_fix()

    print("\n📊 快速修复摘要:")
    print(f"   发现文件数: {result['files_found']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复错误数: {result['fixes_applied']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

    return result

if __name__ == '__main__':
    main()