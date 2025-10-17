#!/usr/bin/env python3
"""
分析覆盖率报告
"""

import json
import os
from collections import defaultdict

def analyze_coverage():
    """分析覆盖率数据"""
    if not os.path.exists('coverage.json'):
        print("❌ coverage.json 文件不存在")
        return

    # 读取覆盖率报告
    with open('coverage.json', 'r') as f:
        coverage = json.load(f)

    # 提取总体覆盖率
    totals = coverage['totals']
    print(f"\n{'='*60}")
    print(f"📊 项目总体覆盖率报告")
    print(f"{'='*60}")
    print(f"行覆盖率: {totals['covered_lines']:,}/{totals['num_statements']:,} = {totals['percent_covered']:.2f}%")
    print(f"分支覆盖率: {totals.get('covered_branches', 0):,}/{totals.get('num_branches', 0):,} = {totals.get('percent_covered_branches', 0):.2f}%")
    print(f"缺失行数: {totals['missing_lines']:,}")

    # 按模块分析
    print(f"\n{'='*60}")
    print(f"📁 按模块分析覆盖率")
    print(f"{'='*60}")

    modules = defaultdict(list)
    files = coverage['files']

    # 按模块分组
    for file_path, data in files.items():
        # 跳过测试文件
        if '/tests/' in file_path:
            continue

        summary = data['summary']
        if summary['num_statements'] == 0:
            continue

        # 提取模块名
        parts = file_path.split('/')
        if 'src/' in file_path:
            idx = parts.index('src')
            if idx + 1 < len(parts):
                module = parts[idx + 1]
                modules[module].append((file_path, summary))

    # 显示每个模块的统计
    module_stats = {}
    for module, file_list in modules.items():
        total_lines = sum(f['num_statements'] for _, f in file_list)
        covered_lines = sum(f['covered_lines'] for _, f in file_list)
        percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0

        module_stats[module] = {
            'total': total_lines,
            'covered': covered_lines,
            'percent': percent,
            'files': file_list
        }

    # 按覆盖率排序模块
    sorted_modules = sorted(module_stats.items(), key=lambda x: x[1]['percent'], reverse=True)

    for module, stats in sorted_modules:
        status = '🟢' if stats['percent'] >= 80 else '🟡' if stats['percent'] >= 50 else '🔴'
        print(f"\n{status} {module}: {stats['percent']:.1f}% ({stats['covered']:,}/{stats['total']:,} 行)")

        # 显示该模块下覆盖率最低的5个文件
        sorted_files = sorted(stats['files'], key=lambda x: x[1]['percent_covered'])
        print(f"   覆盖率最低的文件:")
        for i, (file_path, summary) in enumerate(sorted_files[:5]):
            rel_path = file_path.split('/')[-1]
            percent = summary['percent_covered']
            if percent < 100:
                print(f"   - {percent:5.1f}% | {rel_path}")

    # 分析未覆盖的代码
    print(f"\n{'='*60}")
    print(f"🔍 覆盖率分析详情")
    print(f"{'='*60}")

    # 覆盖率分级
    excellent = []  # >= 90%
    good = []      # 70-90%
    fair = []      # 50-70%
    poor = []      # < 50%

    for module, stats in module_stats.items():
        if stats['percent'] >= 90:
            excellent.append((module, stats['percent']))
        elif stats['percent'] >= 70:
            good.append((module, stats['percent']))
        elif stats['percent'] >= 50:
            fair.append((module, stats['percent']))
        else:
            poor.append((module, stats['percent']))

    print(f"\n🟢 优秀覆盖率 (>=90%): {len(excellent)} 个模块")
    for module, percent in excellent:
        print(f"   - {module}: {percent:.1f}%")

    print(f"\n🟡 良好覆盖率 (70-90%): {len(good)} 个模块")
    for module, percent in good:
        print(f"   - {module}: {percent:.1f}%")

    print(f"\n🟠 一般覆盖率 (50-70%): {len(fair)} 个模块")
    for module, percent in fair:
        print(f"   - {module}: {percent:.1f}%")

    print(f"\n🔴 需要改进 (<50%): {len(poor)} 个模块")
    for module, percent in poor:
        print(f"   - {module}: {percent:.1f}%")

    # 特别关注utils模块
    if 'utils' in module_stats:
        print(f"\n{'='*60}")
        print(f"🛠️ Utils 模块详细分析")
        print(f"{'='*60}")
        utils_stats = module_stats['utils']
        print(f"总体覆盖率: {utils_stats['percent']:.1f}%")

        # 显示utils下每个文件的详情
        utils_files = sorted(utils_stats['files'], key=lambda x: x[1]['percent_covered'], reverse=True)
        print(f"\n文件详情:")
        for file_path, summary in utils_files:
            file_name = file_path.split('/')[-1]
            percent = summary['percent_covered']
            covered = summary['covered_lines']
            total = summary['num_statements']
            missing = summary['missing_lines']

            status = '✅' if percent == 100 else '⚠️' if percent >= 80 else '❌'
            print(f"  {status} {percent:5.1f}% | {covered:3d}/{total:3d} | {file_name}")

            if missing > 0 and percent < 100:
                print(f"      未覆盖行: {missing} 行")

    # 生成改进建议
    print(f"\n{'='*60}")
    print(f"💡 改进建议")
    print(f"{'='*60}")

    if poor:
        print(f"\n1. 优先处理低覆盖率模块 (<50%):")
        for module, _ in poor:
            print(f"   - {module}: 需要添加基础单元测试")

    if fair:
        print(f"\n2. 提升中等覆盖率模块 (50-70%):")
        for module, _ in fair:
            print(f"   - {module}: 添加边界条件和错误处理测试")

    # 查找最需要测试的文件
    all_files = []
    for module, stats in module_stats.items():
        for file_path, summary in stats['files']:
            if summary['percent_covered'] < 80 and summary['num_statements'] > 10:
                all_files.append((file_path, summary['percent_covered'], summary['missing_lines']))

    # 按缺失行数排序
    all_files.sort(key=lambda x: x[2], reverse=True)

    print(f"\n3. 最需要测试覆盖的文件 (按缺失行数排序):")
    for file_path, percent, missing in all_files[:10]:
        file_name = '/'.join(file_path.split('/')[-2:])
        print(f"   - {file_name}: {percent:.1f}% (缺失 {missing} 行)")

if __name__ == "__main__":
    analyze_coverage()