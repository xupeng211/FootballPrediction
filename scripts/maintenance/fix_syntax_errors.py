#!/usr/bin/env python3
"""
批量修复测试文件语法错误脚本
Batch Fix Script for Test File Syntax Errors
"""

import os
from pathlib import Path

def fix_future_import_order(file_path):
    """修复__future__ import顺序问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有__future__ import在后面
        if 'from __future__ import annotations' in content:
            lines = content.split('\n')
            future_import_line = None
            other_imports = []

            for i, line in enumerate(lines):
                if 'from __future__ import' in line and not future_import_line:
                    future_import_line = i
                elif line.strip().startswith(('import', 'from')) and i > 0:
                    other_imports.append(i)

            # 如果__future__ import不在第一行，需要移动
            if future_import_line and future_import_line > 0:
                # 提取__future__ import行
                future_line = lines[future_import_line].strip()

                # 删除原位置的future import
                lines.pop(future_import_line)

                # 重新组织import部分
                future_imports = [future_line]
                other_import_lines = [lines[i] for i in other_imports if lines[i].strip().startswith(('import', 'from'))]

                # 组合新的import部分
                new_import_section = future_imports + other_import_lines

                # 重建文件内容
                before_imports = lines[:future_import_line]
                after_imports = lines[future_import_line + len(other_import_lines):]

                new_content = '\n'.join(before_imports + new_import_section + after_imports)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                return True, "修复__future__ import顺序"

    except Exception as e:
        return False, f"修复失败: {e}"

def check_and_fix_file(file_path):
    """检查并修复单个文件"""
    print(f"检查: {file_path}")

    # 1. 修复__future__ import顺序
    fixed1, msg1 = fix_future_import_order(file_path)
    if fixed1:
        print(f"  ✅ {msg1}")

    # 2. 验证语法
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        print("  ✅ 语法验证通过")
        return True
    except SyntaxError as e:
        print(f"  ❌ 仍有语法错误: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始批量修复测试文件语法错误...")

    # 查找需要修复的测试文件
    test_dir = Path("tests/unit")
    files_to_fix = []

    for pattern in ["test_*.py"]:
        files_to_fix.extend(test_dir.glob(pattern))

    print(f"找到 {len(files_to_fix)} 个测试文件需要检查")

    fixed_count = 0
    failed_count = 0

    # 修复前15个文件
    for i, file_path in enumerate(files_to_fix[:15]):
        print(f"\n[{i+1}/15] 处理: {file_path.name}")

        if check_and_fix_file(file_path):
            fixed_count += 1
        else:
            failed_count += 1

    print("\n📊 修复结果:")
    print(f"- 成功修复: {fixed_count}个文件")
    print(f"- 仍有问题: {failed_count}个文件")
    print(f"- 修复成功率: {fixed_count/(fixed_count+failed_count)*100:.1f}%")

    print("\n🎯 继续运行更多文件！")
    return 0 if fixed_count > failed_count else 1

if __name__ == "__main__":
    exit(main())
