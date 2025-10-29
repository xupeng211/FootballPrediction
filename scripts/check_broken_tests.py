#!/usr/bin/env python3
"""
检查有问题的测试文件
"""

import subprocess
import re
from pathlib import Path


def find_broken_tests():
    """查找有问题的测试文件"""
    print("🔍 查找有问题的测试文件...\n")

    # 运行pytest收集测试
    result = subprocess.run(
        ["pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    # 解析错误
    broken_files = set()
    error_lines = []

    for line in result.stdout.split("\n"):
        if "ERROR collecting" in line:
            # 提取文件路径
            match = re.search(r"ERROR collecting (.+?) ", line)
            if match:
                file_path = match.group(1)
                broken_files.add(file_path)
                error_lines.append(line)

    print(f"发现 {len(broken_files)} 个有问题的测试文件:\n")

    for file_path in sorted(broken_files):
        rel_path = file_path.replace("/home/user/projects/FootballPrediction/", "")
        print(f"  ❌ {rel_path}")

    # 查找具体的错误原因
    print("\n📝 错误详情:\n")

    for error in error_lines[:5]:  # 只显示前5个
        print(f"  {error}")

    if len(broken_files) > 5:
        print(f"\n  ... 还有 {len(broken_files) - 5} 个错误")

    # 检查是否有导入错误
    print("\n🔍 检查导入错误...")

    import_errors = []
    for file_path in broken_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 尝试解析导入
            import ast

            ast.parse(content)
        except Exception as e:
            import_errors.append((file_path, str(e)))

    if import_errors:
        print(f"\n发现 {len(import_errors)} 个导入错误:\n")
        for file_path, error in import_errors[:3]:
            rel_path = file_path.replace("/home/user/projects/FootballPrediction/", "")
            print(f"  - {rel_path}: {error}")

    return broken_files


def main():
    """主函数"""
    print("=" * 80)
    print("🔍 检查有问题的测试文件")
    print("=" * 80)

    broken_files = find_broken_tests()

    if broken_files:
        print("\n" + "=" * 80)
        print("💡 建议")
        print("=" * 80)
        print("\n1. 修复导入错误")
        print("2. 检查Optional、Any等类型注解是否已导入")
        print("3. 运行: pytest --ignore=tests/unit/utils/test_redis_connection_manager.py")
        print("4. 或者临时移除/重命名有问题的测试文件")
    else:
        print("\n✅ 所有测试文件都没有问题！")


if __name__ == "__main__":
    main()
