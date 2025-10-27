#!/usr/bin/env python3
"""
Issue #83 覆盖率分析器
分析当前覆盖率分布，识别重点提升模块
"""

import re
import subprocess
import json
from collections import defaultdict

def parse_coverage_output(coverage_output):
    """解析覆盖率输出，提取模块覆盖率信息"""

    coverage_data = {}

    # 解析覆盖率输出
    lines = coverage_output.split('\n')

    for line in lines:
        # 匹配覆盖率行，例如：
        # src/api/cqrs.py                                                84     33      6      0  56.67%   73, 78, 83, 88, 99-109, 126-135, 150-152, 166-170, 183-191, 206-210, 219-227, 243-247, 259-263, 282, 294-299
        match = re.match(r'^src/([^\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)%', line)
        if match:
            module_path = match.group(1)
            statements = int(match.group(2))
            missing = int(match.group(3))
            branches = int(match.group(4))
            branch_partial = int(match.group(5))
            coverage = float(match.group(6))

            module_data = {
                'path': module_path,
                'statements': statements,
                'missing': missing,
                'branches': branches,
                'branch_partial': branch_partial,
                'coverage': coverage,
                'missing_lines': line.split('%')[-1].strip() if '%' in line else ''
            }

            coverage_data[module_path] = module_data

    return coverage_data

def categorize_modules(coverage_data):
    """将模块按覆盖率分类"""

    categories = {
        'high_coverage': [],    # >70%
        'medium_coverage': [],  # 30-70%
        'low_coverage': [],     # 10-30%
        'no_coverage': [],      # 0-10%
        'untested': []          # 0%覆盖率
    }

    for module_path, data in coverage_data.items():
        coverage = data['coverage']

        if coverage == 0:
            categories['untested'].append((module_path, data))
        elif coverage < 10:
            categories['no_coverage'].append((module_path, data))
        elif coverage < 30:
            categories['low_coverage'].append((module_path, data))
        elif coverage < 70:
            categories['medium_coverage'].append((module_path, data))
        else:
            categories['high_coverage'].append((module_path, data))

    return categories

def identify_high_priority_modules(categories):
    """识别高优先级提升模块"""

    high_priority = []

    # 优先级1: 核心业务模块但覆盖率低
    core_modules = [
        'api/', 'domain/', 'database/', 'services/', 'collectors/'
    ]

    for category in ['untested', 'no_coverage', 'low_coverage']:
        for module_path, data in categories[category]:
            for core_prefix in core_modules:
                if module_path.startswith(core_prefix):
                    high_priority.append({
                        'module': module_path,
                        'current_coverage': data['coverage'],
                        'statements': data['statements'],
                        'priority': 'HIGH',
                        'reason': f'核心模块覆盖率极低 ({data["coverage"]}%)'
                    })
                    break

    # 优先级2: API和路由模块
    for category in ['low_coverage', 'medium_coverage']:
        for module_path, data in categories[category]:
            if module_path.startswith('api/') or 'router' in module_path:
                high_priority.append({
                    'module': module_path,
                    'current_coverage': data['coverage'],
                    'statements': data['statements'],
                    'priority': 'HIGH',
                    'reason': f'API模块覆盖率需要提升 ({data["coverage"]}%)'
                })

    # 优先级3: 中等覆盖率的实用模块
    for module_path, data in categories['medium_coverage']:
        if data['statements'] > 50:  # 代码量较大的模块
            high_priority.append({
                'module': module_path,
                'current_coverage': data['coverage'],
                'statements': data['statements'],
                'priority': 'MEDIUM',
                'reason': f'中等覆盖率大模块 ({data["coverage"]}%, {data["statements"]}行)'
            })

    # 按优先级和语句数量排序
    high_priority.sort(key=lambda x: (x["priority"] != "HIGH", -x["statements"]))

    return high_priority

