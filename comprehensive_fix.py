#!/usr/bin/env python3
"""
全面的语法错误修复工具
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_file_syntax(file_path: Path) -> Tuple[bool, List[str]]:
    """修复单个文件的语法错误"""
    errors = []
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        # 1. 修复最常见的错误模式

        # 1.1 修复类定义中的多余右括号
        content = re.sub(r'^(\s*)class\s+(\w+)\)\s*:', r'\1class \2:', content, flags=re.MULTILINE)

        # 1.2 修复函数定义中的参数类型错误
        # 处理 def func(param): type) -> return_type:
        content = re.sub(
            r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^),]+)\)\s*->\s*([^:]+):',
            r'def \1(\2: \3) -> \4:',
            content
        )

        # 1.3 修复更简单的错误: def func(param): type):
        content = re.sub(
            r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^),]+)\)\s*:',
            r'def \1(\2: \3):',
            content
        )

        # 1.4 修复参数列表中的错误
        # def func(data): dict, fields): list -> def func(data: dict, fields: list)
        content = re.sub(
            r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^),]+?)\),\s*([^),]+?)\)\s*:',
            r'def \1(\2: \3, \4):',
            content
        )

        # 1.5 修复URL断开问题
        url_patterns = [
            (r'postgresql\+asyncpg:\s*//', 'postgresql+asyncpg://'),
            (r'redis:\s*//', 'redis://'),
            (r'http:\s*//', 'http://'),
            (r'https:\s*//', 'https://'),
        ]

        for pattern, replacement in url_patterns:
            content = re.sub(pattern, replacement, content)

        # 1.6 修复断开的字符串字面量
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # 修复未闭合的字符串
            if line.count('"') % 2 == 1 and '"' in line and i + 1 < len(lines):
                # 合并到下一行
                next_line = lines[i + 1].lstrip()
                line = line.rstrip() + ' ' + next_line
                # 跳过下一行
                lines[i + 1] = ''
            
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)

        # 1.7 修复中文字符后的逗号
        content = re.sub(r'，\s*\n\s*', ', ', content)
        content = re.sub(r'，', ', ', content)

        # 写回文件
        if content != original:
            file_path.write_text(content, encoding='utf-8')

            # 验证修复
            try:
                compile(content, str(file_path), 'exec')
                return True, ["修复成功"]
            except SyntaxError as e:
                return False, [f"仍有语法错误: {e.msg} at line {e.lineno}"]

        return True, ["无需修复"]

    except Exception as e:
        return False, [f"修复失败: {str(e)}"]

def main():
    """主函数"""
    src_dir = Path('src')
    
    print("=" * 60)
    print("全面语法错误修复工具")
    print("=" * 60)
    
    # 手动修复几个关键文件
    key_files = [
        'src/utils/dict_utils.py',
        'src/utils/__init__.py',
        'src/utils/string_utils.py',
    ]
    
    print("\n1. 手动修复关键文件...")
    
    # 修复 dict_utils.py
    dict_utils_path = Path('src/utils/dict_utils.py')
    if dict_utils_path.exists():
        content = dict_utils_path.read_text(encoding='utf-8')
        # 修复特定错误
        content = re.sub(r'keys = path\.split\("\."\)\s*\n\s*try: for key in key,\s*\n\s*s:', 
                        'keys = path.split(".")\n        try:\n            for key in keys:', content)
        dict_utils_path.write_text(content, encoding='utf-8')
        print("✓ 修复 dict_utils.py")
    
    # 检查修复效果
    print("\n2. 验证修复效果...")
    test_files = [
        'src/utils/data_validator.py',
        'src/utils/dict_utils.py',
        'src/utils/string_utils.py',
    ]
    
    success_count = 0
    for test_file in test_files:
        path = Path(test_file)
        if path.exists():
            try:
                compile(path.read_text(encoding='utf-8'), str(path), 'exec')
                print(f"✓ {test_file} 语法正确")
                success_count += 1
            except SyntaxError as e:
                print(f"✗ {test_file} 仍有错误: {e.msg[:50]}")
    
    # 尝试运行测试
    if success_count >= 2:
        print("\n3. 尝试运行测试...")
        os.system("python -m pytest tests/unit/utils/test_string_utils.py::test_truncate -v --no-cov 2>&1 | grep -E 'PASSED|FAILED|ERROR'")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
