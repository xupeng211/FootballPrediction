#!/usr/bin/env python3
"""
批量修复import语句和文档字符串错误
"""

import os
import re
from pathlib import Path


def fix_imports_and_docs(file_path: Path) -> bool:
    """修复文件的import语句和文档字符串"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 修复文档字符串
        # 修复双引号文档字符串
        content = re.sub(r'""\s*([^"]*?)\s*""', r'"""\1"""', content)

        # 修复合并的import语句
        content = re.sub(r'import\s+(\w+)\s*import\s+', r'import \1\nimport ', content)
        content = re.sub(r'import\s+(\w+\.\w+)\s*import\s+', r'from \1 import ', content)
        content = re.sub(r'from\s+(\S+)\s*import\s+(\w+)\s*from\s+', r'from \1 import \2\nfrom ', content)

        # 修复合并的from import
        content = re.sub(r'from\s+([^\s]+)\.\s*\.\s*([^\s]+)\s+import', r'from ..\2 import ', content)

        # 分离连在一起的import
        content = re.sub(r'}\s*from', '}\nfrom', content)
        content = re.sub(r'(\w+)}import', r'\1}\nimport', content)
        content = re.sub(r'(\w+)from', r'\1\nfrom', content)
        content = re.sub(r'import(\w+)', r'import \1', content)

        # 修复import后面的语句
        content = re.sub(r'import\s+(\w+)\s*(\w+)', r'import \1\n\2', content)

        # 修复类定义前的文档字符串
        content = re.sub(r'"""\s*([^{]*?)\s*"""\s*(@|class|def)', r'"""\1"""\n\2', content)

        # 修复函数参数中的类型注解错误
        content = re.sub(r'def\s+(\w+)\([^)]*?):\s*Type\)\s*->', r'def \1(\2) ->', content)
        content = re.sub(r'def\s+(\w+)\([^)]*?):\s*[^)]+\)\s*->', r'def \1(\2) ->', content)

        # 修复未闭合的字符串（简单情况）
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # 修复以冒号或句号结尾但后面紧跟代码的文档字符串
            if '"""' in line and not line.strip().endswith('"""'):
                # 查找文档字符串结束位置
                quote_pos = line.rfind('"""')
                if quote_pos > 0:
                    # 检查后面是否还有代码
                    after = line[quote_pos + 3:]
                    if after.strip():
                        lines[i] = line[:quote_pos + 3] + '\n' + after
        content = '\n'.join(lines)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"修复 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    src_dir = Path("src")
    python_files = list(src_dir.rglob("*.py"))

    print(f"批量修复 {len(python_files)} 个Python文件...\n")

    fixed_count = 0
    error_count = 0

    for file_path in sorted(python_files):
        if fix_imports_and_docs(file_path):
            print(f"✓ 修复: {file_path}")
            fixed_count += 1
        else:
            error_count += 1

    print(f"\n修复完成！")
    print(f"  修复文件数: {fixed_count}")
    print(f"  错误文件数: {error_count}")


if __name__ == "__main__":
    main()