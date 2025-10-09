#!/usr/bin/env python3
"""
修复import组织错误（E402）
Fix module level import not at top of file errors
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_imports_in_file(file_path: Path) -> int:
    """修复单个文件的import组织"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return 0

    if not lines:
        return 0

    # 1. 找出所有的import语句（包括top-level和函数内的）
    top_level_imports = []
    other_imports = []
    import_positions = []

    # 记录文档字符串和注释
    docstring_end = 0
    in_docstring = False
    docstring_char = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 检查文档字符串
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                docstring_char = '"""' if stripped.startswith('"""') else "'''"
                docstring_end = i
                # 检查是否是单行文档字符串
                if stripped.endswith(docstring_char) and len(stripped) >= 6:
                    in_docstring = False
                    docstring_end = i
            else:
                if stripped.endswith(docstring_char):
                    in_docstring = False
                    docstring_end = i

        # 检查import语句
        if (stripped.startswith('import ') or stripped.startswith('from ')) and not in_docstring:
            # 检查是否在函数或类内部
            # 简单检查：看前面有多少空格
            indent = len(line) - len(stripped)

            if indent == 0 and i < 50:  # top-level且在文件前50行
                # 这是需要移动到顶部的import
                top_level_imports.append((i, line))
                import_positions.append(i)
            elif indent > 0:
                # 函数或类内部的import，保持不动
                other_imports.append((i, line, indent))

        i += 1

    if not top_level_imports:
        return 0

    # 2. 找到合适的位置插入imports（文档字符串之后）
    insert_pos = docstring_end + 1

    # 跳过空行
    while insert_pos < len(lines) and not lines[insert_pos].strip():
        insert_pos += 1

    # 3. 收集所有需要移动的imports，按类型分组
    stdlib_imports = []
    thirdparty_imports = []
    local_imports = []

    for pos, imp in top_level_imports:
        imp_stripped = imp.strip()

        # 判断import类型
        if imp_stripped.startswith('from .'):
            local_imports.append(imp)
        elif any(imp_stripped.startswith(f'from {lib}') or imp_stripped.startswith(f'import {lib}')
                for lib in ['os', 'sys', 'time', 'datetime', 'json', 'logging', 'asyncio',
                           'pathlib', 're', 'collections', 'itertools', 'functools', 'typing',
                           'uuid', 'hashlib', 'base64', 'urllib', 'http', 'socket', 'threading',
                           'multiprocessing', 'subprocess', 'shutil', 'tempfile', 'glob',
                           'math', 'random', 'statistics', 'decimal', 'fractions',
                           'enum', 'dataclasses', 'contextlib', 'warnings', 'traceback',
                           'inspect', 'importlib', 'pkgutil', 'types', 'copy']):
            stdlib_imports.append(imp)
        elif imp_stripped.startswith('from src') or imp_stripped.startswith('import src'):
            local_imports.append(imp)
        else:
            thirdparty_imports.append(imp)

    # 4. 创建新的import块
    new_imports = []

    # 添加标准库imports
    if stdlib_imports:
        new_imports.extend(sorted(stdlib_imports))
        new_imports.append('')

    # 添加第三方imports
    if thirdparty_imports:
        new_imports.extend(sorted(thirdparty_imports))
        new_imports.append('')

    # 添加本地imports
    if local_imports:
        new_imports.extend(sorted(local_imports))
        new_imports.append('')

    # 5. 重建文件内容
    # 先移除原来的top-level imports
    lines_to_remove = set(pos for pos, _ in top_level_imports)
    new_lines = []

    for i, line in enumerate(lines):
        if i not in lines_to_remove:
            new_lines.append(line)

    # 在insert_pos插入新的imports
    # 先确保insert_pos后面有空行
    while insert_pos < len(new_lines) and new_lines[insert_pos].strip() == '':
        insert_pos += 1

    # 插入imports
    for i, imp in enumerate(new_imports):
        new_lines.insert(insert_pos + i, imp)

    # 6. 写回文件
    try:
        new_content = '\n'.join(new_lines) + '\n'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        fixed_count = len(top_level_imports)
        print(f"✓ 修复 {file_path}: 移动了 {fixed_count} 个imports")
        return fixed_count

    except Exception as e:
        print(f"写入文件失败 {file_path}: {e}")
        return 0


def main():
    """主函数"""
    print("🔧 修复import组织错误（E402）...")

    src_path = Path("src")
    total_fixed = 0

    # 查找所有Python文件
    python_files = list(src_path.rglob("*.py"))
    print(f"找到 {len(python_files)} 个Python文件")

    for file_path in python_files:
        fixed = fix_imports_in_file(file_path)
        total_fixed += fixed

    print(f"\n✅ 完成！共修复 {total_fixed} 个import组织错误")
    print("\n注意：某些import可能需要手动调整，因为它们依赖于执行上下文。")


if __name__ == "__main__":
    main()