def analyze_coverage_distribution():
    """分析覆盖率分布"""

    print("🔍 Issue #83 覆盖率分析开始...")
    print("=" * 60)

    # 运行覆盖率测试
    print("📊 运行覆盖率测试...")
    try:
        result = subprocess.run([
            'python3', '-m', 'pytest',
            'tests/unit/test_lineage_basic.py',
            'tests/unit/test_utils_complete.py',
            '--cov=src',
            '--cov-report=term-missing',
            '--tb=no'
        ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

        if result.returncode != 0:
            print(f"⚠️ 覆盖率测试返回非零退出码: {result.returncode}")
            print("输出:", result.stdout)
            print("错误:", result.stderr)

        coverage_output = result.stdout

    except Exception as e:
        print(f"❌ 运行覆盖率测试失败: {e}")
        return None

    # 解析覆盖率数据
    coverage_data = parse_coverage_output(coverage_output)

    if not coverage_data:
        print("❌ 未能解析覆盖率数据")
        return None

    # 分类模块
    categories = categorize_modules(coverage_data)

    # 生成统计报告
    print("\n📈 覆盖率分布统计:")
    print("-" * 40)
    print(f"🟢 高覆盖率 (>70%): {len(categories['high_coverage'])} 个模块")
    print(f"🟡 中等覆盖率 (30-70%): {len(categories['medium_coverage'])} 个模块")
    print(f"🟠 低覆盖率 (10-30%): {len(categories['low_coverage'])} 个模块")
    print(f"🔴 极低覆盖率 (0-10%): {len(categories['no_coverage'])} 个模块")
    print(f"⚫ 无覆盖 (0%): {len(categories['untested'])} 个模块")

    total_modules = len(coverage_data)
    total_statements = sum(data['statements'] for data in coverage_data.values())
    total_covered = sum(data['statements'] - data['missing'] for data in coverage_data.values())
    overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0

    print("\n📊 总体统计:")
    print(f"总模块数: {total_modules}")
    print(f"总语句数: {total_statements}")
    print(f"已覆盖语句: {total_covered}")
    print(f"总体覆盖率: {overall_coverage:.2f}%")

    # 识别高优先级模块
    high_priority = identify_high_priority_modules(categories)

    print("\n🎯 高优先级提升模块 (前20个):")
    print("-" * 50)

    for i, module in enumerate(high_priority[:20], 1):
        print(f"{i:2d}. {module['module']}")
        print(f"    当前覆盖率: {module['current_coverage']:.1f}%")
        print(f"    语句数: {module['statements']}")
        print(f"    优先级: {module['priority']}")
        print(f"    原因: {module['reason']}")
        print()

    # 生成提升策略建议
    print("🚀 覆盖率提升策略建议:")
    print("-" * 30)

    # 阶段1: 快速提升
    quick_wins = [m for m in high_priority if m['statements'] < 100 and m['priority'] == 'HIGH'][:5]
    print(f"阶段1 - 快速提升 ({len(quick_wins)}个模块):")
    for module in quick_wins:
        print(f"  • {module['module']} ({module['current_coverage']:.1f}% → 目标70%+)")

    # 阶段2: 核心模块
    core_modules = [m for m in high_priority if 'api/' in m['module'] or 'domain/' in m['module']][:5]
    print(f"\n阶段2 - 核心模块 ({len(core_modules)}个模块):")
    for module in core_modules:
        print(f"  • {module['module']} ({module['current_coverage']:.1f}% → 目标60%+)")

    # 阶段3: 大型模块
    large_modules = [m for m in high_priority if m['statements'] > 100][:5]
    print(f"\n阶段3 - 大型模块 ({len(large_modules)}个模块):")
    for module in large_modules:
        print(f"  • {module['module']} ({module['current_coverage']:.1f}% → 目标50%+)")

    return {
        'coverage_data': coverage_data,
        'categories': categories,
        'high_priority': high_priority,
        'overall_coverage': overall_coverage,
        'total_modules': total_modules,
        'total_statements': total_statements
    }

def generate_boost_plan(analysis_result):
    """生成覆盖率提升计划"""

    if not analysis_result:
        return None

    print("\n" + "=" * 60)
    print("📋 Issue #83 覆盖率提升执行计划")
    print("=" * 60)

    high_priority = analysis_result['high_priority']
    overall_coverage = analysis_result['overall_coverage']

    # 计算目标
    target_coverage = 80.0
    coverage_gap = target_coverage - overall_coverage

    print(f"🎯 目标覆盖率: {target_coverage}%")
    print(f"📊 当前覆盖率: {overall_coverage:.2f}%")
    print(f"📈 需要提升: {coverage_gap:.2f}%")
    print(f"📝 高优先级模块: {len(high_priority)}个")

    # 分阶段计划
    phases = [
        {
            'name': '阶段1: 快速见效',
            'duration': '1-2天',
            'modules': high_priority[:5],
            'target_coverage': '60%',
            'focus': '小模块快速覆盖'
        },
        {
            'name': '阶段2: 核心强化',
            'duration': '3-5天',
            'modules': high_priority[5:15],
            'target_coverage': '70%',
            'focus': 'API和核心业务逻辑'
        },
        {
            'name': '阶段3: 全面提升',
            'duration': '5-7天',
            'modules': high_priority[15:30],
            'target_coverage': '80%',
            'focus': '剩余模块和集成测试'
        }
    ]

    for i, phase in enumerate(phases, 1):
        print(f"\n{phase['name']} ({phase['duration']}):")
        print(f"  目标覆盖率: {phase['target_coverage']}")
        print(f"  重点: {phase['focus']}")
        print("  模块列表:")
        for j, module in enumerate(phase['modules'], 1):
            print(f"    {j}. {module['module']} ({module['current_coverage']:.1f}%)")

    return phases

if __name__ == "__main__":
    # 执行分析
    analysis_result = analyze_coverage_distribution()

    if analysis_result:
        # 生成提升计划
        phases = generate_boost_plan(analysis_result)

        print("\n🎉 Issue #83 覆盖率分析完成!")
        print(f"📊 基线覆盖率: {analysis_result['overall_coverage']:.2f}%")
        print("🎯 目标覆盖率: 80%")
        print(f"📈 提升空间: {80 - analysis_result['overall_coverage']:.2f}%")

        # 保存分析结果
        with open('/home/user/projects/FootballPrediction/coverage_analysis_result.json', 'w') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)

        print("💾 分析结果已保存到 coverage_analysis_result.json")
        print("🚀 现在可以开始执行覆盖率提升计划!")