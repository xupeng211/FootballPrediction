#!/usr/bin/env python3
"""
快速修复关键的语法错误
只处理 src/ 目录下的文件
"""

import os
import re
from pathlib import Path

def fix_critical_errors():
    """修复关键的语法错误"""
    src_dir = Path("src")

    if not src_dir.exists():
        print("src/ 目录不存在")
        return

    # 递归查找所有 __init__.py 文件
    init_files = list(src_dir.rglob("__init__.py"))

    fixed_count = 0

    for init_file in init_files:
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # 修复 __all__ = [) -> __all__ = [
            content = re.sub(r'__all__\s*=\s*\[\)', '__all__ = [', content)

            # 修复 __all__ 列表缺少闭合括号
            # 查找未闭合的 __all__ 定义
            lines = content.split('\n')
            new_lines = []
            in_all = False
            all_needs_close = False

            for line in lines:
                stripped = line.strip()

                if stripped.startswith('__all__'):
                    in_all = True
                    new_lines.append(line)
                    # 检查是否以 [ 结尾
                    if '[' in line and not line.strip().endswith(']'):
                        all_needs_close = True
                elif in_all:
                    new_lines.append(line)
                    # 如果这行有内容且不是注释，检查是否需要闭合
                    if stripped and not stripped.startswith('#') and not stripped.startswith('"') and not stripped.startswith("'"):
                        if all_needs_close and not line.strip().endswith(','):
                            # 需要添加闭合括号
                            if ']' not in line:
                                new_lines[-1] = line.rstrip() + ']'
                                all_needs_close = False
                                in_all = False

                # 空行或注释行，继续
                elif not in_all:
                    new_lines.append(line)

            content = '\n'.join(new_lines)

            # 修复三引号问题
            if '"""' in content:
                quote_count = content.count('"""')
                if quote_count % 2 != 0:
                    content = content.rstrip() + '\n"""'

            # 修复 {) 的问题
            content = content.replace('{)', '{')

            # 修复其他括号问题
            content = re.sub(r'\[\)', '[', content)

            if content != original:
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ 修复了 {init_file}")
                fixed_count += 1

        except Exception as e:
            print(f"✗ 处理 {init_file} 时出错: {e}")

    print(f"\n修复完成！共修复了 {fixed_count} 个文件")

    # 现在修复其他关键文件
    critical_files = [
        "src/cache/__init__.py",
        "src/monitoring/metrics_collector.py",
        "src/utils/crypto_utils.py",
        "src/main.py",
        "src/api/app.py"
    ]

    for file_path in critical_files:
        path = Path(file_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # 修复常见问题
                content = content.replace('{)', '{')
                content = re.sub(r'\[\)', '[', content)

                # 修复三引号
                if '"""' in content:
                    quote_count = content.count('"""')
                    if quote_count % 2 != 0:
                        content = content.rstrip() + '\n"""'

                if content != original:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✓ 修复了 {file_path}")

            except Exception as e:
                print(f"✗ 处理 {file_path} 时出错: {e}")

if __name__ == "__main__":
    fix_critical_errors()