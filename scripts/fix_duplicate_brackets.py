#!/usr/bin/env python3
"""
修复HTTPException语法中的重复括号问题
"""

import re
from pathlib import Path


def fix_duplicate_brackets(content):
    """修复重复括号问题"""
    # 匹配模式: )\s*)\s*from e
    pattern = r'\)\s*\)\s*from\s+e'

    # 替换为: ) from e
    fixed_content = re.sub(pattern, ') from e', content)

    return fixed_content

def main():
    """主函数"""
    print("🔧 修复HTTPException重复括号问题...")

    fixed_files = 0
    for py_file in Path("src").rglob("*.py"):
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            # 检查是否有问题
            if re.search(r'\)\s*\)\s*from\s+e', content):
                fixed_content = fix_duplicate_brackets(content)

                if content != fixed_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    print(f"✅ 修复了: {py_file}")
                    fixed_files += 1
        except Exception as e:
            print(f"❌ 处理文件失败 {py_file}: {e}")

    print(f"🎉 总共修复了 {fixed_files} 个文件")

if __name__ == "__main__":
    main()
