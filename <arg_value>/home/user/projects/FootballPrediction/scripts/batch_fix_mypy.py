#!/usr/bin/env python3
"""
批量修复 MyPy 错误的脚本
专门处理最常见的导入和类型注解问题
"""

import re
import subprocess
from pathlib import Path
from typing import List, Tuple


def get_files_with_most_errors(limit: int = 20) -> List[Tuple[str, int]]:
    """获取 MyPy 错误最多的文件"""
    result = subprocess.run(["mypy", "src/"], capture_output=True, text=True)

    error_files = {}
    for line in result.stdout.split("\n"):
        if ": error:" in line:
            file_path = line.split(":")[0]
            error_files[file_path] = error_files.get(file_path, 0) + 1

    # 返回错误数最多的文件
    sorted_files = sorted(error_files.items(), key=lambda x: x[1], reverse=True)
    return sorted_files[:limit]


def add_missing_imports(file_path: Path) -> bool:
    """添加缺失的导入"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False
        lines = content.split("\n")

        # 检查需要添加的导入
        needed_imports = []

        # 检查是否需要 logging
        if "logging.getLogger" in content or "self.logger" in content:
            if "import logging" not in content:
                needed_imports.append("import logging")

        # 检查是否需要 os
        if (
            re.search(r"\bos\.", content)
            or "os.getenv" in content
            or "os.path" in content
        ):
            if "import os" not in content:
                needed_imports.append("import os")

        # 检查是否需要 datetime
        if "datetime.now()" in content or "datetime.utcnow()" in content:
            if (
                "from datetime import datetime" not in content
                and "import datetime" not in content
            ):
                needed_imports.append("from datetime import datetime")

        # 检查是否需要 typing 模块
        typing_needed = []
        for typ in ["Dict", "List", "Optional", "Any", "Union", "Tuple"]:
            if re.search(rf"\b{typ}\b", content):
                typing_needed.append(typ)

        if typing_needed:
            if "from typing import" in content:
                # 检查是否需要添加到现有的 typing 导入
                typing_import_line = None
                for i, line in enumerate(lines):
                    if line.startswith("from typing import"):
                        typing_import_line = i
                        break

                if typing_import_line is not None:
                    # 添加缺失的类型到现有导入
                    existing = set(
                        lines[typing_import_line].split("import")[1].split(",")
                    )
                    existing = {e.strip() for e in existing}
                    for typ in typing_needed:
                        if typ not in existing:
                            existing.add(typ)

                    lines[
                        typing_import_line
                    ] = f"from typing import {', '.join(sorted(existing))}"
                    modified = True
            else:
                # 添加新的 typing 导入
                needed_imports.append(f"from typing import {', '.join(typing_needed)}")

        # 插入导入
        if needed_imports:
            # 找到插入位置（在第一个导入或文档字符串后）
            insert_idx = 0
            for i, line in enumerate(lines):
                if (
                    line.strip().startswith("#")
                    or line.strip() == ""
                    or line.startswith('"""')
                    or line.startswith("'''")
                ):
                    insert_idx = i + 1
                elif line.strip().startswith("import") or line.strip().startswith(
                    "from"
                ):
                    insert_idx = i
                    break

            # 在导入之前插入
            if (
                insert_idx > 0
                and not lines[insert_idx - 1].strip().startswith("import")
                and not lines[insert_idx - 1].strip().startswith("from")
            ):
                # 确保在导入前有空行
                pass

            for imp in needed_imports:
                lines.insert(insert_idx, imp)
                insert_idx += 1
                modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"✅ Fixed imports in {file_path}")
            return True

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False


def fix_variable_annotations(file_path: Path) -> bool:
    """修复变量类型注解"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False
        lines = content.split("\n")

        # 需要修复的模式
        patterns = [
            # result = {"key": "value"} -> result: Dict[str, str] = {"key": "value"}
            (r"(\s+)(\w+) = \{", r"\1\2: Dict[str, Any] = {"),
            # result = [] -> result: List[Any] = []
            (r"(\s+)(\w+) = \[\]", r"\1\2: List[Any] = []"),
            # result = {} -> result: Dict[str, Any] = {}
            (r"(\s+)(\w+) = \{\}", r"\1\2: Dict[str, Any] = {}"),
        ]

        for i, line in enumerate(lines):
            for pattern, replacement in patterns:
                if re.search(pattern, line):
                    # 检查是否已经有类型注解
                    if ":" not in line.split("=")[0]:
                        lines[i] = re.sub(pattern, replacement, line)
                        modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"✅ Fixed annotations in {file_path}")
            return True

    except Exception as e:
        print(f"❌ Error fixing annotations in {file_path}: {e}")
        return False


def verify_fix(file_path: Path) -> bool:
    """验证文件是否可以编译"""
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    """主函数"""
    print("🔧 开始批量修复 MyPy 错误...")

    # 获取错误最多的文件
    error_files = get_files_with_most_errors(10)
    print(f"\n📊 找到 {len(error_files)} 个需要修复的文件")

    fixed_count = 0
    for file_path, error_count in error_files:
        path = Path(file_path)
        print(f"\n🔍 修复 {file_path} ({error_count} 个错误)")

        # 1. 修复导入
        if add_missing_imports(path):
            fixed_count += 1

        # 2. 修复类型注解
        if fix_variable_annotations(path):
            fixed_count += 1

        # 3. 验证修复
        if verify_fix(path):
            print(f"✅ {file_path} 编译成功")
        else:
            print(f"⚠️ {file_path} 仍有问题")

    print(f"\n✨ 修复完成！共修复 {fixed_count} 处")

    # 重新统计错误
    print("\n📈 重新统计 MyPy 错误...")
    result = subprocess.run(["mypy", "src/"], capture_output=True, text=True)

    error_count = result.stdout.count("error:")
    print(f"当前 MyPy 错误数: {error_count}")


if __name__ == "__main__":
    main()
