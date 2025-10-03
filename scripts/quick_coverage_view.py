#!/usr/bin/env python3
"""
快速查看测试覆盖率
"""

import json
import sys
from pathlib import Path

def show_coverage_summary():
    """显示覆盖率摘要"""
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        print("❌ 找不到coverage.json文件")
        print("请先运行: pytest --cov=src --cov-report=json")
        return

    with open(coverage_file) as f:
        data = json.load(f)

    totals = data['totals']
    print("\n📊 测试覆盖率摘要")
    print("=" * 60)
    print(f"总行数: {totals['num_statements']:,}")
    print(f"已覆盖: {totals['covered_lines']:,}")
    print(f"未覆盖: {totals['missing_lines']:,}")
    print(f"覆盖率: {totals['percent_covered']:.1f}%")

    # 显示覆盖率最高的文件
    print("\n✅ 覆盖率最高的文件:")
    files_data = []
    for file_path, file_data in data['files'].items():
        summary = file_data['summary']
        if summary['num_statements'] > 10:  # 忽略太小的文件
            files_data.append((file_path, summary['percent_covered'], summary['num_statements']))

    files_data.sort(key=lambda x: x[1], reverse=True)

    for file_path, coverage, lines in files_data[:10]:
        if coverage > 50:
            print(f"  {coverage:5.1f}% {file_path} ({lines}行)")

    # 显示覆盖率最低的文件
    print("\n❌ 需要改进的文件 (覆盖率 < 20%):")
    low_coverage = [f for f in files_data if f[1] < 20 and f[2] > 50]

    for file_path, coverage, lines in low_coverage[:10]:
        print(f"  {coverage:5.1f}% {file_path} ({lines}行)")

    # 统计目录覆盖率
    print("\n📁 目录覆盖率统计:")
    dir_stats = {}
    for file_path in data['files']:
        parts = file_path.split('/')
        if len(parts) > 2:
            directory = '/'.join(parts[:2])
            file_data = data['files'][file_path]['summary']
            if directory not in dir_stats:
                dir_stats[directory] = {'covered': 0, 'total': 0, 'files': 0}
            dir_stats[directory]['covered'] += file_data['covered_lines']
            dir_stats[directory]['total'] += file_data['num_statements']
            dir_stats[directory]['files'] += 1

    for directory, stats in sorted(dir_stats.items(), key=lambda x: x[1]['covered']/x[1]['total'] if x[1]['total'] > 0 else 0, reverse=True):
        if stats['total'] > 0:
            coverage = stats['covered'] / stats['total'] * 100
            print(f"  {coverage:5.1f}% {directory} ({stats['files']}文件)")

    print(f"\n💡 提示: 查看详细报告: open htmlcov/index.html")

if __name__ == "__main__":
    show_coverage_summary()