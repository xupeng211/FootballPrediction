#!/usr/bin/env python3
"""
快速B904批量修复工具
Quick B904 Batch Fix Tool

快速修复HTTPException异常处理中的B904问题
"""

import re
import sys
from pathlib import Path


def fix_b904_in_file(file_path: str) -> int:
    """修复单个文件中的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")
        return 0

    # 使用正则表达式匹配HTTPException raise语句
    # 匹配模式：raise HTTPException(...) 后面跟着换行，在except块中
    pattern = r'(\s+raise HTTPException\([^)]+\)\s*\n'

    # 检查这些raise语句是否在except块中
    lines = content.split('\n')
    fixed_count = 0

    for i, line in enumerate(lines):
        if 'raise HTTPException(' in line:
            # 检查是否在except块中（向上查找）
            in_except_block = False
            for j in range(max(0, i-20), i):
                if lines[j].strip().startswith('except '):
                    in_except_block = True
                    break
                elif lines[j].strip() and not lines[j].strip().startswith('#'):
                    # 遇到非空行和非注释行，停止查找
                    break

            if in_except_block and 'from None' not in line and 'from ' not in line:
                # 修复这一行
                lines[i] = line.rstrip() + ' from None'
                fixed_count += 1

    if fixed_count > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"✅ 修复了 {file_path} 中的 {fixed_count} 个B904错误")
        except Exception as e:
            print(f"❌ 写入文件失败 {file_path}: {e}")
            return 0

    return fixed_count


def main():
    """主函数"""
    print("🚀 快速B904批量修复工具")
    print("=" * 50)

    # 查找所有Python文件
    src_path = Path("src")
    python_files = list(src_path.rglob("*.py"))

    total_fixed = 0
    processed_files = 0

    for file_path in python_files:
        # 检查文件是否包含HTTPException
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'HTTPException' in content and 'raise' in content:
                fixed = fix_b904_in_file(str(file_path))
                total_fixed += fixed
                if fixed > 0:
                    processed_files += 1
        except Exception:
            continue

    print("=" * 50)
    print(f"📊 修复统计:")
    print(f"   ✅ 总计修复: {total_fixed} 个B904错误")
    print(f"   📁 处理文件: {processed_files} 个文件")
    print(f"   ✨ 批量修复完成!")


if __name__ == "__main__":
    main()