#!/usr/bin/env python3
"""
分析0%和低覆盖率文件，生成补测计划
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple


def get_coverage_data() -> List[Dict]:
    """获取覆盖率数据"""
    result = subprocess.run(
        ["coverage", "report", "--show-missing"], capture_output=True, text=True
    )

    files = []
    for line in result.stdout.split("\n"):
        if line.strip() and "src/" in line and not line.startswith("Name"):
            # 解析覆盖率行
            parts = re.split(r"\s+", line.strip())
            if len(parts) >= 5:
                filename = parts[0]
                stmts = int(parts[1]) if parts[1].isdigit() else 0
                missing = int(parts[2]) if parts[2].isdigit() else 0
                coverage = parts[3].replace("%", "")

                try:
                    coverage_pct = int(coverage)
                except ValueError:
                    coverage_pct = 0

                if stmts > 0:  # 只考虑有代码的文件
                    files.append(
                        {
                            "file": filename,
                            "statements": stmts,
                            "missing": missing,
                            "coverage": coverage_pct,
                            "priority": calculate_priority(stmts, coverage_pct),
                        }
                    )

    return files


def calculate_priority(statements: int, coverage: int) -> int:
    """计算优先级分数"""
    if coverage == 0:
        return statements * 3  # 0%覆盖的文件优先级最高
    elif coverage < 30:
        return statements * 2
    elif coverage < 50:
        return statements
    else:
        return 0


def generate_test_plan(files: List[Dict]) -> Dict[str, List[Dict]]:
    """生成测试计划"""
    plan = {
        "zero_coverage": [],  # 0%覆盖
        "low_coverage": [],  # 1-30%覆盖
        "medium_coverage": [],  # 31-60%覆盖
        "high_impact": [],  # 高价值文件
    }

    for file_info in files:
        if file_info["coverage"] == 0:
            plan["zero_coverage"].append(file_info)
        elif file_info["coverage"] <= 30:
            plan["low_coverage"].append(file_info)
        elif file_info["coverage"] <= 60:
            plan["medium_coverage"].append(file_info)

        # 识别高价值文件（API、核心服务等）
        if (
            any(
                keyword in file_info["file"]
                for keyword in ["api/", "service", "core/", "domain/", "adapter"]
            )
            and file_info["coverage"] < 50
        ):
            plan["high_impact"].append(file_info)

    # 按优先级排序
    for category in plan:
        plan[category].sort(key=lambda x: x["priority"], reverse=True)

    return plan


def generate_test_files(plan: Dict[str, List[Dict]]) -> List[Dict]:
    """生成需要创建的测试文件"""
    test_files = []

    # 处理0%覆盖的文件
    for file_info in plan["zero_coverage"][:10]:  # 前10个最重要的
        src_path = Path(file_info["file"])
        test_path = generate_test_path(src_path)

        test_files.append(
            {
                "source_file": file_info["file"],
                "test_file": str(test_path),
                "type": "comprehensive",
                "priority": "high",
                "estimated_lines": max(file_info["statements"], 50),
            }
        )

    # 处理低覆盖的关键文件
    for file_info in plan["high_impact"][:5]:
        src_path = Path(file_info["file"])
        test_path = generate_test_path(src_path)

        # 检查测试文件是否已存在
        if not test_path.exists():
            test_files.append(
                {
                    "source_file": file_info["file"],
                    "test_file": str(test_path),
                    "type": "integration",
                    "priority": "high",
                    "estimated_lines": max(file_info["missing"] // 2, 30),
                }
            )

    return test_files


def generate_test_path(src_path: Path) -> Path:
    """生成对应的测试文件路径"""
    # 将 src/ 转换为 tests/
    if src_path.parts[0] == "src":
        test_parts = ["tests"] + list(src_path.parts[1:])
        test_path = Path(*test_parts)
    else:
        test_path = Path("tests") / src_path

    # 将 .py 文件名改为 test_*.py
    if test_path.suffix == ".py":
        test_path = test_path.with_name(f"test_{test_path.name}")

    return test_path


def main():
    print("🔍 分析覆盖率数据...")
    files = get_coverage_data()

    print("\n📊 总体统计:")
    print(f"- 源文件总数: {len(files)}")
    zero_files = [f for f in files if f["coverage"] == 0]
    low_files = [f for f in files if 0 < f["coverage"] <= 30]
    print(f"- 0%覆盖率文件: {len(zero_files)}")
    print(f"- 低覆盖率文件(≤30%): {len(low_files)}")

    # 生成测试计划
    plan = generate_test_plan(files)

    print("\n📋 测试计划生成:")
    print("\n1. 0%覆盖率文件 (优先处理):")
    for i, f in enumerate(plan["zero_coverage"][:10], 1):
        print(f"   {i:2d}. {f['file']} ({f['statements']}行, 优先级:{f['priority']})")

    print("\n2. 高价值低覆盖文件:")
    for i, f in enumerate(plan["high_impact"][:5], 1):
        print(f"   {i}. {f['file']} ({f['coverage']}%, {f['missing']}行缺失)")

    # 生成测试文件列表
    test_files = generate_test_files(plan)

    print("\n📝 需要创建的测试文件:")
    for i, test in enumerate(test_files[:10], 1):
        print(f"   {i}. {test['test_file']} (测试 {test['source_file']})")

    # 保存详细报告
    import json

    report = {
        "analysis_date": "2025-01-18",
        "summary": {
            "total_files": len(files),
            "zero_coverage": len(plan["zero_coverage"]),
            "low_coverage": len(plan["low_coverage"]),
            "medium_coverage": len(plan["medium_coverage"]),
        },
        "plan": plan,
        "test_files_to_create": test_files[:15],
    }

    with open("docs/_reports/coverage/zero_coverage_analysis.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(
        "\n✅ 详细分析报告已保存到: docs/_reports/coverage/zero_coverage_analysis.json"
    )
    print("\n🎯 建议下一步行动:")
    print("1. 为0%覆盖率文件创建基础测试框架")
    print("2. 重点提升API和核心服务的覆盖率")
    print("3. 建立自动化测试生成脚本")


if __name__ == "__main__":
    main()
