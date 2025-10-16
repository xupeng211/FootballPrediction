#!/usr/bin/env python3
"""
最终覆盖率验证
总结测试覆盖率提升工作
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

def final_coverage_report():
    """生成最终的覆盖率报告"""
    print("📊 最终测试覆盖率验证")
    print("=" * 60)

    # 运行覆盖率测试
    print("1. 运行完整的单元测试覆盖率...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/unit/", "--cov=src", "--cov-report=json", "-q"],
        capture_output=True,
        text=True,
        timeout=300  # 5分钟超时
    )

    # 读取结果
    if Path("coverage.json").exists():
        with open("coverage.json") as f:
            data = json.load(f)

        total_coverage = data["totals"]["percent_covered"]
        total_lines = data["totals"]["num_statements"]
        covered_lines = data["totals"]["covered_lines"]
        missing_lines = data["totals"]["missing_lines"]

        print(f"\n📈 覆盖率统计:")
        print(f"   总覆盖率: {total_coverage:.2f}%")
        print(f"   总代码行: {total_lines}")
        print(f"   已覆盖行: {covered_lines}")
        print(f"   未覆盖行: {missing_lines}")

        # 统计覆盖率分布
        coverage_ranges = {
            "0%": 0,
            "1-10%": 0,
            "11-30%": 0,
            "31-60%": 0,
            "61-90%": 0,
            "91-100%": 0
        }

        perfect_coverage = []
        good_coverage = []
        needs_improvement = []

        for file_path, metrics in data["files"].items():
            coverage_pct = metrics["summary"]["percent_covered"]
            module_name = file_path.replace("src/", "").replace(".py", "")

            if coverage_pct == 0:
                coverage_ranges["0%"] += 1
            elif coverage_pct <= 10:
                coverage_ranges["1-10%"] += 1
                needs_improvement.append((module_name, coverage_pct))
            elif coverage_pct <= 30:
                coverage_ranges["11-30%"] += 1
                needs_improvement.append((module_name, coverage_pct))
            elif coverage_pct <= 60:
                coverage_ranges["31-60%"] += 1
                good_coverage.append((module_name, coverage_pct))
            elif coverage_pct <= 90:
                coverage_ranges["61-90%"] += 1
                good_coverage.append((module_name, coverage_pct))
            else:
                coverage_ranges["91-100%"] += 1
                perfect_coverage.append((module_name, coverage_pct))

        print(f"\n📋 覆盖率分布:")
        for range_name, count in coverage_ranges.items():
            print(f"   {range_name:>7}: {count:3d} 个模块")

        print(f"\n✨ 完美覆盖的模块 (91-100%):")
        for module, coverage in perfect_coverage[:10]:
            print(f"   - {module}: {coverage:.1f}%")
        if len(perfect_coverage) > 10:
            print(f"   ... 还有 {len(perfect_coverage) - 10} 个模块")

        print(f"\n👍 覆盖良好的模块 (31-90%):")
        for module, coverage in good_coverage[:10]:
            print(f"   - {module}: {coverage:.1f}%")
        if len(good_coverage) > 10:
            print(f"   ... 还有 {len(good_coverage) - 10} 个模块")

        if needs_improvement:
            print(f"\n🔧 需要改进的模块 (<30%):")
            for module, coverage in needs_improvement[:10]:
                print(f"   - {module}: {coverage:.1f}%")

        # 检查是否达到目标
        targets = [20.0, 25.0, 30.0, 35.0]
        print(f"\n🎯 目标达成情况:")
        for target in targets:
            if total_coverage >= target:
                print(f"   ✅ {target}%: 已达成！")
            else:
                print(f"   ❌ {target}%: 还差 {target - total_coverage:.1f}%")

        # 生成改进建议
        print(f"\n💡 改进建议:")
        if total_coverage < 25:
            print("   1. 优先为零覆盖率模块添加基础测试")
            print("   2. 为导入错误检查模块修复依赖问题")
            print("   3. 添加更多参数化测试用例")
        elif total_coverage < 30:
            print("   1. 为低覆盖率模块（<30%）补充测试")
            print("   2. 增加边界条件和异常处理测试")
            print("   3. 添加集成测试覆盖更多场景")
        else:
            print("   1. 持续维护现有测试质量")
            print("   2. 添加更复杂的业务场景测试")
            print("   3. 考虑添加性能测试")

        # 保存详细报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "coverage": {
                "total_percent": total_coverage,
                "total_lines": total_lines,
                "covered_lines": covered_lines,
                "missing_lines": missing_lines
            },
            "distribution": coverage_ranges,
            "modules": {
                "perfect": perfect_coverage,
                "good": good_coverage,
                "needs_improvement": needs_improvement
            },
            "targets_met": [t for t in targets if total_coverage >= t]
        }

        with open("reports/final_coverage_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 详细报告已保存到: reports/final_coverage_report.json")

        return total_coverage

    else:
        print("❌ 无法生成覆盖率报告")
        return 0

def summary_achievements():
    """总结成就"""
    print("\n" + "=" * 60)
    print("🏆 测试覆盖率提升工作总结")
    print("=" * 60)

    print("\n✅ 已完成的工作:")
    print("1. ✅ 分析了当前测试覆盖率状况")
    print("2. ✅ 为核心模块生成了基础测试")
    print("3. ✅ 为API模块补充了测试用例")
    print("4. ✅ 为低覆盖率模块创建了测试模板")
    print("5. ✅ 创建了测试覆盖率提升工具链")

    print("\n🛠️ 创建的工具:")
    print("• scripts/analyze_coverage.py - 覆盖率分析工具")
    print("• scripts/boost_coverage.py - 智能测试生成器")
    print("• scripts/quick_coverage_boost.py - 快速覆盖率提升")
    print("• scripts/boost_low_coverage.py - 低覆盖率模块处理")
    print("• scripts/final_coverage_check.py - 最终验证工具")

    print("\n📊 使用方法:")
    print("• 查看覆盖率: make coverage-local")
    print("• 生成测试: python scripts/boost_coverage.py")
    print("• 分析报告: python scripts/final_coverage_check.py")

if __name__ == "__main__":
    # 创建reports目录
    Path("reports").mkdir(exist_ok=True)

    # 运行最终验证
    coverage = final_coverage_report()

    # 显示总结
    summary_achievements()

    # 最终建议
    print("\n" + "=" * 60)
    if coverage >= 30:
        print("🎉 恭喜！测试覆盖率已达到30%+目标！")
        print("   可以继续向35%目标努力")
    elif coverage >= 25:
        print("👍 做得好！测试覆盖率已达到25%+")
        print("   继续努力可以达到30%目标")
    elif coverage >= 20:
        print("💪 进步明显！测试覆盖率已达到20%+")
        print("   使用提供的工具继续提升")
    else:
        print("📈 继续努力！使用自动化工具提升覆盖率")

    print("\n下一步：")
    print("1. 运行 make prepush 确保代码质量")
    print("2. 查看报告: reports/final_coverage_report.json")
    print("3. 使用工具继续提升覆盖率")
    print("4. 定期运行 Nightly 测试保持质量")
