#!/usr/bin/env python3
"""
简单覆盖率分析器
直接读取现有的coverage.json文件并生成分析报告
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class SimpleCoverageReport:
    """简单覆盖率报告"""
    total_coverage: float
    total_statements: int
    covered_statements: int
    missing_statements: int
    src_files_count: int
    covered_files_count: int
    file_details: List[Dict[str, Any]]


def analyze_coverage() -> SimpleCoverageReport:
    """分析覆盖率数据"""
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        print("❌ coverage.json文件不存在，请先运行测试生成覆盖率报告")
        return None

    try:
        with open(coverage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        totals = data['totals']
        files = data['files']

        # 筛选src目录的文件
        src_files = {k: v for k, v in files.items() if k.startswith('src/')}

        # 统计有覆盖率的文件
        covered_files = [
            {**{'file': k}, **v}
            for k, v in src_files.items()
            if v['summary']['percent_covered'] > 0
        ]

        # 按覆盖率排序
        covered_files.sort(key=lambda x: x['summary']['percent_covered'], reverse=True)

        return SimpleCoverageReport(
            total_coverage=totals['percent_covered'],
            total_statements=totals['num_statements'],
            covered_statements=totals['covered_lines'],
            missing_statements=totals['missing_lines'],
            src_files_count=len(src_files),
            covered_files_count=len(covered_files),
            file_details=covered_files[:20]  # 前20个文件
        )

    except Exception as e:
        print(f"❌ 解析覆盖率数据失败: {e}")
        return None


def generate_improvement_suggestions(report: SimpleCoverageReport) -> List[Dict[str,
    Any]]:
    """生成改进建议"""
    suggestions = []

    # 分析零覆盖率文件
    zero_coverage_files = [
        f for f in report.file_details
        if f['summary']['percent_covered'] == 0
    ]

    # 分析模块类型
    api_files = [f for f in report.file_details if 'api' in f['file']]
    service_files = [f for f in report.file_details if 'services' in f['file']]
    domain_files = [f for f in report.file_details if 'domain' in f['file']]

    # 生成建议
    if api_files:
        suggestions.append({
            'category': 'API模块',
            'priority': 'high',
            'description': f'发现{len(api_files)}个API文件，建议优先创建API端点测试',
            'files': [f['file'] for f in api_files[:3]]
        })

    if service_files:
        suggestions.append({
            'category': '服务模块',
            'priority': 'high',
            'description': f'发现{len(service_files)}个服务文件，建议创建业务逻辑测试',
            'files': [f['file'] for f in service_files[:3]]
        })

    if domain_files:
        suggestions.append({
            'category': '领域模块',
            'priority': 'medium',
            'description': f'发现{len(domain_files)}个领域文件，建议创建核心业务测试',
            'files': [f['file'] for f in domain_files[:3]]
        })

    return suggestions


def main():
    """主函数"""
    print("🔍 简单覆盖率分析器")
    print("=" * 40)

    report = analyze_coverage()

    if not report:
        print("❌ 无法获取覆盖率数据")
        return

    print(f"\n📊 覆盖率概览:")
    print(f"   总覆盖率: {report.total_coverage:.2f}%")
    print(f"   总语句数: {report.total_statements}")
    print(f"   已覆盖语句: {report.covered_statements}")
    print(f"   未覆盖语句: {report.missing_statements}")
    print(f"   src文件数: {report.src_files_count}")
    print(f"   有覆盖率的文件: {report.covered_files_count}")

    print(f"\n🎯 覆盖率最高的文件:")
    for i, file_info in enumerate(report.file_details[:5], 1):
        filename = file_info['file']
        coverage = file_info['summary']['percent_covered']
        statements = file_info['summary']['num_statements']
        print(f"   {i}. {filename}")
        print(f"      覆盖率: {coverage:.1f}% ({statements} 语句)")

    # 生成改进建议
    suggestions = generate_improvement_suggestions(report)

    print(f"\n💡 改进建议:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion['category']} ({suggestion['priority']} 优先级)")
        print(f"      {suggestion['description']}")
        if suggestion['files']:
            print(f"      示例文件: {', '.join(suggestion['files'])}")

    # 下一步行动
    print(f"\n🚀 推荐下一步行动:")
    if report.total_coverage < 5:
        print("   • 使用 create_api_tests.py 生成基础API测试")
        print("   • 使用 create_service_tests.py 生成基础服务测试")
        print("   • 运行 python3 scripts/coverage_optimizer.py --create-tests")
    elif report.total_coverage < 15:
        print("   • 为现有测试添加更多测试用例")
        print("   • 使用 coverage_improvement_executor.py 优化覆盖率")
    else:
        print("   • 继续完善现有测试")
        print("   • 关注边界条件和异常情况测试")

    print(f"\n📈 目标设定:")
    current = report.total_coverage
    target_1 = min(10, current * 2)
    target_2 = min(25, current * 3)

    print(f"   短期目标: {target_1:.1f}% 覆盖率")
    print(f"   中期目标: {target_2:.1f}% 覆盖率")
    print(f"   长期目标: 50%+ 覆盖率")


if __name__ == "__main__":
    main()