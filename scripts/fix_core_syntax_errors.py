#!/usr/bin/env python3
"""
修复核心模块的语法错误
"""

import ast
import os
import re
from pathlib import Path

def fix_core_module_syntax(file_path):
    """修复核心模块的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        modified = False

        # 1. 修复未闭合的字符串
        lines = content.split('\n')
        in_string = False
        string_char = None
        string_start_line = -1

        for i, line in enumerate(lines):
            # 跳过注释
            if line.strip().startswith('#'):
                continue

            # 检查字符串
            for j, char in enumerate(line):
                if char in ['"', "'"] and not in_string:
                    # 检查是否是转义的
                    if j > 0 and line[j-1] == '\\':
                        continue
                    in_string = True
                    string_char = char
                    string_start_line = i
                elif char == string_char and in_string:
                    # 检查是否是转义的
                    if j > 0 and line[j-1] == '\\':
                        continue
                    in_string = False
                    string_char = None

        # 如果有未闭合的字符串，在文件末尾添加闭合
        if in_string:
            lines.append(string_char)  # 添加闭合引号
            content = '\n'.join(lines)
            modified = True

        # 2. 修复括号不匹配（简单情况）
        # 检查常见的括号不匹配模式
        open_brackets = content.count('[') - content.count(']') + \
                        content.count('(') - content.count(')')
        if open_brackets > 0:
            # 如果有多余的开括号，在文件末尾添加闭括号
            content += ']' * open_brackets
            modified = True

        # 3. 修复类型注解中缺失的括号
        content = re.sub(r':\s*Optional\[Dict\[str,\s*Any\](?!\])\s*$',
                        r': Optional[Dict[str, Any]]', content)
        content = re.sub(r':\s*List\[Dict\[str,\s*Any\](?!\])\s*$',
                        r': List[Dict[str, Any]]', content)
        content = re.sub(r':\s*Dict\[str,\s*Any\](?!\])\s*$',
                        r': Dict[str, Any]]', content)

        # 4. 修复缺失的冒号
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # 检查def行但缺少冒号
            if 'def ' in line and '->' in line and not line.strip().endswith(':'):
                if not line.rstrip().endswith(']'):  # 类型注解已经正确
                    lines[i] = line.rstrip() + ':'
                    modified = True

        if modified:
            content = '\n'.join(lines)

        # 5. 修复赋值表达式错误
        # 将 x[y] = value 改为 x[y] == value（在某些上下文中）
        # 这需要更精确的上下文判断，暂时跳过

        # 验证语法
        try:
            ast.parse(content)
            if content != original:
                print(f"✓ 修复: {file_path}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
        except SyntaxError as e:
            print(f"✗ 仍有错误: {file_path} - {e}")
            # 尝试更激进的修复
            return fix_with_heuristics(file_path, content)

    except Exception as e:
        print(f"✗ 处理文件出错 {file_path}: {e}")
        return False


def fix_with_heuristics(file_path, content):
    """使用启发式方法修复语法错误"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复常见错误模式
        # 1. 修复缺少冒号的def
        if 'def ' in line and '->' in line and not line.strip().endswith(':'):
            # 检查下一行是否是文档字符串或函数体
            if '"""' in line or "'''" in line:
                # 当前行有字符串，需要特殊处理
                pass
            else:
                line = line.rstrip() + ':'

        # 2. 修复未闭合的函数定义
        if line.strip().startswith('def ') and '->' in line:
            # 检查类型注解是否完整
            if '->' in line and line.count('[') != line.count(']'):
                # 找到最后一个开括号，添加闭括号
                last_bracket = line.rfind('[')
                if last_bracket > line.rfind(']'):
                    line = line + ']'

        fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    # 最后验证
    try:
        ast.parse(content)
        print(f"✓ 二次修复: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except SyntaxError:
        print(f"✗ 无法修复: {file_path}")
        return False


def main():
    """主函数"""
    print("开始修复核心模块语法错误...")

    # 核心模块列表
    core_modules = [
        'src/core',
        'src/api',
        'src/domain',
        'src/services',
        'src/database',
        'src/cache',
        'src/collectors',
        'src/data',
        'src/events',
        'src/repositories',
        'src/models'
    ]

    fixed_count = 0
    error_count = 0

    for module in core_modules:
        if os.path.exists(module):
            print(f"\n修复模块: {module}")
            for root, dirs, files in os.walk(module):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        if fix_core_module_syntax(file_path):
                            fixed_count += 1
                        else:
                            error_count += 1

    print(f"\n修复完成:")
    print(f"  成功修复: {fixed_count} 个文件")
    print(f"  仍有错误: {error_count} 个文件")


if __name__ == "__main__":
    main()
