#!/usr/bin/env python3
"""
精确的全局代码体量与覆盖率分析脚本
解析coverage.xml获取准确数据
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET


def count_lines_of_code(file_path: str) -> int:
    """计算文件的有效代码行数（排除空行和注释）"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        code_lines = 0
        for line in lines:
            line = line.strip()
            # 排除空行和单行注释
            if line and not line.startswith("#"):
                code_lines += 1
        return code_lines
    except Exception:
        return 0


def parse_coverage_xml() -> Dict[str, Tuple[int, int, float]]:
    """解析coverage.xml文件"""
    coverage_data = {}

    try:
        tree = ET.parse("/home/user/projects/FootballPrediction/coverage.xml")
        root = tree.getroot()

        # 查找所有classes
        for package in root.findall(".//package"):
            for cls in package.findall(".//class"):
                filename = cls.get("filename")
                line_rate = float(cls.get("line-rate", 0))
                lines_covered = int(cls.get("lines-covered", 0))
                lines_valid = int(cls.get("lines-valid", 0))

                if filename and filename.startswith("src/"):
                    coverage_percent = line_rate * 100
                    coverage_data[filename] = (
                        lines_valid,
                        lines_valid - lines_covered,
                        coverage_percent,
                    )

    except Exception as e:
        print(f"解析coverage.xml时出错: {e}")

    return coverage_data


def analyze_source_files() -> List[Dict]:
    """分析源文件"""
    src_dir = Path("/home/user/projects/FootballPrediction/src")
    files_data = []

    print("🔍 正在扫描源文件...")

    # 递归查找所有.py文件
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        relative_path = py_file.relative_to(src_dir.parent)
        file_str = str(relative_path)

        # 计算代码行数
        loc = count_lines_of_code(py_file)

        files_data.append({"file_path": file_str, "loc": loc, "abs_path": str(py_file)})

    return files_data


def main():
    """主函数"""
    print("🚀 开始精确的全局代码体量与覆盖率分析...")

    # 分析源文件
    files_data = analyze_source_files()

    # 获取覆盖率数据
    print("📊 解析coverage.xml...")
    coverage_data = parse_coverage_xml()

    # 合并数据
    analysis_results = []
    for file_info in files_data:
        file_path = file_info["file_path"]

        if file_path in coverage_data:
            total_stmts, missing_stmts, coverage = coverage_data[file_path]
        else:
            # 没有覆盖率数据的文件
            total_stmts = missing_stmts = 0
            coverage = 0.0

        analysis_results.append(
            {
                "file_path": file_path,
                "loc": file_info["loc"],
                "total_stmts": total_stmts,
                "missing_stmts": missing_stmts,
                "coverage": coverage,
                "abs_path": file_info["abs_path"],
            }
        )

    # 过滤掉语句数为0的文件（可能是非代码文件或特殊文件）
    filtered_results = [item for item in analysis_results if item["total_stmts"] > 0]

    # 按优先级排序：覆盖率低 -> 文件行数大 -> 语句数大
    filtered_results.sort(key=lambda x: (x["coverage"], -x["loc"], -x["total_stmts"]))

    # 输出结果
    print("\n" + "=" * 100)
    print("📋 精确的全局代码体量与覆盖率分析结果")
    print("=" * 100)

    print(f"{'文件路径':<55} {'代码行数':<8} {'总语句':<8} {'覆盖率':<8} {'优先级':<6}")
    print("-" * 100)

    for i, item in enumerate(filtered_results[:20], 1):
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
    avg_coverage = (
        sum(item["coverage"] * item["total_stmts"] for item in filtered_results) / total_stmts
        if total_stmts > 0
        else 0
    )

    print("📊 总体统计:")
    print(f"   - 总文件数: {total_files}")
    print(f"   - 总代码行数: {total_loc:,} 行")
    print(f"   - 总语句数: {total_stmts:,} 句")
    print(f"   - 平均覆盖率: {avg_coverage:.1f}%")
    print()

    # 保存结果到文件
    import json

    with open(
        "/home/user/projects/FootballPrediction/coverage_analysis_results_precise.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "timestamp": str(
                    subprocess.run(["date"], capture_output=True, text=True).stdout.strip()
                ),
                "total_files": total_files,
                "total_loc": total_loc,
                "total_stmts": total_stmts,
                "avg_coverage": avg_coverage,
                "top_10_files": top_10_files,
                "all_files": filtered_results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("✅ 分析完成，结果已保存到 coverage_analysis_results_precise.json")
    return top_10_files


if __name__ == "__main__":
    main()
