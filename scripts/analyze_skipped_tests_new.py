#!/usr/bin/env python3
"""
分析跳过测试的脚本
找出原因并提供修复建议
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple


def find_pytest_skips(test_dir: Path) -> List[Dict]:
    """找出所有使用pytest.skip的测试"""
    skips = []

    for py_file in test_dir.rglob("*.py"):
        if "disabled" in str(py_file) or "archive" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)

            # 查找pytest.skip调用
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (
                        isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "pytest"
                        and node.func.attr == "skip"
                    ):
                        # 跳过的原因
                        reason = "No reason"
                        if node.args:
                            reason = ast.literal_eval(node.args[0])

                        skips.append(
                            {
                                "file": str(py_file.relative_to(test_dir.parent)),
                                "line": node.lineno,
                                "reason": reason,
                            }
                        )
        except:
            pass

    return skips


def categorize_skips(skips: List[Dict]) -> Dict[str, List[Dict]]:
    """将跳过的测试按原因分类"""
    categories = {
        "Module import failed": [],
        "Cannot instantiate": [],
        "Test requires external service": [],
        "Test disabled temporarily": [],
        "Other": [],
    }

    for skip in skips:
        reason = skip["reason"].lower()

        if "import" in reason or "module" in reason:
            categories["Module import failed"].append(skip)
        elif "instantiate" in reason or "create" in reason:
            categories["Cannot instantiate"].append(skip)
        elif "external" in reason or "service" in reason or "database" in reason:
            categories["Test requires external service"].append(skip)
        elif "temporarily" in reason or "todo" in reason or "fix" in reason:
            categories["Test disabled temporarily"].append(skip)
        else:
            categories["Other"].append(skip)

    return categories


def analyze_disabled_directory(disabled_dir: Path) -> Dict:
    """分析disabled目录中的测试"""
    disabled_tests = {
        "total_files": 0,
        "total_tests": 0,
        "file_types": {},
        "common_patterns": [],
    }

    if not disabled_dir.exists():
        return disabled_tests

    disabled_tests["total_files"] = len(list(disabled_dir.rglob("*.py")))

    # 分析文件类型
    for py_file in disabled_dir.rglob("*.py"):
        rel_path = py_file.relative_to(disabled_dir)

        # 分类
        if "archive" in str(rel_path):
            file_type = "archived"
        elif "misplaced" in str(rel_path):
            file_type = "misplaced"
        else:
            file_type = "disabled"

        disabled_tests["file_types"][file_type] = (
            disabled_tests["file_types"].get(file_type, 0) + 1
        )

    return disabled_tests


def generate_fix_plan(
    skips: List[Dict], categories: Dict[str, List[Dict]], disabled_info: Dict
) -> str:
    """生成修复计划"""
    plan = []

    plan.append("# 📋 跳过测试处理计划\n")

    # 统计信息
    plan.append("## 📊 统计信息\n")
    plan.append(f"- 总跳过测试数：{len(skips)}")
    plan.append(f"- disabled目录文件数：{disabled_info.get('total_files', 0)}")
    plan.append("")

    # 分类处理建议
    plan.append("## 🔧 分类处理建议\n")

    for category, items in categories.items():
        if items:
            plan.append(f"\n### {category} ({len(items)} 个测试)")

            if category == "Module import failed":
                plan.append("**处理方案：**")
                plan.append("1. 检查模块是否存在")
                plan.append("2. 修复导入路径")
                plan.append("3. 使用Mock替代真实模块")
                plan.append("4. 将测试移到disabled目录如果模块已废弃")

            elif category == "Cannot instantiate":
                plan.append("**处理方案：**")
                plan.append("1. 检查类构造函数参数")
                plan.append("2. 使用fixture提供必要的参数")
                plan.append("3. 使用Mock创建实例")

            elif category == "Test requires external service":
                plan.append("**处理方案：**")
                plan.append("1. 使用pytest-mock模拟外部服务")
                plan.append("2. 创建测试用的假服务")
                plan.append("3. 使用Docker运行真实服务（集成测试）")

            elif category == "Test disabled temporarily":
                plan.append("**处理方案：**")
                plan.append("1. 检查是否还需要禁用")
                plan.append("2. 修复导致禁用的问题")
                plan.append("3. 重新启用测试")

            # 显示部分示例
            plan.append("\n**示例文件：**")
            for item in items[:3]:
                plan.append(f"- {item['file']}:{item['line']} - {item['reason']}")
            if len(items) > 3:
                plan.append(f"- ... 还有 {len(items) - 3} 个")

    # 处理disabled目录
    plan.append("\n## 🗂️ Disabled目录处理\n")

    if disabled_info.get("total_files", 0) > 0:
        plan.append("disabled目录中的测试需要逐个检查：")

        for file_type, count in disabled_info.get("file_types", {}).items():
            if count > 0:
                plan.append(f"\n- **{file_type}** ({count} 个文件)")

                if file_type == "archived":
                    plan.append("  - 这些是旧版本测试，可以删除或保留作为参考")
                elif file_type == "misplaced":
                    plan.append("  - 这些是放错位置的测试，可以移动到正确位置")
                elif file_type == "disabled":
                    plan.append("  - 这些是有问题的测试，需要修复后重新启用")

    # 优先级建议
    plan.append("\n## 🎯 优先级建议\n")
    plan.append("1. **高优先级**：修复Module import failed的测试（使用Mock）")
    plan.append("2. **中优先级**：修复Cannot instantiate的测试（使用fixture）")
    plan.append("3. **低优先级**：处理disabled目录中的文件")

    return "\n".join(plan)


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "tests"
    disabled_dir = test_dir / "disabled"

    print("🔍 分析跳过的测试...")

    # 查找pytest.skip
    skips = find_pytest_skips(test_dir)

    # 分类
    categories = categorize_skips(skips)

    # 分析disabled目录
    disabled_info = analyze_disabled_directory(disabled_dir)

    # 生成计划
    plan = generate_fix_plan(skips, categories, disabled_info)

    # 保存报告
    report_file = project_root / "SKIPPED_TESTS_ANALYSIS.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(plan)

    print(f"✅ 分析完成！报告已保存到：{report_file}")
    print("\n📊 跳过测试统计：")
    for category, items in categories.items():
        if items:
            print(f"  - {category}: {len(items)} 个")

    return skips, categories, disabled_info


if __name__ == "__main__":
    main()
