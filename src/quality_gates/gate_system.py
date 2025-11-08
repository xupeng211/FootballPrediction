from datetime import datetime
from typing import Any

#!/usr/bin/env python3
"""
质量门禁系统
Quality Gate System

提供自动化的质量检查和门禁控制,确保代码质量标准
"""

import json
from enum import Enum
from pathlib import Path

from scripts.quality_guardian import QualityGuardian
from src.core.logging_system import get_logger
from src.metrics.advanced_analyzer import AdvancedMetricsAnalyzer
from src.metrics.quality_integration import QualityMetricsIntegrator

logger = get_logger(__name__)


class GateStatus(Enum):
    """门禁状态枚举"""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class GateResult:
    """类文档字符串"""

    pass  # 添加pass语句
    """门禁检查结果"""

    def __init__(
        self,
        gate_name: str,
        status: GateStatus,
        score: float,
        threshold: float,
        message: str,
        details: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ):
        self.gate_name = gate_name
        self.status = status
        self.score = score
        self.threshold = threshold
        self.message = message
        self.details = details or {}
        self.duration_ms = duration_ms
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "gate_name": self.gate_name,
            "status": self.status.value,
            "score": self.score,
            "threshold": self.threshold,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


class QualityGate:
    """类文档字符串"""

    pass  # 添加pass语句
    """单个质量门禁"""

    def __init__(
        self,
        name: str,
        description: str,
        threshold: float,
        critical: bool = True,
        enabled: bool = True,
    ):
        self.name = name
        self.description = description
        self.threshold = threshold
        self.critical = critical
        self.enabled = enabled
        self.logger = get_logger(self.__class__.__name__)

    def check(self) -> GateResult:
        """执行门禁检查"""
        if not self.enabled:
            return GateResult(
                gate_name=self.name,
                status=GateStatus.SKIPPED,
                score=0.0,
                threshold=self.threshold,
                message=f"门禁 {self.name} 已跳过",
            )

        start_time = datetime.now()
        try:
            score = self._calculate_score()
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if score >= self.threshold:
                status = GateStatus.PASSED
                message = f"✅ {self.name}: {score:.2f} >= {self.threshold}"
            elif score >= self.threshold * 0.9:
                status = GateStatus.WARNING
                message = f"⚠️ {self.name}: {score:.2f} 接近阈值 {self.threshold}"
            else:
                status = GateStatus.FAILED
                message = f"❌ {self.name}: {score:.2f} < {self.threshold}"

            return GateResult(
                gate_name=self.name,
                status=status,
                score=score,
                threshold=self.threshold,
                message=message,
                duration_ms=duration_ms,
            )

        except Exception as e:
            self.logger.error(f"门禁检查失败 {self.name}: {e}")
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return GateResult(
                gate_name=self.name,
                status=GateStatus.FAILED,
                score=0.0,
                threshold=self.threshold,
                message=f"❌ {self.name}: 检查失败 - {str(e)}",
                details={"error": str(e)},
                duration_ms=duration_ms,
            )

    def _calculate_score(self) -> float:
        """计算门禁分数（子类实现）"""
        raise NotImplementedError("子类必须实现 _calculate_score 方法")


class CodeQualityGate(QualityGate):
    """代码质量门禁"""

    def __init__(self, threshold: float = 8.0):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(
            name="代码质量",
            description="检查代码质量分数（Ruff + MyPy）",
            threshold=threshold,
            critical=True,
        )
        self.quality_guardian = QualityGuardian()

    def _calculate_score(self) -> float:
        """计算代码质量分数"""
        report = self.quality_guardian.run_quality_check()

        # Ruff和MyPy满分各5分,总分10分
        ruff_score = (
            5.0
            if report.get("ruff_errors", 0) == 0
            else max(0, 5.0 - report.get("ruff_errors", 0))
        )
        mypy_score = (
            5.0
            if report.get("mypy_errors", 0) == 0
            else max(0, 5.0 - report.get("mypy_errors", 0))
        )

        total_score = ruff_score + mypy_score

        # 转换为10分制
        return total_score


class TestCoverageGate(QualityGate):
    """测试覆盖率门禁"""

    def __init__(self, threshold: float = 80.0):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(
            name="测试覆盖率",
            description="检查测试覆盖率百分比",
            threshold=threshold,
            critical=True,
        )
        self.quality_guardian = QualityGuardian()

    def _calculate_score(self) -> float:
        """计算测试覆盖率分数"""
        report = self.quality_guardian.run_quality_check()
        return report.get("coverage_percentage", 0.0)


