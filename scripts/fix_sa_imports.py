#!/usr/bin/env python3
"""
SQLAlchemy别名（sa）导入修复工具
专门处理F821错误：sa未定义
"""

import os
from pathlib import Path


def fix_sa_imports(file_path):
    """修复文件中缺失的sa导入"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 检查是否使用了sa但没有导入
        has_sa_usage = 'sa.' in content or 'import sqlalchemy as sa' in content
        has_sa_import = 'import sqlalchemy as sa' in content or 'from sqlalchemy import' in content

        if has_sa_usage and not has_sa_import:
            # 找到合适的位置插入导入
            lines = content.split('\n')
            fixed_lines = []
            import_added = False

            for i, line in enumerate(lines):
                # 在其他导入语句之后插入sa导入
                if line.startswith('import ') or line.startswith('from '):
                    fixed_lines.append(line)
                    # 如果这是最后一个import语句，添加sa导入
                    if i + 1 < len(lines) and not lines[i + 1].startswith(('import ', 'from ')):
                        if not import_added:
                            fixed_lines.append('import sqlalchemy as sa')
                            import_added = True
                else:
                    fixed_lines.append(line)

            # 如果没有找到任何导入，在文件开头添加
            if not import_added:
                fixed_lines.insert(0, 'import sqlalchemy as sa')

            fixed_content = '\n'.join(fixed_lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

            return True
        else:
            return False

    except Exception:
        return False

def main():
    """主函数"""

    # 获取所有有F821错误的文件
    result = os.popen("ruff check src/ --output-format=json | jq -r 'select(.code == \"F821\") | .filename' | sort | uniq").read()
    files_with_f821 = [f.strip() for f in result.split('\n') if f.strip()]


    fixed_count = 0
    for file_path in files_with_f821:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_sa_imports(full_path):
                fixed_count += 1


    # 检查修复效果
    os.popen("ruff check src/ --output-format=json | jq -r 'select(.code == \"F821\") | .filename' | wc -l").read().strip()

if __name__ == "__main__":
    main()
