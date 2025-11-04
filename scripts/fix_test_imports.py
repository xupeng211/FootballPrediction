#!/usr/bin/env python3
"""
批量修复测试文件导入错误
"""

import os
import re

def fix_adapter_imports(file_path):
    """修复适配器相关测试的导入路径"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 修复导入路径
    content = re.sub(r'from adapters\.base import', 'from base import', content)
    content = re.sub(r'from adapters\.registry import', 'from registry import', content)
    content = re.sub(r'from adapters\.factory import', 'from factory import', content)

    # 修复路径设置
    content = re.sub(
        r'sys\.path\.append\(os\.path\.join\(os\.path\.dirname\(__file__\), [\'"]\.\.\/\.\.\/\.\.\/src[\'"]\)\)',
        'sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src/adapters"))',
        content
    )

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    test_files = [
        "tests/unit/adapters/test_adapter_pattern.py",
        "tests/unit/adapters/test_adapters_basic.py",
    ]

    fixed_count = 0
    for test_file in test_files:
        if os.path.exists(test_file):
            if fix_adapter_imports(test_file):
                fixed_count += 1
                print(f"已修复: {test_file}")

    print(f"修复完成！共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()
