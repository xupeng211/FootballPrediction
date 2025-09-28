#!/usr/bin/env python3
"""
批量修复integration test文件中的缩进问题
"""
import re

def fix_indentation_issues():
    """修复缩进问题"""
    files_to_fix = [
        'tests/integration/api/test_api_features.py',
        'tests/integration/api/test_features.py',
        'tests/integration/api/test_health.py',
        'tests/integration/database/test_database_performance_optimization.py',
        'tests/integration/features/test_feature_store.py'
    ]

    for file_path in files_to_fix:
        print(f"Fixing {file_path}...")

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        for i, line in enumerate(lines):
            # 检查是否是需要修复的assert语句
            if line.strip().startswith('assert ') and not line.startswith('        '):
                # 检查前一行是否是with语句或函数调用
                if i > 0 and (
                    'response = ' in lines[i-1] or
                    'with ' in lines[i-1] or
                    'await ' in lines[i-1]
                ):
                    # 需要增加缩进
                    fixed_line = '    ' + line
                    print(f"  Fixed line {i+1}: {line.strip()}")
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_indentation_issues()