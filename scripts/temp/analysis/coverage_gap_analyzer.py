#!/usr/bin/env python3
"""
Coverage Gap Analyzer - 覆盖率差距分析器
分析未覆盖的代码行数最多的文件，找出高回报测试目标
"""

import os
import ast
import json
from pathlib import Path
from typing import List, Dict, Tuple


def count_lines_in_file(file_path: Path) -> tuple[int, int]:
    """统计文件中的代码行数和逻辑行数"""
    if not file_path.exists():
        return 0, 0

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 统计非空、非注释的代码行数
        lines = content.split("\n")
        code_lines = 0

        for line in lines:
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                code_lines += 1

        total_lines = len(lines)
        return total_lines, code_lines

    except Exception:
        print(f"Error reading {file_path}: {e}")
        return 0, 0


def find_python_files(src_dir: Path) -> list[Path]:
    """找到所有Python文件"""
    python_files = []
    for root, dirs, files in os.walk(src_dir):
        # 跳过__pycache__目录
        dirs[:] = [d for d in dirs if not d.startswith("__pycache__")]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def load_existing_coverage() -> dict[str, float]:
    """加载现有的覆盖率数据（如果有的话）"""
    coverage_file = Path("coverage_final_gap.json")
    if coverage_file.exists():
        try:
            with open(coverage_file) as f:
                data = json.load(f)
                return {
                    k: v.get("summary", {}).get("percent_covered", 0)
                    for k, v in data.get("files", {}).items()
                }
        except Exception:
            print(f"Error loading coverage data: {e}")

    return {}


def analyze_high_value_targets():
    """分析高价值测试目标"""
    src_dir = Path("src")
    if not src_dir.exists():
        print("src目录不存在")
        return

    # 已处理的文件（今天测试过的）
    processed_files = {
        "src/events/bus.py",
        "src/services/inference_service.py",
        "src/cache/intelligent_cache_warmup.py",
        "src/utils/string_utils.py",
    }

    # 现有覆盖率数据
    existing_coverage = load_existing_coverage()

    print("🔍 扫描Python文件...")
    python_files = find_python_files(src_dir)

    candidates = []

    for file_path in python_files:
        rel_path = str(file_path)

        # 跳过已处理的文件
        if rel_path in processed_files:
            continue

        # 跳过测试文件和特殊文件
        if "test" in str(file_path) or "__init__.py" in str(file_path):
            continue

        # 跳过太小的文件
        total_lines, code_lines = count_lines_in_file(file_path)
        if code_lines < 20:
            continue

        # 估算未覆盖率（如果现有数据可用）
        coverage = existing_coverage.get(rel_path, 0)
        missing_lines = int(code_lines * (1 - coverage / 100))

        # 确定模块类型
        if "api" in str(file_path):
            module_type = "API"
        elif "services" in str(file_path):
            module_type = "Service"
        elif "cache" in str(file_path):
            module_type = "Cache"
        elif "ml" in str(file_path):
            module_type = "ML"
        elif "collectors" in str(file_path):
            module_type = "Collector"
        elif "database" in str(file_path):
            module_type = "Database"
        else:
            module_type = "Core"

        candidates.append(
            {
                "file": rel_path,
                "total_lines": total_lines,
                "code_lines": code_lines,
                "coverage": coverage,
                "missing_lines": missing_lines,
                "module_type": module_type,
            }
        )

    # 按未覆盖行数排序
    candidates.sort(key=lambda x: x["missing_lines"], reverse=True)

    return candidates


def main():
    """主函数"""
    print("📊 Coverage Gap Analysis Report")
    print("=" * 50)

    candidates = analyze_high_value_targets()

    if not candidates:
        print("没有找到合适的候选文件")
        return

    # 显示Top 10
    print("🎯 Top 10 High-Value Coverage Targets:")
    print(f"{'File':<40} {'Type':<10} {'Lines':<8} {'Coverage':<10} {'Missing':<8}")
    print("-" * 80)

    for i, candidate in enumerate(candidates[:10], 1):
        file_name = candidate["file"].split("/")[-1]  # 只显示文件名
        print(
            f"{file_name:<40} {candidate['module_type']:<10} "
            f"{candidate['code_lines']:<8} {candidate['coverage']:.1f}%{' ':<5} "
            f"{candidate['missing_lines']:<8}"
        )

    print("\n📈 分析完成:")
    print(f"   总候选文件数: {len(candidates)}")
    print(
        f"   Top 5 潜在覆盖提升: {sum(c['missing_lines'] for c in candidates[:5]):.0f} 行代码"
    )


if __name__ == "__main__":
    main()
