#!/usr/bin/env python3
"""
简单覆盖率分析器
直接读取现有的coverage.json文件并生成分析报告
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SimpleCoverageReport:
    """简单覆盖率报告"""
    total_coverage: float
    total_statements: int
    covered_statements: int
    missing_statements: int
    src_files_count: int
    covered_files_count: int
    file_details: list[dict[str, Any]]


def analyze_coverage() -> SimpleCoverageReport:
    """分析覆盖率数据"""
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        return None

    try:
        with open(coverage_file, encoding='utf-8') as f:
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

    except Exception:
        return None


def generate_improvement_suggestions(report: SimpleCoverageReport) -> list[dict[str,
    Any]]:
    """生成改进建议"""
    suggestions = []

    # 分析零覆盖率文件
    [
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

    report = analyze_coverage()

    if not report:
        return


    for _i, file_info in enumerate(report.file_details[:5], 1):
        file_info['file']
        file_info['summary']['percent_covered']
        file_info['summary']['num_statements']

    # 生成改进建议
    suggestions = generate_improvement_suggestions(report)

    for _i, suggestion in enumerate(suggestions, 1):
        if suggestion['files']:
            pass

    # 下一步行动
    if report.total_coverage < 5:
        pass
    elif report.total_coverage < 15:
        pass
    else:
        pass

    current = report.total_coverage
    min(10, current * 2)
    min(25, current * 3)



if __name__ == "__main__":
    main()
