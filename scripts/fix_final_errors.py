#!/usr/bin/env python3
"""
最终语法错误修复脚本
处理剩余的42个文件的语法错误
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict, Set

def check_syntax(file_path: str) -> bool:
    """检查文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError:
        return False
    except Exception:
        return False

def fix_common_errors(content: str) -> Tuple[str, int]:
    """修复最常见的语法错误"""
    fixes = 0

    # 1. 修复 Optional[List[str] = None] -> Optional[List[str]] = None
    pattern1 = r'Optional\[(.*?)\s*=\s*None\]'
    matches1 = re.findall(pattern1, content)
    for match in matches1:
        if not match.strip().endswith(']'):
            content = re.sub(f'Optional\\[{re.escape(match)}\\s*=\\s*None\\]',
                           f'Optional[{match}] = None', content)
            fixes += 1

    # 2. 修复 Dict[str, Any] = None] -> Dict[str, Any] = None
    content = re.sub(r'(Dict\[.*?\])\]?\s*=\s*None', r'\1 = None', content)

    # 3. 修复 Union[A, B] = None] -> Union[A, B] = None
    content = re.sub(r'(Union\[.*?\])\]?\s*=\s*None', r'\1 = None', content)

    # 4. 修复 List[Dict[str, Any] = None] -> List[Dict[str, Any]] = None
    content = re.sub(r'List\[(.*?)\s*=\s*None\]', r'List[\1] = None', content)

    # 5. 修复字典初始化错误 {}], {]] -> {}
    content = content.replace('{}]', '{}')
    content = content.replace('{]]', '{}')
    content = content.replace('[}]', '}')
    content = content.replace('[[', '[')
    content = content.replace(']]', ']')

    # 6. 修复函数参数中的类型注解错误
    # data: Optional[List[str] = None] -> data: Optional[List[str]] = None
    content = re.sub(r'(\w+):\s*(Optional\[.*?\])\s*=\s*None\]', r'\1: \2 = None', content)

    # 7. 修复 f-string 中的引号问题
    content = re.sub(r"f'(\{.*?\})\"([^']*)'", r"f'\1\2'", content)
    content = re.sub(r'f"(\{.*?\})\'([^"]*)"', r'f"\1\2"', content)

    # 8. 修复字典键中的错误
    content = re.sub(r'"(\w+)"\s*:\s*([^\s,}]+)\s*]', r'"\1": \2', content)

    # 9. 修复未闭合的字符串
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 检查未闭合的三引号
        if '"""' in line and line.count('"""') % 2 != 0:
            if i + 1 < len(lines) and '"""' not in lines[i + 1]:
                lines[i] += '"""'
                fixes += 1

    content = '\n'.join(lines)

    return content, fixes

def fix_specific_file_errors(content: str, file_path: str) -> Tuple[str, int]:
    """修复特定文件的已知错误"""
    fixes = 0

    # 根据文件路径应用特定的修复
    if 'processing_cache.py' in file_path:
        # 修复 processing_cache.py 中的特定错误
        content = re.sub(r'\"errors\": \[\], \"warnings\": \[\]\}',
                        '{"errors": [], "warnings": []}', content)

    elif 'data_validator.py' in file_path:
        # 修复 data_validator.py 中的类型错误
        content = content.replace(
            'data: Union[Dict[str, Any], List[Dict[str, Any], pd.DataFrame],',
            'data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],'
        )
        # 修复字典初始化
        content = content.replace(
            'result: Dict[str, Any] = {}"errors": [], "warnings": []}',
            '{"errors": [], "warnings": []}'
        )

    elif 'match_processor.py' in file_path:
        # 修复 match_processor.py 中的类型错误
        content = content.replace(
            'raw_data: Union[Dict[str, Any], List[Dict[str, Any]  # type: ignore',
            'raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]  # type: ignore'
        )
        # 修复列表初始化
        content = content.replace('results: List[Any  = {}  # type: ignore',
                                'results: List[Any] = []  # type: ignore')
        content = content.replace('batch_results: List[Any  = {}  # type: ignore',
                                'batch_results: List[Any] = []  # type: ignore')
        content = content.replace('processed_matches: List[Any  = {}  # type: ignore',
                                'processed_matches: List[Any] = []  # type: ignore')
        content = content.replace('duplicates: List[Any  = {}  # type: ignore',
                                'duplicates: List[Any] = []  # type: ignore')

    return content, fixes

def main():
    """主函数"""
    print("开始修复剩余的语法错误...")

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    # 检查哪些文件有语法错误
    error_files = []
    for file_path in python_files:
        if not check_syntax(file_path):
            error_files.append(file_path)

    print(f"\n发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("所有文件语法都正确！")
        return

    # 修复每个文件
    fixed_count = 0
    total_fixes = 0

    for file_path in error_files:
        print(f"\n处理: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            content = original_content
            fixes = 0

            # 应用通用修复
            content, common_fixes = fix_common_errors(content)
            fixes += common_fixes

            # 应用特定文件修复
            content, specific_fixes = fix_specific_file_errors(content, file_path)
            fixes += specific_fixes

            # 如果有修复，保存文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  修复了 {fixes} 个错误")
                fixed_count += 1
                total_fixes += fixes

                # 验证修复是否成功
                if check_syntax(file_path):
                    print(f"  ✓ 语法错误已修复")
                else:
                    print(f"  ✗ 仍有语法错误")
            else:
                print(f"  - 未找到可修复的错误")

        except Exception as e:
            print(f"  ✗ 处理失败: {e}")

    print(f"\n修复完成！")
    print(f"- 处理文件: {len(error_files)}")
    print(f"- 成功修复: {fixed_count}")
    print(f"- 总修复数: {total_fixes}")

    # 再次检查
    remaining_errors = []
    for file_path in python_files:
        if not check_syntax(file_path):
            remaining_errors.append(file_path)

    if remaining_errors:
        print(f"\n仍有 {len(remaining_errors)} 个文件存在语法错误:")
        for file_path in remaining_errors[:10]:  # 只显示前10个
            print(f"  - {file_path}")
        if len(remaining_errors) > 10:
            print(f"  ... 还有 {len(remaining_errors) - 10} 个文件")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")

if __name__ == "__main__":
    main()
