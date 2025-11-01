#!/usr/bin/env python3
"""
快速F821批量修复工具
Quick F821 Batch Fix Tool

基于成功验证的策略，快速批量修复常见F821错误
"""

import subprocess
import json
from pathlib import Path

def get_f821_files_with_errors():
    """获取有F821错误的文件列表"""
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=F821', '--format=json'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.stdout.strip():
            error_data = json.loads(result.stdout)
            files_with_errors = {}

            for error in error_data:
                if error.get('code') == 'F821':
                    file_path = error['filename']
                    if file_path not in files_with_errors:
                        files_with_errors[file_path] = []

                    # 提取未定义的名称
                    message = error['message']
                    if "undefined name '" in message:
                        name = message.split("undefined name '")[1].split("'")[0]
                        files_with_errors[file_path].append(name)

            return files_with_errors

    except Exception as e:
        print(f"获取F821错误失败: {e}")

    return {}

def fix_file_f821(file_path, undefined_names):
    """修复单个文件的F821错误"""
    print(f"🔧 修复文件: {file_path}")
    print(f"   未定义名称: {undefined_names}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # 查找导入区域
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_end = i + 1
            elif line.strip() and not line.startswith('#') and import_end > 0:
                break

        # 常见导入映射
        common_imports = {
            'APIRouter': 'from fastapi import APIRouter',
            'HTTPException': 'from fastapi import HTTPException',
            'Query': 'from fastapi import Query',
            'Depends': 'from fastapi import Depends',
            'BackgroundTasks': 'from fastapi import BackgroundTasks',
            'BaseModel': 'from pydantic import BaseModel',
            'Field': 'from pydantic import Field',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Optional': 'from typing import Optional',
            'datetime': 'from datetime import datetime',
            'logger': 'import logging\nlogger = logging.getLogger(__name__)'
        }

        # 添加缺失的导入
        added_imports = []
        for name in undefined_names:
            if name in common_imports:
                import_statement = common_imports[name]
                if import_statement not in content:
                    lines.insert(import_end, import_statement)
                    import_end += 1
                    added_imports.append(import_statement)

        if added_imports:
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print(f"✅ 添加了 {len(added_imports)} 个导入:")
            for imp in added_imports:
                print(f"   - {imp}")
            return True
        else:
            print("⚠️  没有找到匹配的导入方案")
            return False

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 快速F821批量修复工具")
    print("=" * 50)

    # 获取F821错误
    files_with_errors = get_f821_files_with_errors()

    if not files_with_errors:
        print("✅ 没有发现F821错误")
        return

    print(f"📊 发现 {len(files_with_errors)} 个文件有F821错误")

    # 批量修复
    total_fixed = 0
    for file_path, undefined_names in files_with_errors.items():
        # 只处理src/目录下的文件
        if not file_path.startswith('src/'):
            continue

        # 只处理前10个文件进行测试
        if total_fixed >= 10:
            print("📋 已处理10个文件，停止批量处理")
            break

        if fix_file_f821(file_path, list(set(undefined_names))):
            total_fixed += 1

    print(f"\n🎯 批量修复完成: 修复了 {total_fixed} 个文件")

if __name__ == '__main__':
    main()