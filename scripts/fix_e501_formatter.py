#!/usr/bin/env python3
"""
E501格式错误修复工具
专门处理行长度超过限制的格式错误
"""

import os
import re
from pathlib import Path

def fix_long_lines_in_file(file_path: str, max_length: int = 88) -> int:
    """修复单个文件中的长行问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0

    fixed_count = 0
    new_lines = []

    for i, line in enumerate(lines):
        # 跳过注释行和已经合适长度的行
        if len(line.rstrip()) <= max_length or line.strip().startswith('#'):
            new_lines.append(line)
            continue

        # 特殊处理HTML/CSS模板中的长行
        if '{%' in line or '{{' in line or '<' in line and '>' in line:
            fixed_line = fix_html_css_line(line, max_length)
            if fixed_line != line:
                fixed_count += 1
            new_lines.extend(fixed_line)
        # 处理Python长行
        elif not line.strip().startswith(('<',
    'body {',
    'container {',
    'header {',
    'content {')):
            fixed_line = fix_python_long_line(line, max_length)
            if fixed_line != line:
                fixed_count += 1
            new_lines.extend(fixed_line)
        else:
            new_lines.append(line)

    # 只有在有修复时才写回文件
    if fixed_count > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"修复 {file_path} 中的 {fixed_count} 个长行问题")
        except Exception as e:
            print(f"写入文件 {file_path} 失败: {e}")
            return 0

    return fixed_count

def fix_html_css_line(line: str, max_length: int) -> list:
    """修复HTML/CSS模板中的长行"""
    stripped = line.rstrip()

    # 处理CSS属性长行
    if '{' in line and '}' in line and ':' in line:
        # 分解CSS属性为多行
        parts = stripped.split(';')
        result_lines = []
        for part in parts:
            if part.strip():
                if part.strip().startswith('}'):
                    result_lines.append(part + '\n')
                else:
                    result_lines.append('    ' + part.strip() + ';\n')
        return result_lines

    # 处理HTML属性长行
    if '<' in line and '>' not in line:
        # HTML标签开始，保持原样
        return [line]

    # 处理内联样式
    if 'style=' in line:
        # 提取样式部分进行分解
        style_match = re.search(r'syle="([^"]*)"', line)
        if style_match:
            style_content = style_match.group(1)
            properties = style_content.split(';')
            formatted_style = '\n        '.join([f'{prop.strip()};' for prop in properties if prop.strip()])
            new_line = line.replace(style_content, formatted_style)
            return [new_line]

    return [line]

def fix_python_long_line(line: str, max_length: int) -> list:
    """修复Python长行"""
    stripped = line.rstrip()

    # 处理函数调用参数过长
    if '(' in stripped and ')' in stripped and not stripped.strip().startswith('#'):
        # 尝试在逗号处分行
        if ',' in stripped:
            parts = stripped.split(',')
            if len(parts) > 1:
                result_lines = []
                # 第一行
                result_lines.append(parts[0] + ',\n')
                # 中间行，添加适当缩进
                indent = '    '  # 4个空格缩进
                for part in parts[1:-1]:
                    result_lines.append(f'{indent}{part.strip()},\n')
                # 最后一行
                result_lines.append(f'{indent}{parts[-1].strip()}\n')
                return result_lines

    # 处理字符串拼接过长
    if ' + ' in stripped or 'f"' in stripped:
        # 对于长字符串或f-string，保持原样，让Black处理
        return [line]

    # 处理长的import语句
    if stripped.strip().startswith('import ') and ',' in stripped:
        parts = stripped.split(',')
        if len(parts) > 1:
            result_lines = []
            # 第一行
            result_lines.append(parts[0] + ' (\n')
            # 中间行
            for part in parts[1:-1]:
                result_lines.append(f'    {part.strip()},\n')
            # 最后一行
            result_lines.append(f'    {parts[-1].strip()}\n)\n')
            return result_lines

    # 默认情况下保持原样
    return [line]

def fix_all_e501_errors(project_root: str = ".") -> int:
    """修复整个项目的E501错误"""
    project_path = Path(project_root)
    total_fixed = 0

    # 获取所有有E501错误的文件
    print("正在分析项目中的E501错误...")
    import subprocess

    try:
        # 使用ruff获取所有E501错误
        result = subprocess.run(
            ['ruff', 'check', '--select=E501', '--output-format=concise', project_root],
            capture_output=True,
            text=True
        )

        # 解析结果获取文件列表
        files_with_errors = set()
        for line in result.stdout.split('\n'):
            if line.strip() and ':' in line:
                file_path = line.split(':')[0]
                files_with_errors.add(file_path)

        print(f"发现 {len(files_with_errors)} 个文件存在E501错误")

        # 逐个修复文件
        for file_path in sorted(files_with_errors):
            if os.path.exists(file_path):
                fixed = fix_long_lines_in_file(file_path)
                total_fixed += fixed

    except Exception as e:
        print(f"运行ruff检查失败: {e}")

    return total_fixed

def main():
    """主函数"""
    print("开始修复E501格式错误...")

    total_fixed = fix_all_e501_errors()

    print(f"\n总共修复了 {total_fixed} 个长行问题")

    # 再次运行检查验证结果
    print("\n验证修复结果...")
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E501', '--output-format=concise', '.'],
            capture_output=True,
            text=True
        )
        remaining_errors = len([line for line in result.stdout.split('\n') if line.strip()])
        print(f"剩余 E501 错误: {remaining_errors}")
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    import subprocess
    main()