#!/usr/bin/env python3
"""
覆盖率监控脚本
Coverage Monitor
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import sys


class CoverageMonitor:
    """覆盖率监控器"""

    def __init__(self):
        self.history_file = Path("docs/_reports/coverage_history.json")
        self.target = 50.0
        self.threshold = 45.0

    def load_history(self):
        """加载历史数据"""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return []

    def save_history(self, history):
        """保存历史数据"""
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

    def add_current_coverage(self):
        """添加当前覆盖率"""
        # 读取当前覆盖率
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print("❌ 覆盖率报告不存在")
            return

        with open(coverage_file) as f:
            data = json.load(f)

        coverage = data["totals"]["percent_covered"]

        # 加载历史
        history = self.load_history()

        # 添加新数据
        history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "coverage": coverage,
                "target": self.target,
                "threshold": self.threshold,
            }
        )

        # 只保留最近30天的数据
        cutoff = datetime.now() - timedelta(days=30)
        history = [
            h for h in history if datetime.fromisoformat(h["timestamp"]) > cutoff
        ]

        # 保存历史
        self.save_history(history)

        print(f"✅ 记录当前覆盖率: {coverage:.2f}%")
        return coverage

    def generate_trend_chart(self):
        """生成趋势图"""
        history = self.load_history()

        if len(history) < 2:
            print("⚠️ 数据不足，无法生成趋势图")
            return

        # 提取数据
        dates = [datetime.fromisoformat(h["timestamp"]) for h in history]
        coverages = [h["coverage"] for h in history]

        # 创建图表
        plt.figure(figsize=(12, 6))
        plt.plot(dates, coverages, "b-", label="实际覆盖率")
        plt.axhline(
            y=self.target, color="g", linestyle="--", label=f"目标: {self.target}%"
        )
        plt.axhline(
            y=self.threshold,
            color="r",
            linestyle="--",
            label=f"门槛: {self.threshold}%",
        )

        plt.title("测试覆盖率趋势")
        plt.xlabel("日期")
        plt.ylabel("覆盖率 (%)")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 保存图表
        chart_file = Path("docs/_reports/coverage_trend.png")
        plt.savefig(chart_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ 生成趋势图: {chart_file}")

    def generate_report(self):
        """生成监控报告"""
        history = self.load_history()

        if not history:
            print("⚠️ 没有历史数据")
            return

        latest = history[-1]
        previous = history[-2] if len(history) > 1 else latest

        # 计算变化
        change = latest["coverage"] - previous["coverage"]

        # 计算趋势
        if len(history) >= 7:
            recent = history[-7:]
            avg_change = sum(
                recent[i]["coverage"] - recent[i - 1]["coverage"]
                for i in range(1, len(recent))
            ) / (len(recent) - 1)
        else:
            avg_change = 0

        # 预测达到目标的时间
        if avg_change > 0:
            days_to_target = (self.target - latest["coverage"]) / avg_change
            if days_to_target > 0:
                target_date = datetime.now() + timedelta(days=days_to_target)
                target_str = target_date.strftime("%Y-%m-%d")
            else:
                target_str = "已达到"
        else:
            target_str = "无法预测"

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "current_coverage": latest["coverage"],
            "previous_coverage": previous["coverage"],
            "change": round(change, 2),
            "avg_daily_change": round(avg_change, 2),
            "target_date": target_str,
            "status": "on_track" if change >= 0 else "declining",
            "data_points": len(history),
        }

        # 保存报告
        report_file = Path("docs/_reports/coverage_monitor_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # 打印报告
        print("\n📊 覆盖率监控报告")
        print("=" * 40)
        print(f"当前覆盖率: {latest['coverage']:.2f}%")
        print(f"上次覆盖率: {previous['coverage']:.2f}%")
        print(f"变化: {change:+.2f}%")
        print(f"日均变化: {avg_change:+.2f}%")
        print(f"预计达标日期: {target_str}")
        print(f"状态: {'📈 良好' if change >= 0 else '📉 下降'}")

        return report


def main():
    monitor = CoverageMonitor()

    # 添加当前覆盖率
    monitor.add_current_coverage()

    # 生成趋势图
    try:
        monitor.generate_trend_chart()
    except ImportError:
        print("⚠️ 需要安装matplotlib来生成图表")

    # 生成报告
    monitor.generate_report()


if __name__ == "__main__":
    main()
