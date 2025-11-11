#!/usr/bin/env python3
"""
简单修复SQLAlchemy别名问题
"""

import os

# 直接修复已知有问题的文件
files_to_fix = [
    "src/database/migrations/versions/005_add_multi_tenant_support.py"
]

for file_path in files_to_fix:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已有sa导入
        if 'import sqlalchemy as sa' not in content and 'sa.' in content:
            # 在文件开头添加sa导入
            lines = content.split('\n')
            lines.insert(0, 'import sqlalchemy as sa')

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print(f"✅ 修复 {file_path}")
        else:
            print(f"⚠️  {file_path} 不需要修复")

print("🔧 SQLAlchemy别名修复完成")