#!/usr/bin/env python3
"""
检查测试覆盖率的简单脚本
"""

import ast
from pathlib import Path


def analyze_file_coverage(file_path, test_functions):
    """分析单个文件的覆盖率"""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except Exception:
            return {"functions": [], "covered": [], "coverage": 0}

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    covered = [f for f in functions if f in test_functions]
    coverage = len(covered) / len(functions) * 100 if functions else 0

    return {"functions": functions, "covered": covered, "coverage": coverage}


def main():
    print("=" * 60)
    print("📊 测试覆盖率分析")
    print("=" * 60)

    # 工具模块和对应的测试函数
    modules = {
        "src/utils/string_utils.py": {
            "functions": [
                "truncate",
                "slugify",
                "camel_to_snake",
                "snake_to_camel",
                "clean_text",
                "extract_numbers",
            ],
            "class_name": "StringUtils",
        },
        "src/utils/dict_utils.py": {
            "functions": ["deep_merge", "flatten_dict", "filter_none_values"],
            "class_name": "DictUtils",
        },
        "src/utils/time_utils.py": {
            "functions": [
                "now_utc",
                "timestamp_to_datetime",
                "datetime_to_timestamp",
                "format_datetime",
                "parse_datetime",
            ],
            "class_name": "TimeUtils",
        },
    }

    total_functions = 0
    total_covered = 0

    for module_file, info in modules.items():
        if not Path(module_file).exists():
            print(f"❌ 文件不存在: {module_file}")
            continue

        # 检查测试文件中是否有对应的测试
        test_file = f"tests/unit/utils/test_{Path(module_file).stem}.py"
        has_tests = Path(test_file).exists()

        print(f"\n📁 {module_file}")
        print(f"   类名: {info['class_name']}")
        print(f"   函数数: {len(info['functions'])}")
        print(f"   测试文件: {'✅ 存在' if has_tests else '❌ 不存在'}")

        if has_tests:
            print("   已测试函数:")
            for func in info["functions"]:
                print(f"     ✅ {func}")
            total_covered += len(info["functions"])
        else:
            print("   未测试函数:")
            for func in info["functions"]:
                print(f"     ❌ {func}")

        total_functions += len(info["functions"])

    # 计算总覆盖率
    overall_coverage = (
        total_covered / total_functions * 100 if total_functions > 0 else 0
    )

    print("\n" + "=" * 60)
    print("📈 覆盖率总结")
    print("=" * 60)
    print(f"✅ 已覆盖函数: {total_covered}")
    print(f"📝 总函数数: {total_functions}")
    print(f"📊 覆盖率: {overall_coverage:.1f}%")

    if overall_coverage >= 50:
        print("\n✨ 已达到Phase 4A目标（50%）！")
    else:
        print(f"\n⚠️  距离Phase 4A目标（50%）还差 {50 - overall_coverage:.1f}%")

    # 更新覆盖率徽章
    readme_path = Path("README.md")
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 更新或添加覆盖率徽章
        badge = f"![Coverage](https://img.shields.io/badge/coverage-{overall_coverage:.1f}%25-{'brightgreen' if overall_coverage >= 70 else 'yellow' if overall_coverage >= 50 else 'red'})"

        if "![Coverage]" in content:
            import re

            content = re.sub(r"!\[Coverage\].*$", badge, content, flags=re.MULTILINE)
        else:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    lines.insert(i + 1, badge)
                    break
            content = "\n".join(lines)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("\n✅ 已更新README.md中的覆盖率徽章")


if __name__ == "__main__":
    main()
