#!/usr/bin/env python3
"""
批量修复所有语法错误
"""

import re
from pathlib import Path

def fix_all_syntax_errors():
    """修复所有语法错误"""
    print("开始批量修复语法错误...")

    fixed_count = 0
    error_count = 0

    # 遍历所有Python文件
    for py_file in Path('src').rglob('*.py'):
        try:
            original_content = py_file.read_text(encoding='utf-8')
            content = original_content

            # 修复 __all__ = [) 的问题
            content = re.sub(r'__all__\s*=\s*\[\)', '__all__ = [', content)

            # 修复常见的缩进问题
            lines = content.split('\n')
            new_lines = []

            for line in lines:
                # 修复 {) 的问题
                if '{)' in line:
                    line = line.replace('{)', '{')

                # 修复 [) 的问题（除了已修复的__all__）
                if '[)' in line and '__all__' not in line:
                    line = line.replace('[)', '[')

                # 修复括号不匹配
                # 修复 warnings.filterwarnings() 后面缺少逗号的情况
                if 'warnings.filterwarnings()' in line and not line.strip().endswith(','):
                    line = line.replace('warnings.filterwarnings()', 'warnings.filterwarnings(')

                new_lines.append(line)

            content = '\n'.join(new_lines)

            # 检查是否需要修复括号闭合
            # 简单修复：如果行以 ( 开头但以 ), 结尾，修复为 (
            lines = content.split('\n')
            fixed_lines = []

            for line in lines:
                # 修复不匹配的括号
                if line.count('(') > line.count(')'):
                    # 添加缺少的右括号
                    if line.strip().endswith(','):
                        line = line.rstrip(',') + ')'
                    else:
                        line = line + ')'
                fixed_lines.append(line)

            content = '\n'.join(fixed_lines)

            # 如果内容有变化，写回文件
            if content != original_content:
                py_file.write_text(content, encoding='utf-8')
                fixed_count += 1
                print(f"✓ 修复: {py_file}")

        except Exception as e:
            error_count += 1
            print(f"✗ 错误: {py_file} - {e}")

    print(f"\n修复完成！")
    print(f"修复的文件数: {fixed_count}")
    print(f"出错的文件数: {error_count}")

    return fixed_count

if __name__ == '__main__':
    fix_all_syntax_errors()