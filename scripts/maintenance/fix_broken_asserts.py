#!/usr/bin/env python3
"""
修复被错误处理的assert语句
"""

import re
from pathlib import Path


def fix_broken_asserts():
    """修复被错误处理的assert语句"""

    # 需要修复的文件
    files_to_fix = [
        "tests/unit/api/test_adapters.py",
        "tests/unit/api/test_adapters_simple.py",
    ]

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复错误的assert语句
        # 模式：assert "xxx" in _data" in _data -> assert "xxx" in _data
        content = re.sub(
            r'assert\s+"([^"]+)"\s+in\s+_data"\s+in\s+_data',
            r'assert "\1" in _data',
            content,
        )

        # 模式：assert "xxx" in _data\n" in _data -> assert "xxx" in _data
        content = re.sub(
            r'assert\s+"([^"]+)"\s+in\s+_data\s*\n\s*" in\s+_data',
            r'assert "\1" in _data',
            content,
        )

        # 修复多行的错误assert
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检查是否是错误的assert语句
            if 'assert "' in line and '" in _data' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if '" in _data' in next_line:
                    # 提取assert内容
                    match = re.search(r'assert\s+"([^"]+)"', line)
                    if match:
                        key = match.group(1)
                        new_lines.append(f'        assert "{key}" in _data')
                        i += 2  # 跳过下一行
                        continue

            new_lines.append(line)
            i += 1

        content = "\n".join(new_lines)

        # 保存文件
        if content != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")


if __name__ == "__main__":
    fix_broken_asserts()
