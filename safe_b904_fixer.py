#!/usr/bin/env python3
"""
安全的B904修复工具 - 精确修复API层的异常处理问题
"""

import re
import os
from pathlib import Path

def fix_b904_safe(file_path):
    """安全地修复单个文件中的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes_count = 0

        # 精确匹配B904模式，避免语法错误
        # 查找模式：except Exception as e: ... raise HTTPException(...)
        pattern = r'(except\s+Exception\s+as\s+(\w+):\s*.*?logger\.error\(.*?\)\s*)(raise\s+HTTPException\([^)]+\))'

        def replacement(match):
            nonlocal fixes_count
            except_block = match.group(1)
            exception_var = match.group(2)
            raise_statement = match.group(3)

            # 如果已经有from子句，跳过
            if 'from' in raise_statement:
                return match.group(0)

            fixes_count += 1
            return f"{except_block}{raise_statement} from {exception_var}"

        # 应用修复
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {fixes_count} 个B904错误: {file_path}")
            return fixes_count
        else:
            print(f"ℹ️  没有发现需要修复的B904错误: {file_path}")
            return 0

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0

def main():
    """主函数"""
    target_files = [
        "src/api/betting_api.py",
        "src/api/cqrs.py",
        "src/api/data_integration.py",
        "src/api/data_router.py"
    ]

    total_fixes = 0
    print("🚀 开始安全修复API层B904错误...")

    for file_path in target_files:
        if Path(file_path).exists():
            fixes = fix_b904_safe(file_path)
            total_fixes += fixes
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"\n📊 修复完成:")
    print(f"   总共修复: {total_fixes} 个B904错误")
    print(f"   处理文件: {len(target_files)} 个")

if __name__ == "__main__":
    main()