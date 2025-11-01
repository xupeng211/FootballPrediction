#!/usr/bin/env python3
"""
批量修复Python文件缩进错误
Batch fix Python file indentation errors
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple


class IndentationFixer:
    """缩进错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_fixed = []

    def find_indentation_errors(self) -> List[Tuple[str, int]]:
        """查找所有缩进错误"""
        errors = []

        # 使用py_compile查找语法错误
        for root, dirs, files in os.walk("src/"):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        # 尝试编译文件
                        with open(file_path, "rb") as f:
                            compile(f.read(), file_path, "exec")
                    except IndentationError as e:
                        # 提取行号
                        if hasattr(e, "lineno"):
                            errors.append((file_path, e.lineno))
                        elif "line" in str(e):
                            # 尝试从错误消息中提取行号
                            match = re.search(r"line (\d+)", str(e))
                            if match:
                                errors.append((file_path, int(match.group(1))))
                        # 忽略其他类型的错误
                        pass

        return errors

    def fix_function_definition_indentation(self, file_path: str, line_num: int) -> bool:
        """修复函数定义的缩进问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_num <= len(lines):
                line = lines[line_num - 1]

                # 检查是否是函数定义行且有缩进问题
                if "def " in line and ":" in line and '"""' in line:
                    # 修复模式: def name(param):    """docstring"""
                    match = re.match(r'^(\s*)(def\s+[^:]+):\s*)(.*?)\s*"""([^"]*)"""', line)
                    if match:
                        indent, func_def, middle, docstring = match.groups()
                        # 重新格式化行
                        new_line = f'{indent}{func_def}\n{indent}    """{docstring}"""\n'
                        if middle.strip():
                            new_line = (
                                f'{indent}{func_def} {middle}\n{indent}    """{docstring}"""\n'
                            )

                        # 替换原行
                        lines[line_num - 1] = new_line

                        # 写回文件
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.writelines(lines)

                        return True

            return False

        except Exception as e:
            print(f"❌ 修复失败 {file_path}:{line_num}: {e}")
            return False

    def fix_method_definition_indentation(self, file_path: str, line_num: int) -> bool:
        """修复方法定义的缩进问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")

            if line_num <= len(lines):
                line = lines[line_num - 1]

                # 检查是否是方法定义且缩进有问题
                if re.search(r'^\s*def\s+\w+\(.*\):\s*"""', line):
                    # 修复缩进问题
                    # 找到正确的缩进级别
                    indent_match = re.match(r"^(\s*)", line)
                    if indent_match:
                        indent = indent_match.group(1)

                        # 分割函数定义和文档字符串
                        parts = line.split('"""', 1)
                        if len(parts) == 2:
                            func_def = parts[0].rstrip()
                            docstring_part = parts[1].rstrip()

                            # 重新格式化
                            if docstring_part.strip():
                                new_lines = [f"{func_def}", f'{indent}    """{docstring_part}']
                            else:
                                new_lines = [f"{func_def}", f'{indent}    """""']

                            # 替换原行
                            lines[line_num - 1 : line_num] = new_lines

                            # 写回文件
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write("\n".join(lines))

                            return True

            return False

        except Exception as e:
            print(f"❌ 修复失败 {file_path}:{line_num}: {e}")
            return False

    def fix_class_method_indentation(self, file_path: str, line_num: int) -> bool:
        """修复类方法缩进问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_num <= len(lines):
                line = lines[line_num - 1]

                # 检查类方法缩进问题
                if re.search(r'^\s*def\s+\w+\(self.*\):\s*"""', line):
                    # 提取缩进级别
                    indent_match = re.match(r"^(\s*)def\s+", line)
                    if indent_match:
                        indent = indent_match.group(1)

                        # 检查是否需要添加额外的缩进
                        if len(indent) < 4:  # 方法应该至少有4个空格缩进
                            # 添加正确的缩进
                            new_indent = "    " + indent
                            new_line = line.replace(indent, new_indent, 1)
                            lines[line_num - 1] = new_line

                            # 写回文件
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)

                            return True

            return False

        except Exception as e:
            print(f"❌ 修复失败 {file_path}:{line_num}: {e}")
            return False

    def run_autopep8_fix(self, file_path: str) -> bool:
        """使用autopep8修复格式问题"""
        try:
            # 尝试使用autopep8修复
            result = subprocess.run(
                ["python", "-m", "autopep8", "--in-place", "--aggressive", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
            try:
                pass
    def fix_all_indentation_errors(self):
        """修复所有缩进错误"""
        print("🔍 查找缩进错误...")
        errors = self.find_indentation_errors()

        if not errors:
            print("✅ 没有发现缩进错误")
            return

        print(f"📊 发现 {len(errors)} 个缩进错误")

        # 修复策略
        fix_strategies = [
            self.fix_function_definition_indentation,
            self.fix_method_definition_indentation,
            self.fix_class_method_indentation,
        ]

        for file_path, line_num in errors:
            print(f"\n🔧 修复 {file_path}:{line_num}")

            fixed = False
            for strategy in fix_strategies:
                if strategy(file_path, line_num):
                    fixed = True
                    self.fixes_applied += 1
                    self.files_fixed.append(file_path)
                    print(f"✅ 修复成功: {file_path}:{line_num}")
                    break

            if not fixed:
                # 尝试使用autopep8
                if self.run_autopep8_fix(file_path):
                    fixed = True
                    self.fixes_applied += 1
                    self.files_fixed.append(file_path)
                    print(f"✅ autopep8修复成功: {file_path}")
                else:
                    print(f"⚠️  修复失败: {file_path}:{line_num}")

    def verify_fixes(self) -> int:
        """验证修复结果"""
        print("\n🔍 验证修复结果...")
        remaining_errors = self.find_indentation_errors()

        if remaining_errors:
            print(f"⚠️  仍有 {len(remaining_errors)} 个缩进错误:")
            for file_path, line_num in remaining_errors[:10]:  # 只显示前10个
                print(f"   {file_path}:{line_num}")
            if len(remaining_errors) > 10:
                print(f"   ... 还有 {len(remaining_errors) - 10} 个错误")
        else:
            print("✅ 所有缩进错误已修复")

        return len(remaining_errors)


def main():
    """主函数"""
    print("🔧 Python文件缩进错误修复工具")
    print("=" * 60)

    fixer = IndentationFixer()

    # 修复所有缩进错误
    fixer.fix_all_indentation_errors()

    # 验证修复结果
    remaining_errors = fixer.verify_fixes()

    print(f"\n{'='*60}")
    print("📊 修复统计报告")
    print(f"{'='*60}")
    print(f"   修复数量: {fixer.fixes_applied}")
    print(f"   修复文件: {len(set(fixer.files_fixed))}")
    print(f"   剩余错误: {remaining_errors}")

    if remaining_errors == 0:
        print("🎉 所有缩进错误已成功修复！")
    else:
        print(f"⚠️  还有 {remaining_errors} 个错误需要手动修复")


if __name__ == "__main__":
    main()
