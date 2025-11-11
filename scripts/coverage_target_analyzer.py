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

    except Exception:
        return 0, {}


def calculate_target_improvements(module_data, target_coverage=15):
    """计算每个模块需要提升的覆盖率"""

    total_lines = sum(data['total'] for data in module_data.values())
    total_covered = sum(data['total'] * data['coverage'] // 100 for data in module_data.values())

    target_covered = int(total_lines * target_coverage / 100)
    needed_lines = target_covered - total_covered



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
    for _i, module_info in enumerate(priority_modules, 1):
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


        accumulated_gain += min(potential, total * (suggested_coverage - current) // 100)

    return priority_modules, needed_lines


def generate_action_plan(priority_modules, needed_lines):
    """生成具体行动计划"""

    high_priority = [m for m in priority_modules if m['potential_gain'] > 50]
    medium_priority = [m for m in priority_modules if 20 < m['potential_gain'] <= 50]
    low_priority = [m for m in priority_modules if m['potential_gain'] <= 20]

    for _i, module in enumerate(high_priority[:3], 1):  # 只取前3个
        Path(module['module']).stem

    for _i, module in enumerate(medium_priority[:2], 1):
        Path(module['module']).stem

    for _i, module in enumerate(low_priority[:2], 1):
        Path(module['module']).stem


def main():
    """主函数"""

    # 解析当前覆盖率
    total_coverage, module_data = parse_coverage_output()

    if not module_data:
        return

    # 计算目标改进
    priority_modules, needed_lines = calculate_target_improvements(module_data, 15)

    # 生成行动计划
    generate_action_plan(priority_modules, needed_lines)



if __name__ == "__main__":
    main()
