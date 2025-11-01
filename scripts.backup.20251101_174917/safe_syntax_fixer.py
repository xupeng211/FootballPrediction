#!/usr/bin/env python3
"""
安全的语法修复工具 - 只修复明确的语法错误
"""

import re
import ast
import os
from pathlib import Path


def check_syntax(content):
    """检查Python语法是否正确"""
    try:
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, e
    except Exception as e:
        return False, f"Parse error: {e}"


def fix_specific_syntax_issues(content, file_path):
    """修复特定的、明确的语法问题"""
    changes_made = []

    # 修复1: 字典语法 {"key": value,) → {"key": value}
    def fix_dict_brackets(text):
        # 只修复行尾多余的逗号，不影响其他结构
        pattern = r'(\{"[^}]*),\s*\}'
        return re.sub(pattern, r"\1}", text)

    new_content = fix_dict_brackets(content)
    if new_content != content:
        changes_made.append("Fixed dictionary syntax (trailing comma)")

    # 修复2: 缺失的冒号 def method(...) -> Type"" pass → def method(...) -> Type:\n    """docstring"""\n    pass
    def fix_method_colon(text):
        # 只修复方法定义中缺失的冒号
        pattern = r'(def\s+\w+\([^)]*\)\s*->\s*[^:\n]+)""([^"]*)""\s*pass'
        replacement = r'\1:\n    """\2"""\n    pass'
        return re.sub(pattern, replacement, text, flags=re.MULTILINE)

    new_content = fix_method_colon(new_content)
    if new_content != content:
        changes_made.append("Fixed method definition colon")

    # 修复3: 装饰器格式 @abstractmethodasync def → @abstractmethod\n    async def
    def fix_decorator_format(text):
        pattern = r"@abstractmethodasync def"
        replacement = "@abstractmethod\n    async def"
        return text.replace(pattern, replacement)

    new_content = fix_decorator_format(new_content)
    if new_content != content:
        changes_made.append("Fixed decorator formatting")

    # 修复4: __all__ = [) → __all__ = []
    def fix_all_assignment(text):
        pattern = r"__all__\s*=\s*\[\)"
        return text.replace(pattern, "__all__ = []")

    new_content = fix_all_assignment(new_content)
    if new_content != content:
        changes_made.append("Fixed __all__ assignment")

    # 修复5: 删除重复的return语句
    def fix_duplicate_return(text):
        # 查找并删除重复的return语句
        lines = text.split("\n")
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 检查是否是return语句的开始
            if line.startswith("return {") and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # 如果下一行也是return，合并它们
                if next_line.startswith("return {"):
                    # 找到完整的return块并合并
                    return_block = line
                    j = i + 1
                    brace_count = line.count("{") - line.count("}")
                    while j < len(lines) and brace_count > 0:
                        return_block += "\n" + lines[j]
                        brace_count += lines[j].count("{") - lines[j].count("}")
                        j += 1
                    new_lines.append(return_block)
                    i = j
                    continue
            new_lines.append(lines[i])
            i += 1

        return "\n".join(new_lines)

    new_content = fix_duplicate_return(new_content)
    if new_content != content:
        changes_made.append("Fixed duplicate return statements")

    return new_content, changes_made


def fix_file_safely(file_path):
    """安全地修复单个文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    # 检查原始语法
    is_valid, error = check_syntax(content)
    if is_valid:
        return False, "No syntax errors found"

    # 应用修复
    fixed_content, changes = fix_specific_syntax_issues(content, file_path)

    # 验证修复结果
    is_valid, error = check_syntax(fixed_content)

    if is_valid:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True, f"Fixed: {'; '.join(changes)}"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, f"Fix failed: {error}"


def find_syntax_error_files(directory):
    """找到有语法错误的文件"""
    error_files = []

    for py_file in Path(directory).rglob("*.py"):
        if any(skip in str(py_file) for skip in [".venv", "__pycache__", ".git"]):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            is_valid, error = check_syntax(content)
            if not is_valid:
                error_files.append((str(py_file), str(error)))
        except Exception as e:
            error_files.append((str(py_file), f"Read error: {e}"))

    return error_files


def main():
    """主函数"""
    print("🔧 开始安全的语法修复...")

    src_dir = "/home/user/projects/FootballPrediction/src"

    # 第一步：找到所有有语法错误的文件
    print("\n🔍 检查语法错误...")
    error_files = find_syntax_error_files(src_dir)

    if not error_files:
        print("✅ 没有发现语法错误！")
        return

    print(f"📊 发现 {len(error_files)} 个文件有语法错误")

    # 第二步：逐个修复
    fixed_count = 0
    failed_count = 0

    for file_path, error in error_files[:10]:  # 限制前10个文件
        print(f"\n🔧 修复: {os.path.relpath(file_path, src_dir)}")
        print(f"   错误: {error}")

        success, message = fix_file_safely(file_path)
        if success:
            fixed_count += 1
            print(f"   ✅ {message}")
        else:
            failed_count += 1
            print(f"   ❌ {message}")

    print("\n📊 修复结果:")
    print(f"✅ 成功修复: {fixed_count} 个文件")
    print(f"❌ 修复失败: {failed_count} 个文件")
    print(f"📋 剩余待修复: {len(error_files) - 10} 个文件")


if __name__ == "__main__":
    main()
