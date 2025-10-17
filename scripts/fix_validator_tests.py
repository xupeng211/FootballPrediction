#!/usr/bin/env python3
"""批量修复validators测试"""

import os
import re

def fix_test_file(filepath):
    """修复测试文件中的条件检查"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除所有的条件检查
    patterns = [
        (r'if is_valid_\w+ is not None:\s*\n\s*(result = .*)', r'\1'),
        (r'if \w+ is not None:\s*\n\s*(result = .*)', r'\1'),
        (r'if is_valid_\w+ is not None:\s*\n\s*(.*)', r'\1'),
        (r'if \w+ is not None:\s*\n\s*(.*)', r'\1'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # 移除剩余的条件块
    content = re.sub(r'if \w+ is not None:\s*\n.*?assert.*?\n', '', content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 修复了 {filepath}")

# 修复所有validators测试文件
test_files = [
    'tests/unit/utils/test_validators_parametrized.py',
    'tests/unit/utils/test_validators.py'
]

for file in test_files:
    if os.path.exists(file):
        fix_test_file(file)

print("\n🎉 所有validators测试已修复！")