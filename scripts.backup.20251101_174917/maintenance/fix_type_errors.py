#!/usr/bin/env python3
"""自动修复 MyPy 类型错误的脚本"""

import re
from pathlib import Path


def fix_var_annotated_errors(file_path: str):
    """修复 var-annotated 错误"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 修复 result = {} 的情况
    content = re.sub(r"(\s+)result = \{\}", r"\1result: Dict[str, Any] = {}", content)

    # 修复 results = [] 的情况
    content = re.sub(r"(\s+)results = \[\]", r"\1results: List[Any] = []", content)

    # 修复 features = [] 的情况
    content = re.sub(r"(\s+)features = \[\]", r"\1features: List[Any] = []", content)

    # 修复 request_durations = deque(maxlen=1000)
    content = re.sub(
        r"(\s+)self\.request_durations = deque\(maxlen=\d+\)",
        r"\1self.request_durations: Deque[float] = deque(maxlen=1000)",
        content,
    )

    # 修复 error_counts = defaultdict(int)
    content = re.sub(
        r"(\s+)self\.error_counts = defaultdict\(int\)",
        r"\1self.error_counts: Dict[str, int] = defaultdict(int)",
        content,
    )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed {file_path}")
        return True
    return False


def fix_union_attr_errors(file_path: str):
    """修复 union-attr 错误"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 添加必要的导入
    if "from typing import" in content:
        # 检查是否已经有 cast
        if "cast" not in content:
            content = re.sub(
                r"from typing import ([^\n]+)", r"from typing import \1, cast", content
            )
    else:
        # 如果没有 typing 导入，添加一个
        content = "from typing import cast, Any, Optional, Union\n" + content

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Added imports to {file_path}")
        return True
    return False


def main():
    """主函数"""
    src_dir = Path("src")

    fixed_count = 0

    # 递归处理所有 Python 文件
    for py_file in src_dir.rglob("*.py"):
        if fix_var_annotated_errors(str(py_file)):
            fixed_count += 1
        if fix_union_attr_errors(str(py_file)):
            fixed_count += 1

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
