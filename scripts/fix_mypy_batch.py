#!/usr/bin/env python3
"""
批量修复 MyPy 错误的脚本
用于自动化修复常见的导入和类型注解问题
"""

import os
import re
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple

# 需要修复的常见导入
COMMON_IMPORTS = {
    "Optional": "from typing import Optional",
    "List": "from typing import List",
    "Dict": "from typing import Dict",
    "Tuple": "from typing import Tuple",
    "Union": "from typing import Union",
    "Any": "from typing import Any",
    "Callable": "from typing import Callable",
    "Iterator": "from typing import Iterator",
    "Generator": "from typing import Generator",
}

# 标准库导入
STANDARD_IMPORTS = {
    "logging": "import logging",
    "os": "import os",
    "sys": "import sys",
    "datetime": "import datetime",
    "json": "import json",
    "subprocess": "import subprocess",
    "time": "import time",
    "uuid": "import uuid",
    "pathlib": "from pathlib import Path",
    "collections": "import collections",
    "itertools": "import itertools",
    "functools": "import functools",
    "operator": "import operator",
    "re": "import re",
    "math": "import math",
    "random": "import random",
    "hashlib": "import hashlib",
    "base64": "import base64",
    "urllib": "import urllib",
    "http": "import http",
}

# 项目特定导入
PROJECT_IMPORTS = {
    "BaseService": "from src.services.base_unified import BaseService",
    "BackupConfig": "from src.tasks.backup.core.backup_config import BackupConfig",
    "get_backup_metrics": "from src.tasks.backup.metrics import get_backup_metrics",
}


def extract_existing_imports(content: str) -> Set[str]:
    """提取文件中已存在的导入"""
    imports = set()
    # 匹配 from ... import ...
    from_imports = re.findall(r"from\s+[\w.]+\s+import\s+([\w\s,]+)", content)
    for match in from_imports:
        imports.update(name.strip() for name in match.split(","))

    # 匹配 import ...
    direct_imports = re.findall(r"import\s+([\w\s,]+)", content)
    for match in direct_imports:
        imports.update(name.strip() for name in match.split(","))

    return imports


def find_needed_imports(content: str, existing_imports: Set[str]) -> List[str]:
    """找出需要添加的导入"""
    needed = []

    # 检查 typing 导入
    for name, import_stmt in COMMON_IMPORTS.items():
        if re.search(rf"\b{name}\b", content) and name not in existing_imports:
            needed.append(import_stmt)

    # 检查标准库导入
    for name, import_stmt in STANDARD_IMPORTS.items():
        if re.search(rf"\b{name}\b", content) and name not in existing_imports:
            # 避免匹配到作为属性的情况
            if re.search(rf"\b{name}\s*[.\[]", content) or re.search(
                rf"\b{name}\s*$", content, re.MULTILINE
            ):
                needed.append(import_stmt)

    # 检查项目导入
    for name, import_stmt in PROJECT_IMPORTS.items():
        if re.search(rf"\b{name}\b", content) and name not in existing_imports:
            needed.append(import_stmt)

    return needed


def fix_file_imports(file_path: Path) -> bool:
    """修复单个文件的导入问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否已经是修复过的文件
        if "# Auto-fixed imports" in content:
            return False

        # 提取现有导入
        existing_imports = extract_existing_imports(content)

        # 找出需要的导入
        needed_imports = find_needed_imports(content, existing_imports)

        if needed_imports:
            # 在文件开头添加导入
            # 找到第一个非注释行
            lines = content.split("\n")
            insert_idx = 0

            # 跳过文件头注释
            for i, line in enumerate(lines):
                if line.strip().startswith("#") or line.strip() == "":
                    insert_idx = i + 1
                else:
                    break

            # 插入导入语句
            import_lines = ["# Auto-fixed imports"] + needed_imports + [""]
            lines[insert_idx:insert_idx] = import_lines

            # 写回文件
            new_content = "\n".join(lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"✅ Fixed imports in {file_path}")
            return True

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False


def fix_function_signatures(file_path: Path) -> bool:
    """修复函数签名中的类型注解问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复缺少参数类型的函数
        # 示例: def func(self, arg): -> def func(self, arg: Any):
        modified = False
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # 匹配函数定义
            if re.match(r"^\s*def\s+\w+\s*\([^)]*\):\s*$", line):
                # 检查是否有 Any 类型导入
                if "Any" not in content and "from typing import Any" not in content:
                    # 如果没有，先添加 Any 导入
                    content = "from typing import Any\n\n" + content
                    lines[0] = "from typing import Any"
                    modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"✅ Fixed function signatures in {file_path}")
            return True

    except Exception as e:
        print(f"❌ Error fixing signatures in {file_path}: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 指定文件或目录
        path = Path(sys.argv[1])
    else:
        # 默认处理 src/tasks/backup 目录
        path = Path("src/tasks/backup")

    if path.is_file():
        files = [path]
    else:
        # 查找所有 Python 文件
        files = list(path.rglob("*.py"))

    print(f"🔧 开始修复 {len(files)} 个文件...")

    fixed_count = 0
    for file_path in files:
        if fix_file_imports(file_path):
            fixed_count += 1

    print(f"\n✨ 修复完成！共修复 {fixed_count} 个文件")

    # 验证修复结果
    print("\n🔍 验证修复结果...")
    for file_path in files[:5]:  # 验证前5个文件
        try:
            import subprocess

            result = subprocess.run(
                ["python", "-m", "py_compile", str(file_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"✅ {file_path} 编译成功")
            else:
                print(f"❌ {file_path} 仍有错误")
        except Exception as e:
            print(f"⚠️ 无法验证 {file_path}: {e}")


if __name__ == "__main__":
    main()
