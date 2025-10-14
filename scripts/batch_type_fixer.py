#!/usr/bin/env python3
"""
批量类型错误修复工具
Batch Type Error Fixer

用于自动化修复常见的 MyPy 类型错误
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent


class TypeFixer:
    """类型错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0

    def fix_missing_return_types(self, file_path: Path) -> int:
        """修复缺少返回类型的函数"""
        content = file_path.read_text(encoding="utf-8")
        fixes = 0

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return 0

        # 查找需要修复的函数
        functions_to_fix = []

        class FunctionVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # 跳过已有返回类型的函数
                if not node.returns:
                    # 跳过私有方法和特殊方法
                    if not node.name.startswith("_") or node.name in [
                        "__init__",
                        "__post_init__",
                    ]:
                        functions_to_fix.append((node.lineno, node.name))

            def visit_AsyncFunctionDef(self, node):
                if not node.returns:
                    if not node.name.startswith("_") or node.name in [
                        "__init__",
                        "__post_init__",
                    ]:
                        functions_to_fix.append((node.lineno, node.name))

        visitor = FunctionVisitor()
        visitor.visit(tree)

        # 修复函数
        lines = content.split("\n")
        for line_no, func_name in reversed(functions_to_fix):
            idx = line_no - 1
            if idx < len(lines):
                line = lines[idx]

                # 确定返回类型
                return_type = "None"
                if func_name == "__init__":
                    return_type = "None"
                elif (
                    "get_" in func_name or "find_" in func_name or "load_" in func_name
                ):
                    return_type = "Optional[Any]"
                elif "is_" in func_name or "has_" in func_name or "can_" in func_name:
                    return_type = "bool"
                elif "list" in func_name or "get_all" in func_name:
                    return_type = "List[Any]"
                elif (
                    "create" in func_name or "build" in func_name or "make" in func_name
                ):
                    return_type = "Any"
                elif func_name.startswith("test_") or func_name.startswith("_test"):
                    return_type = "None"

                # 添加返回类型
                if line.strip().endswith(":"):
                    lines[idx] = line[:-1] + f" -> {return_type}:"
                    fixes += 1

        if fixes > 0:
            file_path.write_text("\n".join(lines), encoding="utf-8")

        return fixes

    def fix_undefined_variables(self, file_path: Path) -> int:
        """修复未定义的变量错误"""
        content = file_path.read_text(encoding="utf-8")
        fixes = 0

        # 常见的未定义变量修复
        fixes_map = {
            # 常见变量名错误
            r"\b_result\b(?!\s*#)": "result",
            r"\b_stats\b(?!\s*#)": "stats",
            r"\b_config\b(?!\s*#)": "config",
            # 常见参数错误
            r"_data\s*=": "data=",
            r"_metadata\s*=": "metadata=",
            r"_config\s*=": "config=",
            # 常见类型错误
            r"\bDict\[(?!\s*\])": "Dict[str, Any]",
            r"\bList\[(?!\s*\])": "List[Any]",
            r"\bTuple\[(?!\s*\])": "Tuple[Any, ...]",
        }

        for pattern, replacement in fixes_map.items():
            count = len(re.findall(pattern, content))
            if count > 0:
                content = re.sub(pattern, replacement, content)
                fixes += count

        if fixes > 0:
            file_path.write_text(content, encoding="utf-8")

        return fixes

    def add_missing_imports(self, file_path: Path) -> int:
        """添加缺失的导入"""
        content = file_path.read_text(encoding="utf-8")
        fixes = 0

        # 检查需要添加的导入
        needed_imports = set()

        # 检查类型使用
        if "Dict[" in content and "from typing import" in content:
            if "Dict" not in content.split("from typing import")[1].split("\n")[0]:
                needed_imports.add("Dict")

        if "List[" in content and "from typing import" in content:
            if "List" not in content.split("from typing import")[1].split("\n")[0]:
                needed_imports.add("List")

        if "Optional[" in content and "from typing import" in content:
            if "Optional" not in content.split("from typing import")[1].split("\n")[0]:
                needed_imports.add("Optional")

        if "Union[" in content and "from typing import" in content:
            if "Union" not in content.split("from typing import")[1].split("\n")[0]:
                needed_imports.add("Union")

        if "Any" in content and "from typing import" in content:
            if "Any" not in content.split("from typing import")[1].split("\n")[0]:
                needed_imports.add("Any")

        # 添加导入
        if needed_imports:
            lines = content.split("\n")

            # 找到导入位置
            import_line_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("from typing import"):
                    import_line_idx = i
                    break

            if import_line_idx >= 0:
                # 修改现有导入行
                current_import = lines[import_line_idx]
                imports = current_import.replace("from typing import", "").strip()
                imports_list = [
                    imp.strip() for imp in imports.split(",") if imp.strip()
                ]

                for imp in needed_imports:
                    if imp not in imports_list:
                        imports_list.append(imp)

                imports_list.sort()
                lines[import_line_idx] = f"from typing import {', '.join(imports_list)}"
                fixes = len(needed_imports)

                content = "\n".join(lines)
                file_path.write_text(content, encoding="utf-8")

        return fixes

    def fix_type_annotations(self, file_path: Path) -> int:
        """修复类型注解"""
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        fixes = 0

        # 修复常见的类型注解错误
        type_fixes = [
            # 修复 Optional 类型
            (
                r"(\w+):\s*Optional\[(.+?)\]\s*=\s*None",
                r"\1: Optional[\2] | None = None",
            ),
            # 修复 Union 类型
            (r"Optional\[(.+?)\]\s*\|\s*None", r"Optional[\1]"),
            # 修复泛型类型
            (r"dict\s*\[", "dict["),
            (r"Dict\s*\[", "Dict["),
            (r"list\s*\[", "list["),
            (r"List\s*\[", "List["),
            # 修复 Callable
            (r"Callable\s*\[\[\s*\]", "Callable[[], Any]"),
            # 修复返回类型
            (r"def\s+(\w+)\s*\([^)]*\)\s*:\s*$", r"def \1(self) -> None:"),
        ]

        for pattern, replacement in type_fixes:
            content = re.sub(pattern, replacement, content)

        # 统计修复数量
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            fixes = 1

        return fixes

    def process_file(self, file_path: Path) -> int:
        """处理单个文件"""
        total_fixes = 0

        # 1. 修复缺少返回类型
        fixes = self.fix_missing_return_types(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"  ✓ 添加了 {fixes} 个返回类型")

        # 2. 修复未定义变量
        fixes = self.fix_undefined_variables(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"  ✓ 修复了 {fixes} 个变量错误")

        # 3. 添加缺失导入
        fixes = self.add_missing_imports(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"  ✓ 添加了 {fixes} 个导入")

        # 4. 修复类型注解
        fixes = self.fix_type_annotations(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"  ✓ 修复了 {fixes} 个类型注解")

        return total_fixes

    def process_all(self, target_dirs: List[str]) -> None:
        """批量处理所有文件"""
        print("🔧 批量修复类型错误")
        print("=" * 50)

        total_files = 0
        total_fixes = 0

        for target_dir in target_dirs:
            target_path = PROJECT_ROOT / target_dir
            if not target_path.exists():
                continue

            print(f"\n📁 处理目录: {target_dir}")

            for py_file in target_path.glob("**/*.py"):
                if py_file.name == "__init__.py":
                    continue

                try:
                    fixes = self.process_file(py_file)
                    if fixes > 0:
                        total_files += 1
                        total_fixes += fixes
                except Exception as e:
                    print(f"  ✗ 处理失败 {py_file.relative_to(PROJECT_ROOT)}: {e}")

        print("\n" + "=" * 50)
        print("✅ 批量修复完成！")
        print(f"  • 处理文件数: {total_files}")
        print(f"  • 修复总数: {total_fixes}")


def main():
    """主函数"""
    fixer = TypeFixer()

    # 优先处理核心模块
    target_dirs = [
        "src/core",
        "src/services",
        "src/api",
        "src/domain",
        "src/repositories",
        "src/database/repositories",
    ]

    fixer.process_all(target_dirs)

    # 验证修复效果
    print("\n🔍 验证修复效果...")
    result = subprocess.run(
        [
            "mypy",
            "src/core",
            "src/services",
            "src/api",
            "src/domain",
            "src/repositories",
            "src/database/repositories",
        ],
        capture_output=True,
        text=True,
    )

    errors = result.stdout.count("error:")
    print(f"剩余错误数: {errors}")

    if errors == 0:
        print("✅ 核心模块类型检查通过！")
    else:
        # 显示前几个错误
        error_lines = [line for line in result.stdout.split("\n") if "error:" in line][
            :10
        ]
        for error in error_lines:
            print(f"  • {error}")


if __name__ == "__main__":
    main()
