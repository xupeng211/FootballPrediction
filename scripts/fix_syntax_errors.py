#!/usr/bin/env python3
"""
修复语法错误的脚本
专门处理E902, E701, E702, E703, E721, E722, E741等错误
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

def get_files_with_syntax_errors() -> List[str]:
    """获取有语法错误的文件列表"""
    cmd = [
        "ruff", "check", "src/",
        "--select=E902,E701,E702,E703,E721,E722,E741",
        "--output-format=json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    files = set()
    if result.stdout:
        import json
        try:
            data = json.loads(result.stdout)
            for item in data:
                files.add(item["filename"])
        except:
            pass

    return sorted(files)

def fix_chinese_punctuation(content: str) -> str:
    """修复中文标点符号导致的语法错误"""
    # 替换中文标点为英文标点
    replacements = {
        '。': '.',
        '，': ',',
        '：': ':',
        '；': ';',
        '！': '!',
        '？': '?',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '｛': '{',
        '｝': '}',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
    }

    for chinese, english in replacements.items():
        content = content.replace(chinese, english)

    return content

def fix_indentation_errors(content: str) -> str:
    """修复缩进错误"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复混合缩进（空格和制表符混用）
        if '\t' in line and ' ' in line:
            # 将制表符转换为4个空格
            line = line.replace('\t', '    ')

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_multiple_statements(content: str) -> str:
    """修复多语句同行的问题（E701, E702）"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # 检查是否有多条语句在同一行
        # 简单的启发式：如果行中有多个分号，可能需要拆分
        if ';' in stripped and stripped.count(';') > 1:
            # 获取缩进
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent

            # 拆分语句
            statements = [s.strip() for s in stripped.split(';')]
            for i, stmt in enumerate(statements):
                if stmt:  # 跳过空语句
                    if i == 0:
                        fixed_lines.append(indent_str + stmt)
                    else:
                        fixed_lines.append(indent_str + '    ' + stmt)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_bare_except(content: str) -> str:
    """修复裸露的except语句（E722）"""
    # 将 bare except 替换为 except Exception:
    content = re.sub(r'except\s*:\s*$', 'except Exception:', content)
    content = re.sub(r'except\s*:\s*#', 'except Exception:  #', content)
    return content

def fix_ambiguous_variable_names(content: str) -> str:
    """修复模糊的变量名（E741）"""
    # 单字母变量名 l, O, I 容易与数字混淆
    # 这里只替换一些明显的情况
    lines = content.split('\n')
    fixed_lines = []

    # 这是一个简化的实现，实际情况更复杂
    for line in lines:
        # 跳过字符串和注释
        in_string = False
        quote_char = None
        new_line = []
        i = 0

        while i < len(line):
            char = line[i]

            # 处理字符串
            if not in_string and char in ['"', "'"]:
                in_string = True
                quote_char = char
                new_line.append(char)
            elif in_string and char == quote_char:
                # 检查是否是转义的引号
                if i > 0 and line[i-1] != '\\':
                    in_string = False
                    quote_char = None
                new_line.append(char)
            elif not in_string:
                # 在字符串外，检查单字母变量
                if char in ['l', 'O', 'I'] and (i == 0 or not line[i-1].isalnum()):
                    # 检查是否是独立的变量
                    next_char = line[i+1] if i+1 < len(line) else ''
                    prev_char = line[i-1] if i > 0 else ''

                    if not next_char.isalnum() and not prev_char.isalnum():
                        # 替换为更具描述性的名称
                        if char == 'l' and not (prev_char in ' \t(,' and next_char in ' \t),.='):
                            # 可能是列表，但不总是准确
                            pass
                        elif char == 'O' and not (prev_char in ' \t(,' and next_char in ' \t),.='):
                            # 可能是对象，但不总是准确
                            pass
                        elif char == 'I' and not (prev_char in ' \t(,' and next_char in ' \t),.='):
                            # 可能是整数，但不总是准确
                            pass
                        else:
                            new_line.append(char)
                    else:
                        new_line.append(char)
                else:
                    new_line.append(char)
            else:
                new_line.append(char)

            i += 1

        fixed_lines.append(''.join(new_line))

    return '\n'.join(fixed_lines)

def fix_syntax_errors_in_file(file_path: str) -> bool:
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 应用各种修复
        content = fix_chinese_punctuation(content)
        content = fix_indentation_errors(content)
        content = fix_multiple_statements(content)
        content = fix_bare_except(content)
        # 暂时跳过 E741，因为它容易误伤

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"  修复 {file_path} 失败: {e}")
        return False

def main():
    print("🔧 开始修复语法错误...")

    # 获取有语法错误的文件
    error_files = get_files_with_syntax_errors()
    print(f"📊 发现 {len(error_files)} 个文件需要修复")

    if not error_files:
        print("✅ 没有发现语法错误！")
        return

    # 按优先级分组
    core_files = [f for f in error_files if any(x in f for x in [
        'api/', 'services/', 'models/', 'database/', 'cache/', 'monitoring/'
    ])]
    other_files = [f for f in error_files if f not in core_files]

    fixed_count = 0

    # 修复核心文件
    print("\n🔧 修复核心模块...")
    for file_path in core_files[:50]:  # 限制处理数量
        print(f"  修复 {file_path}")
        if fix_syntax_errors_in_file(file_path):
            fixed_count += 1

    # 修复其他文件
    print("\n🔧 修复其他模块...")
    for file_path in other_files[:50]:
        print(f"  修复 {file_path}")
        if fix_syntax_errors_in_file(file_path):
            fixed_count += 1

    # 运行 ruff 的自动修复
    print("\n🔧 运行 ruff 自动修复...")
    subprocess.run(["ruff", "check", "src/", "--select=E701,E702,E703,E722", "--fix"])

    # 检查修复结果
    print("\n📊 检查修复结果...")
    cmd = ["ruff", "check", "src/", "--select=E902,E701,E702,E703,E721,E722,E741", "--output-format=concise"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        errors = result.stdout.strip().split('\n')
        remaining = len([e for e in errors if e])
        print(f"\n✅ 已修复部分错误，剩余 {remaining} 个语法错误")
    else:
        print("\n✅ 所有语法错误已修复！")

    print(f"\n📈 本次修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()