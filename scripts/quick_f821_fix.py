#!/usr/bin/env python3
"""
快速F821错误修复工具
Quick F821 Error Fixer

快速处理最常见的F821未定义名称错误
"""

import subprocess
import re
from pathlib import Path

def find_and_fix_f821_errors():
    """查找并修复F821错误"""
    print("🔍 查找F821错误...")

    # 运行ruff检查获取F821错误
    result = subprocess.run(
        ['ruff', 'check', '--select=F821', 'src/', '--format=concise'],
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        print("✅ 没有发现F821错误")
        return 0

    # 解析F821错误
    f821_errors = []
    for line in result.stdout.split('\n'):
        if 'F821' in line and 'undefined name' in line:
            # 解析文件路径、行号和未定义名称
            parts = line.split(':')
            if len(parts) >= 4:
                file_path = parts[0]
                line_num = int(parts[1])
                error_msg = ':'.join(parts[3:]).strip()

                # 提取未定义名称
                name_match = re.search(r"undefined name '([^']+)'", error_msg)
                if name_match:
                    undefined_name = name_match.group(1)
                    f821_errors.append({
                        'file': file_path,
                        'line': line_num,
                        'name': undefined_name,
                        'full_error': line.strip()
                    })

    print(f"📊 发现 {len(f821_errors)} 个F821错误")

    # 常见修复映射
    common_fixes = {
        'APIRouter': 'from fastapi import APIRouter',
        'HTTPException': 'from fastapi import HTTPException',
        'Query': 'from fastapi import Query',
        'Depends': 'from fastapi import Depends',
        'BaseModel': 'from pydantic import BaseModel',
        'Field': 'from pydantic import Field',
        'Dict': 'from typing import Dict',
        'List': 'from typing import List',
        'Optional': 'from typing import Optional',
        'datetime': 'from datetime import datetime',
        'Path': 'from pathlib import Path',
        'Mock': 'from unittest.mock import Mock, patch',
        'patch': 'from unittest.mock import patch',
        'logger': 'import logging',
        're': 'import re',
        'json': 'import json'
    }

    # 按文件分组错误
    errors_by_file = {}
    for error in f821_errors:
        file_path = error['file']
        if file_path not in errors_by_file:
            errors_by_file[file_path] = []
        errors_by_file[file_path].append(error)

    # 修复每个文件
    fixed_count = 0
    for file_path, file_errors in errors_by_file.items():
        if fix_file_f821(file_path, file_errors, common_fixes):
            fixed_count += len(file_errors)

    print(f"✅ 修复了 {fixed_count} 个F821错误")
    return fixed_count

def fix_file_f821(file_path, errors, common_fixes):
    """修复单个文件的F821错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        modified = False

        # 查找导入区域
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_end = i + 1
            elif line.strip() and not line.startswith('#') and import_end > 0:
                break

        # 收集需要添加的导入
        needed_imports = set()
        for error in errors:
            undefined_name = error['name']
            if undefined_name in common_fixes:
                needed_imports.add(common_fixes[undefined_name])

        # 添加缺失的导入
        if needed_imports:
            for import_stmt in sorted(needed_imports):
                if import_stmt not in content:
                    lines.insert(import_end, import_stmt)
                    import_end += 1
                    modified = True
                    print(f"   添加导入: {import_stmt}")

        # 写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")

    return False

if __name__ == '__main__':
    print("🚀 快速F821错误修复工具")
    print("=" * 40)

    fixed_count = find_and_fix_f821_errors()

    print(f"\n🎯 修复完成: {fixed_count} 个F821错误")

    if fixed_count > 0:
        print("💡 建议: 运行 'python3 scripts/quality_gate_validator.py' 验证修复效果")