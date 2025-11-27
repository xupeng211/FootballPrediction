#!/usr/bin/env python3
import json

# 解析coverage.json
with open("coverage.json") as f:
    data = json.load(f)

totals = data["totals"]
print("=== 整体覆盖率统计 ===")
print(f"覆盖率: {totals['percent_covered']:.2f}%")
print(f"覆盖行数: {totals['covered_lines']}")
print(f"总行数: {totals['num_statements']}")
print(f"未覆盖行数: {totals['missing_lines']}")

print("\n=== 未覆盖文件Top 50 (按未覆盖行数排序) ===")
uncovered_files = []
for file_path, file_data in data["files"].items():
    missing_lines = file_data["summary"]["missing_lines"]
    if missing_lines > 0:
        uncovered_files.append({
            "file": file_path,
            "missing_lines": missing_lines,
            "total_lines": file_data["summary"]["num_statements"],
            "covered_lines": file_data["summary"]["covered_lines"],
            "coverage": file_data["summary"]["percent_covered"]
        })

uncovered_files.sort(key=lambda x: x["missing_lines"], reverse=True)
print("| Rank | File | Uncovered Lines | Total Lines | Coverage |")
print("|------|------|----------------|-------------|----------|")

for i, file_info in enumerate(uncovered_files[:50], 1):
    file_name = file_info["file"]
    missing = file_info["missing_lines"]
    total = file_info["total_lines"]
    coverage = file_info["coverage"]
    print(f"| {i:2d} | {file_name} | {missing} | {total} | {coverage:.1f}% |")

print(f"\n总未覆盖文件数: {len(uncovered_files)}")