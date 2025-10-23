#!/usr/bin/env python3
"""
CI/CD质量检查脚本
CI/CD Quality Check Script

用于持续集成环境的自动化质量检查，集成覆盖率监控和质量门禁
"""

import os
import sys
import json
import subprocess
import datetime
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CIQualityChecker:
    """CI/CD质量检查器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.results = {}
        self.start_time = datetime.datetime.now()

        # CI环境检测
        self.is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
        self.is_pr = os.getenv('GITHUB_EVENT_NAME') == 'pull_request'

        # 质量标准
        self.quality_gates = {
    "coverage": {
        "minimum": 20.58958038661009,
        "target": 27.58958038661009,
        "excellent": 37.589580386610095,
        "critical_files": {
            "src/api/schemas.py": 95.0,
            "src/core/exceptions.py": 90.0,
            "src/models/": 60.0
        }
    },
    "tests": {
        "min_pass_rate": 85.0,
        "max_failures": 5,
        "min_total": 100
    },
    "code_quality": {
        "max_ruff_errors": 10,
        "max_mypy_errors": 10,
        "format_required": True
    },
    "security": {
        "max_vulnerabilities": 2,
        "max_secrets": 3
    }
}

    def log_info(self, message: str):
        """信息日志"""
        prefix = "🔧 [CI]" if self.is_ci else "🔧 [LOCAL]"
        logger.info(f"{prefix} {message}")

    def log_error(self, message: str):
        """错误日志"""
        prefix = "❌ [CI]" if self.is_ci else "❌ [LOCAL]"
        logger.error(f"{prefix} {message}")

    def log_success(self, message: str):
        """成功日志"""
        prefix = "✅ [CI]" if self.is_ci else "✅ [LOCAL]"
        logger.info(f"{prefix} {message}")

    def run_command(self, command: List[str], description: str = "", timeout: int = 300) -> Dict[str, Any]:
        """运行命令并返回结果"""
        if description:
            self.log_info(f"执行: {description}")

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            self.log_error(f"命令超时: {' '.join(command)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": "命令执行超时",
                "returncode": -1
            }
        except Exception as e:
            self.log_error(f"命令执行失败: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def check_test_coverage(self) -> Dict[str, Any]:
        """检查测试覆盖率"""
        self.log_info("检查测试覆盖率...")

        # 运行覆盖率测试
        result = self.run_command([
            sys.executable, "-m", "pytest",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--tb=short",
            "-q"
        ], "覆盖率测试", timeout=600)

        if not result["success"]:
            return {
                "passed": False,
                "overall_coverage": 0.0,
                "error": "覆盖率测试执行失败",
                "details": result["stderr"]
            }

        # 读取覆盖率报告
        coverage_file = self.project_root / "coverage.json"
        if not coverage_file.exists():
            return {
                "passed": False,
                "overall_coverage": 0.0,
                "error": "覆盖率报告文件未生成"
            }

        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)

            overall_coverage = coverage_data["totals"]["percent_covered"]
            files_coverage = coverage_data.get("files", {})

            # 检查质量门禁
            gates = self.quality_gates["coverage"]
            errors = []
            warnings = []

            # 总体覆盖率检查
            if overall_coverage < gates["minimum"]:
                errors.append(
                    f"总体覆盖率 {overall_coverage:.1f}% 低于最小要求 {gates['minimum']:.1f}%"
                )
            elif overall_coverage < gates["target"]:
                warnings.append(
                    f"总体覆盖率 {overall_coverage:.1f}% 低于目标 {gates['target']:.1f}%"
                )

            # 关键文件检查
            critical_issues = []
            for pattern, required_coverage in gates["critical_files"].items():
                for file_path in files_coverage:
                    if pattern in file_path or (pattern.endswith('/') and file_path.startswith(pattern)):
                        file_coverage = files_coverage[file_path]["summary"]["percent_covered"]
                        if file_coverage < required_coverage:
                            critical_issues.append(
                                f"关键文件 {file_path} 覆盖率 {file_coverage:.1f}% 低于要求 {required_coverage:.1f}%"
                            )

            if critical_issues:
                errors.extend(critical_issues)

            # 生成覆盖率报告
            try:
                self._generate_coverage_report(coverage_data, overall_coverage)
            except Exception as e:
                self.log_error(f"生成覆盖率报告失败: {e}")

            return {
                "passed": len(errors) == 0,
                "overall_coverage": overall_coverage,
                "files_count": len(files_coverage),
                "errors": errors,
                "warnings": warnings,
                "critical_issues": critical_issues,
                "details": f"总体覆盖率: {overall_coverage:.1f}%, 文件数: {len(files_coverage)}"
            }

        except Exception as e:
            return {
                "passed": False,
                "overall_coverage": 0.0,
                "error": f"解析覆盖率报告失败: {e}"
            }

    def _generate_coverage_report(self, coverage_data: Dict, overall_coverage: float):
        """生成覆盖率报告"""
        try:
            # 保存详细的覆盖率数据
            report_dir = self.project_root / "coverage-reports"
            report_dir.mkdir(exist_ok=True)

            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")

            # 详细报告
            detailed_report = {
                "timestamp": self.start_time.isoformat(),
                "overall_coverage": overall_coverage,
                "totals": coverage_data["totals"],
                "files": coverage_data.get("files", {}),
                "quality_gate": self.quality_gates["coverage"]
            }

            report_file = report_dir / f"coverage_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(detailed_report, f, indent=2)

            # 更新最新报告链接
            latest_file = report_dir / "latest_coverage_report.json"
            with open(latest_file, 'w') as f:
                json.dump(detailed_report, f, indent=2)

            self.log_success(f"覆盖率报告已生成: {report_file}")

        except Exception as e:
            self.log_error(f"生成覆盖率报告失败: {e}")

    def check_test_execution(self) -> Dict[str, Any]:
        """检查测试执行情况"""
        self.log_info("检查测试执行情况...")

        result = self.run_command([
            sys.executable, "-m", "pytest",
            "--tb=no",
            "-q",
            "--maxfail=20"  # 最多失败20个测试后停止
        ], "测试执行", timeout=600)

        # 解析pytest输出
        output = result["stdout"] + result["stderr"]
        return self._parse_test_results(output)

    def _parse_test_results(self, output: str) -> Dict[str, Any]:
        """解析测试结果"""
        import re

        # 查找测试结果总结
        patterns = [
            r'= (\d+) passed.*?(\d+) failed.*?(\d+) skipped.*?(\d+) deselected',
            r'= (\d+) passed.*?(\d+) failed.*?(\d+) skipped',
            r'= (\d+) passed.*?(\d+) failed',
            r'= (\d+) passed.*?in .*',
            r'(\d+) passed.*?(\d+) failed'
        ]

        total_tests = failed_tests = passed_tests = skipped_tests = 0

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                groups = match.groups()
                if len(groups) >= 4:
                    passed_tests = int(groups[0])
                    failed_tests = int(groups[1])
                    skipped_tests = int(groups[2])
                    total_tests = passed_tests + failed_tests + skipped_tests
                elif len(groups) >= 3:
                    passed_tests = int(groups[0])
                    failed_tests = int(groups[1])
                    skipped_tests = int(groups[2])
                    total_tests = passed_tests + failed_tests + skipped_tests
                elif len(groups) >= 2:
                    passed_tests = int(groups[0])
                    failed_tests = int(groups[1])
                    total_tests = passed_tests + failed_tests
                else:
                    passed_tests = int(groups[0])
                    total_tests = passed_tests
                break

        if total_tests == 0:
            return {
                "passed": False,
                "error": "无法解析测试结果",
                "details": output[:500]  # 前500字符
            }

        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # 检查质量门禁
        gates = self.quality_gates["tests"]
        errors = []
        warnings = []

        if pass_rate < gates["min_pass_rate"]:
            errors.append(
                f"测试通过率 {pass_rate:.1f}% 低于要求 {gates['min_pass_rate']:.1f}%"
            )

        if failed_tests > gates["max_failures"]:
            errors.append(
                f"失败测试数 {failed_tests} 超过限制 {gates['max_failures']}"
            )

        if total_tests < gates["min_total"]:
            warnings.append(
                f"测试总数 {total_tests} 少于建议值 {gates['min_total']}"
            )

        return {
            "passed": len(errors) == 0,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "pass_rate": pass_rate,
            "errors": errors,
            "warnings": warnings,
            "details": f"测试: {passed_tests}/{total_tests} 通过 ({pass_rate:.1f}%), 失败: {failed_tests}"
        }

    def check_code_quality(self) -> Dict[str, Any]:
        """检查代码质量"""
        self.log_info("检查代码质量...")

        results = {
            "ruff": {"passed": True, "errors": 0, "details": ""},
            "mypy": {"passed": True, "errors": 0, "details": ""}
        }

        # Ruff检查
        ruff_result = self.run_command([
            "ruff", "check", "src/",
            "--output-format=text"
        ], "Ruff代码检查")

        results["ruff"]["success"] = ruff_result["success"]
        results["ruff"]["details"] = ruff_result["stdout"] + ruff_result["stderr"]
        results["ruff"]["errors"] = len([line for line in ruff_result["stdout"].split('\n') if line.strip()])

        # MyPy检查
        mypy_result = self.run_command([
            "mypy", "src/"
        ], "MyPy类型检查")

        results["mypy"]["success"] = mypy_result["success"]
        results["mypy"]["details"] = mypy_result["stdout"] + mypy_result["stderr"]
        results["mypy"]["errors"] = len([line for line in mypy_result["stdout"].split('\n') if 'error:' in line])

        # 格式检查
        format_result = self.run_command([
            "ruff", "format", "--check", "src/"
        ], "代码格式检查")

        # 质量门禁检查
        gates = self.quality_gates["code_quality"]
        errors = []

        if results["ruff"]["errors"] > gates["max_ruff_errors"]:
            errors.append(
                f"Ruff错误数 {results['ruff']['errors']} 超过限制 {gates['max_ruff_errors']}"
            )

        if results["mypy"]["errors"] > gates["max_mypy_errors"]:
            errors.append(
                f"MyPy错误数 {results['mypy']['errors']} 超过限制 {gates['max_mypy_errors']}"
            )

        if gates["format_required"] and not format_result["success"]:
            errors.append("代码格式检查未通过，请运行 'ruff format src/'")

        total_errors = results["ruff"]["errors"] + results["mypy"]["errors"]

        return {
            "passed": len(errors) == 0,
            "total_errors": total_errors,
            "checks": results,
            "format_check": format_result["success"],
            "errors": errors,
            "details": f"代码质量: Ruff({results['ruff']['errors']}), MyPy({results['mypy']['errors']}), 格式化({'通过' if format_result['success'] else '失败'})"
        }

    def check_security(self) -> Dict[str, Any]:
        """检查安全性"""
        self.log_info("检查安全性...")

        results = {
            "vulnerabilities": {"passed": True, "count": 0, "details": ""},
            "secrets": {"passed": True, "count": 0, "details": ""}
        }

        # 依赖漏洞检查
        vuln_result = self.run_command([
            "pip-audit", "--requirement", "requirements/requirements.lock", "--format=json"
        ], "依赖漏洞检查", timeout=120)

        if vuln_result["success"]:
            try:
                audit_data = json.loads(vuln_result["stdout"])
                vuln_count = len(audit_data.get("vulnerabilities", []))
                results["vulnerabilities"]["count"] = vuln_count
                results["vulnerabilities"]["passed"] = vuln_count == 0
                results["vulnerabilities"]["details"] = f"发现 {vuln_count} 个依赖漏洞"
            except json.JSONDecodeError:
                results["vulnerabilities"]["details"] = "解析漏洞报告失败"
        else:
            results["vulnerabilities"]["details"] = "漏洞检查工具未安装或执行失败"

        # 密钥检查（简化版）
        secrets_result = self.run_command([
            "grep", "-r", "-i", "--include=*.py",
            "-e", "password.*=.*['\"][^'\"]+['\"]",
            "-e", "secret.*=.*['\"][^'\"]+['\"]",
            "-e", "api_key.*=.*['\"][^'\"]+['\"]",
            "src/"
        ], "硬编码密钥检查", timeout=60)

        # grep找到匹配时会返回非零退出码，这是正常的
        secret_matches = secrets_result["stdout"].strip().split('\n') if secrets_result["stdout"].strip() else []
        # 过滤掉测试文件和示例
        real_secrets = [match for match in secret_matches if '/test_' not in match and 'example' not in match.lower()]
        secret_count = len(real_secrets)

        results["secrets"]["count"] = secret_count
        results["secrets"]["passed"] = secret_count <= 3  # 允许少量配置用的密钥
        results["secrets"]["details"] = f"发现 {secret_count} 个可能的硬编码密钥"

        # 质量门禁检查
        gates = self.quality_gates["security"]
        errors = []

        if results["vulnerabilities"]["count"] > gates["max_vulnerabilities"]:
            errors.append(
                f"依赖漏洞数 {results['vulnerabilities']['count']} 超过限制 {gates['max_vulnerabilities']}"
            )

        if results["secrets"]["count"] > gates["max_secrets"]:
            errors.append(
                f"硬编码密钥数 {results['secrets']['count']} 超过限制 {gates['max_secrets']}"
            )

        total_issues = results["vulnerabilities"]["count"] + results["secrets"]["count"]

        return {
            "passed": len(errors) == 0,
            "total_issues": total_issues,
            "checks": results,
            "errors": errors,
            "details": f"安全检查: 漏洞({results['vulnerabilities']['count']}), 密钥({results['secrets']['count']})"
        }

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有质量检查"""
        self.log_info("开始CI/CD质量检查...")

        checks = {
            "coverage": self.check_test_coverage,
            "tests": self.check_test_execution,
            "code_quality": self.check_code_quality,
            "security": self.check_security
        }

        results = {}
        failed_checks = []
        all_warnings = []

        # 执行各项检查
        for check_name, check_func in checks.items():
            try:
                result = check_func()
                results[check_name] = result

                if not result["passed"]:
                    failed_checks.append(check_name)
                    if "errors" in result:
                        all_warnings.extend(result["errors"])
                elif "warnings" in result:
                    all_warnings.extend(result["warnings"])

            except Exception as e:
                self.log_error(f"检查 {check_name} 执行失败: {e}")
                results[check_name] = {
                    "passed": False,
                    "error": f"检查执行失败: {e}",
                    "details": str(e)
                }
                failed_checks.append(check_name)

        # 计算总体结果
        duration = (datetime.datetime.now() - self.start_time).total_seconds()

        overall_result = {
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": duration,
            "environment": "CI" if self.is_ci else "LOCAL",
            "is_pr": self.is_pr,
            "overall_passed": len(failed_checks) == 0,
            "failed_checks": failed_checks,
            "warnings": all_warnings,
            "checks": results,
            "summary": self._generate_summary(results)
        }

        # 保存结果
        self._save_ci_results(overall_result)

        return overall_result

    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """生成检查摘要"""
        summary = {
            "coverage": "N/A",
            "tests": "N/A",
            "code_quality": "N/A",
            "security": "N/A"
        }

        if "coverage" in results and results["coverage"].get("overall_coverage"):
            summary["coverage"] = f"{results['coverage']['overall_coverage']:.1f}%"

        if "tests" in results and results["tests"].get("pass_rate"):
            summary["tests"] = f"{results['tests']['pass_rate']:.1f}%"

        if "code_quality" in results:
            total_errors = results["code_quality"].get("total_errors", 0)
            summary["code_quality"] = f"{total_errors} 错误"

        if "security" in results:
            total_issues = results["security"].get("total_issues", 0)
            summary["security"] = f"{total_issues} 问题"

        return summary

    def _save_ci_results(self, results: Dict):
        """保存CI检查结果"""
        try:
            # 创建报告目录
            report_dir = self.project_root / "ci-reports"
            report_dir.mkdir(exist_ok=True)

            # 保存详细结果
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            result_file = report_dir / f"ci_results_{timestamp}.json"

            with open(result_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            # 更新最新结果
            latest_file = report_dir / "latest_ci_results.json"
            with open(latest_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            self.log_success(f"CI检查结果已保存: {result_file}")

        except Exception as e:
            self.log_error(f"保存CI结果失败: {e}")

    def print_ci_report(self, results: Dict):
        """打印CI报告"""
        print("\n" + "=" * 70)
        print("🚀 CI/CD 质量检查报告")
        print("=" * 70)
        print(f"检查时间: {results['timestamp']}")
        print(f"检查环境: {results['environment']}")
        print(f"检查耗时: {results['duration_seconds']:.2f}秒")
        if results['is_pr']:
            print("Pull Request: 是")
        print()

        # 总体状态
        if results["overall_passed"]:
            print("✅ 总体状态: 通过")
        else:
            print("❌ 总体状态: 失败")
            print(f"   失败的检查: {', '.join(results['failed_checks'])}")

        print()

        # 摘要信息
        print("📊 检查摘要:")
        for category, value in results["summary"].items():
            status = "✅" if category not in results["failed_checks"] else "❌"
            print(f"  {category:15} {value:10} {status}")
        print()

        # 详细结果
        for check_name, check_result in results["checks"].items():
            status = "✅ 通过" if check_result["passed"] else "❌ 失败"
            print(f"{check_name.upper():20} {status}")
            if "details" in check_result:
                print(f"{'':20} {check_result['details']}")

            if "errors" in check_result and check_result["errors"]:
                for error in check_result["errors"]:
                    print(f"{'':20} ❌ {error}")

            if "warnings" in check_result and check_result["warnings"]:
                for warning in check_result["warnings"]:
                    print(f"{'':20} ⚠️  {warning}")

            print()

        # 结论
        if results["overall_passed"]:
            print("🎉 CI/CD质量检查通过！代码可以合并。")
        else:
            print("🚫 CI/CD质量检查失败！请修复问题后重试。")

        print("=" * 70)

    def exit_with_status(self, results: Dict):
        """根据检查结果退出"""
        if results["overall_passed"]:
            sys.exit(0)
        else:
            sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CI/CD质量检查系统")
    parser.add_argument("--coverage-only", action="store_true", help="仅检查覆盖率")
    parser.add_argument("--tests-only", action="store_true", help="仅检查测试")
    parser.add_argument("--quality-only", action="store_true", help="仅检查代码质量")
    parser.add_argument("--security-only", action="store_true", help="仅检查安全性")
    parser.add_argument("--no-exit", action="store_true", help="不根据结果退出程序")
    parser.add_argument("--project-root", type=Path, help="项目根目录")

    args = parser.parse_args()

    checker = CIQualityChecker(args.project_root)

    try:
        if args.coverage_only:
            results = {"checks": {"coverage": checker.check_test_coverage()}}
        elif args.tests_only:
            results = {"checks": {"tests": checker.check_test_execution()}}
        elif args.quality_only:
            results = {"checks": {"code_quality": checker.check_code_quality()}}
        elif args.security_only:
            results = {"checks": {"security": checker.check_security()}}
        else:
            results = checker.run_all_checks()

        # 打印报告
        checker.print_ci_report(results)

        # 退出
        if not args.no_exit:
            checker.exit_with_status(results)

    except KeyboardInterrupt:
        logger.info("检查被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"检查过程中发生未预期的错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()