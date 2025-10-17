#!/usr/bin/env python3
"""
检查项目中损坏的文件
"""

import ast
import os
from pathlib import Path
from collections import defaultdict

def check_syntax_errors(directory):
    """检查目录中的语法错误"""
    error_files = {}
    error_types = defaultdict(int)

    for py_file in Path(directory).rglob('*.py'):
        # 跳过虚拟环境和缓存目录
        if '.venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            error_files[str(py_file)] = {
                'error': str(e),
                'line': e.lineno,
                'type': type(e).__name__
            }
            error_types[type(e).__name__] += 1
        except Exception as e:
            error_files[str(py_file)] = {
                'error': str(e),
                'line': None,
                'type': 'OtherError'
            }
            error_types['OtherError'] += 1

    return error_files, error_types

def main():
    """主函数"""
    print("=" * 80)
    print("项目文件损坏情况检查报告")
    print("=" * 80)

    # 检查src目录
    print("\n🔍 检查 src/ 目录...")
    src_errors, src_error_types = check_syntax_errors('src')

    # 检查tests目录
    print("\n🔍 检查 tests/ 目录...")
    test_errors, test_error_types = check_syntax_errors('tests')

    # 检查根目录的Python文件
    print("\n🔍 检查根目录...")
    root_errors, root_error_types = check_syntax_errors('.')

    # 汇总统计
    total_errors = len(src_errors) + len(test_errors) + len(root_errors)
    total_files = len(list(Path('src').rglob('*.py'))) + len(list(Path('tests').rglob('*.py')))

    print("\n" + "=" * 80)
    print("📊 统计结果")
    print("=" * 80)
    print(f"• 总Python文件数: {total_files}")
    print(f"• 损坏文件数: {total_errors}")
    print(f"• 损坏率: {total_errors/total_files*100:.1f}%")

    print("\n📁 按目录分布:")
    print(f"• src/ 目录: {len(src_errors)} 个文件损坏")
    print(f"• tests/ 目录: {len(test_errors)} 个文件损坏")
    print(f"• 根目录: {len(root_errors)} 个文件损坏")

    # 错误类型统计
    print("\n🔧 错误类型分布:")
    all_error_types = defaultdict(int)
    for d in [src_error_types, test_error_types, root_error_types]:
        for k, v in d.items():
            all_error_types[k] += v

    for error_type, count in sorted(all_error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"• {error_type}: {count} 个")

    # 最严重的问题文件
    print("\n🚨 最严重的问题（前20个）:")
    all_errors = {}
    all_errors.update(src_errors)
    all_errors.update(test_errors)
    all_errors.update(root_errors)

    # 按行号排序，优先显示前面的错误
    sorted_errors = sorted(all_errors.items(),
                          key=lambda x: (x[1]['line'] or 0, x[0]))[:20]

    for file_path, error_info in sorted_errors:
        relative_path = file_path.replace('/home/user/projects/FootballPrediction/', '')
        line_info = f" (行 {error_info['line']})" if error_info['line'] else ""
        print(f"• {relative_path}{line_info}: {error_info['error'][:80]}...")

    # 关键模块检查
    critical_modules = [
        'src/utils/string_utils.py',
        'src/utils/helpers.py',
        'src/main.py',
        'src/api/app.py',
        'src/database/models/__init__.py',
        'tests/conftest.py'
    ]

    print("\n⚡ 关键模块状态:")
    for module in critical_modules:
        if module in all_errors:
            status = "❌ 损坏"
            error = all_errors[module]['error'][:50]
            print(f"• {module}: {status} - {error}...")
        else:
            status = "✅ 正常"
            print(f"• {module}: {status}")

    # 保存详细报告
    with open('damaged_files_report.txt', 'w', encoding='utf-8') as f:
        f.write("项目文件损坏情况详细报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"总损坏文件: {total_errors} / {total_files}\n\n")

        for file_path, error_info in all_errors.items():
            f.write(f"文件: {file_path}\n")
            f.write(f"错误类型: {error_info['type']}\n")
            f.write(f"行号: {error_info['line']}\n")
            f.write(f"错误信息: {error_info['error']}\n")
            f.write("-" * 40 + "\n")

    print(f"\n📄 详细报告已保存到: damaged_files_report.txt")

    return total_errors

if __name__ == '__main__':
    total = main()
    exit(1 if total > 0 else 0)