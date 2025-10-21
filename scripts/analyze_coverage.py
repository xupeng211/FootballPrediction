#!/usr/bin/env python3
"""
快速分析测试覆盖率
识别需要添加测试的模块
"""

import os
import sys
from pathlib import Path
import subprocess
import json


def find_uncovered_modules():
    """找出未覆盖的模块"""
    print("🔍 分析测试覆盖率...\n")

    # 运行快速覆盖率测试（只收集数据，不生成详细报告）
    print("1. 运行覆盖率测试（仅单元测试）...")
    subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "-q",  # 安静模式
            "--maxfail=10",  # 最多10个失败就停止
            "-x",  # 遇到第一个失败就停止
        ],
        capture_output=True,
        text=True,
        timeout=120,  # 2分钟超时
    )

    # 读取覆盖率报告
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("❌ 无法生成覆盖率报告")
        return

    with open(coverage_file) as f:
        data = json.load(f)

    total_coverage = data["totals"]["percent_covered"]
    print(f"\n📊 当前总覆盖率: {total_coverage:.2f}%")

    # 分析各模块
    modules = {}
    for file_path, metrics in data["files"].items():
        module_name = file_path.replace("src/", "").replace(".py", "").replace("/", ".")
        coverage_pct = metrics["summary"]["percent_covered"]

        modules[module_name] = {
            "file": file_path,
            "coverage": coverage_pct,
            "lines": metrics["summary"]["num_statements"],
            "missing": metrics["summary"]["missing_lines"],
            "covered": metrics["summary"]["covered_lines"],
        }

    # 按覆盖率排序
    sorted_modules = sorted(modules.items(), key=lambda x: x[1]["coverage"])

    print("\n📈 覆盖率详情:")
    print("-" * 80)
    print(f"{'模块':<40} {'覆盖率':<10} {'行数':<8} {'缺失':<8}")
    print("-" * 80)

    # 显示所有模块
    for module, info in sorted_modules:
        color = ""
        if info["coverage"] == 0:
            color = "🔴"
        elif info["coverage"] < 50:
            color = "🟡"
        else:
            color = "🟢"

        print(
            f"{color} {module:<40} {info['coverage']:>7.1f}% {info['lines']:>7} {info['missing']:>7}"
        )

    # 重点分析0覆盖率的模块
    zero_coverage = [(m, i) for m, i in sorted_modules if i["coverage"] == 0]
    low_coverage = [(m, i) for m, i in sorted_modules if 0 < i["coverage"] < 50]

    print("\n" + "=" * 80)
    print(f"🔴 零覆盖率模块 ({len(zero_coverage)}个):")
    print("=" * 80)

    for module, info in zero_coverage[:10]:  # 只显示前10个
        print(f"  • {module}")
        print(f"    文件: {info['file']}")
        print(f"    代码行数: {info['lines']}")
        print()

    if len(zero_coverage) > 10:
        print(f"  ... 还有 {len(zero_coverage) - 10} 个模块")

    print("\n" + "=" * 80)
    print(f"🟡 低覆盖率模块 (<50%) ({len(low_coverage)}个):")
    print("=" * 80)

    for module, info in low_coverage[:10]:  # 只显示前10个
        print(f"  • {module}: {info['coverage']:.1f}% ({info['missing']} 行未覆盖)")

    # 生成建议
    print("\n" + "=" * 80)
    print("💡 优化建议:")
    print("=" * 80)

    if zero_coverage:
        print("1. 优先为零覆盖率模块添加基础测试:")
        for module, info in zero_coverage[:5]:
            test_file = f"tests/unit/{module.replace('.', '/')}.py"
            print(f"   - 创建 {test_file}")

    if low_coverage:
        print("\n2. 为低覆盖率模块补充测试用例:")
        for module, info in low_coverage[:5]:
            print(f"   - {module}: 需要覆盖 {info['missing']} 行代码")

    print(f"\n3. 目标：将覆盖率从 {total_coverage:.1f}% 提升到 35%+")
    print("4. 重点关注核心业务模块：")
    print("   - services/*")
    print("   - database/repositories/*")
    print("   - domain/*")

    # 保存分析结果
    analysis = {
        "total_coverage": total_coverage,
        "zero_coverage_modules": [m for m, _ in zero_coverage],
        "low_coverage_modules": [(m, i["coverage"]) for m, i in low_coverage],
        "modules": modules,
    }

    with open("reports/coverage_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    print("\n📄 详细分析已保存到: reports/coverage_analysis.json")

    return analysis


def generate_test_templates():
    """为未覆盖的模块生成测试模板"""
    print("\n🛠️  生成测试模板...")

    # 读取分析结果
    analysis_file = Path("reports/coverage_analysis.json")
    if not analysis_file.exists():
        print("请先运行覆盖率分析")
        return

    with open(analysis_file) as f:
        analysis = json.load(f)

    # 为每个零覆盖率模块生成测试模板
    count = 0
    for module in analysis["zero_coverage_modules"][:5]:  # 只生成前5个
        if "tests" in module or "conftest" in module:
            continue

        # 创建测试文件路径
        test_path = Path(f"tests/unit/{module.replace('.', '/')}_test.py")
        test_path.parent.mkdir(parents=True, exist_ok=True)

        if test_path.exists():
            continue

        # 生成测试模板
        template = f'''"""
Tests for {module}
"""

import pytest
from unittest.mock import Mock, patch

# TODO: Import the module to test
# from {module} import ClassName, function_name


class Test{module.title().replace('.', '')}:
    """Test cases for {module}"""

    def setup_method(self):
        """Set up test fixtures"""
        pass

    def teardown_method(self):
        """Clean up after tests"""
        pass

    # TODO: Add test methods
    # def test_example(self):
    #     """Example test case"""
    #     assert True
'''

        with open(test_path, "w") as f:
            f.write(template)

        print(f"✅ 创建测试模板: {test_path}")
        count += 1

    if count == 0:
        print("所有模块都已有测试文件")
    else:
        print(f"\n生成了 {count} 个测试模板")


if __name__ == "__main__":
    # 创建reports目录
    Path("reports").mkdir(exist_ok=True)

    # 运行分析
    analysis = find_uncovered_modules()

    # 生成测试模板
    if analysis and analysis["zero_coverage_modules"]:
        generate_test_templates()

    print("\n✅ 分析完成！")
