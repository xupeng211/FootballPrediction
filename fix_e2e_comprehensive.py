#!/usr/bin/env python3
"""
全面修复E2E测试文件的语法错误
"""

import os
import re
from pathlib import Path

def fix_for_loops(file_path):
    """修复for循环缩进问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    result = []

    for i, line in enumerate(lines):
        # 处理for循环后的缩进
        if re.match(r'^(\s*)for\s+\w+\s+in\s+.+:', line):
            # 保留for行
            result.append(line)
        else:
            # 检查是否是for循环后需要缩进的行
            if i > 0 and re.match(r'^\s*(api_client\.post\.|response\s*=\s*api_client\.|user_data\s*=|login_data\s*=|pred_data\s*=|match_data\s*=|if\s+api_client\.post\.|assert\s+api_client\.|created_matches\.|predictions\.|users\.|user_tokens\.|upload_duration\s*=)', line):
                # 如果这行没有缩进，给它添加适当的缩进
                if not line.startswith('    ') and not line.startswith('\t'):
                    result.append('    ' + line.strip())
                else:
                    result.append(line)
            else:
                result.append(line)

    return '\n'.join(result)

def fix_async_await(file_path):
    """修复async/await问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找包含await但缺少async装饰器的函数
    if 'await ' in content:
        # 在每个包含await的测试函数前添加async装饰器
        lines = content.split('\n')
        result = []

        for i, line in enumerate(lines):
            result.append(line)
            # 如果是测试函数定义
            if 'def test_' in line and 'async def' not in line:
                # 检查函数体是否包含await
                j = i + 1
                in_function = True
                while j < len(lines) and in_function:
                    if 'await ' in lines[j]:
                        # 在函数定义前插入async装饰器
                        result.insert(i, '    @pytest.mark.asyncio')
                        break
                    if lines[j] and not lines[j].startswith('    ') and lines[j].strip() != '':
                        in_function = False
                    j += 1

        return '\n'.join(result)

    return content

def main():
    """主修复函数"""
    e2e_files = [
        'tests/e2e/api/test_user_prediction_flow.py',
        'tests/e2e/performance/test_load_simulation.py',
        'tests/e2e/test_prediction_workflow.py',
        'tests/e2e/workflows/test_batch_processing_flow.py',
        'tests/e2e/workflows/test_match_update_flow.py'
    ]

    for file_path in e2e_files:
        if os.path.exists(file_path):
            print(f"\n修复文件: {file_path}")

            # 读取原始内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original = f.read()

            # 应用修复
            fixed = fix_for_loops(file_path)
            fixed = fix_async_await(file_path)

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed)

            # 验证语法
            try:
                compile(fixed, file_path, 'exec')
                print(f"✅ 语法修复成功: {file_path}")
            except SyntaxError as e:
                print(f"❌ 仍有语法错误: {file_path} - {e}")
                # 回滚
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original)

if __name__ == "__main__":
    main()