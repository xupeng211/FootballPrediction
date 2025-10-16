#!/usr/bin/env python3
"""
修复中文标点符号和字符串问题
"""

import os
import re
import ast
from pathlib import Path

def check_syntax(file_path: str) -> bool:
    """检查文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError:
        return False
    except Exception:
        return False

def fix_chinese_chars(content: str) -> str:
    """修复中文标点符号"""
    # 中文标点映射到英文
    char_map = {
        '（': '(',
        '）': ')',
        '，': ',',
        '。': '.',
        '：': ':',
        '；': ';',
        '！': '!',
        '？': '?',
        '【': '[',
        '】': ']',
        '｛': '{',
        '｝': '}',
        '、': ',',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '《': '<',
        '》': '>',
    }

    # 替换所有中文标点（除了在字符串中的）
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 跳过注释行
        if line.strip().startswith('#'):
            continue

        # 跳过文档字符串行
        if '"""' in line or "'''" in line:
            continue

        # 替换行中的中文标点
        for chinese, english in char_map.items():
            line = line.replace(chinese, english)

        lines[i] = line

    return '\n'.join(lines)

def fix_string_literals(content: str) -> str:
    """修复字符串字面量"""
    lines = content.split('\n')

    # 修复未闭合的三引号字符串
    in_docstring = False
    docstring_start = None
    quote_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检查文档字符串开始
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = True
                docstring_start = i
                quote_char = '"""' if stripped.startswith('"""') else "'''"

                # 检查是否在同一行结束
                if stripped.count(quote_char) >= 2:
                    in_docstring = False
                    docstring_start = None
                    quote_char = None
        else:
            # 检查文档字符串结束
            if quote_char in line:
                if line.count(quote_char) >= 1:
                    in_docstring = False
                    docstring_start = None
                    quote_char = None

    # 如果文档字符串未闭合，添加闭合
    if in_docstring and docstring_start is not None:
        lines.append(quote_char)

    # 修复其他未闭合的字符串
    content = '\n'.join(lines)

    # 修复行尾的逗号后换行的字符串列表
    content = re.sub(r'"\s*,\s*\n\s*"', '",\n        "', content)
    content = re.sub(r"'\s*,\s*\n\s*'", "',\n        '", content)

    # 修复字典中的字符串值
    content = re.sub(r'{\s*"([^"]+)"\s*:\s*"', r'{"\1": "', content)

    # 修复统计信息中的错误
    content = re.sub(r'"([^"]+)":\s*\d+,', r'"\1": \d,', content)

    return content

def fix_specific_patterns(content: str, file_path: str) -> str:
    """修复特定文件的模式"""
    # 修复类型注解
    content = re.sub(r'Optional\[Dict\[str, Any\]\s*\]\s*=\s*None',
                    r'Optional[Dict[str, Any]] = None', content)
    content = re.sub(r'Optional\[List\[str\]\s*\]\s*=\s*None',
                    r'Optional[List[str]] = None', content)

    # 修复字典初始化
    content = re.sub(r'{\s*"errors":\s*\[\],\s*"warnings":\s*\[\]\}',
                    r'{"errors": [], "warnings": []}', content)

    # 修复列表初始化
    content = re.sub(r'List\[Any\]\s*=\s*\{\[\]', r'List[Any] = []', content)

    # 修复函数参数
    if 'data_validator.py' in file_path:
        # 修复特定的验证规则格式
        content = re.sub(r'"required_fields":\s*\[\s*"([^"]+)"\s*,\s*\n\s*"([^"]+)"',
                        r'"required_fields": [\n            "\1",\n            "\2"', content)

        # 修复错误列表
        content = re.sub(r'"errors":\s*\[\s*"([^"]+)"\s*,\s*\n\s*',
                        r'"errors": ["\1"],\n            ', content)

    # 修复 f-string
    content = re.sub(r'f"([^"]*?)\'([^"]*?)"', r'f"\1\2"', content)
    content = re.sub(r"f'([^']*?)\"([^']*?)'", r"f'\1\2'", content)

    return content

def main():
    """主函数"""
    print("开始修复中文标点和字符串问题...")

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    # 检查哪些文件有语法错误
    error_files = []
    for file_path in python_files:
        if not check_syntax(file_path):
            error_files.append(file_path)

    print(f"\n发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("所有文件语法都正确！")
        return

    # 修复每个文件
    fixed_count = 0
    total_fixes = 0

    for file_path in error_files:
        print(f"\n处理: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            content = original_content

            # 应用修复
            content = fix_chinese_chars(content)
            content = fix_string_literals(content)
            content = fix_specific_patterns(content, file_path)

            # 如果有修复，保存文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ 文件已修复")
                fixed_count += 1

                # 验证修复是否成功
                if check_syntax(file_path):
                    print(f"  ✓ 语法错误已修复")
                else:
                    print(f"  ✗ 仍有语法错误")
                    # 显示第一个错误
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        print(f"    错误位置: 第{e.lineno}行")
                        print(f"    错误信息: {e.msg}")
                        # 显示错误行内容
                        lines = content.split('\n')
                        if e.lineno - 1 < len(lines):
                            print(f"    错误行: {lines[e.lineno - 1]}")
            else:
                print(f"  - 未找到需要修复的内容")

        except Exception as e:
            print(f"  ✗ 处理失败: {e}")

    print(f"\n修复完成！")
    print(f"- 处理文件: {len(error_files)}")
    print(f"- 成功修复: {fixed_count}")

    # 再次检查
    remaining_errors = []
    for file_path in python_files:
        if not check_syntax(file_path):
            remaining_errors.append(file_path)

    if remaining_errors:
        print(f"\n仍有 {len(remaining_errors)} 个文件存在语法错误:")
        for file_path in remaining_errors[:10]:
            print(f"  - {file_path}")
        if len(remaining_errors) > 10:
            print(f"  ... 还有 {len(remaining_errors) - 10} 个文件")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")

if __name__ == "__main__":
    main()
