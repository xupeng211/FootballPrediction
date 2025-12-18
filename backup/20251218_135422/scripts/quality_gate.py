#!/usr/bin/env python3
"""
自动化质量门禁系统
在代码提交前自动执行质量检查
"""

import subprocess
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re


class QualityGate:
    """质量门禁系统"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.base_dir = Path(__file__).parent.parent
        self.results = {}
        self.passed = True
        self.start_time = time.time()

        # 质量标准
        self.quality_standards = {
            "test_coverage": {
                "minimum": 25.0 if not strict_mode else 30.0,
                "target": 35.0 if not strict_mode else 40.0,
            },
            "test_success_rate": {"minimum": 95.0, "target": 98.0},
            "code_quality": {
                "max_complexity": 10,
                "max_line_length": 88,
                "max_function_length": 50,
            },
            "performance": {
                "max_test_duration": 300,  # 5分钟
                "max_memory_usage": 200,  # MB
            },
            "security": {
                "no_critical_vulnerabilities": True,
                "max_high_vulnerabilities": 0,
                "max_medium_vulnerabilities": 5 if not strict_mode else 2,
            },
        }

    def run_command(
        self, cmd: List[str], description: str, timeout: int = 120
    ) -> Tuple[bool, Dict[str, Any]]:
        """运行命令并返回结果"""
        print(f"\n🔍 {description}")
        print(f"命令: {' '.join(cmd)}")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, cwd=self.base_dir
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            result_data = {
                "success": success,
                "exit_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            status = "✅ 通过" if success else "❌ 失败"
            print(f"{status} - 耗时: {duration:.2f}s")

            if not success and result.stderr:
                print(f"错误: {result.stderr[:200]}...")

            return success, result_data

        except subprocess.TimeoutExpired:
            print(f"⏰ 超时 ({timeout}s)")
            return False, {"success": False, "timeout": True, "duration": timeout}

    def check_test_coverage(self) -> bool:
        """检查测试覆盖率"""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/working_basic_tests.py",
            "tests/unit/test_ml_inference_fixed.py",
            "tests/unit/test_config.py",
            "tests/unit/test_health_api_complete.py",
            "tests/unit/test_api_routes.py",
            "tests/unit/test_metrics.py",
            "tests/unit/test_exceptions.py",
            "tests/v2/",
            "--ignore=tests/legacy/",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--tb=no",
            "-q",
        ]

        success, result = self.run_command(cmd, "检查测试覆盖率", timeout=180)

        if success:
            # 解析覆盖率报告
            coverage_data = self.parse_coverage_report()
            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)

            min_coverage = self.quality_standards["test_coverage"]["minimum"]
            target_coverage = self.quality_standards["test_coverage"]["target"]

            self.results["test_coverage"] = {
                "success": total_coverage >= min_coverage,
                "coverage": total_coverage,
                "minimum": min_coverage,
                "target": target_coverage,
                "passed_target": total_coverage >= target_coverage,
            }

            print(
                f"📊 覆盖率: {total_coverage:.1f}% (最低要求: {min_coverage}%, 目标: {target_coverage}%)"
            )

            if total_coverage < min_coverage:
                print(f"❌ 覆盖率低于最低要求")
                self.passed = False
            elif total_coverage >= target_coverage:
                print(f"🎯 达到覆盖率目标")
            else:
                print(f"⚠️ 覆盖率未达到目标，但符合最低要求")

            return total_coverage >= min_coverage
        else:
            self.results["test_coverage"] = {
                "success": False,
                "error": result.get("stderr"),
            }
            self.passed = False
            return False

    def parse_coverage_report(self) -> Dict[str, Any]:
        """解析覆盖率报告"""
        try:
            coverage_file = self.base_dir / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"无法解析覆盖率报告: {e}")

        return {"totals": {"percent_covered": 0}}

    def check_test_execution(self) -> bool:
        """检查测试执行"""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/working_basic_tests.py",
            "tests/unit/test_ml_inference_fixed.py",
            "tests/unit/test_config.py",
            "tests/unit/test_health_api_complete.py",
            "tests/unit/test_api_routes.py",
            "tests/unit/test_metrics.py",
            "tests/unit/test_exceptions.py",
            "tests/v2/",
            "--ignore=tests/legacy/",
            "--tb=no",
            "-q",
            "--maxfail=5",
        ]

        success, result = self.run_command(cmd, "执行测试套件", timeout=300)

        # 解析测试结果
        test_stats = self.parse_test_output(result.stdout)

        if test_stats:
            total = (
                test_stats.get("passed", 0)
                + test_stats.get("failed", 0)
                + test_stats.get("skipped", 0)
            )
            passed = test_stats.get("passed", 0)
            success_rate = (passed / total * 100) if total > 0 else 0

            min_success_rate = self.quality_standards["test_success_rate"]["minimum"]
            target_success_rate = self.quality_standards["test_success_rate"]["target"]

            self.results["test_execution"] = {
                "success": success and success_rate >= min_success_rate,
                "total": total,
                "passed": passed,
                "failed": test_stats.get("failed", 0),
                "skipped": test_stats.get("skipped", 0),
                "success_rate": success_rate,
                "minimum": min_success_rate,
                "target": target_success_rate,
            }

            print(f"📋 测试结果: {passed}/{total} 通过 ({success_rate:.1f}%)")

            if success_rate < min_success_rate:
                print(f"❌ 测试通过率低于最低要求")
                self.passed = False
            elif success_rate >= target_success_rate:
                print(f"🎯 达到测试质量目标")
            else:
                print(f"⚠️ 测试质量未达到目标，但符合最低要求")

        return success

    def parse_test_output(self, output: str) -> Dict[str, Any]:
        """解析pytest输出"""
        try:
            # 查找包含测试统计的行
            lines = output.strip().split("\n")
            for line in lines:
                if "passed" in line and ("failed" in line or "skipped" in line):
                    # 解析类似 "120 passed, 22 skipped in 2.00s" 的行
                    stats = {}
                    parts = line.split(" in ")[0].split(", ")
                    for part in parts:
                        part = part.strip()
                        if "passed" in part:
                            stats["passed"] = int(part.split(" ")[0])
                        elif "failed" in part:
                            stats["failed"] = int(part.split(" ")[0])
                        elif "skipped" in part:
                            stats["skipped"] = int(part.split(" ")[0])
                        elif "error" in part:
                            stats["error"] = int(part.split(" ")[0])
                    return stats
        except Exception:
            pass
        return {}

    def check_code_quality(self) -> bool:
        """检查代码质量"""
        checks = {
            "格式化": ["black", "--check", "--diff", "src/", "scripts/", "tests/"],
            "代码风格": [
                "flake8",
                "src/",
                "scripts/",
                "tests/",
                "--format=github",
                "--max-line-length=88",
            ],
            "类型检查": ["mypy", "src/", "--ignore-missing-imports"],
            "复杂度": ["radon", "cc", "src/", "--min=B"],
        }

        quality_results = {}
        overall_success = True

        for check_name, cmd in checks.items():
            success, result = self.run_command(
                cmd, f"代码质量检查 - {check_name}", timeout=60
            )

            if check_name == "复杂度" and success:
                # 解析复杂度结果
                complexity_issues = self.parse_complexity_output(result.stdout)
                max_complexity = self.quality_standards["code_quality"][
                    "max_complexity"
                ]

                quality_results[check_name] = {
                    "success": len(complexity_issues) == 0,
                    "issues": complexity_issues,
                    "max_allowed": max_complexity,
                }

                if complexity_issues:
                    print(f"⚠️ 发现 {len(complexity_issues)} 个复杂度问题")
                    for issue in complexity_issues[:3]:  # 显示前3个
                        print(f"  - {issue}")
            else:
                quality_results[check_name] = {"success": success}

            if not success:
                overall_success = False

        self.results["code_quality"] = quality_results
        return overall_success

    def parse_complexity_output(self, output: str) -> List[str]:
        """解析代码复杂度输出"""
        issues = []
        try:
            lines = output.strip().split("\n")
            for line in lines:
                # 查找复杂度超过阈值的行
                if any(char in line for char in ["B", "C"]) and "src/" in line:
                    # 简单解析，实际可能需要更复杂的逻辑
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            complexity = int(parts[-2])
                            if (
                                complexity
                                > self.quality_standards["code_quality"][
                                    "max_complexity"
                                ]
                            ):
                                issues.append(f"{line.strip()} (复杂度: {complexity})")
                        except ValueError:
                            continue
        except Exception:
            pass
        return issues

    def check_security(self) -> bool:
        """检查安全性"""
        cmd = ["bandit", "-r", "src/", "-f", "json", "-o", "bandit-report.json"]

        success, result = self.run_command(cmd, "安全检查", timeout=90)

        if success:
            security_data = self.parse_security_report()

            critical = security_data.get("critical", 0)
            high = security_data.get("high", 0)
            medium = security_data.get("medium", 0)

            standards = self.quality_standards["security"]
            security_success = (
                critical == 0
                and high <= standards["max_high_vulnerabilities"]
                and medium <= standards["max_medium_vulnerabilities"]
            )

            self.results["security"] = {
                "success": security_success,
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": security_data.get("low", 0),
            }

            print(f"🔒 安全扫描: {critical} 严重, {high} 高危, {medium} 中危")

            if not security_success:
                print(f"❌ 安全检查未通过标准")
                self.passed = False

            return security_success
        else:
            self.results["security"] = {"success": False, "error": result.get("stderr")}
            self.passed = False
            return False

    def parse_security_report(self) -> Dict[str, int]:
        """解析安全报告"""
        try:
            report_file = self.base_dir / "bandit-report.json"
            if report_file.exists():
                with open(report_file, "r") as f:
                    data = json.load(f)

                    # 统计各严重程度的漏洞数量
                    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

                    for result in data.get("results", []):
                        severity = result.get("issue_severity", "unknown").lower()
                        if severity in severity_counts:
                            severity_counts[severity] += 1

                    return severity_counts
        except Exception:
            pass

        return {"critical": 0, "high": 0, "medium": 0, "low": 0}

    def check_dependencies(self) -> bool:
        """检查依赖安全性"""
        cmd = ["safety", "check", "--json", "--output", "safety-report.json"]

        success, result = self.run_command(cmd, "依赖安全检查", timeout=60)

        # Safety检查失败通常表示有漏洞
        dependency_issues = not success

        self.results["dependencies"] = {
            "success": not dependency_issues,
            "vulnerabilities": dependency_issues,
        }

        if dependency_issues:
            print("⚠️ 发现依赖漏洞")
        else:
            print("✅ 依赖安全性检查通过")

        return not dependency_issues

    def generate_quality_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        total_duration = time.time() - self.start_time

        report = {
            "timestamp": time.time(),
            "duration": total_duration,
            "passed": self.passed,
            "strict_mode": self.strict_mode,
            "standards": self.quality_standards,
            "results": self.results,
            "summary": {
                "total_checks": len(self.results),
                "passed_checks": len(
                    [r for r in self.results.values() if r.get("success", False)]
                ),
                "failed_checks": len(
                    [r for r in self.results.values() if not r.get("success", False)]
                ),
            },
        }

        # 保存报告
        report_file = self.base_dir / "quality-gate-report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        return report

    def print_summary(self, report: Dict[str, Any]):
        """打印质量检查摘要"""
        print(f"\n{'='*60}")
        print(f"📊 质量门禁检查报告")
        print(f"{'='*60}")

        status = "✅ 通过" if report["passed"] else "❌ 失败"
        print(f"总体状态: {status}")
        print(f"检查模式: {'严格模式' if self.strict_mode else '标准模式'}")
        print(f"总耗时: {report['duration']:.2f}秒")

        summary = report["summary"]
        print(f"检查项目: {summary['total_checks']}")
        print(f"通过项目: {summary['passed_checks']}")
        print(f"失败项目: {summary['failed_checks']}")

        print(f"\n📋 详细结果:")
        for check_name, result in report["results"].items():
            status_icon = "✅" if result.get("success", False) else "❌"
            print(f"  {status_icon} {check_name}")

            # 显示关键指标
            if check_name == "test_coverage" and "coverage" in result:
                print(f"     覆盖率: {result['coverage']:.1f}%")
            elif check_name == "test_execution" and "success_rate" in result:
                print(f"     通过率: {result['success_rate']:.1f}%")
            elif check_name == "security" and "critical" in result:
                print(f"     漏洞: {result['critical']} 严重, {result['high']} 高危")

        if not report["passed"]:
            print(f"\n💡 修复建议:")
            self.generate_fix_suggestions(report)

        print(f"\n📄 详细报告已保存到: quality-gate-report.json")

    def generate_fix_suggestions(self, report: Dict[str, Any]):
        """生成修复建议"""
        suggestions = []

        for check_name, result in report["results"].items():
            if not result.get("success", False):
                if check_name == "test_coverage":
                    suggestions.append("  🧪 增加测试用例以提高代码覆盖率")
                elif check_name == "test_execution":
                    suggestions.append("  🐛 修复失败的测试用例")
                elif check_name == "code_quality":
                    suggestions.append(
                        "  📝 运行 'black src/ scripts/ tests/' 修复格式问题"
                    )
                    suggestions.append("  🔧 运行 'flake8 src/' 修复代码风格问题")
                elif check_name == "security":
                    suggestions.append("  🔒 修复安全漏洞，查看 bandit-report.json")
                elif check_name == "dependencies":
                    suggestions.append("  📦 更新依赖包版本，查看 safety-report.json")

        for suggestion in suggestions:
            print(suggestion)

    def run_all_checks(self) -> bool:
        """运行所有质量检查"""
        print(f"🚀 开始质量门禁检查 ({'严格模式' if self.strict_mode else '标准模式'})")

        # 运行各项检查
        self.check_test_coverage()
        self.check_test_execution()
        self.check_code_quality()
        self.check_security()
        self.check_dependencies()

        # 生成报告
        report = self.generate_quality_report()

        # 打印摘要
        self.print_summary(report)

        return self.passed


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="质量门禁检查")
    parser.add_argument("--strict", action="store_true", help="启用严格模式")
    parser.add_argument("--coverage-only", action="store_true", help="仅检查覆盖率")
    parser.add_argument("--security-only", action="store_true", help="仅检查安全性")

    args = parser.parse_args()

    gate = QualityGate(strict_mode=args.strict)

    try:
        if args.coverage_only:
            success = gate.check_test_coverage()
        elif args.security_only:
            security_success = gate.check_security()
            dependency_success = gate.check_dependencies()
            success = security_success and dependency_success
        else:
            success = gate.run_all_checks()

        return 0 if success else 1

    except KeyboardInterrupt:
        print(f"\n⏹️ 质量检查被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 质量检查过程中出现错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
