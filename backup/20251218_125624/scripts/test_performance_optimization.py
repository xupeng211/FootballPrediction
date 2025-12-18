#!/usr/bin/env python3
"""
测试性能优化脚本
分析和优化测试执行性能
"""

import subprocess
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import psutil
import os


class TestPerformanceAnalyzer:
    """测试性能分析器"""

    def __init__(self):
        self.results = []
        self.base_dir = Path(__file__).parent.parent

    def run_test_with_timing(
        self, test_path: str, description: str, timeout: int = 120
    ) -> Dict[str, Any]:
        """运行测试并记录性能指标"""
        print(f"\n🔍 分析: {description}")
        print(f"测试路径: {test_path}")

        # 记录开始时间和资源使用
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # 运行测试
        cmd = [sys.executable, "-m", "pytest", test_path, "--tb=no", "-q", "-x"]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, cwd=self.base_dir
            )

            # 记录结束时间和资源使用
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            duration = end_time - start_time
            memory_increase = end_memory - start_memory

            # 解析测试结果
            test_result = self.parse_test_output(result.stdout)

            performance_data = {
                "description": description,
                "test_path": test_path,
                "duration": duration,
                "memory_increase": memory_increase,
                "exit_code": result.returncode,
                "test_result": test_result,
                "success": result.returncode == 0,
            }

            self.results.append(performance_data)

            # 打印结果
            status = "✅ 成功" if performance_data["success"] else "❌ 失败"
            print(
                f"{status} - 耗时: {duration:.2f}s, 内存增长: {memory_increase:.1f}MB"
            )

            if test_result:
                print(f"  测试统计: {test_result}")

            return performance_data

        except subprocess.TimeoutExpired:
            print(f"⏰ 超时 ({timeout}s)")
            return {
                "description": description,
                "test_path": test_path,
                "duration": timeout,
                "memory_increase": 0,
                "exit_code": 124,
                "test_result": None,
                "success": False,
                "timeout": True,
            }

    def parse_test_output(self, output: str) -> Dict[str, Any]:
        """解析pytest输出"""
        try:
            lines = output.strip().split("\n")
            for line in lines:
                if "passed" in line and ("failed" in line or "skipped" in line):
                    # 解析类似 "4 passed, 2 skipped in 0.45s" 的行
                    if "in " in line:
                        result_part = line.split(" in ")[0]
                        parts = result_part.split(", ")
                        result = {}
                        for part in parts:
                            part = part.strip()
                            if "passed" in part:
                                result["passed"] = int(part.split(" ")[0])
                            elif "failed" in part:
                                result["failed"] = int(part.split(" ")[0])
                            elif "skipped" in part:
                                result["skipped"] = int(part.split(" ")[0])
                            elif "error" in part:
                                result["error"] = int(part.split(" ")[0])
                        return result
            return {}
        except Exception:
            return {}

    def run_comprehensive_analysis(self):
        """运行综合性能分析"""
        print("🚀 开始测试性能综合分析")
        print("=" * 60)

        # 定义测试套件
        test_suites = [
            {
                "path": "tests/working_basic_tests.py",
                "desc": "基础功能测试",
                "timeout": 60,
            },
            {
                "path": "tests/unit/test_ml_inference_fixed.py",
                "desc": "ML推理测试",
                "timeout": 60,
            },
            {"path": "tests/unit/test_config.py", "desc": "配置测试", "timeout": 30},
            {
                "path": "tests/unit/test_health_api_complete.py",
                "desc": "健康API测试",
                "timeout": 60,
            },
            {
                "path": "tests/unit/test_api_routes.py",
                "desc": "API路由测试",
                "timeout": 60,
            },
            {"path": "tests/v2/", "desc": "V2测试套件", "timeout": 90},
            {
                "path": "tests/integration/test_api_integration.py",
                "desc": "集成测试",
                "timeout": 60,
            },
            {"path": "tests/unit/test_metrics.py", "desc": "指标测试", "timeout": 45},
            {
                "path": "tests/unit/test_exceptions.py",
                "desc": "异常处理测试",
                "timeout": 45,
            },
        ]

        # 运行各个测试套件
        for suite in test_suites:
            self.run_test_with_timing(suite["path"], suite["desc"], suite["timeout"])

    def run_parallel_analysis(self):
        """运行并行测试分析"""
        print(f"\n🔄 并行测试分析")
        print("=" * 30)

        # 选择可以并行的测试
        parallel_tests = [
            "tests/working_basic_tests.py",
            "tests/unit/test_ml_inference_fixed.py",
            "tests/unit/test_config.py",
            "tests/unit/test_metrics.py",
            "tests/unit/test_exceptions.py",
        ]

        start_time = time.time()

        # 运行并行测试
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            *parallel_tests,
            "--tb=no",
            "-q",
            "-x",
            "-n",
            "auto",  # 使用自动并行
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180, cwd=self.base_dir
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                print(f"✅ 并行测试成功 - 耗时: {duration:.2f}s")
            else:
                print(f"❌ 并行测试失败 - 耗时: {duration:.2f}s")

            # 解析结果
            test_result = self.parse_test_output(result.stdout)
            if test_result:
                print(f"  测试统计: {test_result}")

        except subprocess.TimeoutExpired:
            print("⏰ 并行测试超时")

    def generate_optimization_report(self):
        """生成优化报告"""
        print(f"\n📊 性能优化报告")
        print("=" * 60)

        if not self.results:
            print("没有测试结果")
            return

        # 计算总体统计
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0
        total_memory = 0

        for result in self.results:
            if result["test_result"]:
                total_tests += result["test_result"].get("passed", 0)
                total_tests += result["test_result"].get("failed", 0)
                total_tests += result["test_result"].get("skipped", 0)
                total_passed += result["test_result"].get("passed", 0)
                total_failed += result["test_result"].get("failed", 0)
                total_skipped += result["test_result"].get("skipped", 0)

            total_duration += result["duration"]
            total_memory += result["memory_increase"]

        print(f"📈 总体统计:")
        print(f"  测试总数: {total_tests}")
        print(f"  通过: {total_passed}, 失败: {total_failed}, 跳过: {total_skipped}")
        print(f"  总耗时: {total_duration:.2f}s")
        print(f"  总内存增长: {total_memory:.1f}MB")

        # 性能瓶颈分析
        print(f"\n⚡ 性能瓶颈分析:")
        slowest_tests = sorted(self.results, key=lambda x: x["duration"], reverse=True)[
            :3
        ]
        for i, test in enumerate(slowest_tests, 1):
            print(f"  {i}. {test['description']}: {test['duration']:.2f}s")

        memory_heavy_tests = sorted(
            self.results, key=lambda x: x["memory_increase"], reverse=True
        )[:3]
        print(f"\n💾 内存使用分析:")
        for i, test in enumerate(memory_heavy_tests, 1):
            print(f"  {i}. {test['description']}: {test['memory_increase']:.1f}MB")

        # 优化建议
        print(f"\n💡 优化建议:")

        # 分析慢速测试
        avg_duration = total_duration / len(self.results) if self.results else 0
        slow_tests = [r for r in self.results if r["duration"] > avg_duration * 1.5]

        if slow_tests:
            print(f"  🐌 慢速测试优化 ({len(slow_tests)}个):")
            for test in slow_tests:
                print(f"    - {test['description']}: 考虑并行化或Mock优化")

        # 分析内存使用
        avg_memory = total_memory / len(self.results) if self.results else 0
        memory_heavy = [
            r for r in self.results if r["memory_increase"] > avg_memory * 2
        ]

        if memory_heavy:
            print(f"  💾 内存优化 ({len(memory_heavy)}个):")
            for test in memory_heavy:
                print(f"    - {test['description']}: 考虑测试数据优化")

        # 成功率分析
        success_rate = (
            len([r for r in self.results if r["success"]]) / len(self.results) * 100
        )
        if success_rate < 100:
            print(f"  ⚠️ 稳定性优化 (成功率: {success_rate:.1f}%):")
            failed_tests = [r for r in self.results if not r["success"]]
            for test in failed_tests:
                print(f"    - {test['description']}: 修复测试失败问题")

        # 保存报告
        self.save_performance_report()

    def save_performance_report(self):
        """保存性能报告到文件"""
        report_data = {
            "timestamp": time.time(),
            "results": self.results,
            "summary": {
                "total_tests": len(self.results),
                "total_duration": sum(r["duration"] for r in self.results),
                "total_memory": sum(r["memory_increase"] for r in self.results),
                "success_rate": len([r for r in self.results if r["success"]])
                / len(self.results)
                * 100,
            },
        }

        report_file = self.base_dir / "test_performance_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

    def generate_optimized_test_commands(self):
        """生成优化的测试命令"""
        print(f"\n🚀 优化后的测试命令:")
        print("=" * 30)

        # 快速测试命令
        fast_tests = [
            "tests/working_basic_tests.py",
            "tests/unit/test_config.py",
            "tests/unit/test_metrics.py",
            "tests/unit/test_exceptions.py",
        ]

        print(f"\n⚡ 快速测试 (< 30s):")
        print(f"python -m pytest {' '.join(fast_tests)} -v --tb=short")

        # 核心功能测试
        core_tests = [
            "tests/unit/test_ml_inference_fixed.py",
            "tests/unit/test_health_api_complete.py",
            "tests/unit/test_api_routes.py",
        ]

        print(f"\n🎯 核心功能测试:")
        print(f"python -m pytest {' '.join(core_tests)} -v --tb=short")

        # 并行测试命令
        print(f"\n🔄 并行测试:")
        print(
            f"python -m pytest tests/working_basic_tests.py tests/unit/test_config.py tests/unit/test_metrics.py -n auto"
        )

        # 覆盖率测试
        print(f"\n📊 覆盖率测试:")
        print(
            f"python -m pytest tests/working_basic_tests.py tests/unit/test_ml_inference_fixed.py tests/unit/test_config.py --cov=src --cov-report=term-missing"
        )

        # 性能测试
        print(f"\n⚡ 性能测试:")
        print(
            f"python -m pytest tests/performance/test_inference_performance.py::TestMatchPredictorPerformance -v"
        )


def main():
    """主函数"""
    analyzer = TestPerformanceAnalyzer()

    print("🔧 Football Prediction System - 测试性能优化分析")
    print("=" * 60)

    try:
        # 运行综合分析
        analyzer.run_comprehensive_analysis()

        # 运行并行分析
        analyzer.run_parallel_analysis()

        # 生成优化报告
        analyzer.generate_optimization_report()

        # 生成优化命令
        analyzer.generate_optimized_test_commands()

        print(f"\n✅ 性能优化分析完成！")

    except KeyboardInterrupt:
        print(f"\n⏹️ 分析被用户中断")
    except Exception as e:
        print(f"\n❌ 分析过程中出现错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
