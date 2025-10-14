#!/usr/bin/env python3
"""
批量修复测试文件中被注释的导入语句
"""

import os
import re
from pathlib import Path

def fix_test_imports(test_dir: str = "tests"):
    """修复测试文件中被注释的导入语句"""

    test_path = Path(test_dir)
    fixed_count = 0

    # 需要修复的导入模式
    import_patterns = [
        (r'^#\s*from src\.\w+\. import \w+', 'from'),
        (r'^#\s*from src\.\w+\.\w+ import \w+', 'from'),
        (r'^#\s*import src\.\w+', 'import'),
        (r'^#\s*from src\.', 'from'),
    ]

    # 遍历所有测试文件
    for py_file in test_path.rglob("*.py"):
        if py_file.name.startswith("test_"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # 修复被注释的导入语句
                for pattern, replacement in import_patterns:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.match(pattern, line.strip()):
                            # 取消注释
                            lines[i] = line.strip().lstrip('#').strip()
                            fixed_count += 1

                    content = '\n'.join(lines)

                # 如果内容有变化，写回文件
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    rel_path = py_file.relative_to(Path.cwd())
                    print(f"修复了 {rel_path}")

            except Exception as e:
                print(f"处理 {py_file} 时出错: {e}")

    print(f"\n总计修复了 {fixed_count} 个导入语句")

if __name__ == "__main__":
    fix_test_imports()
