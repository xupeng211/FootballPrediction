#!/usr/bin/env python3
"""
技术债务修复脚本
用于批量修复Phase 1.5的遗留语法错误
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple


def get_files_with_errors() -> List[str]:
    """获取所有有错误的文件列表"""
    cmd = [
        "ruff",
        "check",
        "src/",
        "--select=SyntaxError,E402,F401,F811",
        "--output-format=json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    files = set()
    if result.stdout:
        import json

        try:
            data = json.loads(result.stdout)
            for item in data:
                files.add(item["filename"])
        except Exception:
            pass

    return sorted(files)


def fix_docstring_syntax(content: str) -> str:
    """修复文档字符串语法错误"""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        # 修复未闭合的三引号
        if '"""' in line and line.count('"""') % 2 != 0:
            # 检查是否需要闭合
            if not line.strip().endswith('"""'):
                line = line + '"""'

        # 修复中文文档字符串导致的语法错误
        if re.match(r'^\s*[^\s""\']+[：:]', line) and fixed_lines:
            # 可能是文档字符串的一部分，添加引号
            prev_line = fixed_lines[-1] if fixed_lines else ""
            if '"""' in prev_line and not prev_line.strip().endswith('"""'):
                # 将当前行作为文档字符串的一部分
                line = f"    {line}"

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_import_errors(content: str) -> str:
    """修复导入错误"""
    lines = content.split("\n")

    # 提取所有导入语句
    imports = []
    code_lines = []
    in_docstring = False
    docstring_quotes = None

    for line in lines:
        stripped = line.strip()

        # 处理文档字符串
        if '"""' in line or "'''" in line:
            if not in_docstring:
                in_docstring = True
                docstring_quotes = '"""' if '"""' in line else "'''"
            elif line.count(docstring_quotes) % 2 != 0:
                in_docstring = False
                docstring_quotes = None

        # 收集导入语句（不在文档字符串内）
        if not in_docstring and (
            stripped.startswith("import ") or stripped.startswith("from ")
        ):
            imports.append(line)
        elif not in_docstring and not stripped.startswith("#"):
            code_lines.append(line)
        else:
            code_lines.append(line)

    # 重新构建内容
    # 1. 文件头部（注释、文档字符串）
    header = []
    for line in code_lines[:10]:  # 前10行通常是头部
        if (
            line.strip().startswith("#")
            or '"""' in line
            or "'''" in line
            or not line.strip()
        ):
            header.append(line)
        else:
            break

    # 2. 导入语句
    import_section = []
    if imports:
        import_section = imports + [""]

    # 3. 其余代码
    remaining_code = code_lines[len(header) :]

    # 组合所有部分
    result = "\n".join(header)
    if header and import_section:
        result += "\n"
    if import_section:
        result += "\n".join(import_section)
    if remaining_code:
        result += "\n".join(remaining_code)

    return result


def fix_syntax_errors_in_file(file_path: str) -> bool:
    """修复单个文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 1. 修复文档字符串
        content = fix_docstring_syntax(content)

        # 2. 修复导入错误
        if (
            "E402"
            in subprocess.run(
                ["ruff", "check", file_path, "--select=E402"],
                capture_output=True,
                text=True,
            ).stdout
        ):
            content = fix_import_errors(content)

        # 3. 修复常见的语法问题
        # 修复未闭合的括号
        content = re.sub(r",\s*\n\s*([a-zA-Z_])", r",\n        \1", content)

        # 修复类型注解中的错误
        content = re.sub(r"(\w+)\s*:\s*:\s*(\w+)", r"\1: \2", content)

        # 写回文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"  修复 {file_path} 失败: {e}")
        return False


def main():
    print("🔧 开始修复技术债务...")

    # 获取所有有错误的文件
    error_files = get_files_with_errors()
    print(f"📊 发现 {len(error_files)} 个文件需要修复")

    # 按优先级分组
    core_files = [
        f for f in error_files if any(x in f for x in ["api/", "services/", "models/"])
    ]
    [f for f in error_files if f not in core_files]

    fixed_count = 0

    # 修复核心文件
    print("\n🔧 修复核心模块...")
    for file_path in core_files[:20]:  # 先处理前20个
        print(f"  修复 {file_path}")
        if fix_syntax_errors_in_file(file_path):
            fixed_count += 1

    # 运行自动修复
    print("\n🔧 运行 ruff 自动修复...")
    subprocess.run(["ruff", "check", "src/", "--select=F401,F811", "--fix"])

    # 检查修复结果
    print("\n📊 检查修复结果...")
    cmd = [
        "ruff",
        "check",
        "src/",
        "--select=SyntaxError,E402,F401,F811",
        "--output-format=concise",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        errors = result.stdout.strip().split("\n")
        remaining = len([e for e in errors if e])
        print(f"\n✅ 已修复部分错误，剩余 {remaining} 个错误")

        # 统计各类错误
        syntax_errors = len([e for e in errors if "SyntaxError" in e])
        e402_errors = len([e for e in errors if "E402" in e])
        f401_errors = len([e for e in errors if "F401" in e])
        f811_errors = len([e for e in errors if "F811" in e])

        print(f"   - 语法错误: {syntax_errors}")
        print(f"   - E402 导入错误: {e402_errors}")
        print(f"   - F401 未使用导入: {f401_errors}")
        print(f"   - F811 重复定义: {f811_errors}")
    else:
        print("\n✅ 所有错误已修复！")

    print(f"\n📈 本次修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