class SecurityGate(QualityGate):
    """安全检查门禁"""

    def __init__(self, threshold: float = 9.0):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(
            name="安全检查",
            description="检查安全评分和漏洞扫描",
            threshold=threshold,
            critical=True,
        )
        self.quality_guardian = QualityGuardian()

    def _calculate_score(self) -> float:
        """计算安全分数"""
        report = self.quality_guardian.run_quality_check()
        return report.get("security_score", 0.0)


class OverallQualityGate(QualityGate):
    """综合质量门禁"""

    def __init__(self, threshold: float = 8.5):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(
            name="综合质量",
            description="综合质量分数（包含高级度量）",
            threshold=threshold,
            critical=True,
        )
        self.integrator = QualityMetricsIntegrator()

    def _calculate_score(self) -> float:
        """计算综合质量分数"""
        # 模拟现有质量报告
        quality_guardian = QualityGuardian()
        basic_report = quality_guardian.run_quality_check()

        # 集成高级度量
        enhanced_report = self.integrator.enhance_quality_report(basic_report)

        return enhanced_report.get("enhanced_overall_score", 0.0)


class TechnicalDebtGate(QualityGate):
    """技术债务门禁"""

    def __init__(self, threshold: float = 60.0):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(
            name="技术债务",
            description="检查技术债务分数",
            threshold=threshold,
            critical=False,
        )
        self.analyzer = AdvancedMetricsAnalyzer()

    def _calculate_score(self) -> float:
        """计算技术债务分数"""
        project_root = Path(__file__).parent.parent.parent
        advanced_metrics = self.analyzer.run_full_analysis(project_root)

        return advanced_metrics.get("technical_debt", {}).get("debt_score", 0.0)


class ComplexityGate(QualityGate):
    """复杂度门禁"""

    def __init__(self, threshold: float = 70.0):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(
            name="代码复杂度",
            description="检查代码可维护性指数",
            threshold=threshold,
            critical=False,
        )
        self.analyzer = AdvancedMetricsAnalyzer()

    def _calculate_score(self) -> float:
        """计算复杂度分数（基于可维护性指数）"""
        project_root = Path(__file__).parent.parent.parent
        advanced_metrics = self.analyzer.run_full_analysis(project_root)

        complexity = advanced_metrics.get("complexity_metrics", {}).get("summary", {})
        maintainability_index = complexity.get("avg_maintainability_index", 0.0)

        return maintainability_index


