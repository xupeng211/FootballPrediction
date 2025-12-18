#!/usr/bin/env python3
"""
性能基准测试运行器

提供可定期运行的基准测试脚本，支持：
1. 自动化基准测试执行
2. 性能趋势分析
3. 回归检测报告
4. 多环境对比
5. 定时执行支持

使用方法:
  python run_benchmarks.py --environment production --regression-check
  python run_benchmarks.py --compare environments
  python run_benchmarks.py --trend-analysis --days 30

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Performance Testing)
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# 导入基准测试框架
from benchmark_framework import (
    PerformanceBenchmarkFramework,
    BenchmarkConfig,
    run_performance_benchmark,
    create_benchmark_config,
    BenchmarkDatabase,
)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self):
        self.db = BenchmarkDatabase()

    async def run_single_benchmark(self, config: BenchmarkConfig) -> Dict[str, Any]:
        """运行单个基准测试"""
        logger.info(f"🚀 开始基准测试: {config.benchmark_name}")

        try:
            # 运行基准测试
            report = await run_performance_benchmark(config)

            # 返回摘要信息
            return {
                "success": True,
                "report_id": report.report_id,
                "benchmark_name": report.benchmark_name,
                "environment": report.environment,
                "timestamp": report.timestamp.isoformat(),
                "summary": {
                    "total_tests": report.total_tests,
                    "passed_tests": report.passed_tests,
                    "failed_tests": report.failed_tests,
                    "success_rate": report.success_rate,
                    "avg_execution_time_ms": report.avg_execution_time_ms,
                    "p95_execution_time_ms": report.p95_execution_time_ms,
                },
                "regression_detected": report.regression_detected,
                "regression_count": len(report.regression_details),
                "performance_trend": report.performance_trend,
            }

        except Exception as e:
            logger.error(f"基准测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "benchmark_name": config.benchmark_name,
                "environment": config.environment,
                "timestamp": datetime.now().isoformat(),
            }

    async def run_multiple_benchmarks(
        self, configs: List[BenchmarkConfig]
    ) -> Dict[str, Any]:
        """运行多个基准测试"""
        logger.info(f"🚀 开始批量基准测试: {len(configs)} 个测试")

        results = []
        for config in configs:
            result = await self.run_single_benchmark(config)
            results.append(result)

        # 汇总结果
        successful_runs = [r for r in results if r.get("success", False)]
        failed_runs = [r for r in results if not r.get("success", False)]

        return {
            "total_benchmarks": len(configs),
            "successful_benchmarks": len(successful_runs),
            "failed_benchmarks": len(failed_runs),
            "success_rate": len(successful_runs) / len(configs) if configs else 0,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def compare_environments(
        self, benchmark_name: str, environments: List[str]
    ) -> Dict[str, Any]:
        """比较不同环境的性能"""
        logger.info(f"🔄 比较环境性能: {benchmark_name}")

        comparison_results = {}

        for env in environments:
            config = create_benchmark_config(
                benchmark_name=f"{benchmark_name}_{env}",
                environment=env,
                enable_regression_detection=False,
                generate_html_report=False,
            )

            result = await self.run_single_benchmark(config)
            comparison_results[env] = result

        # 生成对比报告
        comparison_report = await self._generate_comparison_report(
            benchmark_name, comparison_results
        )
        return comparison_report

    async def analyze_performance_trends(
        self, benchmark_name: str, environment: str, days: int = 30
    ) -> Dict[str, Any]:
        """分析性能趋势"""
        logger.info(f"📈 分析性能趋势: {benchmark_name} ({environment}, {days}天)")

        # 获取历史数据
        historical_results = self.db.get_historical_results(
            benchmark_name, environment=environment, days_back=days
        )

        if not historical_results:
            return {
                "success": False,
                "error": "No historical data found",
                "benchmark_name": benchmark_name,
                "environment": environment,
                "days": days,
            }

        # 分析趋势
        trend_analysis = await self._analyze_trends(historical_results)

        return {
            "success": True,
            "benchmark_name": benchmark_name,
            "environment": environment,
            "analysis_period_days": days,
            "total_data_points": len(historical_results),
            "trend_analysis": trend_analysis,
        }

    async def check_regressions(
        self, benchmark_name: Optional[str] = None, environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """检查性能回归"""
        logger.info("🔍 检查性能回归")

        # 定义要检查的基准测试
        if benchmark_name:
            benchmark_names = [benchmark_name]
        else:
            benchmark_names = [
                "football_prediction_system",
                "ml_inference_performance",
                "data_processing_performance",
            ]

        # 定义要检查的环境
        if environment:
            environments = [environment]
        else:
            environments = ["production", "staging"]

        regression_results = []

        for bench_name in benchmark_names:
            for env in environments:
                # 获取最近的结果
                recent_results = self.db.get_historical_results(
                    bench_name, environment=env, days_back=7
                )

                if len(recent_results) < 2:
                    continue

                # 检查回归
                latest_result = recent_results[0]  # 最新的结果
                historical_avg = statistics.mean(
                    [r.execution_time_ms for r in recent_results[1:] if r.success]
                )

                if latest_result.success and historical_avg > 0:
                    regression_percent = (
                        (latest_result.execution_time_ms - historical_avg)
                        / historical_avg
                    ) * 100

                    if regression_percent > 10:  # 10%阈值
                        regression_results.append(
                            {
                                "benchmark_name": bench_name,
                                "environment": env,
                                "latest_time_ms": latest_result.execution_time_ms,
                                "historical_avg_ms": historical_avg,
                                "regression_percent": regression_percent,
                                "latest_timestamp": latest_result.timestamp.isoformat(),
                                "severity": (
                                    "high" if regression_percent > 50 else "medium"
                                ),
                            }
                        )

        return {
            "success": True,
            "total_checks": len(benchmark_names) * len(environments),
            "regressions_detected": len(regression_results),
            "regression_details": regression_results,
            "timestamp": datetime.now().isoformat(),
        }

    async def generate_performance_report(
        self, output_dir: str = "performance_reports"
    ) -> Dict[str, Any]:
        """生成性能报告"""
        logger.info("📊 生成性能报告")

        # 获取所有基准测试的最新结果
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "benchmarks": {},
            "regressions": {},
            "trends": {},
        }

        # 获取基准测试摘要
        benchmark_names = [
            "football_prediction_system",
            "ml_inference_performance",
            "data_processing_performance",
        ]
        environments = ["production", "staging", "development"]

        for bench_name in benchmark_names:
            for env in environments:
                try:
                    recent_results = self.db.get_historical_results(
                        bench_name, environment=env, days_back=7
                    )

                    if recent_results:
                        successful_results = [r for r in recent_results if r.success]

                        if successful_results:
                            execution_times = [
                                r.execution_time_ms for r in successful_results
                            ]
                            report_data["benchmarks"][f"{bench_name}_{env}"] = {
                                "latest_result": successful_results[
                                    0
                                ].execution_time_ms,
                                "avg_execution_time_ms": statistics.mean(
                                    execution_times
                                ),
                                "min_execution_time_ms": min(execution_times),
                                "max_execution_time_ms": max(execution_times),
                                "test_count": len(successful_results),
                                "last_updated": successful_results[
                                    0
                                ].timestamp.isoformat(),
                            }

                except Exception as e:
                    logger.warning(f"获取基准测试数据失败 {bench_name}_{env}: {e}")

        # 检查回归
        regression_check = await self.check_regressions()
        report_data["regressions"] = regression_check

        # 保存报告
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        report_file = (
            output_path
            / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"性能报告已保存: {report_file}")

        return {
            "success": True,
            "report_file": str(report_file),
            "summary": {
                "benchmarks_analyzed": len(report_data["benchmarks"]),
                "regressions_detected": regression_check.get("regressions_detected", 0),
                "report_generated_at": report_data["timestamp"],
            },
        }

    async def _generate_comparison_report(
        self, benchmark_name: str, comparison_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成环境对比报告"""
        successful_results = {
            k: v for k, v in comparison_results.items() if v.get("success", False)
        }

        if len(successful_results) < 2:
            return {
                "success": False,
                "error": "Need at least 2 successful benchmark runs for comparison",
                "benchmark_name": benchmark_name,
            }

        # 计算对比指标
        envs = list(successful_results.keys())
        comparison_metrics = {}

        for metric in [
            "avg_execution_time_ms",
            "p95_execution_time_ms",
            "success_rate",
        ]:
            values = {}
            for env in envs:
                values[env] = successful_results[env]["summary"].get(metric, 0)

            if all(v > 0 for v in values.values()):
                best_env = min(values, key=values.get)
                worst_env = max(values, key=values.get)
                improvement = (
                    (values[worst_env] - values[best_env]) / values[worst_env]
                ) * 100

                comparison_metrics[metric] = {
                    "best_environment": best_env,
                    "worst_environment": worst_env,
                    "best_value": values[best_env],
                    "worst_value": values[worst_env],
                    "improvement_percent": improvement,
                }

        return {
            "success": True,
            "benchmark_name": benchmark_name,
            "environments_compared": envs,
            "comparison_time": datetime.now().isoformat(),
            "detailed_results": successful_results,
            "comparison_metrics": comparison_metrics,
        }

    async def _analyze_trends(self, historical_results: List) -> Dict[str, Any]:
        """分析趋势数据"""
        if len(historical_results) < 3:
            return {
                "trend": "insufficient_data",
                "message": "Need at least 3 data points for trend analysis",
            }

        # 按时间排序
        sorted_results = sorted(historical_results, key=lambda x: x.timestamp)
        execution_times = [r.execution_time_ms for r in sorted_results if r.success]

        if len(execution_times) < 3:
            return {
                "trend": "insufficient_data",
                "message": "Insufficient successful test results",
            }

        # 计算趋势
        import numpy as np

        x = np.arange(len(execution_times))
        y = np.array(execution_times)

        # 线性回归
        slope, intercept = np.polyfit(x, y, 1)
        r_squared = 1 - np.sum((y - (slope * x + intercept)) ** 2) / np.sum(
            (y - np.mean(y)) ** 2
        )

        # 确定趋势
        if abs(slope) < 0.1:
            trend = "stable"
        elif slope > 0:
            trend = "degrading"
        else:
            trend = "improving"

        return {
            "trend": trend,
            "slope": float(slope),
            "r_squared": float(r_squared),
            "data_points": len(execution_times),
            "time_range_days": (
                sorted_results[-1].timestamp - sorted_results[0].timestamp
            ).days,
            "avg_execution_time_ms": statistics.mean(execution_times),
            "first_execution_time_ms": execution_times[0],
            "last_execution_time_ms": execution_times[-1],
            "change_percent": (
                (execution_times[-1] - execution_times[0]) / execution_times[0]
            )
            * 100,
        }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="足球预测系统性能基准测试")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 单个基准测试命令
    single_parser = subparsers.add_parser("run", help="运行单个基准测试")
    single_parser.add_argument(
        "--benchmark-name", default="football_prediction_system", help="基准测试名称"
    )
    single_parser.add_argument("--environment", default="development", help="测试环境")
    single_parser.add_argument(
        "--output-dir", default="benchmark_results", help="输出目录"
    )
    single_parser.add_argument(
        "--target-prediction-time", type=float, default=50.0, help="目标预测时间(毫秒)"
    )
    single_parser.add_argument(
        "--regression-check", action="store_true", help="启用回归检测"
    )
    single_parser.add_argument(
        "--generate-html", action="store_true", help="生成HTML报告"
    )

    # 多环境对比命令
    compare_parser = subparsers.add_parser("compare", help="比较不同环境的性能")
    compare_parser.add_argument("--benchmark-name", required=True, help="基准测试名称")
    compare_parser.add_argument(
        "--environments",
        nargs="+",
        default=["development", "staging"],
        help="要比较的环境",
    )

    # 趋势分析命令
    trend_parser = subparsers.add_parser("trend", help="分析性能趋势")
    trend_parser.add_argument("--benchmark-name", required=True, help="基准测试名称")
    trend_parser.add_argument("--environment", required=True, help="测试环境")
    trend_parser.add_argument("--days", type=int, default=30, help="分析天数")

    # 回归检查命令
    regression_parser = subparsers.add_parser("regression", help="检查性能回归")
    regression_parser.add_argument("--benchmark-name", help="指定基准测试名称")
    regression_parser.add_argument("--environment", help="指定测试环境")

    # 生成报告命令
    report_parser = subparsers.add_parser("report", help="生成性能报告")
    report_parser.add_argument(
        "--output-dir", default="performance_reports", help="报告输出目录"
    )

    args = parser.parse_args()
    runner = BenchmarkRunner()

    try:
        if args.command == "run":
            # 运行单个基准测试
            config = create_benchmark_config(
                benchmark_name=args.benchmark_name,
                environment=args.environment,
                output_dir=args.output_dir,
                target_prediction_time_ms=args.target_prediction_time,
                enable_regression_detection=args.regression_check,
                generate_html_report=args.generate_html,
            )

            result = await runner.run_single_benchmark(config)
            print(f"\n✅ 基准测试完成!")
            print(f"测试名称: {result['benchmark_name']}")
            print(f"环境: {result['environment']}")
            print(f"成功率: {result['summary']['success_rate']:.1%}")
            print(f"平均执行时间: {result['summary']['avg_execution_time_ms']:.2f}ms")

            if result.get("regression_detected"):
                print(f"⚠️ 检测到 {result['regression_count']} 个性能回归")

            return result

        elif args.command == "compare":
            # 环境对比
            result = await runner.compare_environments(
                args.benchmark_name, args.environments
            )

            print(f"\n🔄 环境对比完成!")
            print(f"基准测试: {result['benchmark_name']}")
            print(f"对比环境: {', '.join(result['environments_compared'])}")

            if result.get("comparison_metrics"):
                for metric, data in result["comparison_metrics"].items():
                    print(f"\n{metric}:")
                    print(
                        f"  最佳环境: {data['best_environment']} ({data['best_value']:.2f})"
                    )
                    print(
                        f"  最差环境: {data['worst_environment']} ({data['worst_value']:.2f})"
                    )
                    print(f"  改进幅度: {data['improvement_percent']:.1f}%")

            return result

        elif args.command == "trend":
            # 趋势分析
            result = await runner.analyze_performance_trends(
                args.benchmark_name, args.environment, args.days
            )

            print(f"\n📈 趋势分析完成!")
            print(f"基准测试: {result['benchmark_name']}")
            print(f"环境: {result['environment']}")
            print(f"分析周期: {result['analysis_period_days']} 天")
            print(f"数据点数: {result['total_data_points']}")

            if "trend_analysis" in result:
                trend = result["trend_analysis"]
                print(f"\n趋势: {trend['trend']}")
                print(f"平均执行时间: {trend['avg_execution_time_ms']:.2f}ms")
                print(f"变化幅度: {trend['change_percent']:.1f}%")

            return result

        elif args.command == "regression":
            # 回归检查
            result = await runner.check_regressions(
                args.benchmark_name, args.environment
            )

            print(f"\n🔍 回归检查完成!")
            print(f"检查总数: {result['total_checks']}")
            print(f"发现回归: {result['regressions_detected']} 个")

            if result["regression_details"]:
                print("\n回归详情:")
                for regression in result["regression_details"]:
                    print(
                        f"  - {regression['benchmark_name']} ({regression['environment']}): "
                        f"{regression['regression_percent']:.1f}% 回归"
                    )

            return result

        elif args.command == "report":
            # 生成报告
            result = await runner.generate_performance_report(args.output_dir)

            print(f"\n📊 性能报告已生成!")
            print(f"报告文件: {result['report_file']}")
            print(f"分析的基准测试: {result['summary']['benchmarks_analyzed']}")
            print(f"发现的回归: {result['summary']['regressions_detected']} 个")

            return result

        else:
            parser.print_help()
            return None

    except Exception as e:
        logger.error(f"执行失败: {e}")
        print(f"❌ 执行失败: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
