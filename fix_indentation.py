#!/usr/bin/env python3
"""
修复缩进错误
"""

from pathlib import Path

def fix_indentation_errors():
    """修复缩进错误"""
    print("修复缩进错误...")

    fixed_files = []

    # 首先修复 crypto_utils.py
    crypto_file = Path('src/utils/crypto_utils.py')
    if crypto_file.exists():
        with open(crypto_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复第55行的缩进问题
        lines = content.split('\n')
        if len(lines) > 54:
            # 检查并修复第55行（索引54）
            line_55 = lines[54]
            if 'password.encode("utf-8")' in line_55 and not line_55.startswith('        '):
                lines[54] = '        ' + line_55.strip()
                content = '\n'.join(lines)

                with open(crypto_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(str(crypto_file))
                print(f"✓ 修复: {crypto_file}")

    # 修复其他常见的缩进问题
    for py_file in Path('src/utils').rglob('*.py'):
        if py_file.name in ['__init__.py', 'crypto_utils.py']:
            continue  # 已经处理过了

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # 修复条件语句后的缩进
            lines = content.split('\n')
            new_lines = []

            for i, line in enumerate(lines):
                stripped = line.strip()

                # 修复 if 语句后的代码缩进
                if stripped.startswith('if ') and ':' in line:
                    # 确保同一行的代码有正确缩进
                    if ':' in line and line.count(':') == 1:
                        after_colon = line.split(':')[1].strip()
                        if after_colon and not after_colon.startswith('#'):
                            # 这种情况不应该发生，但为了安全起见
                            pass

                # 修复 else/elif/except/finally 的缩进
                if stripped.startswith(('else:', 'elif ', 'except', 'finally:')):
                    if not line.startswith('    ') and not line.startswith('\t'):
                        # 如果没有缩进，需要检查上下文
                        if i > 0:
                            prev_line = lines[i-1].strip()
                            if prev_line.endswith(':') and not prev_line.startswith('#'):
                                # 前一行是控制结构，这一行应该有缩进
                                line = '    ' + line

                new_lines.append(line)

            content = '\n'.join(new_lines)

            if content != original:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(str(py_file))
                print(f"✓ 修复: {py_file}")

        except Exception as e:
            print(f"✗ 错误: {py_file} - {e}")

    print(f"\n修复完成！修复了 {len(fixed_files)} 个文件")

if __name__ == '__main__':
    fix_indentation_errors()
