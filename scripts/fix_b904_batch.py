#!/usr/bin/env python3
"""
B904异常处理批量修复工具
专门处理raise HTTPException在except块中缺少异常链的问题
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def find_b904_files(directory: str = "src") -> List[Tuple[str, List[Tuple[int, str, str]]]]:
    """查找包含B904错误的文件"""
    files_with_b904 = []

    # 遍历目录查找Python文件
    for py_file in Path(directory).rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            b904_errors = []
            in_except_block = False
            except_indent = 0

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # 检测except块开始
                if re.match(r'^(\s*)except', line):
                    in_except_block = True
                    except_indent = len(line) - len(line.lstrip())
                    continue

                # 检测新的代码块（退出except块）
                if in_except_block and line.strip() and len(line) - len(line.lstrip()) <= except_indent:
                    if not line.strip().startswith('#'):
                        in_except_block = False

                # 在except块中查找raise语句
                if in_except_block and re.search(r'raise\s+HTTPException\(', line):
                    b904_errors.append((i, line.rstrip(), py_file))

            if b904_errors:
                files_with_b904.append((str(py_file), b904_errors))

        except Exception as e:
            print(f"⚠️ 处理文件 {py_file} 时出错: {e}")

    return files_with_b904

def fix_b904_in_file(file_path: str, errors: List[Tuple[int, str, str]]) -> bool:
    """修复单个文件中的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        modified = False

        for line_num, original_line, _ in errors:
            # 查找当前行在文件中的索引
            line_index = line_num - 1

            if line_index < len(lines):
                current_line = lines[line_index]

                # 检查是否已经有异常链
                if ' from ' in current_line:
                    print(f"✅ 行 {line_num}: 已经有异常链，跳过")
                    continue

                # 检查是否在except块中并且能获取到异常变量
                exception_var = None
                for i in range(line_index - 1, max(-1, line_index - 10), -1):
                    if i >= 0 and 'except' in lines[i]:
                        match = re.search(r'except\s+.*?\s+as\s+(\w+)', lines[i])
                        if match:
                            exception_var = match.group(1)
                            break

                # 修复raise语句
                if exception_var:
                    # 有异常变量，使用 from exception_var
                    fixed_line = re.sub(
                        r'(\s*raise\s+HTTPException\([^)]+)\)',
                        f'\\1) from {exception_var}',
                        current_line
                    )
                else:
                    # 没有异常变量，使用 from None
                    fixed_line = re.sub(
                        r'(\s*raise\s+HTTPException\([^)]+)\)',
                        f'\\1) from None',
                        current_line
                    )

                if fixed_line != current_line:
                    lines[line_index] = fixed_line
                    modified = True
                    print(f"✅ 修复行 {line_num}: {current_line.strip()} -> {fixed_line.strip()}")

        if modified:
            # 备份原文件
            backup_path = file_path + '.b904_backup'
            with open(file_path, 'r', encoding='utf-8') as original:
                with open(backup_path, 'w', encoding='utf-8') as backup:
                    backup.write(original.read())

            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            print(f"💾 已保存修复后的文件: {file_path}")
            print(f"📁 原文件已备份到: {backup_path}")

        return modified

    except Exception as e:
        print(f"❌ 修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 B904异常处理批量修复工具")
    print("=" * 50)

    # 查找所有B904错误
    print("🔍 查找B904错误...")
    files_with_errors = find_b904_files()

    if not files_with_errors:
        print("✅ 没有发现B904错误")
        return

    total_errors = sum(len(errors) for _, errors in files_with_errors)
    print(f"📊 发现 {len(files_with_errors)} 个文件包含 {total_errors} 个B904错误")
    print()

    # 显示发现的错误
    for file_path, errors in files_with_errors:
        print(f"📄 {file_path}: {len(errors)} 个错误")
        for line_num, line, _ in errors[:3]:  # 只显示前3个
            print(f"  行 {line_num}: {line.strip()}")
        if len(errors) > 3:
            print(f"  ... 还有 {len(errors) - 3} 个错误")
        print()

    # 自动修复（不需要用户确认）
    print("🚀 自动开始修复B904错误...")

    # 执行修复
    print("\n🔧 开始修复...")
    fixed_files = 0
    total_fixed_errors = 0

    for file_path, errors in files_with_errors:
        print(f"\n📝 处理文件: {file_path}")
        if fix_b904_in_file(file_path, errors):
            fixed_files += 1
            total_fixed_errors += len(errors)

    print(f"\n🎉 修复完成!")
    print(f"📊 修复了 {fixed_files} 个文件中的 {total_fixed_errors} 个B904错误")

    # 验证修复效果
    print("\n🔍 验证修复效果...")
    remaining_errors = find_b904_files()
    remaining_count = sum(len(errors) for _, errors in remaining_errors)

    if remaining_count == 0:
        print("✅ 所有B904错误已成功修复!")
    else:
        print(f"⚠️ 还有 {remaining_count} 个B904错误需要手动处理")

if __name__ == "__main__":
    main()