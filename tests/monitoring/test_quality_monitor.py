"""
测试质量监控系统
提供测试覆盖率、性能、稳定性等指标的实时监控
"""

import json
import time
import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import sys
import os


class TestQualityMonitor:
    """测试质量监控器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.metrics_dir = self.project_root / "tests" / "metrics"
        self.metrics_dir.mkdir(exist_ok=True)
        self.current_metrics = {}

    def collect_coverage_metrics(self) -> Dict[str, Any]:
        """收集测试覆盖率指标"""
        try:
            # 运行覆盖率测试
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "tests/unit/",
                    "--cov=src",
                    "--cov-report=json",
                    "--cov-report=term-missing",
                    "--quiet"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            # 读取覆盖率报告
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                metrics = {
                    "overall_coverage": coverage_data["totals"]["percent_covered"],
                    "covered_lines": coverage_data["totals"]["covered_lines"],
                    "missing_lines": coverage_data["totals"]["missing_lines"],
                    "total_lines": coverage_data["totals"]["num_statements"],
                    "files": {}
                }

                # 各模块覆盖率
                for filename, file_data in coverage_data["files"].items():
                    if "src/" in filename:
                        module_name = filename.replace("src/", "").replace(".py", "")
                        metrics["files"][module_name] = {
                            "coverage": file_data["summary"]["percent_covered"],
                            "covered_lines": file_data["summary"]["covered_lines"],
                            "missing_lines": file_data["summary"]["missing_lines"]
                        }

                return metrics

        except Exception as e:
            print(f"收集覆盖率指标失败: {e}")
            return {"error": str(e)}

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """收集测试性能指标"""
        try:
            start_time = time.time()

            # 运行单元测试并计时
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "tests/unit/",
                    "--durations=0",
                    "--quiet"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            total_time = time.time() - start_time

            # 解析测试时长
            durations = []
            lines = result.stdout.split('\n')
            for line in lines:
                if 'test_' in line and '::' in line:
                    try:
                        parts = line.split()
                        duration = float(parts[-1])
                        test_name = parts[-2]
                        durations.append({
                            "test": test_name,
                            "duration": duration
                        })
                    except:
                        continue

            # 计算统计指标
            if durations:
                durations.sort(key=lambda x: x["duration"], reverse=True)
                avg_duration = sum(d["duration"] for d in durations) / len(durations)
                max_duration = durations[0]["duration"]
                min_duration = durations[-1]["duration"]

                return {
                    "total_time": total_time,
                    "test_count": len(durations),
                    "average_duration": avg_duration,
                    "max_duration": max_duration,
                    "min_duration": min_duration,
                    "slowest_tests": durations[:5],  # 最慢的5个测试
                    "passed": result.returncode == 0
                }

        except Exception as e:
            print(f"收集性能指标失败: {e}")
            return {"error": str(e)}

    def collect_stability_metrics(self) -> Dict[str, Any]:
        """收集测试稳定性指标"""
        try:
            # 多次运行测试检查稳定性
            runs = []
            for i in range(3):
                start_time = time.time()
                result = subprocess.run(
                    [
                        sys.executable, "-m", "pytest",
                        "tests/unit/",
                        "--quiet"
                    ],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                run_time = time.time() - start_time

                # 解析测试结果
                output = result.stdout + result.stderr
                passed = output.count("passed")
                failed = output.count("failed")
                skipped = output.count("skipped")
                errors = output.count("ERROR")

                runs.append({
                    "run": i + 1,
                    "time": run_time,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "errors": errors,
                    "exit_code": result.returncode
                })

            # 计算稳定性指标
            if runs:
                avg_time = sum(r["time"] for r in runs) / len(runs)
                all_passed = all(r["exit_code"] == 0 for r in runs)
                consistency = 1.0 if all_passed else 0.5

                return {
                    "runs": runs,
                    "average_time": avg_time,
                    "all_passed": all_passed,
                    "stability_score": consistency,
                    "total_tests": sum(r["passed"] + r["failed"] for r in runs) / len(runs)
                }

        except Exception as e:
            print(f"收集稳定性指标失败: {e}")
            return {"error": str(e)}

    def analyze_test_trends(self) -> Dict[str, Any]:
        """分析测试趋势"""
        try:
            # 读取历史数据
            history_file = self.metrics_dir / "history.json"
            if not history_file.exists():
                return {"trend": "no_data"}

            with open(history_file) as f:
                history = json.load(f)

            # 分析最近7天的数据
            recent_data = history[-7:] if len(history) >= 7 else history

            if len(recent_data) < 2:
                return {"trend": "insufficient_data"}

            # 覆盖率趋势
            coverage_trend = []
            for record in recent_data:
                if "coverage" in record and "overall_coverage" in record["coverage"]:
                    coverage_trend.append(record["coverage"]["overall_coverage"])

            # 性能趋势
            performance_trend = []
            for record in recent_data:
                if "performance" in record and "total_time" in record["performance"]:
                    performance_trend.append(record["performance"]["total_time"])

            trend_analysis = {
                "coverage_trend": self._calculate_trend(coverage_trend),
                "performance_trend": self._calculate_trend(performance_trend, reverse=True),
                "data_points": len(recent_data)
            }

            return trend_analysis

        except Exception as e:
            print(f"分析测试趋势失败: {e}")
            return {"error": str(e)}

    def _calculate_trend(self, data: List[float], reverse: bool = False) -> str:
        """计算数据趋势"""
        if len(data) < 2:
            return "stable"

        # 计算趋势
        if reverse:  # 对于时间数据，越小越好
            if data[-1] < data[0] * 0.95:
                return "improving"
            elif data[-1] > data[0] * 1.05:
                return "degrading"
        else:  # 对于覆盖率等，越大越好
            if data[-1] > data[0] * 1.02:
                return "improving"
            elif data[-1] < data[0] * 0.98:
                return "degrading"

        return "stable"

    def generate_quality_report(self) -> Dict[str, Any]:
        """生成测试质量报告"""
        print("🔍 开始收集测试质量指标...")

        # 收集各项指标
        coverage_metrics = self.collect_coverage_metrics()
        performance_metrics = self.collect_performance_metrics()
        stability_metrics = self.collect_stability_metrics()
        trend_analysis = self.analyze_test_trends()

        # 计算质量评分
        quality_score = self._calculate_quality_score(
            coverage_metrics,
            performance_metrics,
            stability_metrics
        )

        # 生成报告
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "quality_score": quality_score,
            "coverage": coverage_metrics,
            "performance": performance_metrics,
            "stability": stability_metrics,
            "trends": trend_analysis,
            "recommendations": self._generate_recommendations(
                coverage_metrics,
                performance_metrics,
                stability_metrics
            )
        }

        # 保存报告
        report_file = self.metrics_dir / f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # 更新历史记录
        self._update_history(report)

        print(f"✅ 测试质量报告已生成: {report_file}")
        return report

    def _calculate_quality_score(self, coverage: Dict, performance: Dict, stability: Dict) -> Dict[str, Any]:
        """计算测试质量评分"""
        score = 0
        max_score = 100
        details = {}

        # 覆盖率评分 (40分)
        if "overall_coverage" in coverage:
            cov = coverage["overall_coverage"]
            if cov >= 25:
                cov_score = 40
            elif cov >= 20:
                cov_score = 30
            elif cov >= 15:
                cov_score = 20
            else:
                cov_score = 10
            score += cov_score
            details["coverage"] = {"score": cov_score, "value": cov, "weight": 40}

        # 性能评分 (30分)
        if "total_time" in performance:
            perf_time = performance["total_time"]
            if perf_time <= 60:  # 1分钟内
                perf_score = 30
            elif perf_time <= 180:  # 3分钟内
                perf_score = 25
            elif perf_time <= 300:  # 5分钟内
                perf_score = 20
            else:
                perf_score = 10
            score += perf_score
            details["performance"] = {"score": perf_score, "value": perf_time, "weight": 30}

        # 稳定性评分 (30分)
        if "stability_score" in stability:
            stab_score = stability["stability_score"] * 30
            score += stab_score
            details["stability"] = {"score": stab_score, "value": stability["stability_score"], "weight": 30}

        # 评级
        if score >= 90:
            grade = "A+"
        elif score >= 80:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 60:
            grade = "C"
        else:
            grade = "D"

        return {
            "total_score": score,
            "max_score": max_score,
            "grade": grade,
            "details": details
        }

    def _generate_recommendations(self, coverage: Dict, performance: Dict, stability: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 覆盖率建议
        if "overall_coverage" in coverage:
            cov = coverage["overall_coverage"]
            if cov < 20:
                recommendations.append("📊 覆盖率偏低，建议增加单元测试以达到20%基线")
            elif cov < 25:
                recommendations.append("📈 覆盖率接近基线，再增加少量测试即可达标")

            # 检查低覆盖率模块
            if "files" in coverage:
                low_coverage_files = [
                    f for f, data in coverage["files"].items()
                    if data["coverage"] < 15
                ]
                if low_coverage_files:
                    recommendations.append(f"🔍 以下模块需要额外测试覆盖: {', '.join(low_coverage_files)}")

        # 性能建议
        if "total_time" in performance:
            perf_time = performance["total_time"]
            if perf_time > 300:
                recommendations.append("⚡ 测试执行时间过长，建议优化测试或使用并行执行")

            if "slowest_tests" in performance:
                slow_tests = performance["slowest_tests"][:3]
                if slow_tests and slow_tests[0]["duration"] > 5:
                    recommendations.append(f"🐌 最慢的测试需要优化: {slow_tests[0]['test']} ({slow_tests[0]['duration']:.2f}s)")

        # 稳定性建议
        if "all_passed" in stability and not stability["all_passed"]:
            recommendations.append("⚠️ 测试存在不稳定性，检查失败的测试并修复")

        return recommendations

    def _update_history(self, report: Dict[str, Any]):
        """更新历史记录"""
        history_file = self.metrics_dir / "history.json"

        # 读取现有历史
        history = []
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)

        # 添加新记录
        summary = {
            "timestamp": report["timestamp"],
            "quality_score": report["quality_score"]["total_score"],
            "grade": report["quality_score"]["grade"]
        }

        if "coverage" in report and "overall_coverage" in report["coverage"]:
            summary["coverage"] = {"overall_coverage": report["coverage"]["overall_coverage"]}

        if "performance" in report and "total_time" in report["performance"]:
            summary["performance"] = {"total_time": report["performance"]["total_time"]}

        history.append(summary)

        # 保留最近30天的记录
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
        history = [
            record for record in history
            if datetime.datetime.fromisoformat(record["timestamp"]) > cutoff_date
        ]

        # 保存历史
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def print_report_summary(self, report: Dict[str, Any]):
        """打印报告摘要"""
        print("\n" + "="*60)
        print("📊 测试质量报告摘要")
        print("="*60)

        # 质量评分
        quality = report["quality_score"]
        print(f"\n🎯 总体评分: {quality['total_score']}/{quality['max_score']} ({quality['grade']})")

        # 覆盖率
        if "coverage" in report and "overall_coverage" in report["coverage"]:
            cov = report["coverage"]["overall_coverage"]
            print(f"📈 覆盖率: {cov:.1f}%")

        # 性能
        if "performance" in report and "total_time" in report["performance"]:
            perf = report["performance"]["total_time"]
            print(f"⚡ 执行时间: {perf:.1f}秒")

        # 稳定性
        if "stability" in report and "stability_score" in report["stability"]:
            stab = report["stability"]["stability_score"]
            print(f"🛡️ 稳定性: {stab*100:.1f}%")

        # 趋势
        if "trends" in report:
            trends = report["trends"]
            if "coverage_trend" in trends:
                trend_icon = {"improving": "📈", "degrading": "📉", "stable": "➡️"}
                print(f"📊 覆盖率趋势: {trend_icon.get(trends['coverage_trend'], '➡️')} {trends['coverage_trend']}")

        # 建议
        if "recommendations" in report and report["recommendations"]:
            print(f"\n💡 改进建议:")
            for rec in report["recommendations"]:
                print(f"   {rec}")

        print("\n" + "="*60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试质量监控工具")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    args = parser.parse_args()

    # 创建监控器
    monitor = TestQualityMonitor()

    # 生成报告
    report = monitor.generate_quality_report()

    # 输出摘要
    if not args.quiet:
        monitor.print_report_summary(report)

    # 保存到指定文件
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 报告已保存到: {args.output}")

    # 返回评分（用于CI）
    return report["quality_score"]["total_score"]


if __name__ == "__main__":
    sys.exit(0 if main() >= 60 else 1)