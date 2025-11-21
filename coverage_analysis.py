#!/usr/bin/env python3
"""
Coverage Analysis Script
解析 coverage.json 并生成结构化报告
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

def parse_coverage_json(file_path: str) -> Dict[str, Any]:
    """解析coverage.json文件"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def extract_uncovered_files(coverage_data: Dict[str, Any], top_n: int = 50) -> List[Dict[str, Any]]:
    """提取未覆盖的文件，按未覆盖行数排序"""
    files = coverage_data.get('files', {})
    uncovered_files = []

    for file_path, file_info in files.items():
        # 只关注src目录下的文件
        if not file_path.startswith('src/'):
            continue

        summary = file_info.get('summary', {})
        total_lines = summary.get('num_statements', 0)
        covered_lines = summary.get('covered_lines', 0)
        uncovered_lines = total_lines - covered_lines

        # 跳过完全覆盖的文件
        if uncovered_lines <= 0:
            continue

        uncovered_files.append({
            'file_path': file_path,
            'uncovered_lines': uncovered_lines,
            'total_lines': total_lines,
            'covered_lines': covered_lines,
            'coverage_percent': round((covered_lines / total_lines * 100), 2) if total_lines > 0 else 0,
            'missing_lines': file_info.get('missing_lines', [])
        })

    # 按未覆盖行数排序
    uncovered_files.sort(key=lambda x: x['uncovered_lines'], reverse=True)
    return uncovered_files[:top_n]

def get_overall_stats(coverage_data: Dict[str, Any]) -> Dict[str, Any]:
    """获取整体覆盖率统计"""
    totals = coverage_data.get('totals', {})
    return {
        'coverage_percent': round(totals.get('percent_covered', 0), 2),
        'num_statements': totals.get('num_statements', 0),
        'covered_lines': totals.get('covered_lines', 0),
        'missing_lines': totals.get('missing_lines', 0),
        'excluded_lines': totals.get('excluded_lines', 0)
    }

def main():
    """主函数"""
    coverage_file = 'coverage.json'

    if not os.path.exists(coverage_file):
        print(f"Error: {coverage_file} not found")
        return

    # 解析覆盖率数据
    coverage_data = parse_coverage_json(coverage_file)

    # 获取整体统计
    overall_stats = get_overall_stats(coverage_data)

    # 提取未覆盖文件Top 50
    uncovered_files = extract_uncovered_files(coverage_data, 50)

    # 生成分析报告
    analysis_report = {
        'overall_stats': overall_stats,
        'uncovered_files': uncovered_files,
        'total_files_analyzed': len(uncovered_files)
    }

    # 保存为JSON文件
    with open('coverage_analysis_report.json', 'w') as f:
        json.dump(analysis_report, f, indent=2, ensure_ascii=False)

    # 打印基本信息
    print(f"Coverage Analysis Results:")
    print(f"Overall Coverage: {overall_stats['coverage_percent']}%")
    print(f"Total Statements: {overall_stats['num_statements']}")
    print(f"Covered Lines: {overall_stats['covered_lines']}")
    print(f"Missing Lines: {overall_stats['missing_lines']}")
    print(f"Uncovered Files Found: {len(uncovered_files)}")

    return analysis_report

if __name__ == '__main__':
    main()