#!/usr/bin/env python3
"""
修复测试文件中的语法错误
"""

import os
import ast
from pathlib import Path

# 需要修复的文件列表
problem_files = [
    "tests/e2e/api/test_user_prediction_flow.py",
    "tests/e2e/performance/test_load_simulation.py",
    "tests/e2e/test_prediction_workflow.py",
    "tests/e2e/workflows/test_batch_processing_flow.py",
    "tests/e2e/workflows/test_match_update_flow.py"
]

def fix_file_syntax(file_path):
    """修复单个文件的语法错误"""
    print(f"\n修复文件: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复已知的语法问题
        lines = content.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 处理 test_user_prediction_flow.py 的缩进问题
            if file_path == "tests/e2e/api/test_user_prediction_flow.py":
                if i == 33:  # api_client.post.return_value.status_code = 200
                    fixed_lines.append("        api_client.post.return_value.status_code = 200")
                    i += 1
                    continue
                elif i == 34:  # api_client.post.return_value.json.return_value = {"id": 1, "status": "success"}
                    fixed_lines.append("        api_client.post.return_value.json.return_value = {\"id\": 1, \"status\": \"success\"}")
                    i += 1
                    continue
                elif i == 35:  # response = api_client.post("/api/v1/auth/register", json=user_data)
                    fixed_lines.append("        response = api_client.post(\"/api/v1/auth/register\", json=user_data)")
                    i += 1
                    continue

            # 处理其他文件的常见缩进问题
            stripped = line.lstrip()
            if line and not line.startswith(' ') and not line.startswith('\t'):
                # 行首没有缩进，可能是错误
                if stripped.startswith(('assert ', 'if ', 'return ', 'upload_', 'result =')):
                    # 这些行通常应该有缩进
                    if any('def ' in prev_line for prev_line in lines[max(0, i-5):i]):
                        fixed_lines.append('    ' + line)
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

            i += 1

        # 写回文件
        fixed_content = '\n'.join(fixed_lines)

        # 验证语法是否正确
        try:
            ast.parse(fixed_content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ 语法错误已修复: {file_path}")
            return True
        except SyntaxError as e:
            print(f"❌ 仍存在语法错误在 {file_path}: {e}")
            # 尝试更具体的修复

            # 修复 test_prediction_workflow.py 的 await 问题
            if "await" in str(e):
                content = fixed_content
                # 确保包含await的函数是async的
                if 'async def' not in content and 'await' in content:
                    # 添加pytest.mark.asyncio装饰器
                    content = content.replace(
                        'def test_',
                        '@pytest.mark.asyncio\n    async def test_'
                    )
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ 已添加async装饰器: {file_path}")
                    return True

            return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("开始修复测试文件的语法错误...")

    fixed_count = 0
    total_count = len(problem_files)

    for file_path in problem_files:
        if os.path.exists(file_path):
            if fix_file_syntax(file_path):
                fixed_count += 1
        else:
            print(f"❌ 文件不存在: {file_path}")

    print(f"\n修复完成: {fixed_count}/{total_count} 个文件已修复")

    # 验证修复结果
    print("\n验证修复结果...")
    for file_path in problem_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
                print(f"✅ {file_path} - 语法正确")
            except SyntaxError as e:
                print(f"❌ {file_path} - 仍有错误: {e}")

if __name__ == "__main__":
    main()