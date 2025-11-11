#!/usr/bin/env python3
"""
快速导入修复脚本 - 修复np/pd/sa导入问题
Quick import fix script - fix np/pd/sa import issues
"""

from pathlib import Path


def add_imports_to_file(file_path: Path, needed_imports: list) -> bool:
    """向文件添加需要的导入"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # 找到插入位置（现有导入之后，代码之前）
        insert_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                insert_line = i + 1
            elif line.strip() and not line.startswith('"""') and not line.startswith('#') and not line.startswith('from ') and not line.startswith('import '):
                if insert_line > 0:
                    break

        # 准备要添加的导入
        imports_to_add = []
        for imp in needed_imports:
            if imp not in content:
                imports_to_add.append(f"import {imp}")

        if imports_to_add:
            # 插入导入
            lines.insert(insert_line, '')
            for imp in imports_to_add:
                lines.insert(insert_line + 1, imp)

            # 写回文件
            new_content = '\n'.join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True

        return False

    except Exception:
        return False

def main():
    """主函数"""

    src_path = Path("src")
    fixed_count = 0

    # 定义需要检查的文件模式和对应的导入

    for py_file in src_path.rglob("*.py"):
        # 跳过__init__.py文件
        if py_file.name == "__init__.py":
            continue

        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            needed_imports = []

            # 检查是否需要pandas
            if 'pd.' in content and 'import pandas' not in content and 'import pd' not in content:
                needed_imports.append('pandas as pd')

            # 检查是否需要numpy
            if 'np.' in content and 'import numpy' not in content and 'import np' not in content:
                needed_imports.append('numpy as np')

            # 检查是否需要sqlalchemy (sa)
            if 'sa.' in content and 'from sqlalchemy' not in content and 'import sqlalchemy' not in content:
                # sa通常需要特殊处理，暂时跳过
                pass

            if needed_imports:
                if add_imports_to_file(py_file, needed_imports):
                    fixed_count += 1

        except Exception:
            pass


if __name__ == "__main__":
    main()
