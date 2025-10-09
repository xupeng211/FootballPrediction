#!/usr/bin/env python3
"""
最终的语法错误修复脚本
处理剩余的1964个语法错误
"""

import os
import re
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Set

def get_syntax_errors() -> Dict[str, List[Dict]]:
    """获取所有语法错误的详细信息"""
    cmd = [
        "ruff", "check", "src/",
        "--select=E902,E701,E702,E703,E721,E722,E741",
        "--output-format=json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    errors_by_file = {}
    if result.stdout:
        try:
            data = json.loads(result.stdout)
            for item in data:
                filename = item["filename"]
                if filename not in errors_by_file:
                    errors_by_file[filename] = []
                errors_by_file[filename].append(item)
        except Exception as e:
            print(f"解析错误输出失败: {e}")

    return errors_by_file

def fix_docstring_issues(content: str) -> str:
    """修复文档字符串相关问题"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 跳过空行和注释
        if not line.strip() or line.strip().startswith('#'):
            fixed_lines.append(line)
            i += 1
            continue

        # 检查是否有未闭合的文档字符串
        if '"""' in line or "'''" in line:
            # 计算引号数量
            triple_double = line.count('"""')
            triple_single = line.count("'''")

            # 如果引号数量是奇数，说明未闭合
            if triple_double % 2 != 0 or triple_single % 2 != 0:
                # 检查下一行是否是代码
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and not next_line.strip().startswith('#'):
                        # 这可能是未闭合的文档字符串，添加闭合引号
                        if not line.rstrip().endswith('"""') and not line.rstrip().endswith("'''"):
                            line = line.rstrip() + ('"""' if '"""' in line else "'''")

        fixed_lines.append(line)
        i += 1

    return '\n'.join(fixed_lines)

def fix_import_placement(content: str) -> str:
    """修复导入语句位置问题"""
    lines = content.split('\n')
    fixed_lines = []

    # 分离导入语句和代码
    imports = []
    code = []
    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        # 处理文档字符串
        if '"""' in line or "'''" in line:
            if not in_docstring:
                in_docstring = True
                docstring_char = '"""' if '"""' in line else "'''"
                # 检查是否在同一行闭合
                if line.count(docstring_char) >= 2:
                    in_docstring = False
                    docstring_char = None
            else:
                if line.count(docstring_char) >= 2:
                    in_docstring = False
                    docstring_char = None

        # 收集导入语句（不在文档字符串内）
        if not in_docstring and (stripped.startswith('import ') or stripped.startswith('from ')):
            imports.append(line)
        elif not in_docstring and stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
            # 代码开始
            code.extend(lines[lines.index(line):])
            break
        else:
            if in_docstring or not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                fixed_lines.append(line)

    # 添加导入语句
    if imports:
        # 确保导入语句前有空行
        if fixed_lines and fixed_lines[-1].strip():
            fixed_lines.append('')
        fixed_lines.extend(imports)
        if code:
            fixed_lines.append('')

    # 添加剩余代码
    fixed_lines.extend(code)

    return '\n'.join(fixed_lines)

def fix_colon_issues(content: str) -> str:
    """修复冒号相关的问题"""
    # 修复函数定义后的冒号
    content = re.sub(r'def\s+(\w+)\s*\([^)]*\)\s*->\s*[^:]+\n\s*\n',
                     lambda m: m.group(0).rstrip() + ':\n', content)

    # 修复类定义后的冒号
    content = re.sub(r'class\s+(\w+)\s*(\([^)]*\))?\s*\n\s*\n',
                     lambda m: m.group(0).rstrip() + ':\n', content)

    return content

def fix_tuple_annotation(content: str) -> str:
    """修复元组类型注解问题"""
    # 修复 Only single target (not tuple) can be annotated
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 检查是否有错误的元组注解
        if '->' in line and '(' in line and ')' in line:
            # 简单的启发式检查
            if re.search(r'->\s*\([^)]+\)\s*:', line):
                # 这可能是需要修复的元组注解
                # 转换为正确的形式
                line = re.sub(r'->\s*\(([^)]+)\)\s*:', r' -> \1:', line)

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_file_errors(file_path: str, errors: List[Dict]) -> bool:
    """修复单个文件的错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 应用各种修复
        content = fix_docstring_issues(content)
        content = fix_import_placement(content)
        content = fix_colon_issues(content)
        content = fix_tuple_annotation(content)

        # 特殊处理：如果文件看起来完全损坏，尝试恢复
        if content.count('"""') > 10 or content.count("'''") > 10:
            # 文档字符串太多，可能是损坏的
            # 简单清理：移除孤立的文档字符串标记
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                # 跳过只有文档字符串标记的行
                if stripped in ['"""', "'''", '"""', "'''"]:
                    continue
                cleaned_lines.append(line)
            content = '\n'.join(cleaned_lines)

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
    print("🔧 开始最终语法错误修复...")

    # 获取所有错误
    errors_by_file = get_syntax_errors()
    total_files = len(errors_by_file)
    total_errors = sum(len(errors) for errors in errors_by_file.values())

    print(f"📊 发现 {total_errors} 个错误在 {total_files} 个文件中")

    if total_errors == 0:
        print("✅ 没有发现语法错误！")
        return

    # 按优先级排序文件
    priority_files = []
    other_files = []

    for filename in errors_by_file.keys():
        if any(x in filename for x in [
            'api/', 'services/', 'models/', 'database/', 'cache/', 'monitoring/'
        ]):
            priority_files.append(filename)
        else:
            other_files.append(filename)

    # 修复文件
    fixed_count = 0
    all_files = priority_files + other_files

    for i, file_path in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}] 修复: {file_path}")
        errors = errors_by_file[file_path]

        if fix_file_errors(file_path, errors):
            fixed_count += 1
            print(f"  ✓ 已修复")
        else:
            print(f"  - 无需修复或修复失败")

    # 运行 ruff 的自动修复
    print("\n🔧 运行 ruff 自动修复...")
    subprocess.run(["ruff", "check", "src/", "--select=E701,E702,E703,E722", "--fix"],
                   capture_output=True)

    # 检查最终结果
    print("\n📊 检查最终结果...")
    cmd = ["ruff", "check", "src/", "--select=E902,E701,E702,E703,E721,E722,E741", "--output-format=concise"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        errors = result.stdout.strip().split('\n')
        remaining = len([e for e in errors if e])
        print(f"\n✅ 已修复部分错误，剩余 {remaining} 个语法错误")

        # 显示错误最多的文件
        print("\n📋 错误最多的文件（前10个）:")
        error_counts = {}
        for line in errors:
            if ':' in line:
                filename = line.split(':')[0]
                error_counts[filename] = error_counts.get(filename, 0) + 1

        sorted_files = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        for filename, count in sorted_files[:10]:
            print(f"  {filename}: {count} 个错误")
    else:
        print("\n✅ 所有语法错误已修复！")

    print(f"\n📈 本次修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()