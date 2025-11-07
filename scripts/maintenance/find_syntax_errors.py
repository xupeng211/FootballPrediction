#!/usr/bin/env python3
"""
语法错误检查工具
Find Syntax Errors Tool

检查所有Python文件的语法错误，特别针对测试文件进行优化
"""

import ast
import sys
from pathlib import Path


def check_syntax(file_path: Path) -> list[str]:
    """检查单个文件的语法错误"""
    errors = []

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 尝试解析AST
        ast.parse(content, filename=str(file_path))

    except SyntaxError as e:
        errors.append(f"语法错误 {file_path}:{e.lineno}:{e.offset}: {e.msg}")
    except UnicodeDecodeError as e:
        errors.append(f"编码错误 {file_path}: {e}")
    except Exception as e:
        errors.append(f"其他错误 {file_path}: {e}")

    return errors


def find_python_files(directory: Path) -> list[Path]:
    """查找所有Python文件"""
    python_files = []

    # 查找所有.py文件
    for pattern in ["**/*.py"]:
        python_files.extend(directory.glob(pattern))

    # 排除一些特殊目录
    exclude_dirs = {
        ".git", "__pycache__", ".pytest_cache", "htmlcov",
        ".venv", "venv", "env", ".tox", "build", "dist"
    }

    filtered_files = []
    for file_path in python_files:
        if not any(exclude_dir in file_path.parts for exclude_dir in exclude_dirs):
            filtered_files.append(file_path)

    return sorted(filtered_files)


def main():
    """主函数"""
    project_root = Path.cwd()

    print(f"🔍 在 {project_root} 中检查语法错误...")

    # 查找所有Python文件
    python_files = find_python_files(project_root)

    total_files = 0
    error_files = 0
    total_errors = 0

    for file_path in python_files:
        total_files += 1
        errors = check_syntax(file_path)

        if errors:
            error_files += 1
            total_errors += len(errors)
            print(f"\n❌ {file_path.relative_to(project_root)}")
            for error in errors:
                print(f"   {error}")

    print("\n📊 检查结果:")
    print(f"   总文件数: {total_files}")
    print(f"   错误文件: {error_files}")
    print(f"   错误总数: {total_errors}")

    if total_errors > 0:
        print(f"\n❌ 发现 {total_errors} 个语法错误")
        sys.exit(1)
    else:
        print("\n✅ 所有文件语法检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
