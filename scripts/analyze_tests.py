#!/usr/bin/env python3
"""分析项目测试文件分布情况"""

import json
from collections import defaultdict
from pathlib import Path


def find_test_files():
    """查找所有测试文件"""
    test_files = []
    tests_dir = Path("tests")

    if not tests_dir.exists():
        return []

    for file_path in tests_dir.rglob("*.py"):
        if file_path.name.startswith("test_") and file_path.is_file():
            # 跳过__pycache__目录
            if "__pycache__" not in str(file_path):
                test_files.append(file_path)

    return test_files


def analyze_test_distribution(test_files):
    """分析测试文件分布"""
    distribution = {
        "total_files": len(test_files),
        "by_type": defaultdict(list),
        "by_module": defaultdict(list),
        "by_depth": defaultdict(list),
        "file_sizes": [],
    }

    for file_path in test_files:
        # 按测试类型分类
        parts = file_path.parts
        if "unit" in parts:
            test_type = "unit"
        elif "integration" in parts:
            test_type = "integration"
        elif "e2e" in parts:
            test_type = "e2e"
        else:
            test_type = "other"

        distribution["by_type"][test_type].append(file_path)

        # 按模块分类
        if "api" in parts:
            module = "api"
        elif "database" in parts:
            module = "database"
        elif "services" in parts:
            module = "services"
        elif "cache" in parts:
            module = "cache"
        elif "utils" in parts:
            module = "utils"
        elif "models" in parts:
            module = "models"
        elif "monitoring" in parts:
            module = "monitoring"
        elif "streaming" in parts:
            module = "streaming"
        elif "tasks" in parts:
            module = "tasks"
        elif "data" in parts:
            module = "data"
        elif "features" in parts:
            module = "features"
        elif "quality" in parts:
            module = "quality"
        elif "collectors" in parts:
            module = "collectors"
        else:
            module = "other"

        distribution["by_module"][module].append(file_path)

        # 按深度分类
        depth = len(parts) - 1  # 减去tests目录
        distribution["by_depth"][depth].append(file_path)

        # 文件大小
        if file_path.exists():
            size = file_path.stat().st_size
            distribution["file_sizes"].append(size)

    return distribution


def check_test_file_structure(test_files):
    """检查测试文件结构的合理性"""
    issues = []
    suggestions = []

    # 检查命名规范
    for file_path in test_files:
        if not file_path.name.startswith("test_"):
            issues.append(f"文件命名不规范: {file_path} (应以test_开头)")

    # 检查目录结构
    api_test_files = [f for f in test_files if "api" in str(f)]
    unit_api_files = [f for f in api_test_files if "unit/api" in str(f)]

    if len(api_test_files) > 0:
        unit_ratio = len(unit_api_files) / len(api_test_files)
        if unit_ratio < 0.7:
            suggestions.append(
                f"API模块单元测试比例较低 ({unit_ratio:.1%})，建议增加单元测试"
            )

    # 检查是否有缺失的测试
    src_dir = Path("src")
    if src_dir.exists():
        src_modules = set()
        for file_path in src_dir.rglob("*.py"):
            if file_path.is_file() and not file_path.name.startswith("__"):
                relative = file_path.relative_to(src_dir)
                module_name = str(relative.with_suffix(""))
                src_modules.add(module_name)

        # 检查哪些模块缺少测试
        tested_modules = set()
        for test_file in test_files:
            test_path = test_file.relative_to(Path("tests"))
            if "unit" in test_path.parts:
                # 尝试映射测试文件到源模块
                parts = test_path.parts
                if len(parts) >= 3 and parts[0] == "unit":
                    module_path = (
                        "/".join(parts[1:]).replace("test_", "").replace(".py", "")
                    )
                    tested_modules.add(module_path)

        missing_tests = src_modules - tested_modules
        if missing_tests:
            issues.append(
                f"以下模块可能缺少单元测试: {', '.join(list(missing_tests)[:5])}..."
            )

    return issues, suggestions


def generate_report():
    """生成测试文件分析报告"""
    test_files = find_test_files()
    distribution = analyze_test_distribution(test_files)
    issues, suggestions = check_test_file_structure(test_files)

    print("=" * 60)
    print("📊 测试文件分布分析报告")
    print("=" * 60)

    # 总体统计
    print("\n📈 总体统计")
    print(f"   总测试文件数: {distribution['total_files']}")
    if distribution["file_sizes"]:
        avg_size = sum(distribution["file_sizes"]) / len(distribution["file_sizes"])
        print(f"   平均文件大小: {avg_size:.0f} bytes")
        print(f"   最大文件: {max(distribution['file_sizes'])} bytes")
        print(f"   最小文件: {min(distribution['file_sizes'])} bytes")

    # 按类型分布
    print("\n📋 按测试类型分布")
    for test_type, files in sorted(distribution["by_type"].items()):
        percentage = len(files) / distribution["total_files"] * 100
        print(f"   {test_type:12}: {len(files):3} 个文件 ({percentage:5.1f}%)")

    # 按模块分布
    print("\n📂 按功能模块分布")
    for module, files in sorted(
        distribution["by_module"].items(), key=lambda x: len(x[1]), reverse=True
    ):
        percentage = len(files) / distribution["total_files"] * 100
        print(f"   {module:12}: {len(files):3} 个文件 ({percentage:5.1f}%)")

    # 按深度分布
    print("\n📁 按目录深度分布")
    for depth, files in sorted(distribution["by_depth"].items()):
        percentage = len(files) / distribution["total_files"] * 100
        print(f"   深度 {depth:2}: {len(files):3} 个文件 ({percentage:5.1f}%)")

    # 目录结构合理性评估
    print("\n🔍 目录结构评估")
    if issues:
        print("   ⚠️ 发现的问题:")
        for issue in issues:
            print(f"      • {issue}")
    else:
        print("   ✅ 未发现明显问题")

    if suggestions:
        print("\n   💡 改进建议:")
        for suggestion in suggestions:
            print(f"      • {suggestion}")

    # 测试文件列表
    print("\n📄 所有测试文件列表")
    print("-" * 60)
    for file_path in sorted(test_files):
        relative_path = file_path.relative_to(Path("."))
        print(f"   {relative_path}")

    # 保存详细数据
    report_data = {
        "timestamp": "2025-10-05",
        "total_files": distribution["total_files"],
        "by_type": {k: len(v) for k, v in distribution["by_type"].items()},
        "by_module": {k: len(v) for k, v in distribution["by_module"].items()},
        "issues": issues,
        "suggestions": suggestions,
        "test_files": [str(f.relative_to(".")) for f in test_files],
    }

    with open("test_distribution_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print("\n✅ 详细报告已保存到: test_distribution_report.json")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    generate_report()
