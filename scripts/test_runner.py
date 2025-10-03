#!/usr/bin/env python3
"""
自动化测试运行器
支持分层测试执行、并行运行、质量门禁
"""

import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import datetime


class TestRunner:
    """智能测试运行器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.results = {}
        self.start_time = None

    def run_layered_tests(self, layers: List[str] = None, parallel: bool = True) -> Dict[str, Any]:
        """运行分层测试"""
        if layers is None:
            layers = ["unit", "integration", "e2e"]

        print("🚀 开始分层测试执行")
        print(f"📋 测试层级: {', '.join(layers)}")
        print(f"⚡ 并行执行: {parallel}")
        print("-" * 60)

        self.start_time = time.time()

        for layer in layers:
            print(f"\n🔍 执行 {layer} 测试...")
            layer_result = self._run_test_layer(layer, parallel)
            self.results[layer] = layer_result

            # 如果单元测试失败，停止执行
            if layer == "unit" and not layer_result.get("success", False):
                print("❌ 单元测试失败，停止后续测试")
                break

        # 生成汇总报告
        summary = self._generate_summary()
        self._print_summary(summary)

        return summary

    def _run_test_layer(self, layer: str, parallel: bool) -> Dict[str, Any]:
        """运行指定层级的测试"""
        test_paths = {
            "unit": "tests/unit/",
            "integration": "tests/integration/",
            "e2e": "tests/e2e/"
        }

        test_path = test_paths.get(layer)
        if not test_path or not Path(self.project_root / test_path).exists():
            return {
                "success": True,
                "message": f"测试路径不存在: {test_path}",
                "tests": []
            }

        # 构建pytest命令
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=/tmp/test_report.json"
        ]

        # 添加覆盖率（仅单元测试）
        if layer == "unit":
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-fail-under=20"
            ])

        # 添加并行执行
        if parallel and layer != "e2e":  # E2E测试通常不适合并行
            cmd.extend(["-n", "auto"])

        # 添加超时
        timeout = {
            "unit": 300,      # 5分钟
            "integration": 600,  # 10分钟
            "e2e": 1800      # 30分钟
        }.get(layer, 600)

        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            execution_time = time.time() - start_time

            # 解析测试报告
            test_report = self._parse_test_report("/tmp/test_report.json")

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "execution_time": execution_time,
                "tests": test_report.get("tests", []),
                "summary": test_report.get("summary", {}),
                "coverage": test_report.get("coverage", {}),
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"测试超时 ({timeout}秒)",
                "tests": []
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "tests": []
            }

    def _parse_test_report(self, report_file: str) -> Dict[str, Any]:
        """解析测试报告"""
        try:
            if Path(report_file).exists():
                with open(report_file) as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _generate_summary(self) -> Dict[str, Any]:
        """生成测试汇总"""
        total_time = time.time() - self.start_time
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0

        layer_results = {}
        overall_success = True

        for layer, result in self.results.items():
            layer_tests = result.get("tests", [])
            layer_summary = result.get("summary", {})

            passed = layer_summary.get("passed", 0)
            failed = layer_summary.get("failed", 0)
            skipped = layer_summary.get("skipped", 0)
            errors = layer_summary.get("error", 0)
            total = passed + failed + skipped + errors

            layer_results[layer] = {
                "success": result.get("success", False),
                "tests": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "time": result.get("execution_time", 0)
            }

            total_tests += total
            total_passed += passed
            total_failed += failed
            total_skipped += skipped
            total_errors += errors

            if not result.get("success", False):
                overall_success = False

        # 计算质量指标
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        summary = {
            "overall_success": overall_success,
            "total_time": total_time,
            "layers": layer_results,
            "total": {
                "tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "errors": total_errors,
                "success_rate": success_rate
            },
            "timestamp": datetime.datetime.now().isoformat()
        }

        # 保存汇总报告
        report_file = self.project_root / "test_results" / f"summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)

        return summary

    def _print_summary(self, summary: Dict[str, Any]):
        """打印测试汇总"""
        print("\n" + "="*60)
        print("📊 测试执行汇总")
        print("="*60)

        # 总体结果
        status_icon = "✅" if summary["overall_success"] else "❌"
        print(f"\n{status_icon} 总体状态: {'通过' if summary['overall_success'] else '失败'}")
        print(f"⏱️ 总执行时间: {summary['total_time']:.2f}秒")

        # 分层结果
        print(f"\n📋 各层级详情:")
        for layer, result in summary["layers"].items():
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {layer.upper()}: "
                  f"{result['passed']}通过, "
                  f"{result['failed']}失败, "
                  f"{result['skipped']}跳过 "
                  f"({result['time']:.2f}s)")

        # 总体统计
        total = summary["total"]
        print(f"\n📈 总体统计:")
        print(f"  总测试数: {total['tests']}")
        print(f"  通过率: {total['success_rate']:.1f}%")
        print(f"  成功率: {total['passed']}/{total['tests']}")

        # 失败详情
        if total['failed'] > 0 or total['errors'] > 0:
            print(f"\n⚠️ 失败测试:")
            for layer, result in summary["layers"].items():
                if not result["success"]:
                    print(f"  {layer.upper()}: 查看详细日志")

        print("\n" + "="*60)

    def run_quality_gate(self, min_coverage: float = 20, min_success_rate: float = 90) -> bool:
        """运行质量门禁"""
        print("\n🚪 执行质量门禁检查")
        print("-" * 40)

        # 检查覆盖率
        coverage_passed = True
        if "unit" in self.results:
            unit_result = self.results["unit"]
            coverage = unit_result.get("coverage", {})
            overall_cov = coverage.get("totals", {}).get("percent_covered", 0)

            if overall_cov < min_coverage:
                coverage_passed = False
                print(f"❌ 覆盖率不达标: {overall_cov:.1f}% < {min_coverage}%")
            else:
                print(f"✅ 覆盖率达标: {overall_cov:.1f}% >= {min_coverage}%")

        # 检查成功率
        total_tests = sum(r.get("summary", {}).get("total", 0) for r in self.results.values())
        total_passed = sum(r.get("summary", {}).get("passed", 0) for r in self.results.values())
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        success_passed = success_rate >= min_success_rate
        if success_passed:
            print(f"✅ 成功率达标: {success_rate:.1f}% >= {min_success_rate}%")
        else:
            print(f"❌ 成功率不达标: {success_rate:.1f}% < {min_success_rate}%")

        # 检查关键测试
        critical_passed = True
        if "unit" in self.results and not self.results["unit"]["success"]:
            critical_passed = False
            print("❌ 单元测试未全部通过")

        # 总体结果
        gate_passed = coverage_passed and success_passed and critical_passed
        if gate_passed:
            print("\n✅ 质量门禁通过")
        else:
            print("\n❌ 质量门禁失败")

        return gate_passed

    def run_failing_tests(self) -> Dict[str, Any]:
        """仅运行之前失败的测试"""
        print("🔍 运行失败测试...")

        # 查找上次失败的测试
        failed_tests_file = self.project_root / ".failed_tests"
        if not failed_tests_file.exists():
            print("✅ 没有失败的测试记录")
            return {"success": True, "tests": []}

        with open(failed_tests_file) as f:
            failed_tests = f.read().strip().split('\n')

        if not failed_tests or failed_tests == ['']:
            print("✅ 没有失败的测试")
            return {"success": True, "tests": []}

        # 运行失败的测试
        cmd = [
            sys.executable, "-m", "pytest",
            *failed_tests,
            "-v",
            "--tb=long"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            success = result.returncode == 0
            if success:
                print("✅ 所有失败的测试现在都通过了")
                failed_tests_file.unlink()  # 删除失败记录
            else:
                print("❌ 部分测试仍然失败")

            return {
                "success": success,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except Exception as e:
            print(f"❌ 执行失败: {e}")
            return {"success": False, "error": str(e)}

    def create_test_matrix(self) -> Dict[str, List[str]]:
        """创建测试矩阵（用于CI）"""
        matrix = {
            "unit": [
                "tests/unit/api/",
                "tests/unit/core/",
                "tests/unit/database/",
                "tests/unit/utils/",
                "tests/unit/models/",
                "tests/unit/services/"
            ],
            "integration": [
                "tests/integration/api_database/",
                "tests/integration/api_cache/",
                "tests/integration/database_cache/"
            ],
            "e2e": [
                "tests/e2e/user_workflows/",
                "tests/e2e/prediction_flows/"
            ]
        }

        # 过滤存在的路径
        for layer in matrix:
            matrix[layer] = [
                path for path in matrix[layer]
                if (self.project_root / path).exists()
            ]

        return matrix


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description = os.getenv("TEST_RUNNER_DESCRIPTION_380"))
    parser.add_argument("--layers", "-l", nargs="+",
                       choices=["unit", "integration", "e2e"],
                       help = os.getenv("TEST_RUNNER_HELP_382"))
    parser.add_argument("--parallel", "-p", action = os.getenv("TEST_RUNNER_ACTION_383"), default=True,
                       help = os.getenv("TEST_RUNNER_HELP_384"))
    parser.add_argument("--no-parallel", action = os.getenv("TEST_RUNNER_ACTION_383"),
                       help = os.getenv("TEST_RUNNER_HELP_385"))
    parser.add_argument("--failing-only", "-f", action = os.getenv("TEST_RUNNER_ACTION_383"),
                       help = os.getenv("TEST_RUNNER_HELP_386"))
    parser.add_argument("--quality-gate", "-q", action = os.getenv("TEST_RUNNER_ACTION_383"),
                       help = os.getenv("TEST_RUNNER_HELP_388"))
    parser.add_argument("--coverage", "-c", type=float, default=20,
                       help = os.getenv("TEST_RUNNER_HELP_389"))
    parser.add_argument("--success-rate", "-s", type=float, default=90,
                       help = os.getenv("TEST_RUNNER_HELP_391"))
    parser.add_argument("--matrix", "-m", action = os.getenv("TEST_RUNNER_ACTION_383"),
                       help = os.getenv("TEST_RUNNER_HELP_392"))
    parser.add_argument("--output", "-o", help = os.getenv("TEST_RUNNER_HELP_393"))

    args = parser.parse_args()

    # 处理并行选项
    parallel = args.parallel and not args.no_parallel

    # 创建测试运行器
    runner = TestRunner()

    # 输出测试矩阵
    if args.matrix:
        matrix = runner.create_test_matrix()
        print(json.dumps(matrix, indent=2))
        return 0

    # 仅运行失败测试
    if args.failing_only:
        result = runner.run_failing_tests()
        return 0 if result["success"] else 1

    # 运行分层测试
    results = runner.run_layered_tests(layers=args.layers, parallel=parallel)

    # 执行质量门禁
    if args.quality_gate:
        gate_passed = runner.run_quality_gate(
            min_coverage=args.coverage,
            min_success_rate=args.success_rate
        )
        if not gate_passed:
            return 1

    # 保存结果
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 结果已保存到: {args.output}")

    # 返回退出码
    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    sys.exit(main())