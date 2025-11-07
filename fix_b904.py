#!/usr/bin/env python3
"""
智能修复B904异常处理链问题的脚本
Smart script to fix B904 exception handling chain issues
"""

import re
import sys
from pathlib import Path


def fix_b904_in_file(file_path: Path) -> int:
    """修复文件中的B904错误"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 更精确的匹配模式：匹配多行raise语句
        # 匹配 except Exception as e: 后面跟着的多行 raise HTTPException(...)
        pattern = r'(except\s+.*?as\s+e:\s*\n(?:.*\n)*?.*?)(raise\s+HTTPException\(\s*[^)]*(?:\n[^)]*)*?\))(\s*\n)'

        def replace_func(match):
            except_block = match.group(1)
            raise_statement = match.group(2)
            trailing = match.group(3)
            # 添加 from e 到raise语句
            return f"{except_block}{raise_statement} from e{trailing}"

        # 应用修复
        fixed_content = re.sub(pattern, replace_func, content, flags=re.MULTILINE | re.DOTALL)

        # 如果内容有变化，写回文件
        if fixed_content != original_content:
            file_path.write_text(fixed_content, encoding='utf-8')
            print(f"✅ 修复了 {file_path}")
            return 1
        else:
            print(f"ℹ️  {file_path} 无需修复")
            return 0

    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return 0

def main():
    """主函数"""
    target_files = [
        "src/api/data_router.py",
        "src/api/events.py",
        "src/api/features.py"
    ]

    total_fixed = 0

    for file_path_str in target_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            fixed = fix_b904_in_file(file_path)
            total_fixed += fixed
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"\n📊 总计修复了 {total_fixed} 个文件的B904错误")
    return total_fixed

if __name__ == "__main__":
    sys.exit(main())
