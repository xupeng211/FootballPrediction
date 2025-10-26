#!/usr/bin/env python3
"""
修复Issue #83-C测试文件的导入问题
"""

import os
import re

def fix_imports_in_file(filepath):
    """修复单个文件的导入问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复Mock策略库的导入路径
        # 将: from issue83c_practical_mocks import ...
        # 改为: from scripts.issue83c_practical_mocks import ...

        # 使用正则表达式替换导入语句
        patterns = [
            (r'from issue83c_practical_mocks import', 'from scripts.issue83c_practical_mocks import'),
            (r'import issue83c_practical_mocks', 'import sys; sys.path.append("scripts"); import issue83c_practical_mocks'),
        ]

        fixed_content = content
        for pattern, replacement in patterns:
            fixed_content = re.sub(pattern, replacement, fixed_content)

        # 添加更安全的导入处理
        if 'MOCKS_AVAILABLE = False' in fixed_content:
            # 在文件开头添加路径处理
            lines = fixed_content.split('\n')
            new_lines = []

            for i, line in enumerate(lines):
                new_lines.append(line)

                # 在import sys之后添加路径
                if line.strip() == 'import sys':
                    new_lines.append('sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))')
                    new_lines.append('sys.path.insert(0, os.path.dirname(__file__))')

            fixed_content = '\n'.join(new_lines)

        # 添加os导入如果不存在
        if 'import os' not in fixed_content and 'import sys' in fixed_content:
            lines = fixed_content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == 'import sys':
                    lines.insert(i, 'import os')
                    break
            fixed_content = '\n'.join(lines)

        # 写回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        return True
    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 需要修复的Issue #83-C测试文件
    issue83c_files = [
        'tests/unit/core/config_test_issue83c.py',
        'tests/unit/core/di_test_issue83c.py',
        'tests/unit/core/logging_test_issue83c.py',
        'tests/unit/api/data_router_test_issue83c.py',
        'tests/unit/api/cqrs_test_issue83c.py',
        'tests/unit/database/config_test_issue83c.py',
        'tests/unit/database/definitions_test_issue83c.py',
        'tests/unit/database/dependencies_test_issue83c.py',
        'tests/unit/cqrs/base_test_issue83c.py',
        'tests/unit/cqrs/application_test_issue83c.py'
    ]

    print("🔧 修复Issue #83-C测试文件导入问题...")

    fixed_count = 0
    for filepath in issue83c_files:
        if os.path.exists(filepath):
            print(f"  修复: {os.path.relpath(filepath, 'tests')}")
            if fix_imports_in_file(filepath):
                print("  ✅ 修复成功")
                fixed_count += 1
            else:
                print("  ❌ 修复失败")
        else:
            print(f"  ⚠️ 文件不存在: {filepath}")

    print(f"\n📊 修复总结: {fixed_count}/{len(issue83c_files)} 个文件已修复")

if __name__ == "__main__":
    main()