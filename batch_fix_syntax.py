#!/usr/bin/env python3
"""批量修复语法错误脚本"""

import os
import re
from pathlib import Path

def fix_syntax_errors(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 修复类定义中的多余右括号
        content = re.sub(r'class\s+(\w+)\)\s*:', r'class \1:', content)

        # 修复函数定义中的参数语法错误
        # 处理 def func(param): type 的情况
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+)\)\s*:',
                        r'def \1(\2: \3):', content)

        # 修复更复杂的函数定义错误
        # 例如: def func(param): Type) -> ReturnType:
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\)\s*->\s*([^:]+):',
                        r'def \1(\2: \3) -> \4:', content)

        # 修复 def func(param): type) 的情况
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\)\s*$',
                        r'def \1(\2: \3)', content, flags=re.MULTILINE)

        # 修复函数参数中的类型注解错误
        # 例如: def func(data): dict[str, Any], fields): list[str]
        content = re.sub(r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^)]+?)\),\s*([^)]+?)\)\s*->\s*([^:]+):',
                        r'def \1(\2: \3, \4: \5) -> \6:', content)

        # 修复函数参数中的单独错误
        # 例如: param): Type -> ReturnType:
        content = re.sub(r'(\w+)\)\s*:\s*([^)]+?)\)\s*->\s*([^:\n]+):',
                        r'\1: \2) -> \3:', content)

        # 修复缩进错误 - 清理意外的缩进
        lines = content.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            # 修复意外的缩进行
            if line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                # 检查是否有意外的缩进
                if i > 0 and lines[i-1].strip() and not lines[i-1].strip().endswith(':'):
                    # 如果前一行不是以冒号结尾，当前行不应该有额外缩进
                    if line.startswith('    ') and not line.startswith('        '):
                        # 可能是错误缩进，但需要更智能的判断
                        pass

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 修复中文逗号
        content = content.replace('，', ',')

        # 修复未闭合的三引号字符串
        # 查找孤立的 """
        if '"""' in content:
            # 简单修复：确保每个 """ 都有配对
            quote_count = content.count('"""')
            if quote_count % 2 != 0:
                # 如果是奇数，添加一个闭合
                content += '\n"""'

        # 写回文件
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

    return False

def main():
    """主函数"""
    src_dir = Path('src')
    fixed_count = 0
    error_count = 0

    print("开始批量修复语法错误...")

    for py_file in src_dir.rglob('*.py'):
        # 先检查是否有语法错误
        try:
            compile(py_file.read_text(encoding='utf-8'), str(py_file), 'exec')
            continue  # 没有错误，跳过
        except SyntaxError:
            pass  # 有错误，需要修复

        # 尝试修复
        if fix_syntax_errors(py_file):
            print(f"✓ 修复: {py_file}")
            fixed_count += 1

            # 验证修复是否成功
            try:
                compile(py_file.read_text(encoding='utf-8'), str(py_file), 'exec')
            except SyntaxError as e:
                print(f"  ✗ 仍有错误: {e}")
                error_count += 1
        else:
            error_count += 1

    print(f"\n修复完成!")
    print(f"已修复文件数: {fixed_count}")
    print(f"仍有错误文件数: {error_count}")

if __name__ == '__main__':
    main()