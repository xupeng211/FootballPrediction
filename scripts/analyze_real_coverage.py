#!/usr/bin/env python3
"""分析实际覆盖率情况"""

import subprocess
import re
import json


def get_coverage_stats():
    """获取覆盖率统计"""
    # 运行覆盖率测试
    result = subprocess.run(
        ["coverage", "report", "--format=json"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"Error running coverage: {result.stderr}")
        return None

    try:
        data = json.loads(result.stdout)
        return data
    except json.JSONDecodeError:
        # 如果JSON解析失败，使用文本格式
        return parse_text_coverage(result.stdout)


def parse_text_coverage(text):
    """解析文本格式的覆盖率报告"""
    lines = text.split("\n")
    totals = None

    for line in lines:
        if line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 5:
                totals = {
                    "statements": int(parts[1]),
                    "missing": int(parts[2]),
                    "branches": int(parts[3]) if parts[3] != "-" else 0,
                    "coverage": float(parts[-1].strip("%")),
                }

    return {"totals": totals}


def analyze_source_distribution():
    """分析源代码分布"""
    import os
    from pathlib import Path

    Path("src")
    stats = {}

    # 统计各个模块的行数
    for module in [
        "api",
        "services",
        "database",
        "utils",
        "adapters",
        "core",
        "domain",
    ]:
        cmd = f"find src/{module} -name '*.py' -type f | xargs wc -l | tail -1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split()
            if lines:
                stats[module] = int(lines[0])

    return stats


def main():
    print("📊 覆盖率分析报告\n")

    # 获取覆盖率统计
    coverage_data = get_coverage_stats()
    if not coverage_data:
        print("❌ 无法获取覆盖率数据")
        return

    total = coverage_data.get("totals", {})
    if not total:
        print("❌ 无法解析覆盖率数据")
        return

    print(f"当前总体覆盖率: {total.get('coverage', 0):.1f}%")
    print(f"总语句数: {total.get('statements', 0):,}")
    print(f"未覆盖语句: {total.get('missing', 0):,}\n")

    # 分析源代码分布
    print("📁 源代码分布:")
    stats = analyze_source_distribution()
    total_lines = sum(stats.values())

    for module, lines in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (lines / total_lines * 100) if total_lines > 0 else 0
        print(f"  {module:10}: {lines:6,} 行 ({percentage:5.1f}%)")

    print(f"\n总计: {total_lines:,} 行\n")

    # 计算utils覆盖率对总体的影响
    if "utils" in stats:
        utils_lines = stats["utils"]
        utils_percentage = (utils_lines / total_lines * 100) if total_lines > 0 else 0
        print(f"📈 utils模块占比: {utils_percentage:.1f}%")

        # 假设utils达到100%覆盖率
        utils_current_coverage = 0.35  # 从之前的测试得知utils约35%覆盖率
        additional_coverage = utils_lines * (1 - utils_current_coverage)
        potential_total_coverage = (
            (total.get("statements", 0) - total.get("missing", 0) + additional_coverage)
            / total.get("statements", 0)
            * 100
        )

        print(
            f"🎯 如果utils达到100%覆盖率，总体覆盖率可达: {potential_total_coverage:.1f}%"
        )

    print("\n💡 建议:")
    print("1. 当前主要测试集中在utils模块")
    print("2. 要提升总体覆盖率，需要测试更多模块:")
    print("   - src/api (API路由)")
    print("   - src/services (业务服务)")
    print("   - src/database (数据库模型)")
    print("   - src/adapters (适配器)")
    print("3. 或者调整覆盖率配置，只计算特定模块")


if __name__ == "__main__":
    main()
