#!/usr/bin/env python3
"""
自动化修复Python语法错误脚本
"""

import ast
import re
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple


class SyntaxErrorFixer:
    """语法错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.errors_fixed = {}

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 应用各种修复
            content = self.fix_missing_brackets(content)
            content = self.fix_extra_brackets(content)
            content = self.fix_mismatched_brackets(content)
            content = self.fix_optional_type_annotations(content)
            content = self.fix_dict_type_annotations(content)
            content = self.fix_list_type_annotations(content)
            content = self.fix_union_type_annotations(content)
            content = self.fix_function_parameter_types(content)
            content = self.fix_class_attribute_types(content)
            content = self.fix_generic_type_annotations(content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✓ Fixed: {file_path}")
                return True

        except SyntaxError as e:
            print(f"✗ Syntax error in {file_path}: {e}")
            self.errors_fixed[str(file_path)] = str(e)
        except Exception as e:
            print(f"✗ Error processing {file_path}: {e}")

        return False

    def fix_missing_brackets(self, content: str) -> str:
        """修复缺失的右括号"""
        # 修复 Optional[Dict[str, Any  -> Optional[Dict[str, Any]]
        content = re.sub(
            r"Optional\[Dict\[str,\s*Any\s*$",
            "Optional[Dict[str, Any]]",
            content,
            flags=re.MULTILINE,
        )

        # 修复 Dict[str, Any  -> Dict[str, Any]
        content = re.sub(
            r"Dict\[str,\s*Any\s*$", "Dict[str, Any]", content, flags=re.MULTILINE
        )

        # 修复 List[Any  -> List[Any]
        content = re.sub(r"List\[Any\s*$", "List[Any]", content, flags=re.MULTILINE)

        # 修复 Union[str, Path  -> Union[str, Path]
        content = re.sub(
            r"Union\[str,\s*Path\s*$", "Union[str, Path]", content, flags=re.MULTILINE
        )

        return content

    def fix_extra_brackets(self, content: str) -> str:
        """修复多余的右括号"""
        # 修复 ]] -> ]
        content = re.sub(r"\]\]", "]", content)

        # 修复 ]]] -> ]
        content = re.sub(r"\]\]\]", "]", content)

        # 修复 ]] = None -> ] = None
        content = re.sub(r"\]\]\s*=\s*None", "] = None", content)

        # 修复 ]]] = None -> ] = None
        content = re.sub(r"\]\]\]\s*=\s*None", "] = None", content)

        return content

    def fix_mismatched_brackets(self, content: str) -> str:
        """修复括号不匹配"""
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            # 修复 Optional[Dict[str, Any] ]] = None
            line = re.sub(
                r"Optional\[Dict\[str,\s*Any\]\s*\]\]\s*=\s*None",
                "Optional[Dict[str, Any]] = None",
                line,
            )

            # 修复 Dict[str, Any] ]] = None
            line = re.sub(
                r"Dict\[str,\s*Any\]\s*\]\]\s*=\s*None", "Dict[str, Any] = None", line
            )

            # 修复 List[Any] ]] = None
            line = re.sub(r"List\[Any\]\s*\]\]\s*=\s*None", "List[Any] = None", line)

            new_lines.append(line)

        return "\n".join(new_lines)

    def fix_optional_type_annotations(self, content: str) -> str:
        """修复Optional类型注解"""
        # 修复 Optional[Dict[str, Any] = None
        content = re.sub(
            r"Optional\[Dict\[str,\s*Any\]\s*=\s*None",
            "Optional[Dict[str, Any]] = None",
            content,
        )

        # 修复 Optional[List[Any] = None
        content = re.sub(
            r"Optional\[List\[Any\]\s*=\s*None", "Optional[List[Any]] = None", content
        )

        # 修复 Optional[Union[str, int] = None
        content = re.sub(
            r"Optional\[Union\[([^\]]+)\]\s*=\s*None",
            r"Optional[Union[\1]] = None",
            content,
        )

        return content

    def fix_dict_type_annotations(self, content: str) -> str:
        """修复Dict类型注解"""
        # 修复 Dict[str, Any = None
        content = re.sub(
            r"Dict\[str,\s*Any\]\s*=\s*None", "Dict[str, Any] = None", content
        )

        # 修复 Dict[str, Any] = None
        content = re.sub(
            r"Dict\[str,\s*Any\]\s*=\s*None", "Dict[str, Any] = None", content
        )

        return content

    def fix_list_type_annotations(self, content: str) -> str:
        """修复List类型注解"""
        # 修复 List[Any = None
        content = re.sub(r"List\[Any\]\s*=\s*None", "List[Any] = None", content)

        return content

    def fix_union_type_annotations(self, content: str) -> str:
        """修复Union类型注解"""
        # 修复 Union[str, Path = None
        content = re.sub(
            r"Union\[str,\s*Path\]\s*=\s*None", "Union[str, Path] = None", content
        )

        return content

    def fix_function_parameter_types(self, content: str) -> str:
        """修复函数参数类型注解"""
        # 修复函数参数中的类型注解
        # param: Optional[Dict[str, Any = None -> param: Optional[Dict[str, Any]] = None
        content = re.sub(
            r"(\w+):\s*Optional\[Dict\[str,\s*Any\]\s*=\s*None",
            r"\1: Optional[Dict[str, Any]] = None",
            content,
        )

        # param: Dict[str, Any = None -> param: Dict[str, Any] = None
        content = re.sub(
            r"(\w+):\s*Dict\[str,\s*Any\]\s*=\s*None",
            r"\1: Dict[str, Any] = None",
            content,
        )

        return content

    def fix_class_attribute_types(self, content: str) -> str:
        """修复类属性类型注解"""
        # 修复类属性定义中的类型注解
        # attr: Optional[Dict[str, Any = None -> attr: Optional[Dict[str, Any]] = None
        content = re.sub(
            r"(\w+):\s*Optional\[Dict\[str,\s*Any\]\s*=\s*None",
            r"\1: Optional[Dict[str, Any]] = None",
            content,
        )

        # 修复类属性中的多重括号
        # details: Optional[Dict[str, Any] ]] = None -> details: Optional[Dict[str, Any]] = None
        content = re.sub(
            r"(\w+):\s*Optional\[Dict\[str,\s*Any\]\s*\]\]\s*=\s*None",
            r"\1: Optional[Dict[str, Any]] = None",
            content,
        )

        # 修复三重括号
        # details: Optional[Dict[str, Any] ]]] = None -> details: Optional[Dict[str, Any]] = None
        content = re.sub(
            r"(\w+):\s*Optional\[Dict\[str,\s*Any\]\s*\]\]\]\s*=\s*None",
            r"\1: Optional[Dict[str, Any]] = None",
            content,
        )

        return content

    def fix_generic_type_annotations(self, content: str) -> str:
        """修复泛型类型注解"""
        # 修复 Type[Any][T] -> Type[Any, T]
        content = re.sub(r"Type\[Any\]\[(\w+)\]", r"Type[Any, \1]", content)

        # 修复 Dict[str, Any][Type] -> Dict[Type
        content = re.sub(r"Dict\[str,\s*Any\]\[(\w+)\]", r"Dict[\1", content)

        # 修复 Dict[str, Any][Type, Service] -> Dict[Type, Service]
        content = re.sub(
            r"Dict\[str,\s*Any\]\[(\w+),\s*(\w+)\]", r"Dict[\1, \2]", content
        )

        return content

    def fix_module(self, module_name: str) -> int:
        """修复整个模块"""
        module_path = Path(f"src/{module_name}")
        if not module_path.exists():
            print(f"Module {module_name} not found")
            return 0

        fixed_count = 0
        print(f"\n=== 修复模块: {module_name} ===")

        # 处理所有Python文件
        for py_file in module_path.rglob("*.py"):
            if self.fix_file(py_file):
                fixed_count += 1

        print(f"模块 {module_name} 修复完成，共修复 {fixed_count} 个文件")
        return fixed_count


def main():
    """主函数"""
    fixer = SyntaxErrorFixer()

    # 定义修复顺序（从最基础的模块开始）
    modules = [
        "utils",
        "core",
        "adapters",
        "database",
        "api",
        "services",
        "domain",
        "cache",
        "tasks",
        "monitoring",
    ]

    print("开始修复Python语法错误...")
    print("=" * 50)

    total_fixed = 0
    for module in modules:
        total_fixed += fixer.fix_module(module)

    print("\n" + "=" * 50)
    print("修复完成！")
    print(f"总计修复文件数: {total_fixed}")

    if fixer.errors_fixed:
        print("\n仍有错误的文件:")
        for file_path, error in fixer.errors_fixed.items():
            print(f"  {file_path}: {error}")


if __name__ == "__main__":
    main()
