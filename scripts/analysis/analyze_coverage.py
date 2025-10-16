#!/usr/bin/env python3
"""
全局代码体量与覆盖率分析脚本
扫描src/目录下所有.py文件，获取代码行数和覆盖率数据
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def count_lines_of_code(file_path: str) -> int:
    """计算文件的有效代码行数（排除空行和注释）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        code_lines = 0
        for line in lines:
            line = line.strip()
            # 排除空行和单行注释
            if line and not line.startswith('#'):
                code_lines += 1
        return code_lines
    except Exception:
        return 0


def get_coverage_data() -> Dict[str, Tuple[int, int, int, float]]:
    """获取覆盖率数据"""
    # 运行pytest并获取覆盖率报告
    result = subprocess.run([
        'python', '-m', 'pytest', 'tests/unit/',
        '--cov=src', '--cov-report=term-missing:skip-covered',
        '--disable-warnings', '--tb=no', '-q'
    ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

    coverage_data = {}

    # 解析覆盖率输出
    lines = result.stdout.split('\n')
    for line in lines:
        if 'src/' in line and '%' in line:
            # 匹配格式: src/module/file.py                       100     50      0    50%   1-20
            match = re.match(r'(src/[^\s]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%\s+([\d%-]*)', line.strip())
            if match:
                file_path = match.group(1)
                total_stmts = int(match.group(2))
                missing_stmts = int(match.group(3))
                coverage = float(match.group(5))

                coverage_data[file_path] = (total_stmts, missing_stmts, coverage)

    return coverage_data


def analyze_source_files() -> List[Dict]:
    """分析源文件"""
    src_dir = Path('/home/user/projects/FootballPrediction/src')
    files_data = []

    print("🔍 正在扫描源文件...")

    # 递归查找所有.py文件
    for py_file in src_dir.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        relative_path = py_file.relative_to(src_dir.parent)
        file_str = str(relative_path)

        # 计算代码行数
        loc = count_lines_of_code(py_file)

        files_data.append({
            'file_path': file_str,
            'loc': loc,
            'abs_path': str(py_file)
        })

    return files_data


def main():
    """主函数"""
    print("🚀 开始全局代码体量与覆盖率分析...")

    # 分析源文件
    files_data = analyze_source_files()

    # 获取覆盖率数据
    print("📊 获取覆盖率数据...")
    coverage_data = get_coverage_data()

    # 合并数据
    analysis_results = []
    for file_info in files_data:
        file_path = file_info['file_path']

        if file_path in coverage_data:
            total_stmts, missing_stmts, coverage = coverage_data[file_path]
        else:
            # 没有覆盖率数据的文件
            total_stmts = missing_stmts = 0
            coverage = 0.0

        analysis_results.append({
            'file_path': file_path,
            'loc': file_info['loc'],
            'total_stmts': total_stmts,
            'missing_stmts': missing_stmts,
            'coverage': coverage,
            'abs_path': file_info['abs_path']
        })

    # 按优先级排序：覆盖率低 -> 文件行数大
    analysis_results.sort(key=lambda x: (x['coverage'], -x['loc'], -x['total_stmts']))

    # 输出结果
    print("\n" + "="*100)
    print("📋 全局代码体量与覆盖率分析结果")
    print("="*100)

    print(f"{'文件路径':<50} {'代码行数':<8} {'总语句':<8} {'覆盖率':<8} {'优先级':<6}")
    print("-" * 100)

    for i, item in enumerate(analysis_results[:20], 1):
        priority = "🔴" if item['coverage'] < 20 else "🟡" if item['coverage'] < 50 else "🟢"
        print(f"{item['file_path']:<50} {item['loc']:<8} {item['total_stmts']:<8} {item['coverage']:<8.1f}% {priority}")

    # 输出前10个需要补测的文件
    print("\n" + "="*100)
    print("🎯 前10个优先补测文件 (Batch-Ω 系列)")
    print("="*100)

    top_10_files = analysis_results[:10]
    for i, item in enumerate(top_10_files, 1):
        batch_id = f"Batch-Ω-{i:03d}"
        print(f"{batch_id}: {item['file_path']}")
        print(f"         - 代码行数: {item['loc']:,} 行")
        print(f"         - 语句总数: {item['total_stmts']:,} 句")
        print(f"         - 当前覆盖率: {item['coverage']:.1f}%")
        print("         - 目标覆盖率: ≥70%")
        print()

    # 保存结果到文件
    import json
    with open('/home/user/projects/FootballPrediction/coverage_analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': str(subprocess.run(['date'], capture_output=True, text=True).stdout.strip()),
            'total_files': len(analysis_results),
            'top_10_files': top_10_files,
            'all_files': analysis_results
        }, f, ensure_ascii=False, indent=2)

    print("✅ 分析完成，结果已保存到 coverage_analysis_results.json")
    return top_10_files


if __name__ == "__main__":
    main()
