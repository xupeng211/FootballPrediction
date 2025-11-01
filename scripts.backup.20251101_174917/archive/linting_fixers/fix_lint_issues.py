#!/usr/bin/env python3
"""
自动修复lint问题的脚本
根据项目规则，优先修改现有文件而非创建新文件
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set


class LintFixer:
    """Lint问题修复器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fixed_files: Set[str] = set()
        self.errors_fixed = 0

    def get_lint_errors(self) -> Dict[str, List[str]]:
        """获取flake8 lint错误"""
        try:
            result = subprocess.run(
                ["flake8", "tests/", "src/"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            errors_by_file = {}

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            file_path = parts[0]
                            error_code = parts[3].strip()
                            if file_path not in errors_by_file:
                                errors_by_file[file_path] = []
                            errors_by_file[file_path].append(error_code)

            return errors_by_file
        except Exception as e:
            print(f"获取lint错误失败: {e}")
            return {}

    def remove_unused_imports(self, file_path: Path) -> bool:
        """移除未使用的导入 (F401错误)"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 获取该文件的F401错误
            result = subprocess.run(["flake8", str(file_path)], capture_output=True, text=True)

            if not result.stdout:
                return False

            # 解析F401错误行号
            f401_lines = set()
            for line in result.stdout.strip().split("\n"):
                if "F401" in line and str(file_path) in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            line_num = int(parts[1]) - 1  # 转换为0索引
                            f401_lines.add(line_num)
                        except ValueError:
                            continue

            if not f401_lines:
                return False

            # 移除未使用的导入行
            modified = False
            new_lines = []
            for i, line in enumerate(lines):
                if i in f401_lines:
                    print(f"  移除未使用导入: {line.strip()}")
                    modified = True
                    self.errors_fixed += 1
                else:
                    new_lines.append(line)

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                self.fixed_files.add(str(file_path))

            return modified

        except Exception as e:
            print(f"处理文件 {file_path} 失败: {e}")
            return False

    def fix_boolean_comparisons(self, file_path: Path) -> bool:
        """修复布尔值比较问题 (E712)"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 修复 == True 和 == False
            content = re.sub(r"==\s*True\b", " is True", content)
            content = re.sub(r"==\s*False\b", " is False", content)
            content = re.sub(r"!=\s*True\b", " is not True", content)
            content = re.sub(r"!=\s*False\b", " is not False", content)

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  修复布尔比较: {file_path}")
                self.fixed_files.add(str(file_path))
                self.errors_fixed += 1
                return True

            return False

        except Exception as e:
            print(f"修复布尔比较失败 {file_path}: {e}")
            return False

    def fix_bare_except(self, file_path: Path) -> bool:
        """修复裸except语句 (E722)"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            modified = False
            for i, line in enumerate(lines):
                if re.search(r"except\s*:\s*$", line):
                    lines[i] = line.replace("except:", "except Exception:")
                    print(f"  修复裸except: 行 {i+1}")
                    modified = True
                    self.errors_fixed += 1

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                self.fixed_files.add(str(file_path))

            return modified

        except Exception as e:
            print(f"修复裸except失败 {file_path}: {e}")
            return False

    def remove_unused_variables(self, file_path: Path) -> bool:
        """移除未使用的变量 (F841)"""
        try:
            # 获取该文件的F841错误
            result = subprocess.run(["flake8", str(file_path)], capture_output=True, text=True)

            if "F841" not in result.stdout:
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 解析F841错误，提取未使用的变量名
            unused_vars = set()
            for line in result.stdout.strip().split("\n"):
                if "F841" in line:
                    match = re.search(
                        r"local variable '([^']+)' is assigned to but never used", line
                    )
                    if match:
                        unused_vars.add(match.group(1))

            if not unused_vars:
                return False

            # 注释掉未使用的变量赋值
            modified = False
            for i, line in enumerate(lines):
                for var_name in unused_vars:
                    # 匹配变量赋值行
                    if re.search(
                        rf"\b{re.escape(var_name)}\s*=", line
                    ) and not line.strip().startswith("#"):
                        lines[i] = f"# {line}"
                        print(f"  注释未使用变量 '{var_name}': 行 {i+1}")
                        modified = True
                        self.errors_fixed += 1
                        break

            if modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                self.fixed_files.add(str(file_path))

            return modified

        except Exception as e:
            print(f"移除未使用变量失败 {file_path}: {e}")
            return False

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件的lint问题"""
        print(f"正在修复: {file_path}")

        fixed = False
        fixed |= self.remove_unused_imports(file_path)
        fixed |= self.fix_boolean_comparisons(file_path)
        fixed |= self.fix_bare_except(file_path)
        fixed |= self.remove_unused_variables(file_path)

        return fixed

    def run(self) -> None:
        """运行修复流程"""
        print("🔧 开始自动修复lint问题...")

        # 获取所有Python文件
        python_files = []
        for pattern in ["src/**/*.py", "tests/**/*.py"]:
            python_files.extend(self.project_root.glob(pattern))

        print(f"找到 {len(python_files)} 个Python文件")

        # 修复每个文件
        for file_path in python_files:
            if file_path.is_file():
                self.fix_file(file_path)

        print("\n✅ 修复完成!")
        print(f"   修复文件数: {len(self.fixed_files)}")
        print(f"   修复错误数: {self.errors_fixed}")

        if self.fixed_files:
            print("   修复的文件:")
            for file_path in sorted(self.fixed_files):
                print(f"     - {file_path}")


def main():
    """主函数"""
    project_root = Path(__file__).parent
    fixer = LintFixer(project_root)
    fixer.run()


if __name__ == "__main__":
    main()
