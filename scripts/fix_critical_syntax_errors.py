#!/usr/bin/env python3
"""
关键语法错误修复脚本
专门处理中文标点、未闭合括号、f-string等关键错误
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

def fix_critical_errors(content: str) -> Tuple[str, int]:
    """修复关键的语法错误"""
    fixes = 0

    # 1. 修复中文全角括号为半角（在文档字符串中）
    # 只修复三引号文档字符串中的中文括号
    content = re.sub(r'"""([^"]*?)（([^"]*?)"""', r'"""\1(\2"""', content)
    content = re.sub(r'"""([^"]*?)）([^"]*?)"""', r'"""\1)\2"""', content)

    # 2. 修复函数定义中的类型注解错误
    # 修复 Optional[Dict[str, Any]] = None, 后面多了 ]
    content = re.sub(r':\s*Optional\[Dict\[str, Any\]\]\s*=\s*None,\]',
                    r': Optional[Dict[str, Any]] = None,', content)
    content = re.sub(r':\s*Optional\[List\[str\]\]\s*=\s*None,\]',
                    r': Optional[List[str]] = None,', content)

    # 3. 修复字典初始化中的语法错误
    # 修复 "errors": [], "warnings": []} 缺少开头
    content = re.sub(r':\s*\[\],\s*"warnings":\s*\[\]\}',
                    r': {"errors": [], "warnings": []}', content)

    # 4. 修复未闭合的括号
    # 修复类型注解中缺少的右括号
    content = re.sub(r'Optional\[List\[Dict\[str, Any\]\s*=\s*None\]',
                    r'Optional[List[Dict[str, Any]]] = None', content)

    # 5. 修复 f-string 中的引号问题
    content = re.sub(r'f"([^"]*?)\'([^"]*?)"', r'f"\1\2"', content)
    content = re.sub(r"f'([^']*?)\"([^']*?)'", r"f'\1\2'", content)

    # 6. 修复函数参数列表中缺少的括号
    content = re.sub(r'\)\s*-\s*>\s*Dict\[str, Any\]:',
                    r') -> Dict[str, Any]:', content)

    # 7. 修复字典字面量中的错误
    content = re.sub(r'{\s*"([^"]+)"\s*:\s*([^,}]+)\]',
                    r'"\1": \2', content)

    # 8. 修复列表初始化错误
    content = re.sub(r'List\[Any\]\s*=\s*{\[\]',
                    r'List[Any] = []', content)
    content = re.sub(r'List\[Any\]\s*=\s*{\{\}',
                    r'List[Any] = []', content)

    # 9. 修复类型注解中的特殊错误
    # 修复 Union[Dict[str, Any], List[Dict[str, Any], pd.DataFrame]
    content = re.sub(r'Union\[Dict\[str, Any\],\s*List\[Dict\[str, Any\],\s*pd\.DataFrame\]',
                    r'Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]', content)

    # 10. 修复函数参数中的错误
    # data: Any,  # type: ignore 后面少了 ]
    content = re.sub(r'data:\s*Any,\s*#\s*type:\s*ignore\]',
                    r'data: Any,  # type: ignore', content)

    # 11. 修复字典中的嵌套错误
    content = re.sub(r'{\s*"total_records":\s*\d+,\s*"total_columns":\s*\d+,',
                    r'{\n            "total_records": len(df),\n            "total_columns": len(df.columns),', content)

    # 12. 修复类定义中的错误
    content = re.sub(r'class\s+(\w+)\([^)]*:\s*def\s+__init__\s*\([^)]*\)\s*-\s*>\s*None:',
                    r'class \1:\n    def __init__(self) -> None:', content)

    # 13. 修复多行字典定义的错误
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 修复字典中缺少逗号
        if i > 0 and ('"' in line or "'" in line) and ':' in line:
            # 检查上一行是否是字典项且没有逗号
            prev_line = lines[i-1].strip()
            if prev_line and not prev_line.endswith(',') and not prev_line.endswith('{') and ':' in prev_line:
                if (prev_line.startswith('"') or prev_line.startswith("'")) or \
                   (prev_line.count('"') == 2 or prev_line.count("'") == 2):
                    lines[i-1] = lines[i-1] + ','
                    fixes += 1

    content = '\n'.join(lines)

    return content, fixes

def fix_specific_line_errors(content: str, file_path: str) -> Tuple[str, int]:
    """修复特定文件的已知行错误"""
    fixes = 0

    # 获取行号信息
    lines = content.split('\n')

    # 根据文件路径修复特定错误
    if 'audit_service_mod/__init__.py' in file_path:
        # 修复第46-47行的类型注解错误
        for i, line in enumerate(lines):
            if 'top_users: List[Dict[str, Any]' in line and not line.endswith(']'):
                lines[i] = line + ']'
                fixes += 1
            elif 'top_resources: List[Dict[str, Any]' in line and not line.endswith(']'):
                lines[i] = line + ']'
                fixes += 1

    elif 'data_validator.py' in file_path:
        # 修复字典初始化错误
        for i, line in enumerate(lines):
            if 'result: Dict[str, Any] = {}"errors":' in line:
                lines[i] = line.replace('{}"errors":', '{"errors":')
                fixes += 1
            elif 'result: Dict[str, Any] = {}"errors":' in line:
                lines[i] = line.replace('{}"errors":', '{"errors":')
                fixes += 1
            # 修复统计信息中的错误
            elif '"min": df[col.min(),' in line:
                lines[i] = line.replace('df[col.min(),', 'df[col].min(),')
                fixes += 1
            elif '"max": df[col.max(),' in line:
                lines[i] = line.replace('df[col.max(),', 'df[col].max(),')
                fixes += 1
            elif '"range_days": (df[col.max() - df[col].min()).days,' in line:
                lines[i] = line.replace('df[col.max() - df[col].min()).days,',
                                      'df[col].max() - df[col].min()).days,')
                fixes += 1

    elif 'match_processor.py' in file_path:
        # 修复函数参数错误
        for i, line in enumerate(lines):
            if 'raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]  # type: ignore' in line:
                lines[i] = line.replace(']]  # type: ignore', '] = None  # type: ignore')
                fixes += 1
            elif 'cleaneddata=' in line:
                lines[i] = line.replace('cleaneddata=', 'cleaned_data = ')
                fixes += 1
            elif 'standardizeddata=' in line:
                lines[i] = line.replace('standardizeddata=', 'standardized_data = ')
                fixes += 1
            # 修复缺少的括号
            elif 'def _process_single_match_data(' in line and i+1 < len(lines):
                if 'Dict[str, Any]:  # type: ignore' in lines[i+1] and not lines[i+1].endswith(']'):
                    lines[i+1] = lines[i+1].replace('Dict[str, Any]:  # type: ignore',
                                                   'Dict[str, Any]]:  # type: ignore')
                    fixes += 1
            # 修复参数列表错误
            elif 'matches: List[Dict[str, Any]' in line and 'batch_size: int' in line:
                if not line.endswith(']'):
                    lines[i] = line.replace('List[Dict[str, Any]', 'List[Dict[str, Any]]')
                    fixes += 1
            elif 'def detect_duplicate_matches(' in line and i+1 < len(lines):
                if 'List[Dict[str, Any]:  # type: ignore' in lines[i+1]:
                    lines[i+1] = lines[i+1].replace('List[Dict[str, Any]:  # type: ignore',
                                                   'List[Dict[str, Any]]:  # type: ignore')
                    fixes += 1

    elif 'processing_cache.py' in file_path:
        # 修复缓存相关的错误
        for i, line in enumerate(lines):
            # 修复参数错误
            if 'params: Optional[Dict[str, Any] = None,  # type: ignore' in line:
                lines[i] = line.replace('= None,  # type: ignore', '] = None  # type: ignore')
                fixes += 1
            # 修复字典错误
            elif '"total_requests": total_requests,' in line:
                lines[i] = line.replace('total_requests,', 'total_requests,')
                fixes += 1
            # 修复 Redis 信息中的错误
            elif '"keyspace_hits": info.get("keyspace_hits", 0),' in line:
                lines[i] = line.replace('0),', '0),')
                fixes += 1

    content = '\n'.join(lines)

    return content, fixes

def main():
    """主函数"""
    print("开始修复关键语法错误...")

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

            # 应用关键错误修复
            content, critical_fixes = fix_critical_errors(content)
            fixes += critical_fixes

            # 应用特定文件修复
            content, specific_fixes = fix_specific_line_errors(content, file_path)
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
                    # 显示第一个错误
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        print(f"    错误位置: 第{e.lineno}行")
                        print(f"    错误信息: {e.msg}")
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
