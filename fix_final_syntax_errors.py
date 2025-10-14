#!/usr/bin/env python3
"""
终极语法错误修复脚本
"""

import os
import re
from pathlib import Path

def fix_all_syntax_errors(content):
    """修复所有已知的语法错误模式"""

    # 1. 修复 typing 导入中的语法错误
    # 修复 "Any, Dict[str], Any" -> "Any, Dict, Any"
    content = re.sub(r'from typing import([^\\n]*?),\s*Dict\[str\],\s*Any([^\\n]*?)',
                     r'from typing import\1, Dict, Any\2', content)

    # 修复 "Any, Dict[str, Any]" -> "Any, Dict, Any"
    content = re.sub(r'from typing import([^\\n]*?),\s*Dict\[str,\s*Any\]([^\\n]*?)',
                     r'from typing import\1, Dict, Any\2', content)

    # 修复 "Dict[str], Any" -> "Dict, Any"
    content = re.sub(r'Dict\[str\],\s*Any', 'Dict, Any', content)

    # 修复 "List[Any]" -> "List"
    content = re.sub(r'List\[Any\]', 'List', content)

    # 修复 "List[Any], Optional" -> "List, Optional"
    content = re.sub(r'List\[Any\],\s*Optional', 'List, Optional', content)

    # 修复 "Dict[str, Any], Optional" -> "Dict, Optional"
    content = re.sub(r'Dict\[str,\s*Any\],\s*Optional', 'Dict, Optional', content)

    # 修复 "Dict[str], Any, List[Any]" -> "Dict, Any, List"
    content = re.sub(r'Dict\[str\],\s*Any,\s*List\[Any\]', 'Dict, Any, List', content)

    # 修复 "Dict[str, Any], Any, List[Any]" -> "Dict, Any, List"
    content = re.sub(r'Dict\[str,\s*Any\],\s*Any,\s*List\[Any\]', 'Dict, Any, List', content)

    # 修复 "Dict[str, Any], Any, List[Any], Optional" -> "Dict, Any, List, Optional"
    content = re.sub(r'Dict\[str,\s*Any\],\s*Any,\s*List\[Any\],\s*Optional',
                     'Dict, Any, List, Optional', content)

    # 修复 "Any, Dict[str, Any], List[Any]" -> "Any, Dict, List"
    content = re.sub(r'Any,\s*Dict\[str,\s*Any\],\s*List\[Any\]', 'Any, Dict, List', content)

    # 修复 "Any, Dict[str, Any], Any, List[Any]" -> "Any, Dict, Any, List"
    content = re.sub(r'Any,\s*Dict\[str,\s*Any\],\s*Any,\s*List\[Any\]', 'Any, Dict, Any, List', content)

    # 修复 "Union, Any, Dict[str, Any], Optional" -> "Union, Any, Dict, Optional"
    content = re.sub(r'Union,\s*Any,\s*Dict\[str,\s*Any\],\s*Optional',
                     'Union, Any, Dict, Optional', content)

    # 修复 "Dict[str], Any" -> "Dict, Any"
    content = re.sub(r'Dict\[str\],\s*Any', 'Dict, Any', content)

    # 修复 "Dict[str], Any, Optional" -> "Dict, Any, Optional"
    content = re.sub(r'Dict\[str\],\s*Any,\s*Optional', 'Dict, Any, Optional', content)

    # 2. 修复类定义中的语法错误
    # 修复 "Optional[type = None" -> "Optional[type] = None"
    content = re.sub(r'Optional\[([^\]]+?)\s*=\s*(\w+)', r'Optional[\1] = \2', content)

    # 修复 "Dict[type] = None" -> "Dict[type] = None"
    content = re.sub(r'Dict\[([^\]]+?)\]\s*=\s*(\w+)', r'Dict[\1] = \2', content)

    # 3. 修复括号匹配问题
    # 修复多余的右括号
    content = re.sub(r'\]\s*=\s*None\s*$', ' = None', content, flags=re.MULTILINE)

    # 修复 ]]
    content = re.sub(r'\]\]', ']', content)

    # 修复 ]] = None
    content = re.sub(r'\]\]\s*=\s*None', '] = None', content)

    # 修复 ]] = None
    content = re.sub(r'\]\]\s*=\s*None', '] = None', content)

    # 4. 修复函数定义中的类型注解
    # 修复 "def func(param: Dict[str, Any = None" -> "def func(param: Dict[str, Any] = None"
    content = re.sub(r'def\s+(\w+)\([^)]*?)\s*:\s*(\w+)',
                     lambda m: m.group(0) if ']=' in m.group(0) else f'def {m.group(1)}({m.group(2)}): {m.group(3)}',
                     content)

    # 5. 修复类型注解中的语法错误
    # 修复 "Type[Any][T]" -> "Type[Any, T]"
    content = re.sub(r'Type\[Any\]\[(\w+)\]', r'Type[Any, \1]', content)

    # 修复 "Dict[str, Any][Type[Any]]" -> "Dict[Type[Any], ServiceDescriptor]"
    content = re.sub(r'Dict\[str,\s*Any\]\[([^\]]+)\]', r'Dict[\1', content)

    # 修复 "Dict[str, Any][Type[Any], Any]" -> "Dict[Type[Any], Any]"
    content = re.sub(r'Dict\[str,\s*Any\]\[([^\]]+?),\s*([^\]]+)\]', r'Dict[\1, \2]', content)

    return content

def fix_file_syntax(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        content = fix_all_syntax_errors(content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False

def main():
    """主函数"""
    src_dir = Path("src")

    fixed_count = 0
    total_count = 0

    # 遍历所有 Python 文件
    for py_file in src_dir.rglob("*.py"):
        total_count += 1
        if fix_file_syntax(py_file):
            fixed_count += 1

    print(f"\n修复完成！")
    print(f"总计检查文件: {total_count}")
    print(f"修复文件数: {fixed_count}")

if __name__ == "__main__":
    main()