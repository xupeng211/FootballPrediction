#!/usr/bin/env python3
"""
分析剩余语法错误工具
Analyze remaining syntax errors
"""

import ast
import re
from pathlib import Path
from collections import defaultdict, Counter
import json

def analyze_syntax_errors():
    """分析所有语法错误"""
    error_details = []
    error_types = Counter()
    module_errors = defaultdict(list)

    for py_file in Path('src').rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            module = str(py_file.parent.relative_to('src'))
            error_info = {
                'file': str(py_file.relative_to('src')),
                'module': module,
                'line': e.lineno,
                'column': e.offset,
                'message': e.msg,
                'text': e.text.strip() if e.text else ''
            }
            error_details.append(error_info)
            module_errors[module].append(error_info)

            # 分类错误类型
            error_type = categorize_error(e.msg)
            error_types[error_type] += 1

    return error_details, error_types, module_errors

def categorize_error(message):
    """将错误消息分类"""
    message_lower = message.lower()

    if 'invalid character' in message_lower:
        return 'invalid_character'
    elif 'unterminated string literal' in message_lower:
        return 'unterminated_string'
    elif 'invalid syntax' in message_lower:
        return 'invalid_syntax'
    elif 'unexpected eof' in message_lower or 'eof while scanning' in message_lower:
        return 'unexpected_eof'
    elif 'mismatched parentheses' in message_lower or 'unmatched' in message_lower:
        return 'mismatched_parentheses'
    elif 'indentation' in message_lower:
        return 'indentation_error'
    elif 'import' in message_lower:
        return 'import_error'
    elif 'f-string' in message_lower:
        return 'fstring_error'
    elif 'colon' in message_lower:
        return 'missing_colon'
    else:
        return 'other'

def print_analysis():
    """打印分析结果"""
    error_details, error_types, module_errors = analyze_syntax_errors()

    print("="*80)
    print("语法错误分析报告")
    print("="*80)
    print(f"\n总错误文件数: {len(error_details)}")
    print(f"涉及模块数: {len(module_errors)}")

    print("\n错误类型分布:")
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count} 个")

    print("\n各模块错误数量（前10）:")
    sorted_modules = sorted(module_errors.items(), key=lambda x: len(x[1]), reverse=True)
    for module, errors in sorted_modules[:10]:
        print(f"  {module}: {len(errors)} 个文件")

    # 显示具体错误示例
    print("\n常见错误示例:")
    for error_type in ['invalid_character', 'unterminated_string', 'invalid_syntax']:
        if error_type in error_types:
            print(f"\n{error_type} 示例:")
            for error in error_details[:3]:
                if categorize_error(error['message']) == error_type:
                    print(f"  文件: {error['file']}")
                    print(f"  行号: {error['line']}")
                    print(f"  错误: {error['message']}")
                    if error['text']:
                        print(f"  代码: {error['text'][:50]}...")
                    break

    # 保存详细分析到文件
    with open('syntax_errors_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_errors': len(error_details),
            'error_types': dict(error_types),
            'modules': {m: len(e) for m, e in module_errors.items()},
            'details': error_details[:100]  # 只保存前100个错误详情
        }, f, indent=2, ensure_ascii=False)

    print(f"\n详细分析已保存到: syntax_errors_analysis.json")

    return error_details, error_types, module_errors

if __name__ == '__main__':
    print_analysis()