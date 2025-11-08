#!/usr/bin/env python3
"""
覆盖率目标分析器
分析当前覆盖率状态并制定精确的提升策略
"""

import re
import subprocess
import sys
from pathlib import Path


def parse_coverage_output():
    """解析pytest覆盖率输出"""
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/unit/utils/', '-m', 'unit',
            '--cov=src.utils', '--cov-report=term', '--tb=no'
        ], capture_output=True, text=True, cwd=Path.cwd())

        output = result.stdout

        # 提取TOTAL覆盖率
        total_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
        total_coverage = int(total_match.group(1)) if total_match else 0

        # 提取各模块覆盖率
        module_data = {}
        pattern = r'(src/utils/[^.]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%'
        for match in re.finditer(pattern, output):
            module, total, missing, coverage = match.groups()
            module_data[module] = {
                'total': int(total),
                'missing': int(missing),
                'coverage': int(coverage)
            }

        return total_coverage, module_data

    except Exception as e:
        print(f"❌ 解析覆盖率输出失败: {e}")
        return 0, {}


def calculate_target_improvements(module_data, target_coverage=15):
    """计算每个模块需要提升的覆盖率"""
    improvements = {}

    total_lines = sum(data['total'] for data in module_data.values())
    total_covered = sum(data['total'] * data['coverage'] // 100 for data in module_data.values())

    target_covered = int(total_lines * target_coverage / 100)
    needed_lines = target_covered - total_covered

    print("📊 覆盖率分析报告")
    print("=" * 50)
    print(f"当前整体覆盖率: {total_covered * 100 / total_lines:.2f}%")
    print(f"目标覆盖率: {target_coverage}%")
    print(f"需要额外覆盖的代码行数: {needed_lines}")
    print(f"总代码行数: {total_lines}")
    print()

    print("📈 模块详细分析:")
    print("-" * 50)

    # 按优先级排序模块
    priority_modules = []
    for module, data in module_data.items():
        potential_gain = data['total'] - data['total'] * data['coverage'] // 100
        effort_ratio = potential_gain / data['total'] if data['total'] > 0 else 0

        priority_modules.append({
            'module': module,
            'current_coverage': data['coverage'],
            'potential_gain': potential_gain,
            'effort_ratio': effort_ratio,
            'total_lines': data['total']
        })

    # 按潜在收益排序
    priority_modules.sort(key=lambda x: x['potential_gain'], reverse=True)

    accumulated_gain = 0
    for i, module_info in enumerate(priority_modules, 1):
        module = module_info['module']
        current = module_info['current_coverage']
        potential = module_info['potential_gain']
        total = module_info['total_lines']

        # 计算建议目标覆盖率
        if accumulated_gain < needed_lines:
            remaining_needed = needed_lines - accumulated_gain
            suggested_coverage = min(95, current + int(remaining_needed * 100 / total))
        else:
            suggested_coverage = current

        print(f"{i}. {module}")
        print(f"   当前覆盖率: {current}%")
        print(f"   潜在收益: {potential} 行 ({potential * 100 / total:.1f}%)")
        print(f"   建议目标: {suggested_coverage}%")
        print()

        accumulated_gain += min(potential, total * (suggested_coverage - current) // 100)

    return priority_modules, needed_lines


def generate_action_plan(priority_modules, needed_lines):
    """生成具体行动计划"""
    print("🎯 行动计划")
    print("=" * 50)

    high_priority = [m for m in priority_modules if m['potential_gain'] > 50]
    medium_priority = [m for m in priority_modules if 20 < m['potential_gain'] <= 50]
    low_priority = [m for m in priority_modules if m['potential_gain'] <= 20]

    print("🔥 高优先级模块 (潜在收益 > 50行):")
    for i, module in enumerate(high_priority[:3], 1):  # 只取前3个
        module_name = Path(module['module']).stem
        print(f"   {i}. {module_name}.py - 创建综合测试文件")
        print(f"      当前: {module['current_coverage']}% → 目标: 60%")

    print("\n⚡ 中优先级模块 (潜在收益 20-50行):")
    for i, module in enumerate(medium_priority[:2], 1):
        module_name = Path(module['module']).stem
        print(f"   {i}. {module_name}.py - 扩展现有测试")
        print(f"      当前: {module['current_coverage']}% → 目标: 50%")

    print("\n🔧 低优先级模块 (潜在收益 ≤ 20行):")
    for i, module in enumerate(low_priority[:2], 1):
        module_name = Path(module['module']).stem
        print(f"   {i}. {module_name}.py - 补充关键测试")
        print(f"      当前: {module['current_coverage']}% → 目标: 40%")


def main():
    """主函数"""
    print("🔍 足球预测系统 - 覆盖率目标分析器")
    print("=" * 60)
    print()

    # 解析当前覆盖率
    total_coverage, module_data = parse_coverage_output()

    if not module_data:
        print("❌ 无法获取覆盖率数据，请确保在项目根目录运行此脚本")
        return

    # 计算目标改进
    priority_modules, needed_lines = calculate_target_improvements(module_data, 15)

    # 生成行动计划
    generate_action_plan(priority_modules, needed_lines)

    print("\n📋 预计工作量:")
    print("=" * 30)
    print("• 高优先级模块: 2-3小时")
    print("• 中优先级模块: 1-2小时")
    print("• 低优先级模块: 1小时")
    print("• 总预计时间: 4-6小时")
    print("• 预计完成时间: 今日内")


if __name__ == "__main__":
    main()
