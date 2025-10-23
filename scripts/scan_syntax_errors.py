#!/usr/bin/env python3
"""
语法错误扫描工具
系统性地扫描项目中的所有语法错误并分类
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import json


def scan_syntax_errors(src_dir: str = "src/") -> Dict[str, List[Dict]]:
    """
    扫描源代码目录中的所有语法错误

    Returns:
        Dict: {文件路径: [错误列表]}
    """
    errors_by_file = {}

    for py_file in Path(src_dir).rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 尝试解析AST
            ast.parse(content)

        except SyntaxError as e:
            file_path = str(py_file)
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []

            error_info = {
                'type': type(e).__name__,
                'line': e.lineno,
                'column': e.offset,
                'message': str(e),
                'text': e.text.strip() if e.text else ""
            }
            errors_by_file[file_path].append(error_info)

        except Exception as e:
            # 其他错误（如编码问题）
            file_path = str(py_file)
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []

            error_info = {
                'type': 'OtherError',
                'line': None,
                'column': None,
                'message': str(e),
                'text': ""
            }
            errors_by_file[file_path].append(error_info)

    return errors_by_file


def categorize_errors(errors_by_file: Dict) -> Dict[str, List[str]]:
    """
    按错误类型和模块分类错误
    """
    categories = {
        'indentation_errors': [],
        'syntax_errors': [],
        'other_errors': []
    }

    for file_path, errors in errors_by_file.items():
        for error in errors:
            if 'IndentationError' in error['type']:
                categories['indentation_errors'].append(file_path)
            elif 'SyntaxError' in error['type']:
                categories['syntax_errors'].append(file_path)
            else:
                categories['other_errors'].append(file_path)

    # 去重
    for category in categories:
        categories[category] = list(set(categories[category]))

    return categories


def prioritize_files(errors_by_file: Dict) -> List[Tuple[str, int]]:
    """
    按重要性优先级排序文件
    核心模块优先级更高
    """
    priority_modules = [
        'src/core/', 'src/api/', 'src/domain/', 'src/database/',
        'src/services/', 'src/models/'
    ]

    def get_priority(file_path: str) -> int:
        for i, module in enumerate(priority_modules):
            if file_path.startswith(module):
                return i
        return len(priority_modules)

    # 按优先级和错误数量排序
    file_priorities = []
    for file_path, errors in errors_by_file.items():
        priority = get_priority(file_path)
        error_count = len(errors)
        file_priorities.append((file_path, priority, error_count))

    file_priorities.sort(key=lambda x: (x[1], -x[2]))
    return [(fp[0], fp[2]) for fp in file_priorities]


def generate_fix_plan(errors_by_file: Dict) -> Dict:
    """
    生成修复计划
    """
    categories = categorize_errors(errors_by_file)
    prioritized_files = prioritize_files(errors_by_file)

    fix_plan = {
        'summary': {
            'total_files_with_errors': len(errors_by_file),
            'total_errors': sum(len(errors) for errors in errors_by_file.values()),
            'indentation_files': len(categories['indentation_errors']),
            'syntax_files': len(categories['syntax_errors']),
            'other_files': len(categories['other_errors'])
        },
        'categories': categories,
        'prioritized_files': prioritized_files,
        'fix_order': []
    }

    # 生成修复顺序
    core_modules = ['src/core/', 'src/api/', 'src/domain/', 'src/database/']
    data_modules = ['src/data/', 'src/features/', 'src/ml/']
    infra_modules = ['src/cache/', 'src/monitoring/', 'src/tasks/']
    other_modules = []

    for file_path, error_count in prioritized_files:
        if any(file_path.startswith(module) for module in core_modules):
            fix_plan['fix_order'].append(('core', file_path, error_count))
        elif any(file_path.startswith(module) for module in data_modules):
            fix_plan['fix_order'].append(('data', file_path, error_count))
        elif any(file_path.startswith(module) for module in infra_modules):
            fix_plan['fix_order'].append(('infrastructure', file_path, error_count))
        else:
            fix_plan['fix_order'].append(('other', file_path, error_count))

    return fix_plan


def main():
    print("🔍 扫描项目中的语法错误...")

    # 扫描语法错误
    errors_by_file = scan_syntax_errors()

    if not errors_by_file:
        print("✅ 没有发现语法错误！")
        return

    # 生成修复计划
    fix_plan = generate_fix_plan(errors_by_file)

    # 打印摘要
    summary = fix_plan['summary']
    print(f"\n📊 语法错误摘要:")
    print(f"   总文件数: {summary['total_files_with_errors']}")
    print(f"   总错误数: {summary['total_errors']}")
    print(f"   缩进错误文件: {summary['indentation_files']}")
    print(f"   语法错误文件: {summary['syntax_files']}")
    print(f"   其他错误文件: {summary['other_files']}")

    # 打印修复计划
    print(f"\n📋 修复计划 (按优先级排序):")
    for i, (category, file_path, error_count) in enumerate(fix_plan['fix_order'][:10], 1):
        print(f"   {i:2d}. [{category:12s}] {file_path} ({error_count} 个错误)")

    if len(fix_plan['fix_order']) > 10:
        print(f"   ... 还有 {len(fix_plan['fix_order']) - 10} 个文件")

    # 保存详细报告
    report_path = "syntax_errors_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(fix_plan, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_path}")

    return fix_plan


if __name__ == "__main__":
    main()