#!/usr/bin/env python3
"""分析测试覆盖率缺口"""

import subprocess
import json
from pathlib import Path
from collections import defaultdict

def run_coverage_analysis():
    """运行覆盖率分析"""
    print("📊 测试覆盖率分析报告")
    print("=" * 60)

    # 运行完整的覆盖率报告
    print("\n1. 获取完整覆盖率数据...")
    result = subprocess.run(
        ["python", "-m", "pytest",
         "--cov=src",
         "--cov-report=json",
         "--cov-report=term",
         "--tb=no", "-q"],
        capture_output=True, text=True
    )

    # 读取覆盖率报告
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("❌ 无法找到coverage.json文件")
        return

    with open(coverage_file) as f:
        data = json.load(f)

    total_coverage = data["totals"]["percent_covered"]
    total_files = len(data["files"])

    print(f"\n📈 总体覆盖率：{total_coverage:.1f}%")
    print(f"📁 总文件数：{total_files}")

    # 分析各模块覆盖率
    print("\n2. 模块覆盖率分析：")
    print("-" * 60)

    # 按目录分组
    modules = defaultdict(list)
    for filename, file_data in data["files"].items():
        if "src/" in filename:
            # 提取模块名
            parts = filename.split("/")
            if len(parts) > 2:
                module = parts[2]
                modules[module].append({
                    "file": "/".join(parts[2:]),
                    "coverage": file_data["summary"]["percent_covered"],
                    "lines": file_data["summary"]["num_statements"],
                    "missed": file_data["summary"]["missing_lines"]
                })

    # 显示各模块统计
    module_stats = {}
    for module, files in modules.items():
        total_lines = sum(f["lines"] for f in files)
        total_covered = sum(f["lines"] - f["missed"] for f in files)
        coverage = (total_covered / total_lines * 100) if total_lines > 0 else 0

        module_stats[module] = {
            "coverage": coverage,
            "files": len(files),
            "lines": total_lines
        }

        # 根据覆盖率显示不同的emoji
        if coverage >= 80:
            emoji = "🟢"
        elif coverage >= 50:
            emoji = "🟡"
        else:
            emoji = "🔴"

        print(f"{emoji} {module:20} | {coverage:5.1f}% | {len(files):3}文件 | {total_lines:4}行")

    # 找出需要优先测试的模块
    print("\n3. 优先测试建议（按代码量排序）：")
    print("-" * 60)

    # 按代码量排序
    sorted_modules = sorted(module_stats.items(),
                          key=lambda x: x[1]["lines"],
                          reverse=True)

    for module, stats in sorted_modules[:10]:
        if stats["coverage"] < 50:
            print(f"🎯 {module:20} - {stats['lines']:4}行代码，覆盖率{stats['coverage']:.1f}%")

    # 分析我们已测试的模块
    print("\n4. 已测试模块详情：")
    print("-" * 60)

    tested_modules = ["string_utils", "helpers", "predictions"]
    for module in tested_modules:
        if module in modules:
            print(f"\n✅ {module} 模块：")
            for file_info in modules[module]:
                coverage = file_info["coverage"]
                if coverage == 100:
                    print(f"   - {file_info['file']:30} {coverage:5.1f}% ✅")
                elif coverage >= 80:
                    print(f"   - {file_info['file']:30} {coverage:5.1f}% 🟡")
                else:
                    print(f"   - {file_info['file']:30} {coverage:5.1f}% 🔴")

    # 计算要达到50%覆盖率需要测试的内容
    print("\n5. 达到50%覆盖率的目标：")
    print("-" * 60)

    current_lines = data["totals"]["num_statements"]
    covered_lines = current_lines * (total_coverage / 100)
    target_lines = current_lines * 0.5
    needed_lines = target_lines - covered_lines

    print(f"当前总行数：{current_lines}")
    print(f"已覆盖行数：{covered_lines:.0f}")
    print(f"目标行数（50%）：{target_lines:.0f}")
    print(f"还需覆盖：{needed_lines:.0f}行")

    # 建议测试的模块
    print("\n💡 建议优先测试以下模块：")
    print("-" * 60)

    suggestions = []
    for module, stats in sorted_modules:
        if stats["coverage"] < 30 and stats["lines"] > 50:
            potential_coverage = min(50, stats["coverage"] + 30)
            gain_lines = stats["lines"] * ((potential_coverage - stats["coverage"]) / 100)
            suggestions.append({
                "module": module,
                "current": stats["coverage"],
                "potential": potential_coverage,
                "gain": gain_lines,
                "lines": stats["lines"]
            })

    # 按潜在收益排序
    suggestions.sort(key=lambda x: x["gain"], reverse=True)

    for i, suggestion in enumerate(suggestions[:5], 1):
        print(f"{i}. {suggestion['module']:20}")
        print(f"   当前覆盖率：{suggestion['current']:.1f}%")
        print(f"   潜在覆盖率：{suggestion['potential']:.1f}%")
        print(f"   代码行数：{suggestion['lines']}")
        print(f"   覆盖收益：{suggestion['gain']:.0f}行")
        print()

    # 生成报告文件
    report = {
        "timestamp": "2025-10-15T21:50:00",
        "total_coverage": total_coverage,
        "total_files": total_files,
        "module_stats": module_stats,
        "suggestions": suggestions[:5],
        "target_coverage": 50,
        "needed_lines": needed_lines
    }

    report_file = Path("coverage_gap_analysis.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 详细报告已保存：{report_file}")

    return report

if __name__ == "__main__":
    run_coverage_analysis()
