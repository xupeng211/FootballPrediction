#!/usr/bin/env python3
"""
修复异常处理问题脚本
Fix exception handling script
"""

import os
import re
import sys

def fix_exception_handling(file_path):
    """修复文件中的异常处理问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复 B904: raise without from inside except
        # 模式: except Exception: raise SomeException("message")
        pattern = r'(\s+)except\s+(\w+)\s*:\s*\n(\s+)raise\s+(\w+)\s*\((.*?)\)\s*$'

        def replace_exception(match):
            indent = match.group(1)
            exception_type = match.group(2)
            raise_indent = match.group(3)
            raise_exception = match.group(4)
            raise_message = match.group(5)

            # 添加 from None 来明确断开异常链
            return f"{indent}except {exception_type}:\n{raise_indent}raise {raise_exception}({raise_message}) from None"

        content = re.sub(pattern, replace_exception, content, flags=re.MULTILINE)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """主函数"""
    # 识别有B904问题的文件
    result = os.popen("ruff check src/ --output-format=concise | grep 'B904' | cut -d: -f1 | sort | uniq").read()

    if not result.strip():
        print("✅ 没有发现B904异常处理问题")
        return

    files_to_fix = [f.strip() for f in result.strip().split('\n') if f.strip()]

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_exception_handling(file_path):
                print(f"✅ 修复异常处理: {file_path}")
                fixed_count += 1

    print(f"\n📊 总计修复了 {fixed_count} 个文件的异常处理问题")

if __name__ == '__main__':
    main()
