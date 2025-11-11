#!/usr/bin/env python3
"""
修复常见的导入错误 (numpy, pandas等)
Fix common import errors (numpy, pandas, etc.)
"""

import re
from pathlib import Path

def fix_imports_in_file(file_path: Path) -> bool:
    """修复单个文件中的导入错误"""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 检查是否使用了np但没有导入
        if 'np.' in content and 'import numpy' not in content and 'import np' not in content:
            # 添加numpy导入
            if content.startswith('"""'):
                # 找到docstring结束位置
                doc_end = content.find('"""', 3)
                if doc_end != -1:
                    insert_pos = content.find('\n', doc_end) + 1
                    content = content[:insert_pos] + 'import numpy as np\n' + content[insert_pos:]
            else:
                content = 'import numpy as np\n' + content

        # 检查是否使用了pd但没有导入
        if 'pd.' in content and 'import pandas' not in content and 'import pd' not in content:
            # 添加pandas导入
            if content.startswith('"""'):
                doc_end = content.find('"""', 3)
                if doc_end != -1:
                    insert_pos = content.find('\n', doc_end) + 1
                    # 检查是否已经有numpy导入，避免重复添加
                    if 'import numpy as np\n' in content[:insert_pos+50]:
                        content = content[:insert_pos] + 'import pandas as pd\n' + content[insert_pos:]
                    else:
                        content = content[:insert_pos] + 'import pandas as pd\nimport numpy as np\n' + content[insert_pos:]
            else:
                content = 'import pandas as pd\nimport numpy as np\n' + content

        # 写回修复后的内容
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""

    print("🔧 开始修复常见导入错误...")

    # 查找所有Python文件
    src_path = Path("src")
    fixed_files = []

    for py_file in src_path.rglob("*.py"):
        # 跳过__init__.py文件
        if py_file.name == "__init__.py":
            continue

        # 检查文件是否有F821错误
        try:
            result = !ruff check {py_file} --output-format=json 2>/dev/null
            if result:
                has_f821 = any('F821' in line for line in result)
                if has_f821:
                    if fix_imports_in_file(py_file):
                        fixed_files.append(py_file)
                        print(f"✅ 已修复: {py_file}")
        except:
            pass

    print(f"\n📊 修复结果:")
    print(f"✅ 成功修复: {len(fixed_files)} 个文件")

    if fixed_files:
        print(f"\n🎯 修复的文件:")
        for file_path in fixed_files[:10]:  # 只显示前10个
            print(f"   - {file_path}")
        if len(fixed_files) > 10:
            print(f"   ... 还有 {len(fixed_files) - 10} 个文件")

if __name__ == "__main__":
    main()