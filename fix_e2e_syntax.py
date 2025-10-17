#!/usr/bin/env python3
"""
修复E2E测试文件中的语法错误
"""

import os
import re

def fix_for_loop_indentation(file_path):
    """修复for循环后的缩进问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检查是否是for循环行
        if re.match(r'^(\s*)for\s+\w+\s+in\s+.+:', line):
            # 保留for循环行
            result.append(line)
            i += 1

            # 处理for循环体内的行
            while i < len(lines):
                next_line = lines[i]

                # 如果是空行或注释，保留并继续
                if not next_line.strip() or next_line.strip().startswith('#'):
                    result.append(next_line)
                    i += 1
                    continue

                # 如果下一行没有缩进，且是需要缩进的代码
                if not next_line.startswith('    ') and not next_line.startswith('\t'):
                    stripped = next_line.strip()

                    # 这些模式需要缩进
                    if any(pattern in stripped for pattern in [
                        'api_client.post.return_value.status_code = 200',
                        'api_client.post.return_value.json.return_value =',
                        'response = api_client.post(',
                        'user_data = {',
                        'login_data = {',
                        'pred_data = {',
                        'headers = {',
                        'if api_client.post.return_value.status_code == 201:',
                        'assert api_client.post.return_value.status_code == 201',
                        'created_matches.append(',
                        'predictions.append(',
                        'users.append(',
                        'user_tokens.append(',
                        'upload_duration = performance_metrics.end_timer'
                    ]):
                        # 添加8个空格的缩进
                        result.append('        ' + stripped)
                        i += 1
                    else:
                        # 遇到不需要缩进的行，退出for循环处理
                        result.append(next_line)
                        break
                else:
                    # 已经有缩进的行，保留
                    result.append(next_line)
                    i += 1
        else:
            result.append(line)
            i += 1

    # 写回文件
    fixed_content = '\n'.join(result)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

def add_async_decorator(file_path):
    """添加async装饰器到需要的测试函数"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找包含await但没有async装饰器的函数
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 如果是测试函数定义
        if 'def test_' in line and 'async def' not in line:
            # 检查函数体是否包含await
            result.append(line)
            i += 1

            # 收集函数体
            function_body = []
            indent_level = None
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip() == '':
                    function_body.append(next_line)
                    i += 1
                    continue

                # 计算缩进级别
                current_indent = len(next_line) - len(next_line.lstrip())
                if indent_level is None and current_indent > 0:
                    indent_level = current_indent

                # 如果回到同级或更少缩进，函数结束
                if indent_level is not None and current_indent < indent_level:
                    break

                function_body.append(next_line)

                # 检查是否包含await
                if 'await ' in next_line:
                    # 需要在函数定义前添加装饰器
                    # 找到函数定义的索引
                    for j in range(len(result)-1, -1, -1):
                        if 'def test_' in result[j]:
                            # 在函数定义前插入装饰器
                            result.insert(j, '    @pytest.mark.asyncio')
                            break

                i += 1

            # 添加函数体
            result.extend(function_body)
        else:
            result.append(line)
            i += 1

    # 写回文件
    fixed_content = '\n'.join(result)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

def main():
    """主函数"""
    files_to_fix = [
        {
            'path': 'tests/e2e/api/test_user_prediction_flow.py',
            'fix_func': fix_for_loop_indentation
        },
        {
            'path': 'tests/e2e/performance/test_load_simulation.py',
            'fix_func': fix_for_loop_indentation
        },
        {
            'path': 'tests/e2e/test_prediction_workflow.py',
            'fix_func': add_async_decorator
        },
        {
            'path': 'tests/e2e/workflows/test_batch_processing_flow.py',
            'fix_func': fix_for_loop_indentation
        },
        {
            'path': 'tests/e2e/workflows/test_match_update_flow.py',
            'fix_func': fix_for_loop_indentation
        }
    ]

    for file_info in files_to_fix:
        file_path = file_info['path']
        fix_func = file_info['fix_func']

        if os.path.exists(file_path):
            print(f"\n正在修复: {file_path}")
            try:
                fix_func(file_path)
                print(f"✅ 修复完成: {file_path}")

                # 验证语法
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                print(f"✅ 语法验证通过: {file_path}")
            except SyntaxError as e:
                print(f"❌ 语法错误仍在: {file_path} - {e}")
            except Exception as e:
                print(f"❌ 修复失败: {file_path} - {e}")
        else:
            print(f"❌ 文件不存在: {file_path}")

if __name__ == "__main__":
    main()