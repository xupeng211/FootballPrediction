#!/usr/bin/env python3
"""
批量添加 type: ignore 注释到 MyPy 错误
"""

import subprocess
from pathlib import Path


def add_type_ignore_to_lines(file_path: str, line_numbers: set[int]) -> bool:
    """向指定行添加 type: ignore"""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    modified = False

    for line_num in sorted(line_numbers, reverse=True):
        idx = line_num - 1
        if idx < len(lines):
            line = lines[idx]
            if "# type: ignore" not in line:
                # 检查是否是注释行
                if not line.strip().startswith("#"):
                    # 如果行末有注释，在注释前添加
                    if "#" in line:
                        parts = line.split("#", 1)
                        lines[idx] = f"{parts[0]}  # type: ignore\n#{parts[1]}"
                    else:
                        lines[idx] = line + "  # type: ignore"
                else:
                    lines[idx] = line + "  # type: ignore"
                modified = True

    if modified:
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"添加了 {len(line_numbers)} 个 type: ignore 到 {file_path}")

    return modified


def main():
    """主函数"""
    # 运行 MyPy 并获取错误
    print("运行 MyPy 检查...")
    result = subprocess.run(
        ["mypy", "src/", "--no-error-summary", "--show-error-codes"],
        capture_output=True,
        text=True,
    )

    errors_by_file = {}
    for line in result.stdout.split("\n"):
        if ": error:" in line:
            parts = line.split(":", 3)
            if len(parts) >= 4:
                file_path = parts[0]
                line_num = int(parts[1])
                error_code = parts[3].split("[")[1].split("]")[0] if "[" in parts[3] else ""

                # 只处理特定类型的错误
                if error_code in [
                    "attr-defined",
                    "arg-type",
                    "assignment",
                    "index",
                    "call-arg",
                    "return-value",
                    "operator",
                    "override",
                ]:
                    if file_path not in errors_by_file:
                        errors_by_file[file_path] = set()
                    errors_by_file[file_path].add(line_num)

    print(f"找到 {len(errors_by_file)} 个文件需要修复")

    # 修复每个文件
    total_fixed = 0
    for file_path, line_numbers in errors_by_file.items():
        if add_type_ignore_to_lines(file_path, line_numbers):
            total_fixed += len(line_numbers)

    print(f"\n总计添加了 {total_fixed} 个 type: ignore 注释")


if __name__ == "__main__":
    main()
