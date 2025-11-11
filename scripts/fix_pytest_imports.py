#!/usr/bin/env python3
"""
批量修复pytest导入问题
"""

import os
import re
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_pytest_in_file(file_path):
    """修复单个文件的pytest导入"""
    print(f"🔧 修复文件: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 检查是否使用pytest但没有导入
        if 'pytest.' in content or 'pytest.raises' in content or 'pytest.mark' in content:
            if 'import pytest' not in content:
                # 找到合适的导入位置
                lines = content.split('\n')

                # 查找文档字符串结束位置
                docstring_end = -1
                for i, line in enumerate(lines):
                    if '"""' in line or "'''" in line:
                        quote_type = '"""' if '"""' in line else "'''"
                        if line.count(quote_type) >= 2:
                            docstring_end = i
                        else:
                            # 多行文档字符串
                            for j in range(i + 1, len(lines)):
                                if quote_type in lines[j]:
                                    docstring_end = j
                                    break
                        break

                # 查找第一个导入语句
                first_import = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        first_import = i
                        break

                # 插入pytest导入
                if docstring_end >= 0:
                    # 在文档字符串后添加
                    lines.insert(docstring_end + 1, '')
                    lines.insert(docstring_end + 2, 'import pytest')
                elif first_import >= 0:
                    # 在第一个导入前添加
                    lines.insert(first_import, 'import pytest')
                else:
                    # 在文件开头添加
                    lines.insert(0, 'import pytest')

                content = '\n'.join(lines)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"  ✅ 添加了pytest导入")
            return True
        else:
            print(f"  ℹ️  pytest导入已存在")
            return False

    except Exception as e:
        print(f"  ❌ 修复失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始批量修复pytest导入...")

    # 获取所有F821 pytest错误
    import subprocess
    result = subprocess.run(
        ["ruff", "check", "src/", "tests/", "--output-format=concise"],
        capture_output=True,
        text=True
    )

    files_to_fix = set()
    for line in result.stdout.split('\n'):
        if 'F821' in line and 'pytest' in line:
            parts = line.split(':')
            if len(parts) >= 1:
                files_to_fix.add(Path(parts[0]))

    print(f"📊 发现 {len(files_to_fix)} 个文件需要修复pytest导入")

    # 修复每个文件
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_pytest_in_file(file_path):
            fixed_count += 1

    print(f"🎉 pytest导入修复完成！修复了 {fixed_count} 个文件")
    return fixed_count

if __name__ == "__main__":
    main()