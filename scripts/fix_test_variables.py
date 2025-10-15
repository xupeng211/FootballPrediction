#!/usr/bin/env python3
"""
修复测试文件中的变量名错误
Fix variable name errors in test files
"""

import re
from pathlib import Path

def fix_variable_names():
    """修复变量名错误"""
    test_file = Path("tests/unit/utils/test_dict_utils_comprehensive.py")

    if not test_file.exists():
        print(f"文件不存在: {test_file}")
        return

    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 记录修复数量
    fixes = 0

    # 修复 _data 为 data
    content = re.sub(r'_data\s*=', 'data =', content)
    content = re.sub(r'DictUtils\.get_nested\(data,', 'DictUtils.get_nested(data,', content)
    content = re.sub(r'DictUtils\.set_nested\(data,', 'DictUtils.set_nested(data,', content)
    content = re.sub(r'DictUtils\.flatten\(data\)', 'DictUtils.flatten(data)', content)
    content = re.sub(r'DictUtils\.merge\(([^,]+), ([^)]+)\)', lambda m: f"DictUtils.merge({m.group(1).replace('_data', 'data')}, {m.group(2).replace('_data', 'data')})", content)
    content = re.sub(r'_result\s*=', 'result =', content)
    content = re.sub(r'assert _result ==', 'assert result ==', content)
    content = re.sub(r'_expected\s*=', 'expected =', content)
    content = re.sub(r'assert _result == expected', 'assert result == expected', content)

    # 特殊修复某些模式
    patterns = [
        (r'_data = \{', 'data = {'),
        (r'_dict1 =', 'dict1 ='),
        (r'_dict2 =', 'dict2 ='),
        (r'_dict3 =', 'dict3 ='),
        (r'_keys =', 'keys ='),
        (r'_path =', 'path ='),
        (r'_mapping =', 'mapping ='),
        (r'_result =', 'result ='),
        (r'_expected =', 'expected ='),
        (r'_copy =', 'copy ='),
        (r'_current =', 'current ='),
    ]

    for pattern, replacement in patterns:
        old_content = content
        content = re.sub(pattern, replacement, content)
        if content != old_content:
            fixes += 1

    # 修复特定的错误模式
    # 修复 DictUtils.set_nested({}, "a.b", 1) == {"a": {"b": 1}}
    content = re.sub(
        r'DictUtils\.set_nested\(\{\}, "([^"]+)", ([^)]+)\) == (\{[^}]+\})',
        r'data = {}\n        DictUtils.set_nested(data, "\1", \2)\n        assert data == \3',
        content
    )

    # 修复 data["a"]["b"]["c"] 访问
    content = re.sub(r'data\["([^"]+)"\]', r'data["\1"]', content)

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 修复了测试文件中的变量名错误")

def verify_fixes():
    """验证修复结果"""
    test_file = Path("tests/unit/utils/test_dict_utils_comprehensive.py")

    # 运行一个测试验证
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/unit/utils/test_dict_utils_comprehensive.py::TestDictUtilsComprehensive::test_get_nested_simple", "-q"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ 测试验证通过")
    else:
        print(f"❌ 测试验证失败: {result.stderr[:200]}")

if __name__ == "__main__":
    print("=" * 60)
    print("       修复测试文件变量名错误")
    print("=" * 60)

    fix_variable_names()
    verify_fixes()

    print("=" * 60)