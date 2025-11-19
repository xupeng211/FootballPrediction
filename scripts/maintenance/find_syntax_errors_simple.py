#!/usr/bin/env python3
"""简化的语法错误检查工具
Simple Syntax Errors Check Tool.

只检查src目录的关键Python文件，忽略其他目录
"""

import ast
import sys
from pathlib import Path


def check_syntax(file_path: Path) -> list[str]:
    """检查单个文件的语法错误."""
    errors = []

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 尝试解析AST
        ast.parse(content, filename=str(file_path))

    except SyntaxError as e:
        errors.append(f"语法错误 {file_path}:{e.lineno}:{e.offset}: {e.msg}")
    except Exception:
        # 忽略其他错误，只关注语法错误
        pass

    return errors


def main():
    """主函数."""
    project_root = Path.cwd()
    src_dir = project_root / "src"

    if not src_dir.exists():
        sys.exit(0)


    # 只查找src目录下的Python文件
    python_files = list(src_dir.glob("**/*.py"))

    total_files = 0
    error_files = 0
    total_errors = 0

    for file_path in python_files:
        total_files += 1
        errors = check_syntax(file_path)

        if errors:
            error_files += 1
            total_errors += len(errors)
            for _error in errors:
                pass


    if total_errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
