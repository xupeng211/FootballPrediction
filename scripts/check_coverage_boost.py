#!/usr/bin/env python3
"""
检查覆盖率提升效果
"""

import subprocess
import json
from pathlib import Path


def check_coverage():
    """检查覆盖率"""
    print("📊 检查测试覆盖率提升效果...")
    print("=" * 60)

    # 运行覆盖率测试
    print("1. 运行覆盖率测试...")
    subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=src",
            "--cov-report=json",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=180,  # 3分钟超时
    )

    # 读取结果
    if Path("coverage.json").exists():
        with open("coverage.json") as f:
            data = json.load(f)

        total_coverage = data["totals"]["percent_covered"]
        total_lines = data["totals"]["num_statements"]
        covered_lines = data["totals"]["covered_lines"]
        missing_lines = data["totals"]["missing_lines"]

        print("\n📈 覆盖率统计:")
        print(f"   总覆盖率: {total_coverage:.2f}%")
        print(f"   总代码行: {total_lines}")
        print(f"   已覆盖行: {covered_lines}")
        print(f"   未覆盖行: {missing_lines}")

        # 显示覆盖率>0的模块
        print("\n📋 已覆盖的模块:")
        modules_with_coverage = 0
        for file_path, metrics in data["files"].items():
            if metrics["summary"]["percent_covered"] > 0:
                modules_with_coverage += 1
                module_name = file_path.replace("src/", "").replace(".py", "")
                coverage_pct = metrics["summary"]["percent_covered"]
                print(f"   - {module_name}: {coverage_pct:.1f}%")

        print(f"\n✅ 总计有 {modules_with_coverage} 个模块有测试覆盖")

        # 检查是否达到目标
        target = 35.0
        if total_coverage >= target:
            print(f"\n🎉 恭喜！覆盖率已达到目标 {target}%+")
            print("   可以提交代码了！")
        else:
            print(
                f"\n💪 当前覆盖率 {total_coverage:.1f}%，距离目标 {target}% 还差 {target - total_coverage:.1f}%"
            )
            print("   建议继续添加更多测试用例")

        # 显示覆盖率最低的5个模块（有测试但覆盖率低）
        print("\n🔧 需要改进的模块（有测试但覆盖率低）:")
        sorted_files = sorted(
            [
                (f, m)
                for f, m in data["files"].items()
                if m["summary"]["percent_covered"] > 0
            ],
            key=lambda x: x[1]["summary"]["percent_covered"],
        )
        for file_path, metrics in sorted_files[:5]:
            if metrics["summary"]["percent_covered"] < 50:
                module_name = file_path.replace("src/", "").replace(".py", "")
                missing = metrics["summary"]["missing_lines"]
                print(
                    f"   - {module_name}: {metrics['summary']['percent_covered']:.1f}% (缺{missing}行)"
                )

    else:
        print("❌ 无法生成覆盖率报告")


if __name__ == "__main__":
    check_coverage()
