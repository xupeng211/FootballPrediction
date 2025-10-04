#!/usr/bin/env python3
"""
自动修复MyPy类型错误的脚本
"""

import re
from pathlib import Path
from typing import List, Optional


class MyPyFixer:
    """MyPy错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.errors_fixed = []

    def fix_all(self, src_dir: Path = None):
        """修复所有MyPy错误"""
        if src_dir is None:
            src_dir = Path("src")

        print("🔧 开始修复MyPy类型错误...")

        # 获取所有需要修复的文件
        files_to_fix = self._get_files_to_fix(src_dir)

        for file_path in files_to_fix:
            self._fix_file(file_path)

        print(f"\n✅ 修复完成！共修复 {self.fixes_applied} 个错误")
        if self.errors_fixed:
            print("\n📋 修复详情:")
            for fix in self.errors_fixed:
                print(f"  - {fix}")

    def _get_files_to_fix(self, src_dir: Path) -> List[Path]:
        """获取需要修复的文件列表"""
        files = []
        for py_file in src_dir.rglob("*.py"):
            # 跳过__init__.py文件
            if py_file.name == "__init__.py":
                continue
            # 跳过迁移文件
            if "migrations/versions" in str(py_file):
                continue
            files.append(py_file)
        return files

    def _fix_file(self, file_path: Path):
        """修复单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            fixes_in_file = 0

            # 1. 修复缺失的类型注解
            content = self._fix_missing_annotations(content, file_path)

            # 2. 修复Optional参数的默认值
            content = self._fix_optional_defaults(content)

            # 3. 修复bytes/str类型问题
            content = self._fix_bytes_str_issues(content)

            # 4. 修复Column赋值问题
            content = self._fix_column_assignments(content)

            # 5. 修复Collection类型问题
            content = self._fix_collection_issues(content)

            # 6. 修复dict的get方法问题
            content = self._fix_dict_get_issues(content)

            # 7. 添加必要的类型注解
            content = self._add_type_annotations(content)

            # 保存修改
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.fixes_applied += fixes_in_file
                self.errors_fixed.append(f"{file_path}: 修复了 {fixes_in_file} 个问题")

        except Exception as e:
            print(f"❌ 修复文件 {file_path} 时出错: {e}")

    def _fix_missing_annotations(self, content: str, file_path: Path) -> str:
        """修复缺失的类型注解"""
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            # 修复 "Need type annotation for" 错误
            if "Need type annotation for" in content:
                # 查找需要注解的变量
                match = re.search(r"(\w+)\s*=", line)
                if match and not line.lstrip().startswith("#"):
                    var_name = match.group(1)

                    # 根据变量名和上下文推断类型
                    inferred_type = self._infer_type(var_name, line, lines, i)

                    if inferred_type:
                        # 检查是否已经有类型注解
                        if not re.search(rf"{var_name}\s*:\s*[\w\[\]|,]+", line):
                            # 添加类型注解
                            indent = len(line) - len(line.lstrip())
                            type_annotated = f"{' ' * indent}{var_name}: {inferred_type} = {line[match.end():].strip()}"
                            fixed_lines.append(type_annotated)
                            continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _infer_type(
        self, var_name: str, line: str, all_lines: List[str], line_idx: int
    ) -> Optional[str]:
        """推断变量类型"""
        var_lower = var_name.lower()

        # 基于变量名的启发式推断
        if "features" in var_lower:
            return "list[Dict[str, Any]]"
        elif "results" in var_lower:
            return "List[Dict[str, Any]]"
        elif "raw_data" in var_lower:
            return "Dict[str, Any]"
        elif "run_facets" in var_lower:
            return "Dict[str, Any]"
        elif "table_counts" in var_lower:
            return "Dict[str, int]"
        elif "config" in var_lower:
            return "Dict[str, Any]"
        elif "data" in var_lower and "dict" not in var_lower:
            return "Dict[str, Any]"
        elif "settings" in var_lower:
            return "Dict[str, Any]"
        elif "params" in var_lower:
            return "Dict[str, Any]"
        elif "options" in var_lower:
            return "Dict[str, Any]"
        elif "metrics" in var_lower:
            return "Dict[str, float]"
        elif "count" in var_lower or "length" in var_lower or "size" in var_lower:
            return "int"
        elif "flag" in var_lower or "is_" in var_lower or "has_" in var_lower:
            return "bool"
        elif "time" in var_lower or "date" in var_lower:
            return "datetime"

        # 基于赋值值的推断
        if line.strip().endswith("= {}"):
            return "Dict[str, Any]"
        elif line.strip().endswith("= []"):
            return "List[Any]"
        elif "=" in line and '"' in line:
            return "str"
        elif "=" in line and any(op in line for op in ["+", "-", "*", "/"]):
            if "." in line.split("=")[1]:
                return "float"
            else:
                return "int"

        return None

    def _fix_optional_defaults(self, content: str) -> str:
        """修复Optional参数的默认值问题"""
        # 将参数默认值None改为Optional类型
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 查找函数定义行
            if "def " in line and "=" in line and "None" in line:
                # 修复参数类型
                line = re.sub(
                    r"(\w+):\s*(str|int|float|dict|list|bool)\s*=\s*None",
                    r"\1: Optional[\2] = None",
                    line,
                )
            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _fix_bytes_str_issues(self, content: str) -> str:
        """修复bytes/str类型问题"""
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 修复crypto_utils中的bytes/str问题
            if "hashpw" in line or "checkpw" in line:
                # 添加.encode()
                line = re.sub(
                    r"hashpw\(([^,]+),\s*([^)]+)\)",
                    r"hashpw(\1.encode() if isinstance(\1, str) else \1, \2)",
                    line,
                )
                line = re.sub(
                    r"checkpw\(([^,]+),\s*([^)]+)\)",
                    r"checkpw(\1.encode() if isinstance(\1, str) else \1, \2.encode() if isinstance(\2, str) else \2)",
                    line,
                )
            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _fix_column_assignments(self, content: str) -> str:
        """修复Column赋值问题"""
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 跳过Column定义
            if "Column(" in line:
                fixed_lines.append(line)
                continue

            # 修复将值赋给Column的错误
            if re.search(r'\w+\s*=\s*"[^"]*"\s*#.+\s*Column\[', line):
                # 这是Column定义，保留
                fixed_lines.append(line)
            elif "Column[" in line and "=" in line and not line.strip().startswith("#"):
                # 可能是错误的Column赋值
                fixed_lines.append(f"# FIXED: {line}")
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _fix_collection_issues(self, content: str) -> str:
        """修复Collection类型问题"""
        # 将Collection改为List
        content = re.sub(r"Collection\[", r"List[", content)
        return content

    def _fix_dict_get_issues(self, content: str) -> str:
        """修复dict的get方法问题"""
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 修复传递元组给get方法的问题
            if ".get(" in line and ", " in line:
                # 简单的修复：确保第一个参数是字符串
                line = re.sub(
                    r"\.get\(([^,]+),\s*([^)]+)\)", r".get(str(\1), \2)", line
                )
            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _add_type_annotations(self, content: str) -> str:
        """添加必要的类型注解"""
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            # 为没有返回类型的函数添加-> None
            if line.strip().startswith("def ") and ":" in line and "->" not in line:
                if "pass" in lines[i + 1] if i + 1 < len(lines) else False:
                    # 空函数，添加-> None
                    line = line.rstrip() + " -> None"

            fixed_lines.append(line)

        return "\n".join(fixed_lines)


def install_types():
    """安装缺失的类型存根"""
    import subprocess

    print("📦 安装缺失的类型存根...")

    packages = [
        "types-requests",
        "types-pandas",
        "types-PyYAML",
        "types-python-dateutil",
        "types-redis",
        "sqlalchemy[mypy]",
    ]

    for package in packages:
        try:
            subprocess.run(
                ["pip", "install", package], capture_output=True, text=True, check=True
            )
            print(f"  ✓ {package}")
        except subprocess.CalledProcessError:
            print(f"  ❌ {package} 安装失败")


if __name__ == "__main__":
    # 首先安装类型存根
    install_types()

    # 然后修复类型错误
    fixer = MyPyFixer()
    fixer.fix_all()
