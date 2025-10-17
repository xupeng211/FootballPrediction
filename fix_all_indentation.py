#!/usr/bin/env python3
"""
修复所有测试文件的缩进问题
"""

import os
import re

def fix_file_indentation(file_path):
    """修复文件的缩进问题"""
    print(f"\n正在修复: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复特定模式
    # 1. 修复 api_client.post 相关的缩进
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检查是否需要缩进的行
        if stripped.startswith(('api_client.post.return_value.status_code = 200',
                               'api_client.post.return_value.json.return_value =',
                               'response = api_client.post(',
                               'if api_client.post.return_value.status_code == 201:',
                               'assert api_client.post.return_value.status_code == 201',
                               'upload_duration = performance_metrics.end_timer')):
            # 这些行应该有8个空格的缩进（两级缩进）
            fixed_lines.append('        ' + stripped)
        elif stripped and not line.startswith(' ') and not line.startswith('\t'):
            # 检查前一行是否是函数调用或条件语句
            if i > 0:
                prev_line = lines[i-1].strip()
                if (prev_line.endswith(':') or
                    (prev_line.startswith('response = api_client.post') and
                     not any(x in stripped for x in ['def ', 'class ', '@']))):
                    # 如果上一行以冒号结尾，或者上一行是api_client调用，当前行需要缩进
                    if not stripped.startswith(('#', '"""', "'''")):
                        fixed_lines.append('    ' + stripped)
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
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
    # 需要修复的文件列表
    files_to_fix = [
        "tests/e2e/api/test_user_prediction_flow.py",
        "tests/e2e/performance/test_load_simulation.py",
        "tests/e2e/workflows/test_batch_processing_flow.py",
        "tests/e2e/workflows/test_match_update_flow.py"
    ]

    print("开始修复所有缩进问题...")

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            try:
                fix_file_indentation(file_path)
                print(f"✅ 已修复: {file_path}")
            except Exception as e:
                print(f"❌ 修复失败 {file_path}: {e}")
        else:
            print(f"❌ 文件不存在: {file_path}")

    print("\n所有修复完成！")

if __name__ == "__main__":
    main()