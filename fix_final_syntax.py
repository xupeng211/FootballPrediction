#!/usr/bin/env python3
"""
最终修复E2E测试文件的语法错误
"""

import os

def fix_file_manually(file_path):
    """手动修复文件的语法错误"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复for循环后缺少缩进的问题
    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 处理for循环
        if stripped.startswith('for ') and stripped.endswith(':'):
            # 添加for循环行
            fixed_lines.append(line)
            i += 1

            # 找到下一个非空行
            while i < len(lines) and lines[i].strip() == '':
                fixed_lines.append(lines[i])
                i += 1

            # 处理for循环体
            if i < len(lines):
                next_line = lines[i]
                if next_line and not next_line.startswith('    '):
                    # 需要缩进的行
                    if any(pattern in next_line for pattern in [
                        'api_client.post.return_value.status_code = 200',
                        'api_client.post.return_value.json.return_value =',
                        'response = api_client.post(',
                        'user_data = {',
                        'login_data = {',
                        'pred_data = {',
                        'match_data = {',
                    ]):
                        # 添加8个空格缩进
                        fixed_lines.append('        ' + next_line.strip())
                        i += 1
                    else:
                        # 保持原样
                        fixed_lines.append(next_line)
                        i += 1
                else:
                    # 已经有缩进
                    fixed_lines.append(next_line)
                    i += 1
        else:
            fixed_lines.append(line)
            i += 1

    # 写回文件
    fixed_content = '\n'.join(fixed_lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

def add_pass_to_empty_blocks(file_path):
    """为空的代码块添加pass语句"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检查是否是空代码块
        if line.strip().endswith(':'):
            fixed_lines.append(line)
            i += 1

            # 检查下一行是否是空的或只有注释
            if i < len(lines):
                next_line = lines[i]
                if not next_line.strip() or next_line.strip().startswith('#'):
                    # 需要添加pass
                    # 计算缩进
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * (indent + 4) + 'pass')

        fixed_lines.append(line)
        i += 1

    # 避免重复
    final_lines = []
    prev_line = ''
    for line in fixed_lines:
        if line != prev_line:
            final_lines.append(line)
        prev_line = line

    # 写回文件
    fixed_content = '\n'.join(final_lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

def main():
    """主函数"""
    # 修复具体的语法错误
    fixes = [
        {
            'file': 'tests/e2e/api/test_user_prediction_flow.py',
            'line': 229,
            'fix': '        api_client.post.return_value.status_code = 200'
        },
        {
            'file': 'tests/e2e/performance/test_load_simulation.py',
            'line': 55,
            'fix': '            api_client.post.return_value.status_code = 200'
        }
    ]

    for fix in fixes:
        if os.path.exists(fix['file']):
            with open(fix['file'], 'r') as f:
                lines = f.readlines()

            # 修复特定行
            line_idx = fix['line'] - 1
            if line_idx < len(lines):
                lines[line_idx] = fix['fix'] + '\n'

            with open(fix['file'], 'w') as f:
                f.writelines(lines)

            print(f"✅ 修复了 {fix['file']} 第 {fix['line']} 行")

    # 处理缩进问题
    problem_files = [
        'tests/e2e/workflows/test_batch_processing_flow.py',
        'tests/e2e/workflows/test_match_update_flow.py'
    ]

    for file_path in problem_files:
        if os.path.exists(file_path):
            fix_file_manually(file_path)
            print(f"✅ 修复了缩进: {file_path}")

if __name__ == "__main__":
    main()