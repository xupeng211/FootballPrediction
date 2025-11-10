#!/usr/bin/env python3
"""
简单的代码风格修复工具
专注于修复最常见的代码风格和命名问题
"""

import os
import re
import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

class SimpleStyleFixer:
    def __init__(self):
        self.fixed_files = []
        self.fix_count = 0

    def fix_file(self, file_path: str) -> bool:
        """修复单个文件的代码风格问题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            fixed_content = self._apply_fixes(original_content)

            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                self.fixed_files.append(file_path)
                return True
            return False

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")
            return False

    def _apply_fixes(self, content: str) -> str:
        """应用一系列代码风格修复"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            fixed_line = line

            # 修复1: 未使用导入
            if 'importlib' in fixed_line and 'import importlib' in fixed_line:
                if not any('importlib.' in prev_line for prev_line in fixed_lines[-3:]):
                    fixed_line = None

            # 修复2: logging 未使用
            if 'import logging' in fixed_line and 'import logging' in fixed_line:
                if not any('logging.' in prev_line for prev_line in fixed_lines[-3:]):
                    fixed_line = None

            # 修复3: os 未使用
            if 'import os' in fixed_line and 'import os' in fixed_line:
                if not any('os.' in prev_line for prev_line in fixed_lines[-3:]):
                    fixed_line = None

            # 修复4: 裸露的 except
            if 'except:' in fixed_line and 'except Exception' not in fixed_line:
                fixed_line = fixed_line.replace('except:', 'except Exception:')

            # 修复5: 函数命名（改为小写）
            if 'class ' in fixed_line and '_' in fixed_line:
                # 修复类名中的下划线
                class_name_match = re.search(r'class\s+([A-Z][a-zA-Z0-9_]*)', fixed_line)
                if class_name_match:
                    class_name = class_name_match.group(1)
                    if '_' in class_name and not class_name.startswith('_'):
                        fixed_class_name = ''.join(word.capitalize() for word in class_name.split('_'))
                        fixed_line = fixed_line.replace(class_name, fixed_class_name)

            # 修复6: 变量命名（大写变量）
            # X, Q1, Q3, IQR 等统计学变量改为小写
            fixed_line = re.sub(r'\bX\b', 'x', fixed_line)
            fixed_line = re.sub(r'\bQ1\b', 'q1', fixed_line)
            fixed_line = re.sub(r'\bQ3\b', 'q3', fixed_line)
            fixed_line = re.sub(r'\bIQR\b', 'iqr', fixed_line)

            if fixed_line is not None:
                fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines)

    def fix_directory(self, directory: str, pattern: str = "*.py") -> int:
        """修复目录中的所有Python文件"""
        print(f"🔧 修复目录: {directory}")

        py_files = list(Path(directory).rglob(pattern))
        total_files = len(py_files)
        fixed_count = 0

        for i, py_file in enumerate(py_files, 1):
            print(f"  [{i}/{total_files}] 修复: {py_file}")
            if self.fix_file(str(py_file)):
                fixed_count += 1

        self.fix_count += fixed_count
        return fixed_count

    def run_ruff_fix(self, directory: str) -> bool:
        """运行ruff自动修复"""
        print(f"🔧 运行ruff自动修复: {directory}")
        try:
            result = subprocess.run([
                'ruff', 'check', directory, '--fix', '--unsafe-fixes'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ ruff修复成功")
                return True
            else:
                print(f"⚠️ ruff修复部分问题: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ ruff修复失败: {e}")
            return False

    def run_black_format(self, directory: str) -> bool:
        """运行black格式化"""
        print(f"🔧 运行black格式化: {directory}")
        try:
            result = subprocess.run([
                'black', directory
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ black格式化成功")
                return True
            else:
                print(f"⚠️ black格式化部分问题: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ black格式化失败: {e}")
            return False

def main():
    """主函数"""
    print("🚀 开始简单代码风格修复...")

    fixer = SimpleStyleFixer()

    # 目标目录
    target_dirs = ['src', 'tests']

    total_fixes = 0

    for target_dir in target_dirs:
        if os.path.exists(target_dir):
            print(f"\n📁 处理目录: {target_dir}")

            # 1. 运行ruff修复
            fixer.run_ruff_fix(target_dir)

            # 2. 运行black格式化
            fixer.run_black_format(target_dir)

            # 3. 手动修复特定问题
            fixes = fixer.fix_directory(target_dir)
            total_fixes += fixes

            print(f"✅ {target_dir}: 修复了 {fixes} 个文件")
        else:
            print(f"⚠️ 目录不存在: {target_dir}")

    print(f"\n📊 总修复统计:")
    print(f"  - 修复文件数: {len(fixer.fixed_files)}")
    print(f"  - 总修复数: {total_fixes}")

    if fixer.fixed_files:
        print(f"\n📄 修复的文件:")
        for file_path in fixer.fixed_files:
            print(f"  - {file_path}")

    print(f"\n✅ 代码风格修复完成！")

if __name__ == "__main__":
    main()