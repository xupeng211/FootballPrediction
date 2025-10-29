#!/usr/bin/env python3
"""
修复测试文件中的变量名错误
专门处理 data -> _data, config -> _config, result -> _result 的问题
"""

import os
import re
from pathlib import Path


def fix_test_file(file_path: Path):
    """修复单个测试文件中的变量名问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复问题：更精确的模式匹配
        # 1. 修复 data -> _data 在assert语句中（但不修复已经正确的 _data）
        # 匹配 assert ... in data 但不匹配 assert ... in _data
        content = re.sub(r"\bassert\s+(.+?)\s+in\s+data\b(?!\s*=)", r"assert \1 in _data", content)

        # 2. 修复 data["key"] -> _data["key"]
        content = re.sub(r"\bdata\[([^\]]+)\]", r"_data[\1]", content)

        # 3. 修复 config.xxx -> _config.xxx
        content = re.sub(r"\bconfig\.([a-zA-Z_][a-zA-Z0-9_]*)", r"_config.\1", content)

        # 4. 修复 config["key"] -> _config["key"]
        content = re.sub(r"\bconfig\[([^\]]+)\]", r"_config[\1]", content)

        # 5. 修复 assert result -> assert _result
        content = re.sub(r"\bassert\s+result\b(?!\s*=)", "assert _result", content)

        # 6. 修复 result["key"] -> _result["key"]
        content = re.sub(r"\bresult\[([^\]]+)\]", r"_result[\1]", content)

        # 7. 修复变量赋值（但不包括已经正确的 _data, _config, _result）
        # 匹配 data = response.json() 但不匹配 _data = response.json()
        content = re.sub(r"\bdata\s*=\s*response\.json\(\)", "_data = response.json()", content)

        # 8. 特殊修复：处理被错误修改的 assert 语句
        # 修复 assert "key" in _data 被错误修改的情况
        content = re.sub(
            r'assert\s+"([^"]+)"\s+in\s+_data\s*$',
            r'assert "\1" in _data',
            content,
            flags=re.MULTILINE,
        )

        # 9. 修复被错误处理的 assert 语句（去掉多余的引号）
        content = re.sub(r'assert\s+"([^"]+)"\s+in\s+_data"$', r'assert "\1" in _data', content)

        # 保存文件
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True
    except Exception as e:
        print(f"❌ 错误: {file_path} - {e}")

    return False


def main():
    """主函数"""
    test_dir = Path("tests/unit")
    fixed_count = 0

    print("🔧 开始修复测试文件中的变量名问题...")

    # 先修复已知的问题文件
    problem_files = [
        "tests/unit/api/test_adapters_simple.py",
        "tests/unit/api/test_adapters.py",
    ]

    for file_path in problem_files:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_test_file(full_path):
                fixed_count += 1

    # 然后遍历所有测试文件
    for test_file in test_dir.rglob("test_*.py"):
        # 跳过已经处理过的文件
        if str(test_file) not in problem_files:
            if fix_test_file(test_file):
                fixed_count += 1

    print(f"\n✅ 完成！修复了 {fixed_count} 个文件。")


if __name__ == "__main__":
    main()
