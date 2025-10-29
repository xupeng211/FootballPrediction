#!/usr/bin/env python3
"""
自动化质量门禁系统
基于Issue #98智能质量修复方法论和Issue #94覆盖率提升实践

集成Issue #98建立的智能修复工具链：
- 智能语法修复
- 质量检查自动化
- 覆盖率监控
- 持续改进建议

为Issue #89 CI/CD优化提供核心自动化支持
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AutomatedQualityGate:
    """自动化质量门禁系统 - 基于Issue #98方法论"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.reports_dir = self.project_root / "quality-reports"
        self.ci_reports_dir = self.project_root / "ci-reports"

        # 确保目录存在
        self.reports_dir.mkdir(exist_ok=True)
        self.ci_reports_dir.mkdir(exist_ok=True)

        # 质量标准 - 基于Issue #98实践
        self.quality_standards = {
            "min_coverage": 10.0,  # 当前基线，逐步提升到80%
            "max_syntax_errors": 50,
            "max_import_errors": 100,
            "min_test_pass_rate": 85.0,
            "max_ruff_errors": 20,
            "max_mypy_errors": 15,
        }

        # 检查结果
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks_performed": [],
            "overall_status": "pending",
            "summary": {},
            "recommendations": [],
            "gate_status": "unknown",
        }

    def run_syntax_check(self) -> Dict[str, Any]:
        """运行语法检查 - 基于Issue #98语法修复方法论"""
        logger.info("🔧 执行语法检查...")

        # 基于Issue #98的智能语法修复
        syntax_check_cmd = ["python3", "scripts/smart_quality_fixer.py", "--syntax-only"]

        try:
            result = subprocess.run(
                syntax_check_cmd, cwd=self.project_root, capture_output=True, text=True, timeout=300
            )

            syntax_result = {
                "check_name": "syntax_check",
                "status": "pass" if result.returncode == 0 else "fail",
                "errors_fixed": 0,  # 从输出中解析
                "details": result.stdout,
                "recommendations": [],
            }

            # 解析修复结果
            if "修复语法错误:" in result.stdout:
                try:
                    fixed_count = int(
                        result.stdout.split("修复语法错误:")[1].split("个")[0].strip()
                    )
                    syntax_result["errors_fixed"] = fixed_count
                except:
                    pass

            # 生成建议
            if syntax_result["status"] == "fail":
                syntax_result["recommendations"].append("运行语法修复工具解决语法问题")
            elif syntax_result["errors_fixed"] > 0:
                syntax_result["recommendations"].append(
                    f"成功修复{syntax_result['errors_fixed']}个语法错误"
                )

            logger.info(f"✅ 语法检查完成: {syntax_result['status']}")
            return syntax_result

        except subprocess.TimeoutExpired:
            logger.error("❌ 语法检查超时")
            return {
                "check_name": "syntax_check",
                "status": "timeout",
                "errors_fixed": 0,
                "details": "检查超时",
                "recommendations": ["检查是否有无限循环或复杂语法问题"],
            }
        except Exception as e:
            logger.error(f"❌ 语法检查失败: {e}")
            return {
                "check_name": "syntax_check",
                "status": "error",
                "errors_fixed": 0,
                "details": str(e),
                "recommendations": ["检查语法检查工具是否正常工作"],
            }

    def run_quality_check(self) -> Dict[str, Any]:
        """运行质量检查 - 基于Issue #98质量守护系统"""
        logger.info("🛡️ 执行质量检查...")

        # 基于Issue #98的质量守护工具
        quality_check_cmd = ["python3", "scripts/quality_guardian.py", "--check-only"]

        try:
            result = subprocess.run(
                quality_check_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时
            )

            quality_result = {
                "check_name": "quality_check",
                "status": "pass" if result.returncode == 0 else "fail",
                "details": result.stdout,
                "metrics": {},
                "recommendations": [],
            }

            # 解析质量指标
            if "综合质量分数:" in result.stdout:
                try:
                    score_line = [
                        line for line in result.stdout.split("\n") if "综合质量分数:" in line
                    ][0]
                    score = float(score_line.split("综合质量分数:")[1].split("/")[0].strip())
                    quality_result["metrics"]["overall_score"] = score
                except:
                    pass

            if "测试覆盖率:" in result.stdout:
                try:
                    coverage_line = [
                        line for line in result.stdout.split("\n") if "测试覆盖率:" in line
                    ][0]
                    coverage = float(coverage_line.split("测试覆盖率:")[1].split("%")[0].strip())
                    quality_result["metrics"]["coverage"] = coverage
                except:
                    pass

            # 生成建议
            if (
                quality_result["metrics"].get("coverage", 0)
                < self.quality_standards["min_coverage"]
            ):
                quality_result["recommendations"].append(
                    f"覆盖率{quality_result['metrics']['coverage']:.1f}%低于标准{self.quality_standards['min_coverage']}%"
                )

            if quality_result["metrics"].get("overall_score", 0) < 6.0:
                quality_result["recommendations"].append("整体质量分数偏低，建议优先解决关键问题")

            logger.info(f"✅ 质量检查完成: {quality_result['status']}")
            return quality_result

        except subprocess.TimeoutExpired:
            logger.error("❌ 质量检查超时")
            return {
                "check_name": "quality_check",
                "status": "timeout",
                "details": "检查超时",
                "metrics": {},
                "recommendations": ["检查项目复杂度或优化检查逻辑"],
            }
        except Exception as e:
            logger.error(f"❌ 质量检查失败: {e}")
            return {
                "check_name": "quality_check",
                "status": "error",
                "details": str(e),
                "metrics": {},
                "recommendations": ["检查质量守护工具是否正常工作"],
            }

    def run_test_coverage_check(self) -> Dict[str, Any]:
        """运行测试覆盖率检查 - 支持Issue #94覆盖率提升计划"""
        logger.info("📊 执行测试覆盖率检查...")

        try:
            # 运行快速测试和覆盖率检查
            test_cmd = [
                "python",
                "-m",
                "pytest",
                "tests/unit/utils/",  # 重点检查utils模块
                "--cov=src/utils",
                "--cov-report=term-missing",
                "--cov-report=json:htmlcov/coverage.json",
                "--tb=short",
                "-x",  # 遇到第一个失败就停止
                "--maxfail=10",
            ]

            result = subprocess.run(
                test_cmd, cwd=self.project_root, capture_output=True, text=True, timeout=600
            )

            coverage_result = {
                "check_name": "test_coverage",
                "status": "pass" if result.returncode == 0 else "fail",
                "details": result.stdout,
                "metrics": {},
                "recommendations": [],
            }

            # 尝试读取覆盖率报告
            coverage_file = self.project_root / "htmlcov" / "coverage.json"
            if coverage_file.exists():
                try:
                    with open(coverage_file, "r") as f:
                        coverage_data = json.load(f)
                        coverage_result["metrics"]["coverage_percent"] = coverage_data.get(
                            "totals", {}
                        ).get("percent_covered", 0)
                        coverage_result["metrics"]["lines_covered"] = coverage_data.get(
                            "totals", {}
                        ).get("covered_lines", 0)
                        coverage_result["metrics"]["lines_missing"] = coverage_data.get(
                            "totals", {}
                        ).get("missing_lines", 0)
                except Exception as e:
                    logger.warning(f"无法解析覆盖率报告: {e}")

            # 从输出中解析测试结果
            if "passed" in result.stdout and "failed" in result.stdout:
                try:
                    summary_lines = [
                        line
                        for line in result.stdout.split("\n")
                        if "passed" in line and "failed" in line
                    ]
                    if summary_lines:
                        summary_line = summary_lines[0]
                        # 解析类似 "20 passed, 1 failed" 的格式
                        if "passed" in summary_line:
                            passed = int(summary_line.split("passed")[0].strip().split()[-1])
                            coverage_result["metrics"]["tests_passed"] = passed
                        if "failed" in summary_line:
                            failed_part = summary_line.split("failed")[0].strip()
                            failed = int(failed_part.split()[-1])
                            coverage_result["metrics"]["tests_failed"] = failed
                except:
                    pass

            # 生成建议
            coverage_percent = coverage_result["metrics"].get("coverage_percent", 0)
            if coverage_percent < self.quality_standards["min_coverage"]:
                coverage_result["recommendations"].append(
                    f"覆盖率{coverage_percent:.1f}%低于目标{self.quality_standards['min_coverage']}%，继续执行Issue #94计划"
                )
            else:
                coverage_result["recommendations"].append(
                    f"覆盖率{coverage_percent:.1f}%达到当前标准，继续向80%目标迈进"
                )

            logger.info(f"✅ 覆盖率检查完成: {coverage_percent:.1f}%")
            return coverage_result

        except subprocess.TimeoutExpired:
            logger.error("❌ 覆盖率检查超时")
            return {
                "check_name": "test_coverage",
                "status": "timeout",
                "details": "检查超时",
                "metrics": {},
                "recommendations": ["优化测试执行效率或增加超时时间"],
            }
        except Exception as e:
            logger.error(f"❌ 覆盖率检查失败: {e}")
            return {
                "check_name": "test_coverage",
                "status": "error",
                "details": str(e),
                "metrics": {},
                "recommendations": ["检查测试环境和依赖"],
            }

    def evaluate_gate_status(self, results: List[Dict[str, Any]]) -> str:
        """评估质量门禁状态"""
        logger.info("🎯 评估质量门禁状态...")

        failed_checks = [r for r in results if r.get("status") == "fail"]
        error_checks = [r for r in results if r.get("status") == "error"]
        timeout_checks = [r for r in results if r.get("status") == "timeout"]

        if error_checks:
            return "error"
        elif timeout_checks:
            return "timeout"
        elif failed_checks:
            # 检查是否是可接受的失败
            critical_failures = [r for r in failed_checks if r["check_name"] in ["syntax_check"]]
            if critical_failures:
                return "fail"
            else:
                return "warning"
        else:
            return "pass"

    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成质量报告"""
        logger.info("📋 生成质量报告...")

        # 统计检查结果
        passed_checks = len([r for r in results if r.get("status") == "pass"])
        failed_checks = len([r for r in results if r.get("status") == "fail"])
        error_checks = len([r for r in results if r.get("status") == "error"])
        timeout_checks = len([r for r in results if r.get("status") == "timeout"])

        # 收集所有建议
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.get("recommendations", []))

        # 汇总关键指标
        metrics = {}
        for result in results:
            if "metrics" in result:
                metrics.update(result["metrics"])

        report = {
            "timestamp": datetime.now().isoformat(),
            "gate_status": self.evaluate_gate_status(results),
            "summary": {
                "total_checks": len(results),
                "passed": passed_checks,
                "failed": failed_checks,
                "errors": error_checks,
                "timeouts": timeout_checks,
            },
            "metrics": metrics,
            "checks": results,
            "recommendations": list(set(all_recommendations)),  # 去重
            "next_steps": self._generate_next_steps(results),
            "integration_notes": {
                "issue_94_support": "支持Issue #94覆盖率提升计划",
                "issue_98_methodology": "基于Issue #98智能质量修复方法论",
                "issue_89_objective": "为Issue #89 CI/CD优化提供自动化支持",
            },
        }

        return report

    def _generate_next_steps(self, results: List[Dict[str, Any]]) -> List[str]:
        """生成下一步行动建议"""
        next_steps = []

        # 基于检查结果生成建议
        for result in results:
            if result.get("status") == "fail":
                if result["check_name"] == "syntax_check":
                    next_steps.append("运行完整语法修复: python3 scripts/smart_quality_fixer.py")
                elif result["check_name"] == "quality_check":
                    next_steps.append("执行深度质量分析: python3 scripts/quality_guardian.py")
                elif result["check_name"] == "test_coverage":
                    next_steps.append("继续Issue #94覆盖率提升计划，重点关注utils模块")

        # 基于指标生成建议
        coverage = self._get_metric(results, "coverage_percent")
        if coverage and coverage < 15:
            next_steps.append("优先提升覆盖率到15%+，巩固Issue #94 Day 1成果")

        return next_steps

    def _get_metric(self, results: List[Dict[str, Any]], metric_name: str) -> Optional[float]:
        """从检查结果中获取指标"""
        for result in results:
            if metric_name in result.get("metrics", {}):
                return result["metrics"][metric_name]
        return None

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有质量检查"""
        logger.info("🚀 开始自动化质量门禁检查...")

        # 执行各项检查
        checks = []

        # 1. 语法检查
        checks.append(self.run_syntax_check())

        # 2. 质量检查
        checks.append(self.run_quality_check())

        # 3. 测试覆盖率检查
        checks.append(self.run_test_coverage_check())

        # 生成报告
        report = self.generate_report(checks)

        # 保存报告
        report_file = (
            self.ci_reports_dir
            / f"quality_gate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 质量报告已保存: {report_file}")

        return report

    def print_summary(self, report: Dict[str, Any]):
        """打印检查摘要"""
        print("\n" + "=" * 60)
        print("🎯 自动化质量门禁检查摘要")
        print("=" * 60)

        # 门禁状态
        status_emoji = {"pass": "✅", "warning": "⚠️", "fail": "❌", "error": "🚨", "timeout": "⏰"}

        gate_status = report["gate_status"]
        print(f"门禁状态: {status_emoji.get(gate_status, '❓')} {gate_status.upper()}")

        # 检查摘要
        summary = report["summary"]
        print(f"检查总数: {summary['total_checks']}")
        print(f"通过: {summary['passed']} ✅")
        print(f"失败: {summary['failed']} ❌")
        print(f"错误: {summary['errors']} 🚨")
        print(f"超时: {summary['timeouts']} ⏰")

        # 关键指标
        if report["metrics"]:
            print("\n📊 关键指标:")
            for metric, value in report["metrics"].items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.1f}")
                else:
                    print(f"  {metric}: {value}")

        # 建议
        if report["recommendations"]:
            print("\n💡 主要建议:")
            for rec in report["recommendations"][:5]:  # 只显示前5个
                print(f"  • {rec}")

        # 下一步
        if report["next_steps"]:
            print("\n🚀 下一步行动:")
            for step in report["next_steps"]:
                print(f"  • {step}")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化质量门禁系统")
    parser.add_argument("--project-root", type=Path, help="项目根目录")
    parser.add_argument(
        "--output-format", choices=["json", "text"], default="text", help="输出格式"
    )
    parser.add_argument("--save-report", action="store_true", help="保存详细报告")

    args = parser.parse_args()

    # 创建质量门禁实例
    gate = AutomatedQualityGate(args.project_root)

    try:
        # 运行所有检查
        report = gate.run_all_checks()

        # 输出结果
        if args.output_format == "json":
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            gate.print_summary(report)

        # 设置退出码
        exit_codes = {"pass": 0, "warning": 0, "fail": 1, "error": 2, "timeout": 3}

        sys.exit(exit_codes.get(report["gate_status"], 2))

    except KeyboardInterrupt:
        logger.info("用户中断检查")
        sys.exit(130)
    except Exception as e:
        logger.error(f"质量门禁检查失败: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
