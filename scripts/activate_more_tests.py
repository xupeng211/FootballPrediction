#!/usr/bin/env python3
"""批量激活更多被跳过的测试"""

import os
import re
from pathlib import Path

def find_and_fix_skipped_tests():
    """查找并修复被跳过的测试"""
    fixed_files = []

    # 查找包含条件跳过的测试文件
    test_dir = Path('tests/unit')

    for py_file in test_dir.rglob('*.py'):
        if 'test_' in py_file.name:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # 修复常见的跳过模式
            # 1. 模块导入错误类型
            if 'ImportError' in content and 'AVAILABLE' in content:
                # 尝试修复常见的导入问题
                content = re.sub(
                    r'try:\s*\n\s*from (src\.[^:]+).*?\n\s*(\w+_AVAILABLE)\s*=\s*True\n\s*except ImportError.*?\n\s*\1_AVAILABLE\s*=\s*False',
                    lambda m: f'from {m.group(1)}\n{m.group(2)} = True',
                    content,
                    flags=re.DOTALL
                )

            # 2. 移除不必要的 skipif 标记（当模块实际存在时）
            content = re.sub(
                r'@pytest\.mark\.skipif\(not \w+_AVAILABLE, reason=".*module not available"\)\s*\n',
                '',
                content
            )

            # 3. 修复函数名不匹配（常见模式）
            replacements = {
                'validate_email': 'is_valid_email',
                'validate_phone': 'is_valid_phone',
                'validate_url': 'is_valid_url',
                'validate_username': 'is_valid_username',
                'validate_password': 'is_valid_password',
                'validate_credit_card': 'is_valid_credit_card',
                'validate_ipv4_address': 'is_valid_ipv4_address',
                'validate_mac_address': 'is_valid_mac_address',
                'validate_date_string': 'is_valid_date_string',
                'validate_json_string': 'is_valid_json_string',
            }

            for old, new in replacements.items():
                if old in content and new in content:
                    content = content.replace(old, new)

            # 4. 移除条件检查（if function is not None）
            content = re.sub(
                r'if (\w+) is not None:\s*\n\s*(result = .+)',
                r'\2',
                content
            )

            if content != original:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(str(py_file))
                print(f"✅ 修复了: {py_file}")

    return fixed_files

# 重点修复一些高价值的测试文件
priority_files = [
    'tests/unit/utils/test_validators.py',
    'tests/unit/utils/test_formatters.py',
    'tests/unit/utils/test_string_utils.py',
    'tests/unit/utils/test_helpers.py',
    'tests/unit/utils/test_response.py',
    'tests/unit/utils/test_crypto_utils.py',
    'tests/unit/utils/test_file_utils.py',
    'tests/unit/utils/test_time_utils.py',
]

print("🔧 批量修复被跳过的测试...")
fixed = find_and_fix_skipped_tests()

# 额外处理优先文件
print("\n📋 处理优先文件...")
for file_path in priority_files:
    if os.path.exists(file_path):
        print(f"处理: {file_path}")
        # 这里可以添加特定的修复逻辑

print(f"\n✅ 总共修复了 {len(fixed)} 个文件")