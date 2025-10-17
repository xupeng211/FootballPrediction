#!/usr/bin/env python3
"""
修复剩余的缩进问题
"""

import os
import re

def fix_remaining_issues(file_path):
    """修复剩余的缩进问题"""
    print(f"\n正在修复: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    fixed_lines = []
    in_for_loop = False
    in_if_block = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # 检查特定模式
        if 'for ' in stripped and stripped.endswith(':'):
            fixed_lines.append(line)
            in_for_loop = True
            continue
        elif 'if ' in stripped and stripped.endswith(':'):
            fixed_lines.append(line)
            in_if_block = True
            continue

        # 需要缩进的行
        if (in_for_loop or in_if_block) and not line.startswith('    '):
            # 检查是否是需要缩进的代码行
            if any(pattern in stripped for pattern in [
                'api_client.post.return_value.status_code = 200',
                'api_client.post.return_value.json.return_value =',
                'response = api_client.post(',
                'user_data = {',
                'login_data = {',
                'pred_data = {',
                'headers = {'
            ]):
                fixed_lines.append('    ' + stripped)
                in_for_loop = False
                in_if_block = False
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # 写回文件
    fixed_content = '\n'.join(fixed_lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

def main():
    """主函数"""
    files_to_fix = [
        "tests/e2e/api/test_user_prediction_flow.py",
        "tests/e2e/performance/test_load_simulation.py",
        "tests/e2e/workflows/test_batch_processing_flow.py",
        "tests/e2e/workflows/test_match_update_flow.py"
    ]

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            fix_remaining_issues(file_path)

if __name__ == "__main__":
    main()