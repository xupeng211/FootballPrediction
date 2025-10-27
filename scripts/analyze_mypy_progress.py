#!/usr/bin/env python3
"""
分析MyPy错误改进进展
对比修复前后的错误变化
"""

import subprocess
import json
import re
from datetime import datetime
from pathlib import Path

def count_mypy_errors():
    """精确统计MyPy错误数量"""
    try:
        result = subprocess.run(
            ['mypy', 'src/', '--show-error-codes', '--no-error-summary'],
            capture_output=True,
            text=True,
            cwd='/home/user/projects/FootballPrediction'
        )

        lines = result.stdout.strip().split('\n')
        error_lines = [line for line in lines if ': error:' in line]

        # 按错误类型分类
        error_types = {}
        errors_by_file = {}

        for line in error_lines:
            # 解析文件路径
            if ': error:' in line:
                file_path = line.split(':')[0]
                error_code = line.split('[')[-1].strip(']') if '[' in line else 'unknown'

                errors_by_file[file_path] = errors_by_file.get(file_path, 0) + 1
                error_types[error_code] = error_types.get(error_code, 0) + 1

        return {
            'total_errors': len(error_lines),
            'errors_by_file': errors_by_file,
            'error_types': error_types,
            'error_lines': error_lines
        }
    except Exception as e:
        return {
            'total_errors': -1,
            'error': str(e),
            'errors_by_file': {},
            'error_types': {},
            'error_lines': []
        }

def analyze_progress():
    """分析改进进展"""
    print("🔍 分析MyPy错误改进进展...")
    print("=" * 60)

    current_stats = count_mypy_errors()

    if current_stats['total_errors'] < 0:
        print(f"❌ 错误分析失败: {current_stats['error']}")
        return

    print(f"📊 当前状态: {current_stats['total_errors']} 个类型错误")
    print()

    # 显示错误最多的文件
    print("📁 错误分布 (Top 10):")
    sorted_files = sorted(current_stats['errors_by_file'].items(),
                          key=lambda x: x[1], reverse=True)

    for i, (file_path, count) in enumerate(sorted_files[:10], 1):
        short_path = file_path.replace('/home/user/projects/FootballPrediction/', '')
        print(f"  {i:2d}. {short_path:<40} {count:4d} 个错误")

    print()

    # 显示错误类型分布
    print("🏷️  错误类型分布:")
    sorted_types = sorted(current_stats['error_types'].items(),
                         key=lambda x: x[1], reverse=True)

    for i, (error_type, count) in enumerate(sorted_types[:10], 1):
        print(f"  {i:2d}. {error_type:<30} {count:4d} 个错误")

    print()

    # 检查修复效果
    print("🎯 修复效果分析:")

    # 检查我们修复的文件
    fixed_files = [
        'src/api/middleware.py',
        'src/api/monitoring.py',
        'src/api/adapters.py',
        'src/api/cqrs.py',
        'src/services/data_processing.py',
        'src/services/event_prediction_service.py'
    ]

    improvement_count = 0
    for file_path in fixed_files:
        if file_path in current_stats['errors_by_file']:
            count = current_stats['errors_by_file'][file_path]
            short_path = file_path.replace('src/', '')
            print(f"  📝 {short_path:<30} 仍有 {count:4d} 个错误")
        else:
            short_path = file_path.replace('src/', '')
            print(f"  ✅ {short_path:<30} 已修复!")
            improvement_count += 1

    if improvement_count > 0:
        print(f"\n🎉 发现 {improvement_count} 个文件已完全修复!")

    # 识别需要优先修复的文件
    print("\n🔥 优先修复建议 (高错误文件):")
    high_error_files = [(f, c) for f, c in sorted_files[:5]
                        if any(keyword in f for keyword in ['src/api/', 'src/core/', 'src/utils/'])]

    if high_error_files:
        for file_path, count in high_error_files:
            short_path = file_path.replace('/home/user/projects/FootballPrediction/', '')
            print(f"  🎯 {short_path:<40} {count:4d} 个错误")
    else:
        print("  ℹ️  主要错误集中在第三方库和边缘模块")

    return current_stats

def generate_progress_report(stats):
    """生成进展报告"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_errors': stats['total_errors'],
        'errors_by_file': stats['errors_by_file'],
        'error_types': stats['error_types'],
        'analysis': {
            'top_files': list(sorted(stats['errors_by_file'].items(),
                                    key=lambda x: x[1], reverse=True)[:10]),
            'common_errors': list(sorted(stats['error_types'].items(),
                                       key=lambda x: x[1], reverse=True)[:10])
        }
    }

    # 保存报告
    reports_dir = Path('/home/user/projects/FootballPrediction/reports/quality')
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / f'mypy_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 详细报告已保存: {report_file}")
    return report_file

def main():
    """主函数"""
    print("🚀 MyPy错误改进进展分析")
    print("⏰ 分析时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    stats = analyze_progress()

    if stats and stats['total_errors'] >= 0:
        generate_progress_report(stats)

        print("\n📋 总结:")
        print(f"   • 总错误数: {stats['total_errors']}")
        print(f"   • 涉及文件: {len(stats['errors_by_file'])}")
        print(f"   • 错误类型: {len(stats['error_types'])}")

        if stats['total_errors'] < 1200:
            print("   🎯 建议: 继续当前策略，错误数在控制范围内")
        elif stats['total_errors'] < 1500:
            print("   📈 建议: 保持小批量修复，每周减少200-300个错误")
        else:
            print("   ⚠️  建议: 需要更大规模的修复努力")

if __name__ == '__main__':
    main()