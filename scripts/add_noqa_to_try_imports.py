#!/usr/bin/env python3
"""
为 try 块中的条件导入添加 noqa 注释
"""

from pathlib import Path


def add_noqa_to_try_imports(file_path: Path) -> bool:
    """为文件中的 try 块导入添加 noqa 注释"""
    content = file_path.read_text(encoding="utf-8")
    original = content

    # 查找 try 块并添加 noqa
    lines = content.split("\n")
    new_lines = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # 检查是否在 try 块内
        if "try:" in line:
            # 找到 try 块开始
            new_lines.append(line)
            i += 1
            in_try = True

            # 处理 try 块内容
            while i < n and in_try:
                line = lines[i]
                stripped = line.strip()

                # 检查是否是导入语句
                if (
                    stripped.startswith("from ") or stripped.startswith("import ")
                ) and not stripped.endswith("# noqa: F401"):
                    # 添加 noqa 注释
                    if stripped.endswith('"'):
                        # 三引号导入
                        new_lines.append(line)
                    else:
                        # 普通导入
                        new_lines.append(line + "  # noqa: F401")
                else:
                    new_lines.append(line)

                # 检查是否离开 try 块
                if (
                    stripped.startswith("except ")
                    or stripped.startswith("finally ")
                    or stripped == "except Exception:"
                ):
                    in_try = False

                i += 1
        else:
            new_lines.append(line)
            i += 1

    new_content = "\n".join(new_lines)

    if new_content != original:
        file_path.write_text(new_content, encoding="utf-8")
        return True

    return False


def main():
    """主函数"""
    print("为 try 块中的条件导入添加 noqa 注释...")

    # 获取所有需要修复的文件
    result = subprocess.run(
        ["ruff", "check", "--select=F401", "--quiet", "tests/unit/"],
        capture_output=True,
        text=True,
    )

    # 提取文件路径
    files_to_fix = set()
    for line in result.stdout.split("\n"):
        if ": F401 " in line:
            file_path = line.split(":")[0]
            if "try:" in Path(file_path).read_text(encoding="utf-8"):
                files_to_fix.add(file_path)

    print(f"找到 {len(files_to_fix)} 个需要修复的文件")

    fixed_count = 0
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            if add_noqa_to_try_imports(path):
                print(f"  ✓ 修复了 {file_path}")
                fixed_count += 1

    print(f"\n✅ 修复了 {fixed_count} 个文件！")


if __name__ == "__main__":
    import subprocess

    main()
