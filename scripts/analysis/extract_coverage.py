#!/usr/bin/env python3
"""
从pytest覆盖率输出中提取数据进行分析
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple
import json


def count_lines_of_code(file_path: str) -> int:
    """计算文件的有效代码行数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        code_lines = 0
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                code_lines += 1
        return code_lines
    try:
        pass
def extract_coverage_from_output() -> Dict[str, Tuple[int, int, float]]:
    """从pytest覆盖率输出中提取数据"""
    # 运行pytest获取覆盖率
    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=src",
            "--cov-report=term-missing:skip-covered",
            "--disable-warnings",
            "--tb=no",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd="/home/user/projects/FootballPrediction",
    )

    coverage_data = {}
    lines = result.stdout.split("\n")

    # 解析覆盖率输出
    for line in lines:
        if "src/" in line and "%" in line and not line.startswith("TOTAL"):
            # 匹配格式: src/module/file.py                       100     50      0    50%   1-20
            match = re.match(
                r"(src/[^\s]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%\s+([\d%-]*)",
                line.strip(),
            )
            if match:
                file_path = match.group(1)
                total_stmts = int(match.group(2))
                missing_stmts = int(match.group(3))
                coverage = float(match.group(5))
                coverage_data[file_path] = (total_stmts, missing_stmts, coverage)

    return coverage_data


def main():
    """主函数"""
    print("🚀 开始从pytest输出提取覆盖率数据...")

    # 获取覆盖率数据
    print("📊 提取覆盖率数据...")
    coverage_data = extract_coverage_from_output()

    # 分析源文件
    src_dir = Path("/home/user/projects/FootballPrediction/src")
    analysis_results = []

    print("🔍 扫描源文件...")
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        relative_path = py_file.relative_to(src_dir.parent)
        file_str = str(relative_path)
        loc = count_lines_of_code(py_file)

        if file_str in coverage_data:
            total_stmts, missing_stmts, coverage = coverage_data[file_str]
        else:
            total_stmts = missing_stmts = 0
            coverage = 0.0

        analysis_results.append(
            {
                "file_path": file_str,
                "loc": loc,
                "total_stmts": total_stmts,
                "missing_stmts": missing_stmts,
                "coverage": coverage,
                "abs_path": str(py_file),
            }
        )

    # 过滤掉语句数为0的文件
    filtered_results = [item for item in analysis_results if item["total_stmts"] > 0]

    # 按优先级排序：覆盖率低 -> 文件行数大 -> 语句数大
    filtered_results.sort(key=lambda x: (x["coverage"], -x["loc"], -x["total_stmts"]))

    # 输出结果
    print("\n" + "=" * 100)
    print("📋 全局代码体量与覆盖率分析结果")
    print("=" * 100)

    print(f"{'文件路径':<55} {'代码行数':<8} {'总语句':<8} {'覆盖率':<8} {'优先级':<6}")
    print("-" * 100)

    for i, item in enumerate(filtered_results[:25], 1):
        priority = "🔴" if item["coverage"] < 20 else "🟡" if item["coverage"] < 50 else "🟢"
        print(
            f"{item['file_path']:<55} {item['loc']:<8} {item['total_stmts']:<8} {item['coverage']:<8.1f}% {priority}"
        )

    # 输出前10个需要补测的文件
    print("\n" + "=" * 100)
    print("🎯 前10个优先补测文件 (Batch-Ω 系列)")
    print("=" * 100)

    top_10_files = filtered_results[:10]
    for i, item in enumerate(top_10_files, 1):
        batch_id = f"Batch-Ω-{i:03d}"
        impact_score = item["loc"] * (100 - item["coverage"]) / 100
        print(f"{batch_id}: {item['file_path']}")
        print(f"         - 代码行数: {item['loc']:,} 行")
        print(f"         - 语句总数: {item['total_stmts']:,} 句")
        print(f"         - 当前覆盖率: {item['coverage']:.1f}%")
        print(f"         - 未覆盖语句: {item['missing_stmts']:,} 句")
        print(f"         - 影响分数: {impact_score:.1f}")
        print("         - 目标覆盖率: ≥70%")
        print()

    # 计算总体统计
    total_files = len(filtered_results)
    total_loc = sum(item["loc"] for item in filtered_results)
    total_stmts = sum(item["total_stmts"] for item in filtered_results)
    weighted_coverage = (
        sum(item["coverage"] * item["total_stmts"] for item in filtered_results) / total_stmts
        if total_stmts > 0
        else 0
    )

    print("📊 总体统计:")
    print(f"   - 总文件数: {total_files}")
    print(f"   - 总代码行数: {total_loc:,} 行")
    print(f"   - 总语句数: {total_stmts:,} 句")
    print(f"   - 加权平均覆盖率: {weighted_coverage:.1f}%")
    print()

    # 保存结果到文件
    with open(
        "/home/user/projects/FootballPrediction/coverage_analysis_final.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "timestamp": subprocess.run(
                    ["date"], capture_output=True, text=True
                ).stdout.strip(),
                "total_files": total_files,
                "total_loc": total_loc,
                "total_stmts": total_stmts,
                "weighted_coverage": weighted_coverage,
                "top_10_files": top_10_files,
                "all_files": filtered_results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("✅ 分析完成，结果已保存到 coverage_analysis_final.json")
    return top_10_files


if __name__ == "__main__":
    main()
