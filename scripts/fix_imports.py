#!/usr/bin/env python3
"""
批量修复导入缺失问题的脚本
用于解决F821未定义名称错误
"""

import os
from pathlib import Path


def add_import_to_file(file_path: str, import_line: str) -> bool:
    """向文件添加导入语句"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # 找到合适的导入位置（在docstring之后，第一个代码行之前）
        import_pos = 0
        docstring_end = False

        for i, line in enumerate(lines):
            # 跳过空行和注释
            if line.strip() == '' or line.strip().startswith('#'):
                continue

            # 如果是三引号docstring开始
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                docstring_end = True
                # 跳过docstring
                if line.count('"""') == 1 or line.count("'''") == 1:
                    # 单行docstring
                    import_pos = i + 1
                else:
                    # 多行docstring，找到结束
                    for j in range(i + 1, len(lines)):
                        if line.strip().endswith('"""') or line.strip().endswith("'''"):
                            import_pos = j + 1
                            break
                break

        if not docstring_end:
            # 没有docstring，在文件开始添加
            import_pos = 0
            # 跳过shebang和编码声明
            for i, line in enumerate(lines):
                if line.startswith('#!') or 'coding:' in line or 'coding=' in line:
                    import_pos = i + 1
                else:
                    break

        # 检查是否已经存在该导入
        for line in lines[:import_pos + 10]:  # 检查导入位置附近的行
            if import_line in line:
                return False

        # 找到导入区域的最后位置（现有导入之后）
        final_import_pos = import_pos
        for i in range(import_pos, len(lines)):
            line = lines[i].strip()
            if line.startswith('import ') or line.startswith('from '):
                final_import_pos = i + 1
            elif line and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                break

        # 插入导入语句
        lines.insert(final_import_pos, import_line)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return True

    except Exception:
        return False

def fix_numpy_imports(files):
    """修复numpy导入问题"""
    import_line = "import numpy as np"

    fixed_count = 0
    for file_path in files:
        if add_import_to_file(file_path, import_line):
            fixed_count += 1


def fix_pandas_imports(files):
    """修复pandas导入问题"""
    import_line = "import pandas as pd"

    fixed_count = 0
    for file_path in files:
        if add_import_to_file(file_path, import_line):
            fixed_count += 1


def main():
    """主函数"""

    # 获取src目录
    Path("src")

    # 使用ruff检查需要修复的文件
    import subprocess

    # 获取需要numpy导入的文件
    try:
        result = subprocess.run(
            ["ruff", "check", "src/", "--output-format=concise"],
            capture_output=True, text=True
        )

        numpy_files = set()
        pandas_files = set()

        for line in result.stdout.split('\n'):
            if 'F821.*np' in line:
                file_path = line.split(':')[0]
                if os.path.exists(file_path):
                    numpy_files.add(file_path)
            elif 'F821.*pd' in line:
                file_path = line.split(':')[0]
                if os.path.exists(file_path):
                    pandas_files.add(file_path)


        # 修复导入问题
        if numpy_files:
            fix_numpy_imports(sorted(numpy_files))

        if pandas_files:
            fix_pandas_imports(sorted(pandas_files))


    except Exception:
        pass

if __name__ == "__main__":
    main()
