#!/usr/bin/env python3
"""
修复缺失的from语句的脚本
Fix script for missing from statements
"""

import os
import re
import sys

def fix_missing_from_statements(file_path):
    """修复文件中缺失的from语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复常见的模式：缺少from语句的try块
        patterns = [
            # 模式1: try: 后面直接跟缩进的导入
            (r'(\s+?)try:\s*\n(\s+)([A-Za-z_][A-Za-z0-9_]*,\s*\n(?:\s+[A-Za-z_][A-Za-z0-9_]*,\s*\n)*\s+\))\s*\n',
             lambda m: f"{m.group(1)}try:\n{m.group(1)}    from .{get_module_name(m.group(3))} import (\n{m.group(2)}{fix_indentation(m.group(3))}\n{m.group(1)})"),
        ]

        # 应用修复模式
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # 修复简单的缩进错误
        content = re.sub(r'^(\s+)([A-Za-z_][A-Za-z0-9_]*),\s*$', r'    \2,', content, flags=re.MULTILINE)

        # 修复多余的except语句
        content = re.sub(r'except ImportError:\s*\n\s*except ImportError:\s*\n', 'except ImportError:\n', content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def get_module_name(import_list):
    """根据导入列表猜测模块名"""
    # 简单的启发式规则
    if 'Decorator' in import_list:
        return 'common_decorators'
    elif 'Facade' in import_list:
        return 'system_facades'
    elif 'Features' in import_list:
        return 'feature_types'
    elif 'Prediction' in import_list:
        return 'prediction'
    elif 'Entity' in import_list:
        return 'feature_definitions'
    else:
        return 'missing_module'  # 默认值

def fix_indentation(text):
    """修复缩进"""
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            fixed_lines.append(f'        {stripped}')
        else:
            fixed_lines.append(line)
    return '\n'.join(fixed_lines)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python fix_missing_imports.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    fixed = fix_missing_from_statements(file_path)
    if fixed:
        print(f"Fixed: {file_path}")
    else:
        print(f"No changes needed: {file_path}")

if __name__ == '__main__':
    main()