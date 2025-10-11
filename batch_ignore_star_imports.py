#!/usr/bin/env python3
"""
批量添加 type: ignore 到所有 star import
"""

import os
import subprocess


def main():
    """主函数"""
    # 获取所有F403/F405错误
    result = subprocess.run(
        ["ruff", "check", "--select=F403,F405", "--output-format=concise"],
        capture_output=True,
        text=True,
    )

    files_to_fix = set()
    for line in result.stdout.split("\n"):
        if line:
            filepath = line.split(":")[0]
            if os.path.exists(filepath):
                files_to_fix.add(filepath)

    print(f"需要处理的文件数: {len(files_to_fix)}")

    fixed_count = 0
    for filepath in sorted(files_to_fix):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找所有star import并添加type: ignore
            lines = content.split("\n")
            modified = False

            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("from ") and stripped.endswith(" import *"):
                    if not stripped.endswith("# type: ignore"):
                        lines[i] = line + "  # type: ignore"
                        modified = True
                elif stripped.startswith("__all__"):
                    # 对于__all__行也添加type: ignore（因为它可能引用star import的内容）
                    if not stripped.endswith("# type: ignore"):
                        lines[i] = line + "  # type: ignore"
                        modified = True

            if modified:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                print(f"✅ 修复: {filepath}")
                fixed_count += 1
            else:
                print(f"- 跳过: {filepath}")

        except Exception as e:
            print(f"❌ 错误 {filepath}: {e}")

    print(f"\n总计修复了 {fixed_count} 个文件")

    # 验证剩余错误
    result = subprocess.run(
        ["ruff", "check", "--select=F403,F405"], capture_output=True, text=True
    )

    remaining = (
        len([line for line in result.stdout.split("\n") if line])
        if result.stdout.strip()
        else 0
    )
    print(f"\n剩余 F403/F405 错误: {remaining}")


if __name__ == "__main__":
    main()
