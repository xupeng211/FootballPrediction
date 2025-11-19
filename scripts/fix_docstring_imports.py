#!/usr/bin/env python3
"""批量修复docstring中import语句的脚本.

解决F821错误的系统性问题：
- import语句被包含在docstring中
- 导致pandas、numpy、sqlalchemy等库无法正确导入
"""

import os
import re


def find_files_with_f821():
    """查找所有有F821错误的Python文件."""
    os.system("ruff check src/ --select=F821 --output-format=full > f821_errors.txt")

    files_with_errors = set()
    with open('f821_errors.txt') as f:
        for line in f:
            if 'F821 Undefined name' in line and '-->' in line:
                # 提取文件路径
                match = re.search(r'--> (.*?):', line)
                if match:
                    files_with_errors.add(match.group(1))

    return sorted(files_with_errors)

def fix_docstring_imports(file_path):
    """修复单个文件的docstring导入问题."""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 模式1: 以 """ 开头，包含 import 语句的docstring
        pattern1 = r'"""[^"]*?(import pandas as pd|import numpy as np|import sqlalchemy as sa)[^"]*?"""'

        # 查找需要修复的docstring
        docstrings_to_fix = re.finditer(pattern1, content, re.DOTALL)

        for match in docstrings_to_fix:
            docstring = match.group(0)

            # 提取import语句
            imports = []
            if 'import pandas as pd' in docstring:
                imports.append('import pandas as pd')
            if 'import numpy as np' in docstring:
                imports.append('import numpy as np')
            if 'import sqlalchemy as sa' in docstring:
                imports.append('import sqlalchemy as sa')

            # 移除docstring中的import语句
            cleaned_docstring = docstring
            for imp in imports:
                cleaned_docstring = cleaned_docstring.replace(imp, '')

            # 替换原docstring
            content = content.replace(docstring, cleaned_docstring)

            # 在第一个import语句之前添加正确的导入
            if imports:
                # 找到第一个import语句的位置
                first_import = re.search(r'\nimport ', content)
                if first_import:
                    pos = first_import.start()
                    # 在第一个import之前添加我们的导入
                    import_block = '\n' + '\n'.join(imports) + '\n'
                    content = content[:pos] + import_block + content[pos:]

        # 只有内容发生变化时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception:
        return False

def main():
    """主函数."""
    # 查找需要修复的文件
    files_to_fix = find_files_with_f821()

    # 逐个修复
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_docstring_imports(file_path):
            fixed_count += 1
        else:
            pass

    # 清理临时文件
    if os.path.exists('f821_errors.txt'):
        os.remove('f821_errors.txt')


    # 验证修复效果
    os.system("echo '🔍 验证修复效果...'")
    os.system("ruff check src/ --select=F821 | wc -l | xargs echo '剩余F821错误数:'")

if __name__ == "__main__":
    main()
