#!/usr/bin/env python3
"""
批量修复所有语法错误
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set


class SyntaxFixer:
    """语法错误修复器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.fixes_applied = 0
        self.errors_fixed = {}
        self.remaining_errors = []

    def find_syntax_errors(self) -> List[Tuple[str, int, str]]:
        """查找所有语法错误"""
        errors = []

        for py_file in self.src_dir.rglob("*.py"):
            if self.should_skip_file(py_file):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                errors.append((str(py_file), e.lineno, e.msg))

        return errors

    def should_skip_file(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        skip_patterns = [
            "__pycache__",
            ".pytest_cache",
            "venv",
            ".venv",
            "stubs",
            "migrations",
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def fix_file(self, file_path: str, line_num: int, error_msg: str) -> bool:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            content = "".join(lines)
            original_content = content

            # 修复模式1: 类型注解中缺少的 ]
            if "unmatched ']'" in error_msg or "'[' was never closed" in error_msg:
                content = self.fix_missing_brackets(content, line_num)

            # 修复模式2: 类型注解中多余的 ]
            elif (
                "cannot assign to subscript" in error_msg
                and "Maybe you meant '==' instead of '='" in error_msg
            ):
                content = self.fix_assignment_type_annotation(content, line_num)

            # 修复模式3: f-string格式错误
            elif "expected ':'" in error_msg:
                content = self.fix_fstring_format(content, line_num)

            # 修复模式4: 导入错误
            elif "not defined" in error_msg:
                content = self.fix_import_errors(content, error_msg)

            # 修复模式5: 函数定义错误
            elif (
                "invalid syntax" in error_msg
                and "Perhaps you forgot a comma" in error_msg
            ):
                content = self.fix_comma_errors(content, line_num)

            # 写回文件
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"修复文件失败 {file_path}: {e}")

        return False

    def fix_missing_brackets(self, content: str, line_num: int) -> str:
        """修复缺失的括号"""
        lines = content.split("\n")
        error_line = lines[line_num - 1] if line_num <= len(lines) else ""

        # 修复 Dict[str, Any] 模式
        if re.search(r"Dict\[str,\s*Any\](?!=])", error_line):
            content = re.sub(r"(Dict\[str,\s*Any\])(?!=])", r"\1]", content)

        # 修复 List[str] 模式
        if re.search(r"List\[\w+\](?!=])", error_line):
            content = re.sub(r"(List\[\w+\])(?!=])", r"\1]", content)

        # 修复 Optional[Dict[str, Any]] 模式
        if re.search(r"Optional\[Dict\[str,\s*Any\](?!=])", error_line):
            content = re.sub(r"(Optional\[Dict\[str,\s*Any\])(?!=])", r"\1]", content)

        # 修复 Union[str, Path] 模式
        if re.search(r"Union\[[^\]]+(?!=])", error_line):
            content = re.sub(r"(Union\[[^\]]+)(?!=])", r"\1]", content)

        return content

    def fix_assignment_type_annotation(self, content: str, line_num: int) -> str:
        """修复赋值语句中的类型注解错误"""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # 修复模式: self._field: Dict[str, List[float] = value
            if re.search(r":\s*\w+\[[^\]]*\]\s*=\s*[^=]", line):
                # 找到类型注解部分
                match = re.search(r"(\w+\s*:\s*)(\w+\[[^\]]*\])\s*=", line)
                if match:
                    # 确保有正确的括号匹配
                    type_annotation = match.group(2)
                    if type_annotation.count("[") > type_annotation.count("]"):
                        # 添加缺失的括号
                        fixed_type = type_annotation + "]"
                        line = line.replace(type_annotation, fixed_type)
                        lines[i] = line

        return "\n".join(lines)

    def fix_fstring_format(self, content: str, line_num: int) -> str:
        """修复f-string格式错误"""
        # 修复 @router.get(f"/path/{id}") 模式
        content = re.sub(
            r'@router\.(get|post|put|delete|patch)\(f"([^"]+)"',
            r'@router.\1("/\2"',
            content,
        )

        # 修复 ff" 字符串
        content = re.sub(r'ff"([^"]*)"', r'f"\1"', content)

        return content

    def fix_import_errors(self, content: str, error_msg: str) -> str:
        """修复导入错误"""
        # 修复 Optional 未定义
        if "Optional" in error_msg:
            if "from typing import" in content:
                # 检查是否已经导入了Optional
                if "from typing import" in content and "Optional" not in content:
                    content = re.sub(
                        r"from typing import ([^\n]+)",
                        r"from typing import Optional, \1",
                        content,
                    )
            else:
                # 添加导入语句
                first_import = content.find("import")
                if first_import != -1:
                    content = (
                        content[:first_import]
                        + "from typing import Optional\n"
                        + content[first_import:]
                    )

        # 修复 Union 未定义
        elif "Union" in error_msg:
            if "from typing import" in content and "Union" not in content:
                content = re.sub(
                    r"from typing import ([^\n]+)",
                    r"from typing import Union, \1",
                    content,
                )

        # 修复 ClassVar 未定义
        elif "ClassVar" in error_msg:
            if "from typing import" in content and "ClassVar" not in content:
                content = re.sub(
                    r"from typing import ([^\n]+)",
                    r"from typing import ClassVar, \1",
                    content,
                )

        return content

    def fix_comma_errors(self, content: str, line_num: int) -> str:
        """修复逗号错误"""
        lines = content.split("\n")

        for i in range(max(0, line_num - 2), min(len(lines), line_num + 2)):
            line = lines[i]

            # 修复函数参数列表中的逗号
            if re.search(r"\w+\s*:\s*\w+\[\w+\]\s*=\s*\w+\s*(?!,)", line):
                # 在参数后添加逗号
                line = re.sub(
                    r"(\w+\s*:\s*\w+\[\w+\]\s*=\s*\w+)(\s*\))", r"\1,\2", line
                )
                lines[i] = line

        return "\n".join(lines)

    def apply_generic_fixes(self, file_path: str) -> int:
        """应用通用修复"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复所有已知的模式
        fixes = [
            # Dict[str, Any] 类型注解
            (r":\s*Dict\[str,\s*Any\]\s*=\s*([^=\n]+)", r": Dict[str, Any] = \1"),
            # List[str] 类型注解
            (r":\s*List\[(\w+)\]\s*=\s*([^=\n]+)", r": List[\1] = \2"),
            # Optional[Dict] 类型注解
            (
                r":\s*Optional\[Dict\[str,\s*Any\]\]\s*=\s*([^=\n]+)",
                r": Optional[Dict[str, Any]] = \1",
            ),
            # f-string 路由
            (r'@router\.(get|post|put|delete|patch)\(f"/([^"]+)"', r'@router.\1("/\2"'),
            # dict[] 类型提示
            (r"dict\[str,\s*Any\]", "Dict[str, Any]"),
            # list[] 类型提示
            (r"list\[(\w+)\]", r"List[\1]"),
            # ff- 字符串
            (r'ff"([^"]*)"', r'f"\1"'),
        ]

        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)

        # 写回文件
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return 1

        return 0

    def run(self) -> Dict:
        """运行修复流程"""
        print("🔧 开始修复语法错误...")

        # 1. 查找所有语法错误
        errors = self.find_syntax_errors()
        total_errors = len(errors)
        print(f"找到 {total_errors} 个语法错误")

        # 2. 应用通用修复
        print("\n📝 应用通用修复...")
        for py_file in self.src_dir.rglob("*.py"):
            if self.should_skip_file(py_file):
                continue
            fixes = self.apply_generic_fixes(str(py_file))
            if fixes > 0:
                self.fixes_applied += fixes
                print(f"  ✓ {py_file.name}: {fixes} 个通用修复")

        # 3. 重新检查错误
        remaining_errors = self.find_syntax_errors()
        print(f"\n剩余 {len(remaining_errors)} 个错误需要手动修复")

        # 4. 尝试修复剩余错误
        print("\n🔨 尝试修复剩余错误...")
        for file_path, line_num, error_msg in remaining_errors[:20]:  # 只处理前20个
            if self.fix_file(file_path, line_num, error_msg):
                self.fixes_applied += 1
                print(f"  ✓ {Path(file_path).name}:{line_num} - {error_msg}")
                self.errors_fixed[file_path] = self.errors_fixed.get(file_path, 0) + 1
            else:
                self.remaining_errors.append((file_path, line_num, error_msg))
                print(f"  ✗ {Path(file_path).name}:{line_num} - {error_msg}")

        # 5. 输出报告
        print("\n" + "=" * 60)
        print("修复报告")
        print("=" * 60)
        print(f"原始错误数: {total_errors}")
        print(f"已修复: {self.fixes_applied}")
        print(f"剩余错误: {len(self.remaining_errors)}")

        if self.remaining_errors:
            print("\n需要手动修复的错误:")
            for file_path, line_num, error_msg in self.remaining_errors:
                print(f"  • {file_path}:{line_num} - {error_msg}")

        return {
            "total_errors": total_errors,
            "fixed": self.fixes_applied,
            "remaining": len(self.remaining_errors),
            "remaining_errors": self.remaining_errors,
        }


def main():
    """主函数"""
    import sys

    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print("FootballPrediction 语法错误修复工具")
    print("=" * 60)

    # 创建修复器并运行
    fixer = SyntaxFixer()
    result = fixer.run()

    # 返回退出码
    sys.exit(0 if result["remaining"] == 0 else 1)


if __name__ == "__main__":
    main()
