#!/usr/bin/env python3
"""
持续改进监控器
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any


def monitor_improvements():
    """监控改进进展"""
    project_root = Path(__file__).parent.parent
    improvement_log = project_root / "improvement-log.json"

    if not improvement_log.exists():
        print("❌ 改进日志文件不存在")
        print("💡 请先运行: python3 scripts/continuous_improvement_engine.py")
        return

    try:
        with open(improvement_log) as f:
            history = json.load(f)
    except Exception as e:
        print(f"❌ 读取改进日志失败: {e}")
        return

    if not history:
        print("📝 暂无改进记录")
        return

    print("📈 持续改进监控面板")
    print("=" * 50)

    # 总体统计
    print("\n📊 总体统计:")
    print(f"总改进周期: {len(history)}")

    successful_cycles = [c for c in history if c.get('success', False)]
    print(f"成功周期: {len(successful_cycles)}")
    print(f"成功率: {len(successful_cycles)/len(history)*100:.1f}%")

    # 最近7天的改进情况
    print("\n📅 最近7天改进情况:")
    recent_cutoff = datetime.now() - timedelta(days=7)
    recent_cycles = [
        cycle for cycle in history
        if datetime.fromisoformat(cycle['timestamp']) > recent_cutoff
    ]

    if recent_cycles:
        print(f"最近周期数: {len(recent_cycles)}")

        recent_successful = [c for c in recent_cycles if c.get('success', False)]
        print(f"成功周期: {len(recent_successful)}")
        print(f"成功率: {len(recent_successful)/len(recent_cycles)*100:.1f}%")
    else:
        print("最近7天无改进记录")

    # 计算改进趋势
    if len(successful_cycles) >= 2:
        print("\n📈 改进趋势分析:")

        # 取最近5个成功周期
        recent_successful = successful_cycles[-5:]

        coverage_changes = []
        score_changes = []

        for cycle in recent_successful:
            verification = cycle.get('verification_results', {})
            improvements = verification.get('improvements', {})

            if 'coverage' in improvements:
                coverage_changes.append(improvements['coverage']['improvement'])
            if 'overall_score' in improvements:
                score_changes.append(improvements['overall_score']['improvement'])

        if coverage_changes:
            avg_coverage_change = sum(coverage_changes) / len(coverage_changes)
            print(f"平均覆盖率改进: +{avg_coverage_change:.2f}%/周期")

        if score_changes:
            avg_score_change = sum(score_changes) / len(score_changes)
            print(f"平均综合分数改进: +{avg_score_change:.2f}/周期")

    # 显示最新状态
    if history:
        latest_cycle = history[-1]
        print("\n📊 最新质量状态:")

        verification = latest_cycle.get('verification_results', {})
        new_status = verification.get('new_quality_status', {})

        print(f"综合分数: {new_status.get('overall_score', 0):.1f}/10")
        print(f"覆盖率: {new_status.get('coverage', 0):.1f}%")
        print(f"代码质量: {new_status.get('code_quality', 0):.1f}/10")
        print(f"安全性: {new_status.get('security', 0):.1f}/10")

        # 显示最新改进措施
        improvements_made = latest_cycle.get('improvement_results', {}).get('improvements_made', [])
        if improvements_made:
            print("\n✅ 最近执行的改进:")
            for improvement in improvements_made:
                print(f"  - {improvement['action']}")

    # 质量目标达成情况
    goals_file = project_root / "quality-goals.json"
    if goals_file.exists() and new_status:
        try:
            with open(goals_file) as f:
                goals = json.load(f)

            print("\n🎯 质量目标达成情况:")

            for metric, target in goals.items():
                if metric in new_status:
                    current = new_status[metric]
                    achievement = (current / target) * 100
                    status = "✅ 已达成" if current >= target else f"🔄 {achievement:.0f}%"
                    print(f"  {metric}: {current:.1f}/{target:.1f} ({status})")

        except Exception as e:
            print(f"⚠️ 无法读取质量目标: {e}")

    # 建议和下一步
    print("\n💡 改进建议:")
    if new_status.get('coverage', 0) < 20:
        print("  - 🎯 优先提升测试覆盖率到20%以上")
    if new_status.get('overall_score', 0) < 7:
        print("  - 🔧 继续优化代码质量指标")
    if new_status.get('code_quality', 0) >= 10:
        print("  - ✅ 代码质量已达优秀，保持即可")

    print("\n📋 报告文件:")
    improvement_reports = list(project_root.glob("improvement-report-*.md"))
    if improvement_reports:
        latest_report = sorted(improvement_reports)[-1]
        print(f"  - 最新改进报告: {latest_report.name}")

    quality_reports = list(project_root.glob("quality-reports/*.json"))
    if quality_reports:
        latest_quality = sorted(quality_reports)[-1]
        print(f"  - 最新质量报告: {latest_quality.name}")

    print("\n🚀 下一步操作:")
    print("  - 运行改进: ./start-improvement.sh")
    print("  - 查看历史: python3 scripts/continuous_improvement_engine.py --history")
    print("  - 自动改进: python3 scripts/continuous_improvement_engine.py --automated")


if __name__ == "__main__":
    monitor_improvements()