class QualityGateSystem:
    """类文档字符串"""

    pass  # 添加pass语句
    """质量门禁系统主类"""

    def __init__(self, config_path: str | None = None):
        """函数文档字符串"""
        # 添加pass语句
        self.config = self._load_config(config_path)
        self.gates = self._initialize_gates()
        self.logger = get_logger(self.__class__.__name__)

    def _load_config(self, config_path: str | None) -> dict[str, Any]:
        """加载门禁配置"""
        default_config = {
            "gates": {
                "code_quality": {"enabled": True, "threshold": 8.0, "critical": True},
                "test_coverage": {"enabled": True, "threshold": 80.0, "critical": True},
                "security": {"enabled": True, "threshold": 9.0, "critical": True},
                "overall_quality": {
                    "enabled": True,
                    "threshold": 8.5,
                    "critical": True,
                },
                "technical_debt": {
                    "enabled": True,
                    "threshold": 60.0,
                    "critical": False,
                },
                "complexity": {"enabled": True, "threshold": 70.0, "critical": False},
            },
            "blocking_mode": True,
            "warning_threshold": 2,  # 允许的警告数量
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                self.logger.error(f"加载门禁配置失败: {e}")

        return default_config

    def _initialize_gates(self) -> list[QualityGate]:
        """初始化门禁列表"""
        gates_config = self.config.get("gates", {})
        gates = []

        if gates_config.get("code_quality", {}).get("enabled", True):
            threshold = gates_config["code_quality"].get("threshold", 8.0)
            gates.append(CodeQualityGate(threshold))

        if gates_config.get("test_coverage", {}).get("enabled", True):
            threshold = gates_config["test_coverage"].get("threshold", 80.0)
            gates.append(TestCoverageGate(threshold))

        if gates_config.get("security", {}).get("enabled", True):
            threshold = gates_config["security"].get("threshold", 9.0)
            gates.append(SecurityGate(threshold))

        if gates_config.get("overall_quality", {}).get("enabled", True):
            threshold = gates_config["overall_quality"].get("threshold", 8.5)
            gates.append(OverallQualityGate(threshold))

        if gates_config.get("technical_debt", {}).get("enabled", True):
            threshold = gates_config["technical_debt"].get("threshold", 60.0)
            gates.append(TechnicalDebtGate(threshold))

        if gates_config.get("complexity", {}).get("enabled", True):
            threshold = gates_config["complexity"].get("threshold", 70.0)
            gates.append(ComplexityGate(threshold))

        return gates

    def run_all_checks(self) -> dict[str, Any]:
        """运行所有门禁检查"""
        self.logger.info("开始运行质量门禁检查...")
        start_time = datetime.now()

        results = []
        critical_failures = []
        warnings = []

        for gate in self.gates:
            self.logger.info(f"检查门禁: {gate.name}")
            result = gate.check()
            results.append(result)

            if result.status == GateStatus.FAILED:
                if gate.critical:
                    critical_failures.append(result)
                    self.logger.error(f"关键门禁失败: {result.message}")
                else:
                    warnings.append(result)
                    self.logger.warning(f"非关键门禁失败: {result.message}")
            elif result.status == GateStatus.WARNING:
                warnings.append(result)
                self.logger.warning(f"门禁警告: {result.message}")

        # 计算总体状态
        duration = (datetime.now() - start_time).total_seconds()

        if critical_failures:
            overall_status = "FAILED"
            should_block = self.config.get("blocking_mode", True)
        elif len(warnings) > self.config.get("warning_threshold", 2):
            overall_status = "WARNING"
            should_block = False
        else:
            overall_status = "PASSED"
            should_block = False

        # 计算总体分数
        if results:
            total_score = sum(
                r.score for r in results if r.status != GateStatus.SKIPPED
            )
            avg_score = total_score / len(
                [r for r in results if r.status != GateStatus.SKIPPED]
            )
        else:
            total_score = 0.0
            avg_score = 0.0

        gate_report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "overall_status": overall_status,
            "should_block": should_block,
            "total_score": total_score,
            "average_score": avg_score,
            "gates_checked": len(results),
            "critical_failures": len(critical_failures),
            "warnings": len(warnings),
            "results": [result.to_dict() for result in results],
            "summary": {
                "passed": len([r for r in results if r.status == GateStatus.PASSED]),
                "failed": len([r for r in results if r.status == GateStatus.FAILED]),
                "warning": len([r for r in results if r.status == GateStatus.WARNING]),
                "skipped": len([r for r in results if r.status == GateStatus.SKIPPED]),
            },
        }

        self.logger.info(f"质量门禁检查完成: {overall_status} ({duration:.2f}s)")
        return gate_report

    def generate_report(self, results: dict[str, Any]) -> str:
        """生成门禁检查报告"""
        report_lines = [
            "# 质量门禁检查报告",
            f"生成时间: {results['timestamp']}",
            f"检查耗时: {results['duration_seconds']:.2f}秒",
            "",
            f"## 总体状态: {results['overall_status']}",
            f"平均分数: {results['average_score']:.2f}",
            f"检查门禁: {results['gates_checked']}",
            f"通过: {results['summary']['passed']}",
            f"失败: {results['summary']['failed']}",
            f"警告: {results['summary']['warning']}",
            f"跳过: {results['summary']['skipped']}",
            "",
            "## 详细结果",
        ]

        for result in results["results"]:
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "warning": "⚠️",
                "skipped": "⏭️",
            }.get(result["status"], "❓")

            report_lines.append(f"### {result['gate_name']}")
            report_lines.append(f"{status_icon} {result['message']}")
            report_lines.append(f"分数: {result['score']:.2f} / {result['threshold']}")

            if result["details"]:
                report_lines.append("详细信息:")
                for key, value in result["details"].items():
                    report_lines.append(f"  - {key}: {value}")

            report_lines.append("")

        if results["should_block"]:
            report_lines.extend(
                [
                    "## ⚠️ 阻止合并",
                    "由于存在关键门禁失败,建议阻止代码合并.",
                    "请修复所有关键问题后重新检查.",
                ]
            )

        return "\n".join(report_lines)

    def should_block_merge(self, results: dict[str, Any]) -> bool:
        """判断是否应该阻止合并"""
        return results.get("should_block", False)


def main():
    """函数文档字符串"""
    pass  # 添加pass语句
    """主函数,用于测试"""
    gate_system = QualityGateSystem()

    # 运行所有检查
    results = gate_system.run_all_checks()

    # 显示详细结果
    for _result in results["results"]:
        pass

    # 生成报告
    report = gate_system.generate_report(results)
    report_path = Path("quality_gate_report.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    main()
