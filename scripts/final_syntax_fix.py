#!/usr/bin/env python3
"""
最终语法错误修复
"""

import ast
import re
from pathlib import Path

def check_syntax(file_path):
    """检查文件语法并返回错误信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return None
    except SyntaxError as e:
        return e
    except Exception as e:
        return Exception(f"其他错误: {e}")

def fix_performance_py():
    """修复performance.py"""
    file_path = "src/api/performance.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 检查第68行附近的问题
    for i, line in enumerate(lines[65:75], start=66):
        if 'f"' in line and not line.strip().endswith('"'):
            # 找到未终止的f-string
            lines[i-1] = line.rstrip() + '"\n'
            print(f"修复了第{i}行: {line.strip()}")
            break

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def fix_facades_py():
    """修复facades.py"""
    file_path = "src/api/facades.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复第188-189行的问题
    content = re.sub(
        r'strategies: Optional\[List\[str\]\] = None\)',
        'strategies: Optional[List[str]] = None',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """主函数"""

    files_to_fix = [
        ("src/api/performance.py", fix_performance_py),
        ("src/api/facades.py", fix_facades_py)
    ]

    print("最终语法错误修复...")

    for file_path, fix_func in files_to_fix:
        print(f"\n修复 {file_path}")
        error = check_syntax(file_path)
        if error:
            print(f"  发现错误: {error}")
            fix_func()
            # 再次检查
            error = check_syntax(file_path)
            if error:
                print(f"  ❌ 仍有错误: {error}")
            else:
                print(f"  ✅ 修复成功")
        else:
            print(f"  ✅ 无需修复")

    # 最终验证
    print("\n最终验证:")
    all_good = True
    for file_path, _ in files_to_fix:
        error = check_syntax(file_path)
        if error:
            print(f"❌ {file_path}: {error}")
            all_good = False
        else:
            print(f"✅ {file_path}: 语法正确")

    if all_good:
        print("\n🎉 所有语法错误已修复！")
    else:
        print("\n⚠️ 仍有语法错误需要手动修复")

if __name__ == "__main__":
    main()
