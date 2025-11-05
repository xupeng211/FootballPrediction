#!/usr/bin/env python3
"""
批量修复B904异常处理错误的工具
"""

import re
import os
from pathlib import Path

def fix_b904_in_file(file_path):
    """修复单个文件中的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes_count = 0

        # 匹配except块中的raise语句模式
        pattern = r'(\s+)(except\s+.*?\s+as\s+\w+:\s*.*?\s+)(raise\s+HTTPException\([^)]+\))'

        def replace_func(match):
            nonlocal fixes_count
            indent = match.group(1)
            except_block = match.group(2)
            raise_statement = match.group(3)

            # 检查是否已经有 from err
            if 'from e' in raise_statement or 'from err' in raise_statement:
                return match.group(0)

            # 提取异常变量名
            as_match = re.search(r'as\s+(\w+):', except_block)
            if as_match:
                exc_var = as_match.group(1)
                fixed_raise = f"{raise_statement} from {exc_var}"
                fixes_count += 1
                return f"{indent}{except_block}\n{indent}{fixed_raise}"

            return match.group(0)

        content = re.sub(pattern, replace_func, content, flags=re.DOTALL)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {fixes_count} 个B904错误: {file_path}")
            return fixes_count
        else:
            print(f"ℹ️  没有发现可修复的B904错误: {file_path}")
            return 0

    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return 0

def main():
    """主函数"""
    src_dir = Path("src")
    total_fixes = 0

    print("🚀 开始批量修复B904异常处理错误...")

    # 优先处理API文件
    api_files = list(src_dir.glob("api/**/*.py"))
    for file_path in api_files:
        if file_path.is_file():
            fixes = fix_b904_in_file(file_path)
            total_fixes += fixes

    print(f"\n📊 修复完成:")
    print(f"   总共修复: {total_fixes} 个B904错误")
    print(f"   处理文件: {len(api_files)} 个")

if __name__ == "__main__":
    main()