#!/usr/bin/env python3
"""
分析MyPy错误的类型和分布
"""

import subprocess
import re
from collections import Counter
import json

def run_mypy():
    """运行MyPy并获取输出"""
    try:
        result = subprocess.run(
            ['mypy', 'src/', '--show-error-codes', '--no-error-summary'],
            capture_output=True,
            text=True,
            cwd='/home/user/projects/FootballPrediction'
        )
        return result.stdout
    except Exception as e:
        print(f"Error running mypy: {e}")
        return ""

def parse_mypy_errors(output):
    """解析MyPy错误输出"""
    errors = []
    lines = output.split('\n')

    for line in lines:
        # 匹配MyPy错误格式: file:line: error: message [error-code]
        match = re.match(r'^(.+?):(\d+): error: (.+?)\s*(\[[^\]]+\])?$', line)
        if match:
            file_path, line_num, message, error_code = match.groups()
            errors.append({
                'file': file_path,
                'line': int(line_num),
                'message': message.strip(),
                'error_code': error_code.strip('[]') if error_code else 'general'
            })

    return errors

def categorize_errors(errors):
    """将错误分类"""
    categories = {
        'name_not_defined': [],
        'unexpected_keyword': [],
        'no_any_return': [],
        'assignment_issue': [],
        'return_type': [],
        'attribute_error': [],
        'import_not_found': [],
        'type_annotation': [],
        'unreachable_code': [],
        'unused_ignore': [],
        'other': []
    }

    for error in errors:
        message = error['message'].lower()

        if 'name "' in message and ' is not defined' in message:
            categories['name_not_defined'].append(error)
        elif 'unexpected keyword argument' in message:
            categories['unexpected_keyword'].append(error)
        elif 'returning any' in message and 'declared to return' in message:
            categories['no_any_return'].append(error)
        elif 'assignment' in message or 'incompatible types in assignment' in message:
            categories['assignment_issue'].append(error)
        elif 'return value' in message or 'incompatible return value' in message:
            categories['return_type'].append(error)
        elif 'has no attribute' in message:
            categories['attribute_error'].append(error)
        elif 'cannot find implementation' in message or 'import-not-found' in message:
            categories['import_not_found'].append(error)
        elif 'need type annotation' in message or 'annotation' in message:
            categories['type_annotation'].append(error)
        elif 'unreachable' in message:
            categories['unreachable_code'].append(error)
        elif 'unused "type: ignore" comment' in message:
            categories['unused_ignore'].append(error)
        else:
            categories['other'].append(error)

    return categories

def generate_report(errors, categories):
    """生成分析报告"""
    total_errors = len(errors)

    print("🔍 MyPy错误分析报告")
    print("=" * 50)
    print(f"总错误数: {total_errors}")
    print()

    # 按类型统计
    print("📊 错误类型分布:")
    for category, items in categories.items():
        if items:
            percentage = (len(items) / total_errors) * 100
            print(f"  {category}: {len(items)} ({percentage:.1f}%)")

    print()

    # 按文件统计
    file_errors = Counter(error['file'] for error in errors)
    print("📁 错误最多的文件:")
    for file_path, count in file_errors.most_common(10):
        print(f"  {file_path}: {count} errors")

    print()

    # 详细分析每种错误类型
    print("📋 错误详细分析:")
    for category, items in categories.items():
        if not items:
            continue

        print(f"\n🔹 {category.upper()} ({len(items)} errors)")

        # 显示前几个例子
        for error in items[:3]:
            print(f"  {error['file']}:{error['line']}: {error['message']}")

        if len(items) > 3:
            print(f"  ... 还有 {len(items) - 3} 个类似错误")

    # 生成修复建议
    print("\n💡 修复建议 (按优先级):")

    # 简单修复
    simple_fixes = []
    for category, items in categories.items():
        if category in ['name_not_defined', 'unexpected_keyword', 'unused_ignore']:
            simple_fixes.extend(items)

    if simple_fixes:
        print(f"  1. 简单修复 ({len(simple_fixes)} 个):")
        print(f"     - 变量命名问题 (_result → result)")
        print(f"     - 参数名称问题 (_data → data)")
        print(f"     - 清理未使用的 type: ignore 注释")

    # 中等难度
    medium_fixes = []
    for category, items in categories.items():
        if category in ['assignment_issue', 'return_type', 'type_annotation']:
            medium_fixes.extend(items)

    if medium_fixes:
        print(f"  2. 中等难度 ({len(medium_fixes)} 个):")
        print(f"     - 添加类型注解")
        print(f"     - 修复类型不匹配")

    # 复杂问题
    complex_fixes = []
    for category, items in categories.items():
        if category in ['no_any_return', 'attribute_error', 'import_not_found']:
            complex_fixes.extend(items)

    if complex_fixes:
        print(f"  3. 复杂问题 ({len(complex_fixes)} 个):")
        print(f"     - 重构代码避免 Any 类型")
        print(f"     - 修复属性访问错误")
        print(f"     - 解决导入问题")

def main():
    """主函数"""
    print("🚀 开始分析MyPy错误...")

    # 运行MyPy
    output = run_mypy()

    if not output:
        print("❌ 无法获取MyPy输出")
        return

    # 解析错误
    errors = parse_mypy_errors(output)

    if not errors:
        print("✅ 没有发现MyPy错误")
        return

    # 分类错误
    categories = categorize_errors(errors)

    # 生成报告
    generate_report(errors, categories)

    # 保存详细数据
    with open('/home/user/projects/FootballPrediction/mypy_error_analysis.json', 'w') as f:
        json.dump({
            'total_errors': len(errors),
            'categories': {k: len(v) for k, v in categories.items()},
            'errors': errors
        }, f, indent=2)

    print(f"\n💾 详细数据已保存到 mypy_error_analysis.json")

if __name__ == '__main__':
    main()