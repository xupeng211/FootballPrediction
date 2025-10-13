#!/usr/bin/env python3
"""
启用被跳过的测试 - 通过修复导入或禁用 skipif
"""

import os
import re
from pathlib import Path


def enable_tests_in_file(filepath):
    """启用文件中被跳过的测试"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        modified = False

        # 策略1: 临时禁用所有 skipif，让测试尝试运行
        # 将 @pytest.mark.skipif(...) 替换为 @pytest.mark.skipif(False, ...)
        # 这样测试会尝试运行，如果导入失败会报错而不是跳过

        # 查找所有 skipif 模式
        skipif_pattern = r'(@pytest\.mark\.skipif\([^)]+\))'

        def replace_skipif(match):
            original_skipif = match.group(1)
            # 如果是 skipif(True)，保持不变（这些是占位测试）
            if 'True' in original_skipif:
                return original_skipif
            # 其他 skipif 临时禁用
            return '@pytest.mark.skipif(False, reason="临时禁用 - Phase 2 优化")'

        content = re.sub(skipif_pattern, replace_skipif, content)

        if content != original:
            modified = True
            print(f"✓ 修改了 {filepath} - 禁用了 skipif 条件")
            return True

    except Exception as e:
        print(f"✗ 处理 {filepath} 失败: {e}")

    return False


def main():
    print("启用被跳过的测试 - Phase 2 优化")
    print("=" * 60)
    print("策略：临时禁用 skipif 条件，让测试尝试运行")
    print("-" * 60)

    # 重点处理 tests/unit/api/ 目录
    api_test_dir = Path("tests/unit/api")
    modified_count = 0

    # 处理 API 测试
    for test_file in api_test_dir.glob("test_*.py"):
        if enable_tests_in_file(test_file):
            modified_count += 1

    # 处理其他关键目录
    other_dirs = [
        "tests/unit/services",
        "tests/unit/utils",
        "tests/unit/monitoring",
        "tests/unit/data",
    ]

    for dir_path in other_dirs:
        dir_path = Path(dir_path)
        if dir_path.exists():
            for test_file in dir_path.glob("test_*.py"):
                if enable_tests_in_file(test_file):
                    modified_count += 1

    print("-" * 60)
    print(f"总共修改了 {modified_count} 个测试文件")
    print("\n说明：")
    print("- 这些测试现在会尝试运行而不是跳过")
    print("- 如果有导入错误，会以 ERROR 形式显示而不是 SKIPPED")
    print("- 这有助于我们识别真正需要修复的问题")

    print("\n" + "=" * 60)
    print("下一步：运行 pytest 验证跳过数量是否 < 100")


if __name__ == "__main__":
    main()