#!/usr/bin/env python3
"""
SQLAlchemy别名（sa）错误批量修复工具
"""

import os
import re
from pathlib import Path

def fix_sa_in_file(file_path):
    """修复单个文件中的sa未定义错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否包含sa的使用
        if 'sa.' not in content:
            return False

        # 检查是否已经有sa导入
        if 'import sqlalchemy as sa' in content:
            return False

        # 在文件开头添加sa导入
        lines = content.split('\n')
        fixed_lines = []
        sa_import_added = False

        # 寻找合适的插入位置
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                insert_index = i + 1
            elif line.strip() == '' and insert_index > 0:
                # 在导入块结束后添加
                break
            elif not line.startswith(('import ', 'from ', '#', '\n')) and insert_index > 0:
                # 遇到非导入行，停止
                break

        # 插入sa导入
        if insert_index > 0:
            lines.insert(insert_index, 'import sqlalchemy as sa')
        else:
            lines.insert(0, 'import sqlalchemy as sa')

        fixed_content = '\n'.join(lines)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        print(f"✅ 修复 {file_path}")
        return True

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复SQLAlchemy别名（sa）错误...")

    # 使用ruff查找所有包含F821错误的文件
    result = os.popen("ruff check src/ --output-format=text | grep 'F821.*sa' | cut -d':' -f1 | sort | uniq").read()
    files_with_sa_errors = [f.strip() for f in result.split('\n') if f.strip()]

    print(f"📁 找到 {len(files_with_sa_errors)} 个需要修复sa错误的文件")

    fixed_count = 0
    for file_path in files_with_sa_errors:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_sa_in_file(full_path):
                fixed_count += 1

    print(f"\n📊 修复完成: {fixed_count} 个文件")

    # 检查修复效果
    print("\n🔍 检查修复效果...")
    remaining_sa_errors = os.popen("ruff check src/ | grep 'F821.*sa' | wc -l").read().strip()
    print(f"剩余sa相关F821错误: {remaining_sa_errors} 个")

if __name__ == "__main__":
    main()