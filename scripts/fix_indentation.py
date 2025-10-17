#!/usr/bin/env python3
"""修复缩进问题"""

import re

# 读取文件
with open('tests/unit/utils/test_validators_parametrized.py', 'r') as f:
    content = f.read()

# 修复所有缩进问题
content = re.sub(r'^(\s+)result = (.*)\n(\s+)assert result == expected', r'\1result = \2\n\1assert result == expected', content, flags=re.MULTILINE)

# 写回文件
with open('tests/unit/utils/test_validators_parametrized.py', 'w') as f:
    f.write(content)

print("✅ 修复了缩进问题")