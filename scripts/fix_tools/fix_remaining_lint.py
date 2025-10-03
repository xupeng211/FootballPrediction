import os
#!/usr/bin/env python3
"""
修复剩余的lint问题
处理未定义名称、空白行、缩进等问题
"""

import re
import subprocess
from pathlib import Path
from typing import Set


class RemainingLintFixer:
    """修复剩余的lint问题"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fixed_files: Set[str] = set()
        self.errors_fixed = 0

    def fix_whitespace_lines(self, file_path: Path) -> bool:
        """修复空白行包含空格的问题 (W293)"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            modified = False
            for i, line in enumerate(lines):
                # 如果行只包含空格或制表符，清空它
                if line.strip() == "" and len(line) > 1:
                    lines[i] = "\n"
                    modified = True
                    self.errors_fixed += 1

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                self.fixed_files.add(str(file_path))
                print(f"  修复空白行: {file_path}")

            return modified

        except Exception as e:
            print(f"修复空白行失败 {file_path}: {e}")
            return False

    def fix_missing_imports(self, file_path: Path) -> bool:
        """修复缺失的导入 (F821)"""
        try:
            # 获取该文件的F821错误
            result = subprocess.run(
                ["flake8", str(file_path)], capture_output=True, text=True
            )

            if "F821" not in result.stdout:
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            imports_to_add = []

            # 分析需要添加的导入
            for line in result.stdout.strip().split("\n"):
                if "F821" in line and "undefined name" in line:
                    # 提取未定义的名称
                    match = re.search(r"undefined name '([^']+)'", line)
                    if match:
                        undefined_name = match.group(1)

                        # 根据常见的模式添加导入
                        if undefined_name in [
                            "patch",
                            "Mock",
                            "MagicMock",
                            "AsyncMock",
                        ]:
                            if "from unittest.mock import" not in content:
                                imports_to_add.append(
                                    "from unittest.mock import AsyncMock, MagicMock, Mock, patch"
                                )
                        elif undefined_name == "result" and "# result" not in content:
                            # 对于被注释的变量，恢复它们
                            content = content.replace("# result =", "result = os.getenv("FIX_REMAINING_LINT_RESULT_85")\n")
                import_line = -1

                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        import_line = i

                # 在导入区域后添加新的导入
                if import_line >= 0:
                    for imp in set(imports_to_add):  # 去重
                        if imp not in content:
                            lines.insert(import_line + 1, imp)
                            import_line += 1

                content = "\n".join(lines)

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixed_files.add(str(file_path))
                print(f"  修复导入: {file_path}")
                self.errors_fixed += len(imports_to_add)
                return True

            return False

        except Exception as e:
            print(f"修复导入失败 {file_path}: {e}")
            return False

    def fix_indentation_errors(self, file_path: Path) -> bool:
        """修复缩进错误 (E115, E999)"""
        try:
            result = subprocess.run(
                ["flake8", str(file_path)], capture_output=True, text=True
            )

            if "E115" not in result.stdout and "E999" not in result.stdout:
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            modified = False

            # 处理E115错误：注释行应该有适当缩进
            for line_output in result.stdout.strip().split("\n"):
                if (
                    "E115" in line_output
                    and "expected an indented block (comment)" in line_output
                ):
                    parts = line_output.split(":")
                    if len(parts) >= 2:
                        try:
                            line_num = int(parts[1]) - 1  # 转换为0索引
                            if 0 <= line_num < len(lines):
                                # 如果是注释行，添加适当的缩进
                                if lines[line_num].strip().startswith("#"):
                                    lines[line_num] = (
                                        "        " + lines[line_num].lstrip()
                                    )
                                    modified = True
                                    self.errors_fixed += 1
                        except ValueError:
                            continue

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                self.fixed_files.add(str(file_path))
                print(f"  修复缩进: {file_path}")

            return modified

        except Exception as e:
            print(f"修复缩进失败 {file_path}: {e}")
            return False

    def fix_arithmetic_spacing(self, file_path: Path) -> bool:
        """修复算术运算符周围缺少空格 (E226)"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 修复常见的算术运算符空格问题
            # 注意：这里要小心，不要影响字符串或其他上下文
            patterns = [
                (r"(\w)(\+)(\w)", r"\1 \2 \3"),  # word+word -> word + word
                (r"(\w)(-)(\w)", r"\1 \2 \3"),  # word-word -> word - word
                (r"(\w)(\*)(\w)", r"\1 \2 \3"),  # word*word -> word * word
                (r"(\w)(/)(\w)", r"\1 \2 \3"),  # word/word -> word / word
            ]

            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixed_files.add(str(file_path))
                print(f"  修复运算符空格: {file_path}")
                self.errors_fixed += 1
                return True

            return False

        except Exception as e:
            print(f"修复运算符空格失败 {file_path}: {e}")
            return False

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件"""
        print(f"正在修复剩余问题: {file_path}")

        fixed = False
        fixed |= self.fix_whitespace_lines(file_path)
        fixed |= self.fix_missing_imports(file_path)
        fixed |= self.fix_indentation_errors(file_path)
        fixed |= self.fix_arithmetic_spacing(file_path)

        return fixed

    def run(self) -> None:
        """运行修复流程"""
        print("🔧 开始修复剩余的lint问题...")

        # 获取所有Python文件
        python_files = []
        for pattern in ["src/**/*.py", "tests/**/*.py"]:
            python_files.extend(self.project_root.glob(pattern))

        # 只处理有lint错误的文件
        error_files = []
        result = subprocess.run(
            ["flake8", "src/", "tests/"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    file_path = line.split(":", 1)[0]
                    full_path = self.project_root / file_path
                    if full_path not in error_files:
                        error_files.append(full_path)

        print(f"找到 {len(error_files)} 个有lint错误的文件")

        # 修复每个有错误的文件
        for file_path in error_files:
            if file_path.is_file():
                self.fix_file(file_path)

        print("\n✅ 剩余问题修复完成!")
        print(f"   修复文件数: {len(self.fixed_files)}")
        print(f"   修复错误数: {self.errors_fixed}")

        if self.fixed_files:
            print("   修复的文件:")
            for file_path in sorted(self.fixed_files):
                print(f"     - {file_path}")


def main():
    """主函数"""
    project_root = Path(__file__).parent
    fixer = RemainingLintFixer(project_root)
    fixer.run()


if __name__ == "__main__":
    main()
