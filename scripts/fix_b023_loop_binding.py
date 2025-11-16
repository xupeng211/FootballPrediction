#!/usr/bin/env python3
"""
B023循环绑定错误修复工具
修复函数定义中的循环变量绑定问题
"""

import os
import re
from pathlib import Path

def fix_b023_errors():
    """修复B023循环绑定错误"""
    print("🔄 开始修复B023循环绑定错误...")

    # 文件和修复模式
    file_fixes = {
        'tests/performance/test_load.py': [
            # 修复异步函数中的循环变量绑定
            (r'(\s+)async def simulate_query\(\):\s*start_time = time\.time\(\s*\n\s+await asyncio\.sleep\(expected_delay / 1000\)\s*# Simulate delay\s*\n\s+await mock_db\.fetch\(query\)',
             r'\1async def simulate_query():\n\1    start_time = time.time()\n\1    # 使用捕获的变量\n\1    await asyncio.sleep(expected_delay / 1000)  # Simulate delay\n\1    await mock_db.fetch(query)'),
            # 修复循环变量的捕获
            (r'for expected_delay, query in queries:\s*\n\s*async def simulate_query\(\)',
             r'for expected_delay, query in queries:\n\1    # 创建闭包以捕获循环变量\n\1    async def create_simulator(expected_delay, query):\n\1        async def simulate_query():\n\1            start_time = time.time()\n\1            await asyncio.sleep(expected_delay / 1000)\n\1            await mock_db.fetch(query)\n\1            end_time = time.time()\n\1            return (end_time - start_time) * 1000\n\1        return simulate_query\n\1\n\1    # 创建模拟器列表\n\1    simulators = [create_simulator(exp_delay, q) for exp_delay, q in queries]'),
        ],
        'tests/unit/utils/test_warning_filters_error_path.py': [
            # 修复循环变量在异常处理中的绑定
            (r'(\s+)def failing_filterwarnings\(\*args, \*\*kwargs\):\s*\n\s+raise exc_type\(f"\{exc_type\.__name__\}测试异常"\)',
             r'\1def failing_filterwarnings(*args, **kwargs):\n\1    # 闭包捕获异常类型\n\1    def inner_function():\n\1        raise exc_type(f"{exc_type.__name__}测试异常")\n\1    return inner_function'),
        ],
        'tests/unit/utils/test_warning_filters_final_coverage.py': [
            # 修复循环变量在日志捕获中的绑定
            (r'(\s+)def capture_log\(message\):\s*\n\s+logged_messages\.append\(message\)',
             r'\1def capture_log(message):\n\1    # 使用非局部变量捕获\n\1    nonlocal logged_messages\n\1    logged_messages.append(message)'),
        ],
    }

    total_fixes = 0

    for file_path, patterns in file_fixes.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                file_fixes_count = 0

                for pattern, replacement in patterns:
                    new_content = re.subn(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
                    if new_content != content:
                        content = new_content
                        file_fixes_count += 1

                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    total_fixes += file_fixes_count
                    print(f"  ✅ 修复文件: {file_path} ({file_fixes_count}处修改)")
                else:
                    print(f"  ⚠️  文件无需修改: {file_path}")

            except Exception as e:
                print(f"  ❌ 修复文件失败: {file_path} - {e}")
        else:
            print(f"  ⚠️  文件不存在: {file_path}")

    print(f"\n🎉 B023循环绑定错误修复完成！总计修复 {total_fixes} 个文件")
    return total_fixes

if __name__ == "__main__":
    fix_b023_errors()
