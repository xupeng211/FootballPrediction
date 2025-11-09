#!/usr/bin/env python3
"""
安全的B904修复工具
Safe B904 Fix Tool

只修复确实缺少from None的HTTPException，避免语法错误
"""

import re
import sys
from pathlib import Path


def fix_b904_in_file_safe(file_path: str) -> int:
    """安全地修复单个文件中的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")
        return 0

    # 使用正则表达式匹配except块中缺少from None的HTTPException
    # 模式：在except块中，raise HTTPException(...) 但没有from语句
    lines = content.split('\n')
    fixed_count = 0

    for i, line in enumerate(lines):
        # 查找raise HTTPException行
        if 'raise HTTPException(' in line and ')' in line:
            # 检查是否在except块中
            in_except_block = False
            for j in range(max(0, i-10), i):  # 检查前10行
                if lines[j].strip().startswith('except '):
                    in_except_block = True
                    break
                elif lines[j].strip() and not lines[j].strip().startswith('#') and not lines[j].strip().startswith(' '):
                    # 遇到非缩进的非注释行，停止查找
                    break

            if in_except_block:
                # 检查raise语句是否已经有from语句
                # 查找完整的raise语句（可能跨多行）
                raise_lines = [line]
                k = i + 1
                while k < len(lines) and ')' not in raise_lines[-1]:
                    raise_lines.append(lines[k])
                    k += 1

                full_raise = '\n'.join(raise_lines)

                # 检查是否已经有from语句
                if not re.search(r'\)\s*from\s+(None|\w+)', full_raise):
                    # 找到最后的)并添加from None
                    if ')' in raise_lines[-1]:
                        raise_lines[-1] = raise_lines[-1].replace(')', ') from None', 1)
                        # 更新原始lines
                        for idx, replacement in enumerate(raise_lines):
                            lines[i + idx] = replacement
                        fixed_count += 1
                        print(f"✅ 修复了 {file_path} 第{i+1}行的B904错误")

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
    print("🚀 安全B904修复工具")
    print("=" * 50)

    # 要修复的文件列表（基于ruff检查结果）
    files_to_fix = [
        "src/api/optimization/cache_performance_api.py",
        "src/api/optimization/database_performance_api.py",
        "src/performance/api.py",
        "src/realtime/match_api.py"
    ]

    total_fixed = 0
    processed_files = 0

    for file_path in files_to_fix:
        if Path(file_path).exists():
            fixed = fix_b904_in_file_safe(file_path)
            total_fixed += fixed
            if fixed > 0:
                processed_files += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print("=" * 50)
    print(f"📊 修复统计:")
    print(f"   ✅ 总计修复: {total_fixed} 个B904错误")
    print(f"   📁 处理文件: {processed_files} 个文件")
    print(f"   ✨ 安全修复完成!")


if __name__ == "__main__":
    main()