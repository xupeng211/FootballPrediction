#!/usr/bin/env python3
"""
定向F821修复器
Targeted F821 Fixer

快速修复常见的F821未定义名称错误
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Set

class TargetedF821Fixer:
    """定向F821修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0

        # 常见导入映射
        self.common_imports = {
            'Any': 'from typing import Any',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Optional': 'from typing import Optional',
            'Union': 'from typing import Union',
            'Callable': 'from typing import Callable',
            'Tuple': 'from typing import Tuple',
            'Type': 'from typing import Type',
            'Protocol': 'from typing import Protocol',
            'Generic': 'from typing import Generic',
            'datetime': 'from datetime import datetime',
            'date': 'from datetime import date',
            'time': 'from datetime import time',
            'timedelta': 'from datetime import timedelta',
            'Path': 'from pathlib import Path',
            'AsyncSession': 'from sqlalchemy.ext.asyncio import AsyncSession',
            'Session': 'from sqlalchemy.orm import Session',
            'create_async_engine': 'from sqlalchemy.ext.asyncio import create_async_engine',
            'select': 'from sqlalchemy import select',
            'update': 'from sqlalchemy import update',
            'delete': 'from sqlalchemy import delete',
            'insert': 'from sqlalchemy import insert',
            'Column': 'from sqlalchemy import Column',
            'Integer': 'from sqlalchemy import Integer',
            'String': 'from sqlalchemy import String',
            'Boolean': 'from sqlalchemy import Boolean',
            'Float': 'from sqlalchemy import Float',
            'DateTime': 'from sqlalchemy import DateTime',
            'Text': 'from sqlalchemy import Text',
            'BaseModel': 'from pydantic import BaseModel',
            'Field': 'from pydantic import Field',
            'validator': 'from pydantic import validator',
            'APIRouter': 'from fastapi import APIRouter',
            'HTTPException': 'from fastapi import HTTPException',
            'Query': 'from fastapi import Query',
            'Depends': 'from fastapi import Depends',
            'BackgroundTasks': 'from fastapi import BackgroundTasks',
            'Body': 'from fastapi import Body',
            'Path': 'from fastapi import Path',
            'Request': 'from fastapi import Request',
            'Response': 'from fastapi import Response',
            'status': 'from fastapi import status',
            'asynccontext_manager': 'from contextlib import asynccontext_manager',
            'asyncio': 'import asyncio',
            'logging': 'import logging',
            'logger': 'import logging\nlogger = logging.getLogger(__name__)',
            'os': 'import os',
            'sys': 'import sys',
            'json': 'import json',
            're': 'import re',
            'uuid': 'import uuid',
            'random': 'import random',
            'hashlib': 'import hashlib',
            'base64': 'import base64',
            'decimal': 'from decimal import Decimal',
            'fractions': 'from fractions import Fraction',
            'dataclasses': 'import dataclasses',
            'enum': 'import enum',
            'abc': 'import abc',
            'collections': 'import collections',
            'itertools': 'import itertools',
            'functools': 'import functools',
            'operator': 'import operator',
            'typing_extensions': 'import typing_extensions',
        }

    def get_f821_errors(self) -> List[Dict]:
        """获取F821错误列表"""
        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=F821', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            errors = []
            if result.stdout.strip():
                try:
                    error_data = json.loads(result.stdout)
                    for error in error_data:
                        if error.get('code') == 'F821':
                            # 提取未定义名称
                            message = error['message']
                            if "undefined name `" in message:
                                name = message.split("undefined name `")[1].split("`")[0]
                                errors.append({
                                    'file': error['filename'],
                                    'line': error['location']['row'],
                                    'col': error['location']['column'],
                                    'name': name,
                                    'message': message
                                })
                except json.JSONDecodeError:
                    # 备用解析方法
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'F821' in line and 'undefined name' in line:
                            # 简单解析
                            parts = line.split(':')
                            if len(parts) >= 4:
                                file_path = parts[0]
                                line_num = int(parts[1])
                                message = ':'.join(parts[3:])
                                if "undefined name `" in message:
                                    name = message.split("undefined name `")[1].split("`")[0]
                                    errors.append({
                                        'file': file_path,
                                        'line': line_num,
                                        'name': name,
                                        'message': message
                                    })

            return errors

        except Exception as e:
            print(f"❌ 获取F821错误失败: {e}")
            return []

    def fix_file(self, file_path: str, undefined_names: List[str]) -> bool:
        """修复单个文件的F821错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            lines.copy()

            # 查找导入区域
            import_end = 0
            in_import_section = False

            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')) or stripped.startswith('#'):
                    if stripped.startswith(('import ', 'from ')):
                        import_end = i + 1
                        in_import_section = True
                elif stripped and in_import_section:
                    break

            # 需要添加的导入
            imports_to_add = []
            for name in undefined_names:
                if name in self.common_imports:
                    import_stmt = self.common_imports[name]
                    if import_stmt not in content:
                        imports_to_add.append(import_stmt)

            if imports_to_add:
                # 添加导入
                for import_stmt in imports_to_add:
                    lines.insert(import_end, import_stmt)
                    import_end += 1

                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

                print(f"✅ 修复文件: {file_path}")
                print(f"   添加导入: {len(imports_to_add)} 个")
                for imp in imports_to_add:
                    print(f"   - {imp}")

                return True
            else:
                print(f"⚠️  无法修复: {file_path} (没有找到对应的导入)")
                return False

        except Exception as e:
            print(f"❌ 修复文件失败 {file_path}: {e}")
            return False

    def run_targeted_fix(self):
        """运行定向F821修复"""
        print("🎯 定向F821修复器")
        print("=" * 50)

        # 获取F821错误
        errors = self.get_f821_errors()

        if not errors:
            print("✅ 没有发现F821错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'message': '没有F821错误需要修复'
            }

        print(f"📊 发现 {len(errors)} 个F821错误")

        # 按文件分组
        errors_by_file = {}
        for error in errors:
            file_path = error['file']
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error['name'])

        # 修复每个文件
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, undefined_names in errors_by_file.items():
            # 只处理src/目录下的文件
            if not file_path.startswith('src/'):
                print(f"⚠️  跳过非src目录文件: {file_path}")
                continue

            undefined_names = list(set(undefined_names))  # 去重

            if self.fix_file(file_path, undefined_names):
                files_fixed += 1
                total_errors_fixed += len(undefined_names)
                self.fixes_applied += len(undefined_names)

            self.files_processed += 1

        result = {
            'success': files_fixed > 0,
            'total_errors_found': len(errors),
            'errors_fixed': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'message': f'修复了 {files_fixed} 个文件中的 {total_errors_fixed} 个错误'
        }

        print("\n📊 修复摘要:")
        print(f"   发现错误数: {result['total_errors_found']}")
        print(f"   修复错误数: {result['errors_fixed']}")
        print(f"   处理文件数: {result['files_processed']}")
        print(f"   修复文件数: {result['files_fixed']}")
        print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 部分成功'}")

        return result

def main():
    """主函数"""
    fixer = TargetedF821Fixer()
    result = fixer.run_targeted_fix()

    # 保存报告
    report_file = Path('targeted_f821_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n📄 修复报告已保存到: {report_file}")
    return result

if __name__ == '__main__':
    main()