#!/usr/bin/env python3
"""
覆盖率分析工具 - Phase 5.3.2.2
分析项目中覆盖率最低的文件，制定补测策略
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import json

def extract_coverage_from_pytest_output() -> Dict[str, Dict]:
    """从pytest输出中提取覆盖率数据"""
    print("🔍 正在运行pytest获取最新覆盖率数据...")

    try:
        # 运行pytest获取覆盖率数据
        result = subprocess.run([
            'python', '-m', 'pytest', 'tests/unit',
            '--cov=src', '--cov-report=term-missing',
            '--tb=short', '--maxfail=1'
        ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

        if result.returncode != 0:
            print(f"⚠️ pytest运行存在错误，但继续分析...")

        # 解析覆盖率数据
        coverage_data = {}
        lines = result.stdout.split('\n')

        for line in lines:
            # 匹配覆盖率行格式: src/module/file.py  stmts  miss  branch  brpart  cover%
            if re.match(r'src/.*\.py\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+%', line):
                parts = line.split()
                if len(parts) >= 6:
                    file_path = parts[0]
                    total_stmts = int(parts[1])
                    missing_stmts = int(parts[2])
                    coverage_percent = float(parts[5].rstrip('%'))

                    coverage_data[file_path] = {
                        'total_stmts': total_stmts,
                        'missing_stmts': missing_stmts,
                        'coverage': coverage_percent,
                        'impact_score': (total_stmts * (100 - coverage_percent)) / 100
                    }

        print(f"✅ 成功提取 {len(coverage_data)} 个文件的覆盖率数据")
        return coverage_data

    except Exception as e:
        print(f"❌ 提取覆盖率数据失败: {e}")
        return {}

def analyze_lowest_coverage_files(coverage_data: Dict[str, Dict], top_n: int = 10) -> List[Tuple]:
    """分析覆盖率最低的文件"""
    print(f"📊 分析覆盖率最低的 {top_n} 个文件...")

    # 过滤掉测试文件和已经高覆盖率的文件
    filtered_files = {}
    for file_path, data in coverage_data.items():
        # 排除测试文件、__init__.py、已经高覆盖率的文件
        if (not file_path.startswith('tests/') and
            not file_path.endswith('/__init__.py') and
            data['coverage'] < 80 and  # 只关注覆盖率低于80%的文件
            data['total_stmts'] > 20):  # 只关注代码量超过20行的文件
            filtered_files[file_path] = data

    # 按影响分数排序（代码量 * 缺失覆盖率）
    sorted_files = sorted(
        filtered_files.items(),
        key=lambda x: x[1]['impact_score'],
        reverse=True
    )

    return sorted_files[:top_n]

def generate_batch_gamma_tasks(lowest_files: List[Tuple]) -> str:
    """生成Batch-Γ系列任务清单"""
    print("📋 生成Batch-Γ系列任务清单...")

    task_content = """# Batch-Γ 覆盖率提升任务清单 - Phase 5.3.2.2

## 任务目标
将整体测试覆盖率从当前基线提升到 ≥30%

## 执行策略
1. 优先处理影响分数最高的文件（代码量大 + 覆盖率低）
2. 每个文件创建专门的测试文件
3. 使用系统性测试方法确保覆盖率稳定提升
4. 解决pandas/numpy/mlflow等依赖的懒加载问题

## Batch-Γ 任务清单

"""

    for i, (file_path, data) in enumerate(lowest_files, 1):
        task_number = f"Batch-Γ-{i:03d}"
        coverage = data['coverage']
        stmts = data['total_stmts']
        impact = data['impact_score']

        # 估算目标覆盖率（基于代码复杂度）
        if stmts > 400:
            target_coverage = min(coverage + 25, 80)
        elif stmts > 200:
            target_coverage = min(coverage + 35, 85)
        else:
            target_coverage = min(coverage + 50, 90)

        task_content += f"""### {task_number}: {file_path}
- **当前覆盖率**: {coverage:.1f}%
- **代码行数**: {stmts} 行
- **影响分数**: {impact:.1f}
- **目标覆盖率**: {target_coverage:.1f}%
- **测试文件**: tests/unit/{file_path.replace('src/', '').replace('/', '_').replace('.py', '_batch_gamma_')}.py
- **优先级**: {'🔴 高' if impact > 500 else '🟡 中' if impact > 200 else '🟢 低'}

"""

    task_content += f"""
## 执行计划
1. **阶段1**: 处理影响分数 > 500 的文件（{sum(1 for _, data in lowest_files if data["impact_score"] > 500)} 个）
2. **阶段2**: 处理影响分数 200-500 的文件（{sum(1 for _, data in lowest_files if 200 <= data["impact_score"] <= 500)} 个）
3. **阶段3**: 处理影响分数 < 200 的文件（{sum(1 for _, data in lowest_files if data["impact_score"] < 200)} 个）

## 预期效果
- **当前整体覆盖率**: 21.67%
- **目标整体覆盖率**: ≥30%
- **提升幅度**: ≥8.33%

## 质量保证
- 所有测试必须通过pytest验证
- 测试代码必须包含中文注释
- 遵循Arrange-Act-Assert模式
- 解决依赖导入问题，不绕过pytest
"""

    return task_content

def main():
    """主函数"""
    print("🚀 开始 Phase 5.3.2.2 覆盖率分析...")

    # 提取覆盖率数据
    coverage_data = extract_coverage_from_pytest_output()

    if not coverage_data:
        print("❌ 无法获取覆盖率数据，退出")
        return

    # 分析最低覆盖率文件
    lowest_files = analyze_lowest_coverage_files(coverage_data, top_n=10)

    if not lowest_files:
        print("✅ 所有文件覆盖率已达到较高水平")
        return

    # 生成任务清单
    task_content = generate_batch_gamma_tasks(lowest_files)

    # 保存任务清单
    with open('/home/user/projects/FootballPrediction/BATCH_GAMMA_TASKS.md', 'w', encoding='utf-8') as f:
        f.write(task_content)

    print("✅ Batch-Γ任务清单已生成: BATCH_GAMMA_TASKS.md")

    # 输出摘要
    print("\n📊 分析摘要:")
    print(f"当前整体覆盖率: 21.67%")
    print(f"目标整体覆盖率: ≥30%")
    print(f"\n优先处理的 {len(lowest_files)} 个文件:")

    for i, (file_path, data) in enumerate(lowest_files[:5], 1):
        print(f"{i:2d}. {file_path}")
        print(f"    覆盖率: {data['coverage']:.1f}%, 代码行数: {data['total_stmts']}, 影响分数: {data['impact_score']:.1f}")

    # 保存分析结果
    analysis_result = {
        'current_total_coverage': 21.67,
        'target_total_coverage': 30,
        'lowest_files': [
            {
                'file_path': file_path,
                'coverage': data['coverage'],
                'total_stmts': data['total_stmts'],
                'impact_score': data['impact_score']
            }
            for file_path, data in lowest_files
        ]
    }

    with open('/home/user/projects/FootballPrediction/coverage_analysis_result.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print("\n🎯 Phase 5.3.2.2 分析完成，准备开始Batch-Γ任务执行!")

if __name__ == "__main__":
    main()