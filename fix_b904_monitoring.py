#!/usr/bin/env python3
"""
修复monitoring模块中的B904异常处理错误
按照最佳实践添加 from e 语句
"""

import re
import os

def fix_b904_in_file(file_path):
    """修复单个文件中的B904错误"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 使用正则表达式匹配需要修复的异常处理模式
    # 匹配: except Exception as e: 后面跟着 raise HTTPException(...)
    pattern = r'(\s+)(except Exception as e:\s*\n\s+logger\.error\(f"[^"]*{e}"\)\s*\n\s+)(raise HTTPException\([^)]+\))\s*$'

    def replacement_func(match):
        indent1, except_block, raise_statement = match.groups()
        # 检查raise语句是否已经有from
        if ' from ' not in raise_statement:
            return f"{indent1}{except_block}{raise_statement} from e"
        return match.group(0)

    # 应用替换
    content = re.sub(pattern, replacement_func, content, flags=re.MULTILINE)

    # 如果内容有变化，写回文件
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    return False

def main():
    """主函数"""

    # 需要修复的文件
    files_to_fix = [
        'src/monitoring/alert_routes.py',
        'src/monitoring/log_routes.py'
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"正在修复: {file_path}")
            if fix_b904_in_file(file_path):
                print(f"  ✓ 已修复: {file_path}")
                fixed_count += 1
            else:
                print(f"  - 无需修复或修复失败: {file_path}")
        else:
            print(f"  ✗ 文件不存在: {file_path}")

    print(f"\n总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()