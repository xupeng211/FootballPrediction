#!/usr/bin/env python3
"""测试覆盖率反馈循环"""

import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

def run_coverage_test():
    """运行覆盖率测试"""
    cmd = [
        'pytest', '-m', 'not slow',
        '--maxfail=20',
        '--cov=src',
        '--cov-report=json',
        '--cov-report=term-missing:skip-covered',
        '-q'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def parse_coverage_output(output):
    """解析覆盖率输出"""
    # 从term输出中提取覆盖率
    lines = output.split('\n')
    for line in lines:
        if 'TOTAL' in line and '%' in line:
            # 格式: TOTAL 26465 19049 6572  21 23%
            parts = line.split()
            if len(parts) >= 6:
                return {
                    'total_statements': int(parts[1]),
                    'covered_statements': int(parts[2]),
                    'missing_statements': int(parts[3]),
                    'coverage_percent': float(parts[-1].strip('%'))
                }
    return None

def update_feedback_log(data):
    """更新反馈日志"""
    log_file = Path('docs/_reports/coverage/feedback_loop.json')
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # 读取现有日志
    if log_file.exists():
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []

    # 添加新记录
    logs.append({
        'timestamp': datetime.now().isoformat(),
        'coverage': data['coverage_percent'],
        'statements': {
            'total': data['total_statements'],
            'covered': data['covered_statements'],
            'missing': data['missing_statements']
        }
    })

    # 只保留最近10条记录
    logs = logs[-10:]

    # 写回文件
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def generate_suggestions(coverage_data):
    """生成改进建议"""
    coverage = coverage_data['coverage_percent']
    missing = coverage_data['missing_statements']

    suggestions = []

    if coverage < 25:
        suggestions.append("🎯 覆盖率低于25%，建议继续修复导入错误和语法错误")
        suggestions.append("📝 使用 `python scripts/quick_fix_failures.py` 快速修复")

    if coverage >= 25 and coverage < 30:
        suggestions.append("✅ 覆盖率达标！建议开始引入mock机制")
        suggestions.append("🔧 重点处理Redis/PostgreSQL依赖的测试")

    if coverage >= 30:
        suggestions.append("🚀 覆盖率良好！可以开始补0%覆盖的模块")

    # 根据缺失语句数给建议
    if missing > 5000:
        suggestions.append("📊 大量代码未覆盖，建议优先处理核心模块")

    return suggestions

def show_progress_dashboard(logs):
    """显示进度仪表板"""
    if not logs:
        print("📊 暂无历史数据")
        return

    print("\n" + "="*60)
    print("📊 测试覆盖率进度仪表板")
    print("="*60)

    # 显示最近5次记录
    recent_logs = logs[-5:]
    for i, log in enumerate(recent_logs):
        timestamp = datetime.fromisoformat(log['timestamp']).strftime("%m-%d %H:%M")
        coverage = log['coverage']
        arrow = "↑" if i > 0 and coverage > recent_logs[i-1]['coverage'] else "→"
        print(f"  {timestamp} | {coverage:5.1f}% {arrow}")

    # 计算趋势
    if len(logs) >= 2:
        change = logs[-1]['coverage'] - logs[-2]['coverage']
        if change > 0:
            print(f"\n📈 趋势: +{change:.1f}% (进步中)")
        elif change < 0:
            print(f"\n📉 趋势: {change:.1f}% (需要关注)")
        else:
            print(f"\n➡️ 趋势: 持平")

def main():
    """主函数"""
    print("🔄 测试覆盖率反馈循环")
    print("="*50)

    # 运行测试
    print("🧪 运行覆盖率测试...")
    result = run_coverage_test()

    # 解析结果
    coverage_data = parse_coverage_output(result.stdout + result.stderr)

    if coverage_data:
        print(f"\n📊 当前覆盖率: {coverage_data['coverage_percent']:.1f}%")
        print(f"   总语句: {coverage_data['total_statements']}")
        print(f"   已覆盖: {coverage_data['covered_statements']}")
        print(f"   未覆盖: {coverage_data['missing_statements']}")

        # 更新日志
        update_feedback_log(coverage_data)

        # 生成建议
        suggestions = generate_suggestions(coverage_data)

        print("\n💡 改进建议:")
        for suggestion in suggestions:
            print(f"  {suggestion}")

        # 读取并显示历史
        log_file = Path('docs/_reports/coverage/feedback_loop.json')
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
            show_progress_dashboard(logs)

        # 保存快速报告
        report = {
            'last_update': datetime.now().isoformat(),
            'current_coverage': coverage_data,
            'suggestions': suggestions
        }

        with open('docs/_reports/coverage/quick_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✅ 反馈已记录: docs/_reports/coverage/quick_report.json")

    else:
        print("❌ 无法解析覆盖率结果")

if __name__ == '__main__':
    main()