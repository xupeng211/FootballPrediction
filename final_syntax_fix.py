#!/usr/bin/env python3
"""
最终语法修复脚本 - 使用正则表达式精确修复缩进
"""

import os
import re

def fix_file_completely(file_path):
    """完全修复文件的缩进问题"""
    print(f"\n修复文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则表达式修复
    # 模式1: for 循环后的代码块
    content = re.sub(
        r'(\s+for .+:\n)((?:api_client\.post\.|response\s*=|user_data\s*=|login_data\s*=|pred_data\s*=|if\s+api_client\.post\.|assert\s+api_client\.post\.|\s+created_matches\.append|\s+predictions\.append|\s+users\.append|\s+user_tokens\.append).*)',
        lambda m: m.group(1) + re.sub(r'^(?!\s)', '    ', m.group(2), flags=re.MULTILINE),
        content,
        flags=re.MULTILINE
    )

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 验证语法
    try:
        compile(content, file_path, 'exec')
        print(f"✅ 语法修复成功: {file_path}")
        return True
    except SyntaxError as e:
        print(f"❌ 仍有语法错误: {file_path} - {e}")
        return False

def manual_fix():
    """手动修复最顽固的问题"""
    files = [
        "tests/e2e/api/test_user_prediction_flow.py",
        "tests/e2e/performance/test_load_simulation.py",
        "tests/e2e/workflows/test_batch_processing_flow.py",
        "tests/e2e/workflows/test_match_update_flow.py"
    ]

    for file_path in files:
        if not os.path.exists(file_path):
            continue

        print(f"\n手动修复: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                i += 1
                continue

            # 检查 for 循环
            if 'for ' in stripped and ' in ' in stripped and stripped.endswith(':'):
                # 这是 for 循环行，添加后缩进后续行
                fixed_lines.append(line)
                i += 1
                # 添加缩进直到遇到空行或相同/更少缩进的行
                while i < len(lines):
                    next_line = lines[i]
                    if next_line.strip() == '':
                        fixed_lines.append(next_line)
                        i += 1
                        continue
                    if not next_line.startswith('    ') and not next_line.startswith('\t'):
                        if any(kw in next_line.strip() for kw in ['def ', 'class ', '@', 'if ', 'elif ', 'else:', 'except', 'finally:']):
                            break
                    # 如果下一行没有缩进，添加缩进
                    if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                        if any(pattern in next_line.strip() for pattern in [
                            'api_client.post.return_value.status_code = 200',
                            'api_client.post.return_value.json.return_value =',
                            'response = api_client.post(',
                            'user_data = {',
                            'login_data = {',
                            'pred_data = {',
                            'headers = {',
                            'if api_client.post.return_value.status_code',
                            'assert api_client.post.return_value.status_code',
                            'upload_duration = performance_metrics.end_timer'
                        ]):
                            fixed_lines.append('    ' + next_line.strip() + '\n')
                            i += 1
                        else:
                            break
                    else:
                        fixed_lines.append(next_line)
                        i += 1
            else:
                fixed_lines.append(line)
                i += 1

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        # 验证语法
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, file_path, 'exec')
            print(f"✅ 语法修复成功: {file_path}")
        except SyntaxError as e:
            print(f"❌ 仍有语法错误: {file_path} - {e}")

def main():
    """主函数"""
    print("开始最终语法修复...")

    # 先尝试自动修复
    files = [
        "tests/e2e/api/test_user_prediction_flow.py",
        "tests/e2e/performance/test_load_simulation.py",
        "tests/e2e/workflows/test_batch_processing_flow.py",
        "tests/e2e/workflows/test_match_update_flow.py"
    ]

    success_count = 0
    for file_path in files:
        if os.path.exists(file_path):
            if fix_file_completely(file_path):
                success_count += 1

    if success_count < len(files):
        print("\n尝试手动修复顽固问题...")
        manual_fix()

    print("\n修复完成！")

if __name__ == "__main__":
    main()