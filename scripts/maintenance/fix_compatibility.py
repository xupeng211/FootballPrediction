#!/usr/bin/env python3
"""Python 兼容性批量修复脚本
Batch fix script for Python version compatibility issues.

修复所有 `Type | None` 语法为 `Optional[Type]` 语法
Fix all `Type | None` syntax to `Optional[Type]` syntax
"""

import re
import sys
from pathlib import Path


def add_optional_import(file_path: Path) -> bool:
    """添加 Optional 导入到文件头部."""
    try:
        content = file_path.read_text(encoding='utf-8')

        # 检查是否已经有 Optional 导入
        if 'from typing import Optional' in content or 'import Optional' in content:
            return False

        # 查找合适的导入位置
        lines = content.split('\n')
        import_index = -1

        # 查找最后一个 typing 相关导入
        for i, line in enumerate(lines):
            if line.strip().startswith('from typing import') or line.strip().startswith('import typing'):
                import_index = i

        # 如果找到 typing 导入，添加 Optional
        if import_index >= 0:
            existing_import = lines[import_index]
            if 'from typing import' in existing_import:
                # 在现有导入中添加 Optional
                if 'Optional' not in existing_import:
                    lines[import_index] = existing_import.rstrip() + ', Optional'
            else:
                # 添加新的 from typing import Optional 行
                lines.insert(import_index + 1, 'from typing import Optional')
        else:
            # 在文件开头添加导入
            import_lines = [
                'from typing import Optional',
                ''
            ]
            lines = import_lines + lines

        # 写回文件
        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return True

    except Exception:
        return False


def fix_type_annotations(file_path: Path) -> int:
    """修复单个文件中的类型注解."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 修复模式: Type | None -> Optional[Type]
        patterns = [
            # 基本类型: int | None
            (r'(\w+)\s*\|\s*None', r'Optional[\1]'),
            # 带泛型的类型: dict[str, Any] | None
            (r'(\w+\[.*?\])\s*\|\s*None', r'Optional[\1]'),
            # None | Type -> Optional[Type]
            (r'None\s*\|\s*(\w+)', r'Optional[\2]'),
            # None | Type[...] -> Optional[Type[...]]
            (r'None\s*\|\s*(\w+\[.*?\])', r'Optional[\2]'),
            # 复杂类型中的 Union: dict[str, Any] | None | str
            # 这种情况需要特殊处理，先拆分成多个替换
        ]

        fixes_count = 0

        # 逐个模式替换
        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                fixes_count += count

        # 特殊处理：多重 Union 类型，如 dict[str, Any] | None | str
        # 需要手动处理这些复杂情况
        complex_patterns = [
            (r'Optional\[(\w+\[.*?\])\]\s*\|\s*(\w+)', r'Union[\1, \2]'),
            (r'(\w+)\s*\|\s*Optional\[(\w+\[.*?\])\]', r'Union[\1, \2]'),
        ]

        # 先添加 Union 导入（如果需要）
        if '| Optional[' in content and '| None' in content:
            if 'from typing import Union' not in content and 'import Union' not in content:
                # 添加 Union 导入
                if 'from typing import' in content:
                    content = re.sub(r'(from typing import [^\n]+)', r'\1, Union', content)
                else:
                    lines = content.split('\n')
                    import_index = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('import ') and 'typing' in line:
                            import_index = i
                            break
                    if import_index > 0:
                        lines[import_index] = lines[import_index] + ', Union'
                    else:
                        lines.insert(0, 'from typing import Union, Optional')
                        lines.insert(1, '')
                    content = '\n'.join(lines)

        # 应用复杂模式
        for pattern, replacement in complex_patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                fixes_count += count

        # 如果有修改，写回文件
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')

        return fixes_count

    except Exception:
        return 0


def fix_project_compatibility(project_root: str):
    """修复整个项目的兼容性问题."""
    project_path = Path(project_root)

    # 需要处理的目录
    directories = ['src', 'tests']

    total_files = 0
    total_fixes = 0
    errors = 0


    for directory in directories:
        dir_path = project_path / directory
        if not dir_path.exists():
            continue


        # 递归查找所有 Python 文件
        python_files = list(dir_path.rglob('*.py'))

        for py_file in python_files:
            # 跳过 __pycache__ 等目录
            if '__pycache__' in str(py_file):
                continue

            total_files += 1

            try:
                # 1. 添加 Optional 导入
                import_added = add_optional_import(py_file)
                if import_added:
                    pass

                # 2. 修复类型注解
                fixes = fix_type_annotations(py_file)
                if fixes > 0:
                    total_fixes += fixes

            except Exception:
                errors += 1



if __name__ == '__main__':
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # 默认使用当前目录
        project_root = '.'


    fix_project_compatibility(project_root)

