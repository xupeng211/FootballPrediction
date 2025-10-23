#!/usr/bin/env python3
"""
覆盖率趋势跟踪器
Coverage Trend Tracker

跟踪测试覆盖率的历史变化，生成趋势报告和预测
"""

import os
import sys
import json
import datetime
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoverageTrendTracker:
    """覆盖率趋势跟踪器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.data_dir = self.project_root / "monitoring-data"
        self.history_file = self.data_dir / "coverage_trend_history.json"
        self.report_file = self.data_dir / "coverage_trend_report.json"
        self.trend_chart_file = self.data_dir / "coverage_trend_chart.png"

        # 确保数据目录存在
        self.data_dir.mkdir(exist_ok=True)

        # 目标配置
        self.targets = {
            "minimum": 20.0,
            "target": 30.0,
            "excellent": 50.0
        }

    def load_current_coverage(self) -> Optional[float]:
        """加载当前覆盖率"""
        coverage_file = self.project_root / "coverage.json"

        if not coverage_file.exists():
            logger.warning("coverage.json文件不存在，请先运行覆盖率测试")
            return None

        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)

            return coverage_data["totals"]["percent_covered"]
        except Exception as e:
            logger.error(f"读取覆盖率文件失败: {e}")
            return None

    def load_history(self) -> List[Dict[str, Any]]:
        """加载历史数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载历史数据失败: {e}")

        return []

    def save_history(self, history: List[Dict[str, Any]]):
        """保存历史数据"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
            logger.info(f"已保存历史数据: {len(history)} 条记录")
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")

    def add_coverage_record(self, coverage: float, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加覆盖率记录"""
        history = self.load_history()

        record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "coverage": coverage,
            "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
            "week": datetime.datetime.utcnow().isocalendar()[:2],  # (year, week_number)
            "metadata": metadata or {}
        }

        # 计算变化
        if history:
            last_record = history[-1]
            record["change_from_previous"] = coverage - last_record["coverage"]
            record["change_percentage"] = (record["change_from_previous"] / last_record["coverage"] * 100) if last_record["coverage"] > 0 else 0
        else:
            record["change_from_previous"] = 0.0
            record["change_percentage"] = 0.0

        history.append(record)

        # 保留最近180天的数据
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=180)
        history = [
            record for record in history
            if datetime.datetime.fromisoformat(record["timestamp"]) > cutoff_date
        ]

        self.save_history(history)
        logger.info(f"已添加覆盖率记录: {coverage:.2f}%")
        return record

    def calculate_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算趋势指标"""
        if len(history) < 2:
            return {
                "trend": "insufficient_data",
                "avg_daily_change": 0.0,
                "avg_weekly_change": 0.0,
                "momentum": 0.0,
                "volatility": 0.0
            }

        # 按日期排序
        sorted_history = sorted(history, key=lambda x: x["timestamp"])

        # 计算日变化
        daily_changes = []
        for i in range(1, len(sorted_history)):
            prev_date = datetime.datetime.fromisoformat(sorted_history[i-1]["timestamp"])
            curr_date = datetime.datetime.fromisoformat(sorted_history[i]["timestamp"])
            days_diff = (curr_date - prev_date).days or 1

            change = sorted_history[i]["coverage"] - sorted_history[i-1]["coverage"]
            daily_changes.append(change / days_diff)

        # 计算周变化
        weekly_changes = []
        for i in range(7, len(sorted_history)):
            week_change = sorted_history[i]["coverage"] - sorted_history[i-7]["coverage"]
            weekly_changes.append(week_change)

        # 趋势分析
        recent_changes = daily_changes[-30:] if len(daily_changes) >= 30 else daily_changes
        older_changes = daily_changes[:-30] if len(daily_changes) > 30 else []

        avg_recent_change = sum(recent_changes) / len(recent_changes) if recent_changes else 0
        avg_older_change = sum(older_changes) / len(older_changes) if older_changes else 0

        # 趋势判断
        if avg_recent_change > 0.1:
            trend = "improving"
        elif avg_recent_change < -0.1:
            trend = "declining"
        else:
            trend = "stable"

        # 动量 (最近变化相对于历史变化)
        momentum = avg_recent_change - avg_older_change

        # 波动性
        if len(daily_changes) > 1:
            mean_change = sum(daily_changes) / len(daily_changes)
            variance = sum((x - mean_change) ** 2 for x in daily_changes) / len(daily_changes)
            volatility = variance ** 0.5
        else:
            volatility = 0.0

        return {
            "trend": trend,
            "avg_daily_change": avg_recent_change,
            "avg_weekly_change": sum(weekly_changes) / len(weekly_changes) if weekly_changes else 0,
            "momentum": momentum,
            "volatility": volatility,
            "data_points": len(sorted_history)
        }

    def predict_timeline(self, current_coverage: float, trends: Dict[str, Any]) -> Dict[str, Any]:
        """预测达到目标的时间线"""
        if trends["avg_daily_change"] <= 0:
            return {
                "can_reach_target": False,
                "estimated_days": None,
                "estimated_date": None,
                "confidence": "low"
            }

        predictions = {}

        for target_name, target_coverage in self.targets.items():
            if current_coverage >= target_coverage:
                predictions[target_name] = {
                    "reached": True,
                    "estimated_days": 0,
                    "estimated_date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                    "confidence": "high"
                }
            else:
                remaining = target_coverage - current_coverage
                daily_change = trends["avg_daily_change"]
                estimated_days = int(remaining / daily_change)

                # 计算置信度
                confidence = "high"
                if trends["volatility"] > 0.5:
                    confidence = "low"
                elif trends["volatility"] > 0.2:
                    confidence = "medium"

                # 限制最大预测天数
                if estimated_days > 365:
                    predictions[target_name] = {
                        "reached": False,
                        "estimated_days": None,
                        "estimated_date": None,
                        "confidence": "very_low"
                    }
                else:
                    target_date = datetime.datetime.utcnow() + datetime.timedelta(days=estimated_days)
                    predictions[target_name] = {
                        "reached": False,
                        "estimated_days": estimated_days,
                        "estimated_date": target_date.strftime("%Y-%m-%d"),
                        "confidence": confidence
                    }

        return predictions

    def generate_report(self) -> Dict[str, Any]:
        """生成趋势报告"""
        history = self.load_history()
        current_coverage = self.load_current_coverage()

        if not history or current_coverage is None:
            return {
                "error": "数据不足，无法生成报告",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

        # 计算趋势
        trends = self.calculate_trends(history)

        # 生成预测
        predictions = self.predict_timeline(current_coverage, trends)

        # 统计信息
        coverages = [record["coverage"] for record in history]
        stats = {
            "min_coverage": min(coverages),
            "max_coverage": max(coverages),
            "avg_coverage": sum(coverages) / len(coverages),
            "current_coverage": current_coverage,
            "total_records": len(history)
        }

        # 按周统计
        weekly_stats = self._calculate_weekly_stats(history)

        # 最近30天表现
        recent_30_days = [
            record for record in history
            if datetime.datetime.fromisoformat(record["timestamp"]) >
               datetime.datetime.utcnow() - datetime.timedelta(days=30)
        ]

        recent_performance = {
            "records_count": len(recent_30_days),
            "avg_coverage": sum(r["coverage"] for r in recent_30_days) / len(recent_30_days) if recent_30_days else 0,
            "improvement": recent_30_days[-1]["coverage"] - recent_30_days[0]["coverage"] if len(recent_30_days) > 1 else 0
        }

        report = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "current_coverage": current_coverage,
            "targets": self.targets,
            "statistics": stats,
            "trends": trends,
            "predictions": predictions,
            "weekly_stats": weekly_stats,
            "recent_performance": recent_performance,
            "history_summary": {
                "total_records": len(history),
                "date_range": {
                    "start": history[0]["timestamp"] if history else None,
                    "end": history[-1]["timestamp"] if history else None
                }
            }
        }

        # 保存报告
        try:
            with open(self.report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"趋势报告已保存: {self.report_file}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")

        return report

    def _calculate_weekly_stats(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """计算按周统计"""
        weekly_data = {}

        for record in history:
            week_key = f"{record['week'][0]}-W{record['week'][1]:02d}"

            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "week": week_key,
                    "year": record["week"][0],
                    "week_number": record["week"][1],
                    "coverages": [],
                    "start_date": record["timestamp"],
                    "end_date": record["timestamp"]
                }

            weekly_data[week_key]["coverages"].append(record["coverage"])
            if record["timestamp"] < weekly_data[week_key]["start_date"]:
                weekly_data[week_key]["start_date"] = record["timestamp"]
            if record["timestamp"] > weekly_data[week_key]["end_date"]:
                weekly_data[week_key]["end_date"] = record["timestamp"]

        # 计算统计值
        weekly_stats = []
        for week_data in weekly_data.values():
            coverages = week_data["coverages"]
            weekly_stats.append({
                "week": week_data["week"],
                "year": week_data["year"],
                "week_number": week_data["week_number"],
                "avg_coverage": sum(coverages) / len(coverages),
                "min_coverage": min(coverages),
                "max_coverage": max(coverages),
                "measurements": len(coverages),
                "improvement": coverages[-1] - coverages[0] if len(coverages) > 1 else 0
            })

        return sorted(weekly_stats, key=lambda x: (x["year"], x["week_number"]))

    def generate_trend_chart(self) -> bool:
        """生成趋势图表"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime
        except ImportError:
            logger.warning("matplotlib未安装，无法生成图表")
            return False

        history = self.load_history()
        if len(history) < 2:
            logger.warning("数据不足，无法生成图表")
            return False

        # 准备数据
        dates = [datetime.fromisoformat(record["timestamp"]) for record in history]
        coverages = [record["coverage"] for record in history]

        # 创建图表
        plt.figure(figsize=(12, 8))

        # 主图：覆盖率趋势
        plt.subplot(2, 1, 1)
        plt.plot(dates, coverages, 'b-', linewidth=2, label='实际覆盖率')
        plt.axhline(y=self.targets["minimum"], color='r', linestyle='--', alpha=0.7, label=f'最低要求: {self.targets["minimum"]}%')
        plt.axhline(y=self.targets["target"], color='orange', linestyle='--', alpha=0.7, label=f'目标: {self.targets["target"]}%')
        plt.axhline(y=self.targets["excellent"], color='g', linestyle='--', alpha=0.7, label=f'优秀: {self.targets["excellent"]}%')

        plt.title('测试覆盖率趋势', fontsize=16, fontweight='bold')
        plt.ylabel('覆盖率 (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(loc='upper left')

        # 格式化x轴
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(plt.gca().xaxis.get_majorticklabels(), rotation=45)

        # 子图：日变化
        plt.subplot(2, 1, 2)
        daily_changes = []
        for i in range(1, len(history)):
            change = history[i]["coverage"] - history[i-1]["coverage"]
            daily_changes.append(change)

        change_dates = dates[1:]
        colors = ['g' if change > 0 else 'r' if change < 0 else 'gray' for change in daily_changes]

        plt.bar(change_dates, daily_changes, color=colors, alpha=0.7)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.title('每日覆盖率变化', fontsize=14)
        plt.ylabel('变化 (%)', fontsize=12)
        plt.xlabel('日期', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 格式化x轴
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(plt.gca().xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        # 保存图表
        try:
            plt.savefig(self.trend_chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"趋势图表已保存: {self.trend_chart_file}")
            return True
        except Exception as e:
            logger.error(f"保存图表失败: {e}")
            plt.close()
            return False

    def print_report(self, report: Dict[str, Any]):
        """打印报告"""
        if "error" in report:
            print(f"❌ {report['error']}")
            return

        print("\n" + "=" * 60)
        print("📈 覆盖率趋势跟踪报告")
        print("=" * 60)
        print(f"生成时间: {report['timestamp']}")
        print()

        # 当前状态
        print("📊 当前状态:")
        print(f"  当前覆盖率: {report['current_coverage']:.2f}%")
        print(f"  历史最低: {report['statistics']['min_coverage']:.2f}%")
        print(f"  历史最高: {report['statistics']['max_coverage']:.2f}%")
        print(f"  平均覆盖率: {report['statistics']['avg_coverage']:.2f}%")
        print()

        # 趋势分析
        trends = report["trends"]
        trend_emoji = {"improving": "📈", "declining": "📉", "stable": "➡️"}
        print(f"📈 趋势分析: {trend_emoji.get(trends['trend'], '?')} {trends['trend'].title()}")
        print(f"  日均变化: {trends['avg_daily_change']:+.3f}%")
        print(f"  周均变化: {trends['avg_weekly_change']:+.3f}%")
        print(f"  动量指标: {trends['momentum']:+.3f}")
        print(f"  波动性: {trends['volatility']:.3f}")
        print()

        # 最近表现
        recent = report["recent_performance"]
        print("📅 最近30天:")
        print(f"  测量次数: {recent['records_count']}")
        print(f"  平均覆盖率: {recent['avg_coverage']:.2f}%")
        print(f"  净改进: {recent['improvement']:+.2f}%")
        print()

        # 目标预测
        print("🎯 目标预测:")
        predictions = report["predictions"]
        for target_name, prediction in predictions.items():
            if isinstance(prediction, dict):
                if prediction.get("reached", False):
                    print(f"  {target_name.title():10}: ✅ 已达到")
                elif prediction.get("estimated_days"):
                    confidence_emoji = {"high": "🔥", "medium": "🔸", "low": "🔹", "very_low": "⚪"}
                    print(f"  {target_name.title():10}: 📅 {prediction['estimated_date']} ({prediction['estimated_days']}天) {confidence_emoji.get(prediction['confidence'], '?')}")
                else:
                    print(f"  {target_name.title():10}: ❌ 无法预测")
            else:
                print(f"  {target_name.title():10}: ℹ️ 数据格式异常")
        print()

        # 质量建议
        self._generate_recommendations(report)

    def _generate_recommendations(self, report: Dict[str, Any]):
        """生成改进建议"""
        print("💡 改进建议:")

        coverage = report["current_coverage"]
        trends = report["trends"]

        if coverage < self.targets["minimum"]:
            print("  ❌ 覆盖率低于最低要求，建议:")
            print("     - 优先为核心模块编写测试")
            print("     - 设置每日覆盖率提升目标")
            print("     - 考虑使用TDD开发模式")
        elif coverage < self.targets["target"]:
            print("  ⚠️ 覆盖率接近目标，建议:")
            print("     - 专注于边界条件和异常处理测试")
            print("     - 增加集成测试覆盖率")
            print("     - 定期审查未覆盖的代码")
        else:
            print("  ✅ 覆盖率达到目标，建议:")
            print("     - 维持当前覆盖率水平")
            print("     - 优化测试执行效率")
            print("     - 关注测试质量和有效性")

        if trends["trend"] == "declining":
            print("  📉 覆盖率呈下降趋势，建议:")
            print("     - 建立覆盖率监控预警")
            print("     - 在代码审查中检查覆盖率")
            print("     - 设置质量门禁防止倒退")
        elif trends["trend"] == "improving":
            print("  📈 覆盖率呈上升趋势，继续保持！")
        else:
            print("  ➡️ 覆盖率稳定，可考虑进一步提升")

        if trends["volatility"] > 0.5:
            print("  🌊 覆盖率波动较大，建议:")
            print("     - 建立更稳定的测试流程")
            print("     - 定期运行完整测试套件")
            print("     - 减少测试环境的不确定性")

    def track_and_report(self) -> Dict[str, Any]:
        """执行完整的跟踪和报告流程"""
        logger.info("开始覆盖率趋势跟踪...")

        # 加载当前覆盖率
        current_coverage = self.load_current_coverage()
        if current_coverage is None:
            logger.error("无法获取当前覆盖率")
            return {"error": "无法获取当前覆盖率"}

        # 添加记录
        self.add_coverage_record(current_coverage)

        # 生成报告
        report = self.generate_report()

        # 生成图表
        try:
            self.generate_trend_chart()
        except Exception as e:
            logger.warning(f"生成趋势图表失败: {e}")

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="覆盖率趋势跟踪器")
    parser.add_argument("--report-only", action="store_true", help="仅生成报告")
    parser.add_argument("--chart-only", action="store_true", help="仅生成图表")
    parser.add_argument("--add-record", action="store_true", help="添加当前覆盖率记录")
    parser.add_argument("--project-root", type=Path, help="项目根目录")
    parser.add_argument("--metadata", help="附加元数据 (JSON格式)")

    args = parser.parse_args()

    tracker = CoverageTrendTracker(args.project_root)

    # 解析元数据
    metadata = {}
    if args.metadata:
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError:
            logger.error("元数据格式错误，应为JSON格式")
            sys.exit(1)

    if args.add_record:
        current_coverage = tracker.load_current_coverage()
        if current_coverage is not None:
            tracker.add_coverage_record(current_coverage, metadata)
            print(f"✅ 已添加覆盖率记录: {current_coverage:.2f}%")
        else:
            print("❌ 无法获取当前覆盖率")
            sys.exit(1)

    if args.chart_only:
        success = tracker.generate_trend_chart()
        sys.exit(0 if success else 1)

    if args.report_only or (not args.add_record and not args.chart_only):
        report = tracker.generate_report()
        tracker.print_report(report)

    if not any([args.report_only, args.chart_only, args.add_record]):
        # 默认执行完整流程
        report = tracker.track_and_report()
        tracker.print_report(report)


if __name__ == "__main__":
    main()