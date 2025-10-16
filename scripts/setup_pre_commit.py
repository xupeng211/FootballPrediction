#!/usr/bin/env python3
"""
设置pre-commit钩子
"""

import os
import shutil
from pathlib import Path


def setup_pre_commit():
    """设置pre-commit钩子"""
    hooks_dir = Path(".git/hooks")

    # 确保hooks目录存在
    hooks_dir.mkdir(exist_ok=True)

    # 创建pre-commit钩子
    pre_commit_content = """#!/bin/bash
# Pre-commit hook for syntax checking

echo "运行语法检查..."

# 检查暂存的Python文件
python scripts/syntax_check.py

# 运行快速lint检查
if command -v ruff &> /dev/null; then
    echo "运行ruff lint..."
    ruff check --no-fix src/
fi

# 运行类型检查（核心模块）
if command -v mypy &> /dev/null; then
    echo "运行mypy typecheck..."
    mypy src/core/ src/api/ src/domain/ src/services/ src/database/
fi

exit 0
"""

    pre_commit_path = hooks_dir / "pre-commit"

    # 写入钩子文件
    with open(pre_commit_path, 'w') as f:
        f.write(pre_commit_content)

    # 设置可执行权限
    os.chmod(pre_commit_path, 0o755)

    print("✅ Pre-commit钩子已设置成功！")
    print("\n钩子包含以下检查：")
    print("  1. Python语法检查")
    print("  2. Ruff代码风格检查")
    print("  3. MyPy类型检查（核心模块）")


if __name__ == "__main__":
    setup_pre_commit()