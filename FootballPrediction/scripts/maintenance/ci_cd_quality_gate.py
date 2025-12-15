#!/usr/bin/env python3
"""
CI/CD质量门禁系统
CI/CD Quality Gate System

自动化质量检查和门禁控制，确保只有符合质量标准的代码才能通过CI/CD流水线。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class GateResult(Enum):
    """门禁结果枚举"""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class QualityLevel(Enum):
    """质量等级枚举"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityMetric:
    """质量指标数据结构"""

    name: str
    value: float
    threshold: float
    unit: str
    status: GateResult
    level: QualityLevel
    message: str


@dataclass
class GateReport:
    """门禁报告数据结构"""

    timestamp: str
    overall_result: GateResult
    total_metrics: int
    passed_metrics: int
    failed_metrics: int
    warning_metrics: int
    metrics: list[QualityMetric]
    recommendations: list[str]
    summary: dict[str, Any]


class QualityGate:
    """质量门禁控制器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.timestamp = datetime.now().isoformat()

        # 质量标准配置
        self.quality_thresholds = {
            # 测试覆盖率阈值
            "min_coverage": {
                "critical": 80.0,  # 关键模块覆盖率
                "high": 60.0,  # 高优先级模块覆盖率
                "medium": 40.0,  # 中等优先级模块覆盖率
                "low": 20.0,  # 最低覆盖率要求
            }
            # 测试通过率阈值
            "min_pass_rate": {
                "critical": 100.0,  # 关键测试必须100%通过
                "high": 95.0,  # 高优先级测试通过率
                "medium": 90.0,  # 中等优先级测试通过率
                "low": 80.0,  # 最低通过率要求
            }
            # 代码质量评分
            "min_quality_score": {
                "critical": 90.0,  # 关键模块质量评分
                "high": 80.0,  # 高优先级模块质量评分
                "medium": 70.0,  # 中等优先级模块质量评分
                "low": 60.0,  # 最低质量评分要求
            }
            # 性能基准
            "max_test_execution_time": {
                "critical": 60.0,  # 关键测试最长执行时间(秒)
                "high": 180.0,  # 高优先级测试执行时间
                "medium": 300.0,  # 中等优先级测试执行时间
                "low": 600.0,  # 最长可接受执行时间
            }
            # 安全检查
            "max_security_issues": {
                "critical": 0,  # 关键安全问题必须为0
                "high": 1,  # 高优先级安全问题上限
                "medium": 3,  # 中等优先级安全问题上限
                "low": 5,  # 最多允许的低优先级安全问题
            }
        }

    def run_test_checks(self) -> list[QualityMetric]:
        """运行测试相关检查"""
        metrics = []

        try:
            # 运行pytest并收集覆盖率
            result = subprocess.run(
                ["pytest", "--cov=src", "--cov-report=json", "--tb=short"]
                cwd=self.project_root
                capture_output=True
                text=True
                timeout=600
            )

            # 读取覆盖率报告
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get("totals", {}).get(
                        "percent_covered", 0.0
                    )

                # 覆盖率检查
                coverage_metric = self._evaluate_metric(
                    "test_coverage"
                    total_coverage
                    self.quality_thresholds["min_coverage"]["low"]
                    "%"
                    QualityLevel.MEDIUM
                )
                metrics.append(coverage_metric)

            # 解析pytest输出获取测试结果
            test_output = result.stdout
            # 提取测试统计信息
            lines = test_output.split("\n")
            for line in lines:
                # 解析测试结果行
                parts = line.split()
                passed = failed = errors = 0

                for part in parts:
                    if part.endswith("passed"):
                        passed = int(part.replace("passed", ""))
                    elif part.endswith("failed"):
                        failed = int(part.replace("failed", ""))
                    elif part.endswith("error"):
                        errors = int(part.replace("error", ""))

                total_tests = passed + failed + errors
                pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0.0

                # 测试通过率检查
                pass_rate_metric = self._evaluate_metric(
                    "test_pass_rate"
                    pass_rate
                    self.quality_thresholds["min_pass_rate"]["low"]
                    "%"
                    QualityLevel.HIGH
                )
                metrics.append(pass_rate_metric)

                # 测试执行时间检查
                execution_time = self._extract_execution_time(test_output)
                time_metric = self._evaluate_metric(
                    "test_execution_time"
                    execution_time
                    self.quality_thresholds["max_test_execution_time"]["low"]
                    "s"
                    QualityLevel.MEDIUM
                    reverse=True,  # 时间越短越好
                )
                metrics.append(time_metric)
                break

        except subprocess.TimeoutExpired:
            metrics.append(
                QualityMetric(
                    name="test_execution_timeout"
                    value=999.0
                    threshold=600.0
                    unit="s"
                    status=GateResult.FAIL
                    level=QualityLevel.CRITICAL
                    message="测试执行超时(>10分钟)"
                )
            )
        except Exception as e:
            metrics.append(
                QualityMetric(
                    name="test_check_error"
                    value=0.0
                    threshold=0.0
                    unit=""
                    status=GateResult.FAIL
                    level=QualityLevel.CRITICAL
                    message=f"测试检查失败: {str(e)}"
                )
            )

        return metrics

    def run_code_quality_checks(self) -> list[QualityMetric]:
        """运行代码质量检查"""
        metrics = []

        try:
            # 运行Ruff代码检查
            result = subprocess.run(
                ["ruff", "check", "src/", "--output-format=json"]
                cwd=self.project_root
                capture_output=True
                text=True
            )

            if result.stdout:
                try:
                    ruff_issues = json.loads(result.stdout)
                    issue_count = len(ruff_issues)

                    # 代码问题数量检查
                    issues_metric = self._evaluate_metric(
                        "code_issues"
                        100.0 - issue_count,  # 转换为分数，问题越少越好
                        80.0,  # 期望至少80分(即不超过20个问题)
                        "score"
                        QualityLevel.MEDIUM
                    )
                    metrics.append(issues_metric)

                except json.JSONDecodeError:
                    pass

            # 运行类型检查
            mypy_result = subprocess.run(
                ["mypy", "src/", "--show-error-codes"]
                cwd=self.project_root
                capture_output=True
                text=True
            )

            mypy_errors = mypy_result.stdout.count("error:")
            mypy_metric = self._evaluate_metric(
                "type_errors", 100.0 - mypy_errors, 90.0, "score", QualityLevel.HIGH
            )
            metrics.append(mypy_metric)

        except Exception as e:
            metrics.append(
                QualityMetric(
                    name="code_quality_check_error"
                    value=0.0
                    threshold=0.0
                    unit=""
                    status=GateResult.FAIL
                    level=QualityLevel.CRITICAL
                    message=f"代码质量检查失败: {str(e)}"
                )
            )

        return metrics

    def run_security_checks(self) -> list[QualityMetric]:
        """运行安全检查"""
        metrics = []

        try:
            # 运行bandit安全扫描
            result = subprocess.run(
                ["bandit", "-r", "src/", "-f", "json"]
                cwd=self.project_root
                capture_output=True
                text=True
            )

            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    high_severity_issues = len(
                        [
                            i
                            for i in bandit_data.get("results", [])
                            if i.get("issue_severity") == "HIGH"
                        ]
                    )

                    # 安全问题检查
                    security_metric = self._evaluate_metric(
                        "security_issues"
                        100.0 - high_severity_issues
                        95.0
                        "score"
                        QualityLevel.CRITICAL
                    )
                    metrics.append(security_metric)

                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            # bandit未安装，添加警告
            metrics.append(
                QualityMetric(
                    name="security_check_unavailable"
                    value=0.0
                    threshold=0.0
                    unit=""
                    status=GateResult.WARN
                    level=QualityLevel.MEDIUM
                    message="安全检查工具bandit未安装，请运行: pip install bandit"
                )
            )
        except Exception as e:
            metrics.append(
                QualityMetric(
                    name="security_check_error"
                    value=0.0
                    threshold=0.0
                    unit=""
                    status=GateResult.FAIL
                    level=QualityLevel.CRITICAL
                    message=f"安全检查失败: {str(e)}"
                )
            )

        return metrics

    def _evaluate_metric(
        self
        name: str
        value: float
        threshold: float
        unit: str
        level: QualityLevel
        reverse: bool = False
    ) -> QualityMetric:
        """评估单个质量指标"""
        if reverse:
            # 对于时间等指标，值越小越好
            status = GateResult.PASS if value <= threshold else GateResult.FAIL
        else:
            # 对于覆盖率等指标，值越大越好
            status = GateResult.PASS if value >= threshold else GateResult.FAIL

        if status == GateResult.FAIL:
            if level in [QualityLevel.CRITICAL, QualityLevel.HIGH]:
                message = f"{name} {value}{unit} 低于要求阈值 {threshold}{unit}"
            else:
                status = GateResult.WARN  # 中低优先级失败降级为警告
                message = f"{name} {value}{unit} 低于推荐值 {threshold}{unit}"
        else:
            message = f"{name} {value}{unit} 符合要求"

        return QualityMetric(
            name=name
            value=value
            threshold=threshold
            unit=unit
            status=status
            level=level
            message=message
        )

    def _extract_execution_time(self, test_output: str) -> float:
        """从pytest输出中提取测试执行时间"""
        for line in test_output.split("\n"):
            if "seconds" in line and "=" in line:
                try:
                    time_part = line.split("=")[1].strip()
                    return float(time_part.split()[0])
                except (IndexError, ValueError):
                    continue
        return 0.0

    def evaluate_quality_gate(self) -> GateReport:
        """执行质量门禁评估"""

        all_metrics = []

        # 运行各类质量检查
        test_metrics = self.run_test_checks()
        all_metrics.extend(test_metrics)

        quality_metrics = self.run_code_quality_checks()
        all_metrics.extend(quality_metrics)

        security_metrics = self.run_security_checks()
        all_metrics.extend(security_metrics)

        # 统计结果
        passed = len([m for m in all_metrics if m.status == GateResult.PASS])
        failed = len([m for m in all_metrics if m.status == GateResult.FAIL])
        warning = len([m for m in all_metrics if m.status == GateResult.WARN])

        # 确定总体结果
        critical_failures = [
            m
            for m in all_metrics
            if m.status == GateResult.FAIL and m.level == QualityLevel.CRITICAL
        ]
        overall_result = (
            GateResult.FAIL
            if critical_failures
            else GateResult.WARN
            if failed > 0
            else GateResult.PASS
        )

        # 生成建议
        recommendations = self._generate_recommendations(all_metrics)

        # 生成摘要
        summary = self._generate_summary(all_metrics)

        return GateReport(
            timestamp=self.timestamp
            overall_result=overall_result
            total_metrics=len(all_metrics)
            passed_metrics=passed
            failed_metrics=failed
            warning_metrics=warning
            metrics=all_metrics
            recommendations=recommendations
            summary=summary
        )

    def _generate_recommendations(self, metrics: list[QualityMetric]) -> list[str]:
        """生成改进建议"""
        recommendations = []

        failed_metrics = [m for m in metrics if m.status == GateResult.FAIL]
        warning_metrics = [m for m in metrics if m.status == GateResult.WARN]

        if failed_metrics:
            critical_failures = [
                m for m in failed_metrics if m.level == QualityLevel.CRITICAL
            ]
            if critical_failures:
                recommendations.append("🚨 **关键问题必须修复**:")
                for metric in critical_failures:
                    recommendations.append(f"   - {metric.message}")

            high_failures = [m for m in failed_metrics if m.level == QualityLevel.HIGH]
            if high_failures:
                recommendations.append("⚠️ **高优先级问题**:")
                for metric in high_failures:
                    recommendations.append(f"   - {metric.message}")

        if warning_metrics:
            recommendations.append("💡 **改进建议**:")
            for metric in warning_metrics:
                recommendations.append(f"   - {metric.message}")

        if not failed_metrics and not warning_metrics:
            recommendations.append("🎉 **所有质量检查通过！** 代码质量符合CI/CD要求。")

        return recommendations

    def _generate_summary(self, metrics: list[QualityMetric]) -> dict[str, Any]:
        """生成质量摘要"""
        summary = {
            "health_score": 0.0
            "critical_issues": 0
            "high_issues": 0
            "medium_issues": 0
            "low_issues": 0
            "categories": {
                "testing": {"pass": 0, "fail": 0, "warn": 0}
                "quality": {"pass": 0, "fail": 0, "warn": 0}
                "security": {"pass": 0, "fail": 0, "warn": 0}
            }
        }

        for metric in metrics:
            # 按严重程度统计
            if (
                metric.level == QualityLevel.CRITICAL
                and metric.status == GateResult.FAIL
            ):
                summary["critical_issues"] += 1
            elif metric.level == QualityLevel.HIGH and metric.status == GateResult.FAIL:
                summary["high_issues"] += 1
            elif metric.level == QualityLevel.MEDIUM and metric.status in [
                GateResult.FAIL
                GateResult.WARN
            ]:
                summary["medium_issues"] += 1
            elif metric.level == QualityLevel.LOW and metric.status in [
                GateResult.FAIL
                GateResult.WARN
            ]:
                summary["low_issues"] += 1

            # 按类别统计
            category = (
                "testing"
                if "test" in metric.name
                else "security"
                if "security" in metric.name
                else "quality"
            )
            summary["categories"][category][metric.status.value] += 1

        # 计算健康评分
        total_metrics = len(metrics)
        if total_metrics > 0:
            passed_percentage = (
                len([m for m in metrics if m.status == GateResult.PASS]) / total_metrics
            ) * 100
            warning_penalty = (
                len([m for m in metrics if m.status == GateResult.WARN]) / total_metrics
            ) * 10
            failure_penalty = (
                len([m for m in metrics if m.status == GateResult.FAIL]) / total_metrics
            ) * 30
            summary["health_score"] = max(
                0, passed_percentage - warning_penalty - failure_penalty
            )

        return summary

    def export_report(
        self, report: GateReport, output_file: Path | None = None
    ) -> Path:
        """导出质量门禁报告"""
        if output_file is None:
            output_file = (
                self.project_root
                / "reports"
                / "quality_gate"
                / f"quality_gate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的字典
        report_dict = asdict(report)
        report_dict["overall_result"] = report.overall_result.value
        report_dict["metrics"] = [
            {
                **asdict(metric)
                "status": metric.status.value
                "level": metric.level.value
            }
            for metric in report.metrics
        ]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return output_file


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD质量门禁系统")
    parser.add_argument("--project-root", type=Path, help="项目根目录路径")
    parser.add_argument("--output-file", type=Path, help="报告输出文件路径")
    parser.add_argument(
        "--strict", action="store_true", help="严格模式，任何警告都会导致门禁失败"
    )

    args = parser.parse_args()

    # 创建质量门禁实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    gate = QualityGate(project_root)

    try:
        # 执行质量门禁评估
        report = gate.evaluate_quality_gate()

        # 导出报告
        gate.export_report(report, args.output_file)

        # 显示结果摘要

        # 显示关键问题
        critical_issues = [
            m
            for m in report.metrics
            if m.status == GateResult.FAIL and m.level == QualityLevel.CRITICAL
        ]
        if critical_issues:
            for _metric in critical_issues:
                pass

        # 显示建议
        if report.recommendations:
            for _rec in report.recommendations:
                pass

        # 设置退出码
        if report.overall_result == GateResult.FAIL:
            sys.exit(1)
        elif report.overall_result == GateResult.WARN and args.strict:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()