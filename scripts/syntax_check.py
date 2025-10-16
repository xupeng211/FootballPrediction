#!/usr/bin/env python3
"""
语法检查脚本 - 用于CI/CD流水线
检查所有Python文件的语法错误
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """检查单个文件的语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试解析AST
        ast.parse(content)
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """主函数"""
    print("=" * 60)
    print("Python语法检查工具")
    print("=" * 60)

    # 查找所有Python文件
    src_dir = Path("src")
    python_files = list(src_dir.rglob("*.py"))

    errors = []
    success_count = 0

    print(f"\n检查 {len(python_files)} 个Python文件...\n")

    for file_path in sorted(python_files):
        is_valid, message = check_syntax(file_path)
        relative_path = file_path.relative_to(Path.cwd())

        if is_valid:
            print(f"✓ {relative_path}")
            success_count += 1
        else:
            print(f"✗ {relative_path}: {message}")
            errors.append((str(relative_path), message))

    # 输出结果
    print("\n" + "=" * 60)
    print("检查结果:")
    print(f"  总文件数: {len(python_files)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {len(errors)}")

    if errors:
        print("\n语法错误的文件:")
        for file_path, error in errors[:10]:  # 只显示前10个
            print(f"  - {file_path}: {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个文件有错误")

    # 设置退出码
    if errors:
        print("\n❌ 存在语法错误！")
        sys.exit(1)
    else:
        print("\n✅ 所有文件语法正确！")
        sys.exit(0)


if __name__ == "__main__":
    main()