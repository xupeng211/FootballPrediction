#!/usr/bin/env python3
"""修复所有缩进问题"""

# 读取文件
with open('tests/unit/utils/test_validators_parametrized.py', 'r') as f:
    lines = f.readlines()

# 修复缩进
fixed_lines = []
for line in lines:
    # 修复 assert 前的缩进
    if line.strip().startswith('assert ') and not line.startswith('        '):
        # 检查前一行是否是 result =
        if fixed_lines and fixed_lines[-1].strip().startswith('result ='):
            fixed_lines.append('    ' + line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# 写回文件
with open('tests/unit/utils/test_validators_parametrized.py', 'w') as f:
    f.writelines(fixed_lines)

print("✅ 修复了所有缩进问题")