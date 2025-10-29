#!/usr/bin/env python3
"""
📊 CI/CD性能监控器
监控和分析CI/CD工作流的性能指标

版本: v1.0 | 创建时间: 2025-10-26 | 作者: Claude AI Assistant
"""

import os
import sys
import json
import time
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    job_name: str
    start_time: float
    end_time: float
    duration: float
    status: str
    cache_hits: int = 0
    cache_misses: int = 0
    test_count: int = 0
    test_passed: int = 0
    test_failed: int = 0
    coverage_percent: float = 0.0


class CIPerformanceMonitor:
    """CI/CD性能监控器"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.start_time = time.time()
        self.root_dir = Path(__file__).parent.parent

    def start_job_timer(self, job_name: str) -> None:
        """开始计时作业"""
        metric = PerformanceMetrics(
            job_name=job_name, start_time=time.time(), end_time=0.0, duration=0.0, status="running"
        )
        self.metrics.append(metric)
        print(f"⏱️  开始计时: {job_name}")

    def end_job_timer(self, job_name: str, status: str = "completed") -> None:
        """结束计时作业"""
        for metric in self.metrics:
            if metric.job_name == job_name and metric.status == "running":
                metric.end_time = time.time()
                metric.duration = metric.end_time - metric.start_time
                metric.status = status
                print(f"⏹️  结束计时: {job_name} (耗时: {metric.duration:.2f}s)")
                break

    def run_performance_test(self, test_type: str = "quick") -> Dict:
        """运行性能测试"""
        print(f"🚀 运行{test_type}性能测试...")

        results = {}

        # 测试1: 依赖安装性能
        print("📦 测试依赖安装性能...")
        start_time = time.time()
        try:
            subprocess.run(
                ["pip", "install", "--quiet", "-r", "requirements/requirements.lock"],
                check=True,
                capture_output=True,
            )
            install_time = time.time() - start_time
            results["install_time"] = install_time
            print(f"✅ 依赖安装耗时: {install_time:.2f}s")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            results["install_time"] = -1

        # 测试2: 语法检查性能
        print("🔧 测试语法检查性能...")
        start_time = time.time()
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", "src/**/*.py"],
                check=True,
                capture_output=True,
                shell=True,
            )
            syntax_time = time.time() - start_time
            results["syntax_time"] = syntax_time
            print(f"✅ 语法检查耗时: {syntax_time:.2f}s")
        except subprocess.CalledProcessError:
            syntax_time = time.time() - start_time
            results["syntax_time"] = syntax_time
            print(f"⚠️ 语法检查发现问题 (耗时: {syntax_time:.2f}s)")

        # 测试3: Lint检查性能
        print("🔍 测试Lint检查性能...")
        start_time = time.time()
        try:
            result = subprocess.run(
                ["ruff", "check", "src/", "--output-format=json"],
                check=True,
                capture_output=True,
                text=True,
            )
            lint_time = time.time() - start_time
            lint_issues = len(result.stdout.strip()) if result.stdout.strip() else 0
            results["lint_time"] = lint_time
            results["lint_issues"] = lint_issues
            print(
                f"✅ Lint检查耗时: {lint_time:.2f}s (问题: {len(json.loads(result.stdout) if result.stdout.strip() else '[]')})"
            )
        except subprocess.CalledProcessError:
            lint_time = time.time() - start_time
            results["lint_time"] = lint_time
            results["lint_issues"] = -1
            print(f"⚠️ Lint检查发现问题 (耗时: {lint_time:.2f}s)")

        # 测试4: 测试执行性能
        if test_type == "full":
            print("🧪 测试测试执行性能...")
            start_time = time.time()
            try:
                result = subprocess.run(
                    ["pytest", "tests/unit/", "--tb=no", "-q"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                test_time = time.time() - start_time
                # 解析pytest输出
                lines = result.stdout.strip().split("\n")
                test_summary = lines[-1] if lines else ""
                results["test_time"] = test_time
                results["test_summary"] = test_summary
                print(f"✅ 测试执行耗时: {test_time:.2f}s")
            except subprocess.CalledProcessError:
                test_time = time.time() - start_time
                results["test_time"] = test_time
                results["test_summary"] = "测试失败"
                print(f"⚠️ 测试执行失败 (耗时: {test_time:.2f}s)")

        return results

    def generate_performance_report(self) -> str:
        """生成性能报告"""
        total_time = time.time() - self.start_time
        completed_metrics = [m for m in self.metrics if m.status != "running"]

        report = f"""## 📊 CI/CD性能报告

### 📈 总体性能
- **总执行时间**: {total_time:.2f}s
- **已完成作业**: {len(completed_metrics)}/{len(self.metrics)}
- **平均作业时间**: {sum(m.duration for m in completed_metrics)/len(completed_metrics):.2f}s

### 🏃‍♂️ 作业性能详情
"""

        for metric in completed_metrics:
            status_emoji = "✅" if metric.status == "completed" else "❌"
            report += f"""
#### {status_emoji} {metric.job_name}
- **执行时间**: {metric.duration:.2f}s
- **状态**: {metric.status}
"""

        if completed_metrics:
            slowest = max(completed_metrics, key=lambda m: m.duration)
            fastest = min(completed_metrics, key=lambda m: m.duration)
            report += f"""
### 🏆 性能统计
- **最慢作业**: {slowest.job_name} ({slowest.duration:.2f}s)
- **最快作业**: {fastest.job_name} ({fastest.duration:.2f}s)
- **性能差异**: {slowest.duration - fastest.duration:.2f}s
"""

        return report

    def save_report(self, filename: str = "ci_performance_report.md") -> None:
        """保存性能报告"""
        report = self.generate_performance_report()
        report_path = Path(filename)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# CI/CD性能监控报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("**监控器版本**: v1.0\n\n")
            f.write(report)

        print(f"📄 性能报告已保存到: {report_path}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD性能监控器")
    parser.add_argument("--test", choices=["quick", "full"], default="quick", help="性能测试类型")
    parser.add_argument("--job", help="监控特定作业名称")
    parser.add_argument("--start", help="开始计时作业")
    parser.add_argument("--end", help="结束计时作业")
    parser.add_argument("--report", action="store_true", help="生成性能报告")
    parser.add_argument("--output", default="ci_performance_report.md", help="报告输出文件")

    args = parser.parse_args()

    monitor = CIPerformanceMonitor()

    if args.start:
        monitor.start_job_timer(args.start)
    elif args.end:
        monitor.end_job_timer(args.end)
    elif args.test:
        results = monitor.run_performance_test(args.test)
        print("\n📊 性能测试结果:")
        for key, value in results.items():
            print(f"  {key}: {value}")
    elif args.report:
        monitor.save_report(args.output)
    else:
        # 默认运行快速性能测试
        results = monitor.run_performance_test("quick")
        monitor.save_report()


if __name__ == "__main__":
    main()
