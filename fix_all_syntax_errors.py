#!/usr/bin/env python3
"""
批量修复所有Python文件中的语法错误
"""

import ast
import re
from pathlib import Path


def fix_file(file_path: Path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复模式1: 类型注解中缺少的 ]
        # Dict[str, Dict[str, Any] =  ->  Dict[str, Dict[str, Any]] =
        content = re.sub(
            r"(\w+\s*:\s*Dict\[[^\]]*,\s*Dict\[str,\s*Any)\s*=\s*", r"\1]] = ", content
        )

        # 修复模式2: 其他类型注解
        # List[str] =  ->  List[str]] =
        content = re.sub(r"(\w+\s*:\s*\w+\[[^\]]*)\s*=\s*", r"\1] = ", content)

        # 修复模式3: f-string路由定义
        content = re.sub(
            r'@router\.(get|post|put|delete|patch)\(f"/([^"]+)"',
            r'@router.\1("/\2"',
            content,
        )

        # 修复模式4: ff-字符串
        content = re.sub(r'ff"([^"]*)"', r'f"\1"', content)

        # 修复模式5: 闭括号不匹配
        # 查找并修复 )=  应该是 ]) =
        content = re.sub(r"\)\s*=\s*{\}", "]) = {}", content)

        # 修复模式6: 多余的]]
        content = re.sub(r"\]\]\]", "]]", content)
        content = re.sub(r"\]\]\)", "])", content)

        # 修复模式7: Union类型导入问题
        if "Union[" in content and "from typing import Union" not in content:
            if "from typing import" in content:
                content = re.sub(
                    r"from typing import ([^\n]+)",
                    r"from typing import Union, \1",
                    content,
                )

        # 如果有修改，写回文件
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def main():
    """主函数"""
    src_dir = Path("src")
    fixed_count = 0

    # 忽略的目录
    ignore_dirs = {"__pycache__", ".pytest_cache", ".venv", "stubs"}

    print("开始扫描并修复Python语法错误...")

    for py_file in src_dir.rglob("*.py"):
        # 跳过忽略的目录
        if any(ignore_dir in str(py_file) for ignore_dir in ignore_dirs):
            continue

        # 尝试解析语法
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            print(f"\n发现语法错误: {py_file}:{e.lineno} - {e.msg}")

            # 尝试修复
            if fix_file(py_file):
                print("  ✓ 已修复")
                fixed_count += 1

                # 验证修复
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    ast.parse(content)
                    print("  ✓ 验证通过")
                except SyntaxError as e2:
                    print(f"  ✗ 仍有错误: {e2.msg}")
            else:
                print("  ✗ 无法自动修复")
        except Exception as e:
            print(f"Error checking {py_file}: {e}")

    print(f"\n总计修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
