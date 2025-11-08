#!/usr/bin/env python3
"""
质量监控仪表板
自动化质量监控和报告生成系统
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from src.core.logger import get_logger

logger = get_logger(__name__)


class QualityMetrics:
    """质量指标数据类"""

    def __init__(self):
        self.timestamp = datetime.now()
        self.code_quality_score = 0.0
        self.test_coverage = 0.0
        self.test_pass_rate = 0.0
        self.security_issues = 0
        self.performance_score = 0.0
        self.technical_debt = 0
        self.build_status = "unknown"
        self.metrics = {}


class QualityMonitor:
    """质量监控器"""

    def __init__(self, project_root: str = None):
        self.project_root = (
            Path(project_root) if project_root else Path(__file__).parent.parent.parent
        )
        self.metrics_history: list[QualityMetrics] = []
        self.reports_dir = self.project_root / "reports" / "quality"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all_metrics(self) -> QualityMetrics:
        """收集所有质量指标"""
        metrics = QualityMetrics()

        logger.info("开始收集质量指标...")

        # 并行收集各项指标
        tasks = [
            self._collect_code_quality(metrics),
            self._collect_test_metrics(metrics),
            self._collect_security_metrics(metrics),
            self._collect_performance_metrics(metrics),
            self._collect_technical_debt(metrics),
            self._collect_build_status(metrics),
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        # 计算综合质量分数
        metrics.code_quality_score = self._calculate_overall_score(metrics)

        # 保存到历史记录
        self.metrics_history.append(metrics)

        logger.info(f"质量指标收集完成，综合评分: {metrics.code_quality_score:.1f}")
        return metrics

    async def _collect_code_quality(self, metrics: QualityMetrics):
        """收集代码质量指标"""
        try:
            # 运行Ruff检查
            result = await self._run_command_async(
                ["ruff", "check", "src/", "tests/", "--output-format=json"], timeout=60
            )

            if result and result.returncode == 0:
                ruff_data = json.loads(result.stdout)
                error_count = len(ruff_data.get("results", []))
                warning_count = len(
                    [
                        r
                        for r in ruff_data.get("results", [])
                        if r.get("type") == "warning"
                    ]
                )

                # 计算代码质量分数
                total_issues = error_count + warning_count
                if total_issues == 0:
                    metrics.metrics["code_quality_score"] = 100
                else:
                    # 基础分100分，每个问题扣分
                    base_score = 100
                    deduction = min(90, total_issues * 0.5)  # 最多扣90分
                    metrics.metrics["code_quality_score"] = max(
                        10, base_score - deduction
                    )

                metrics.metrics["ruff_errors"] = error_count
                metrics.metrics["ruff_warnings"] = warning_count
                logger.info(
                    f"代码质量检查完成: {error_count} 错误, {warning_count} 警告"
                )

        except Exception as e:
            logger.error(f"代码质量检查失败: {e}")
            metrics.metrics["code_quality_score"] = 50

    async def _collect_test_metrics(self, metrics: QualityMetrics):
        """收集测试指标"""
        try:
            # 运行测试并收集覆盖率
            result = await self._run_command_async(
                [
                    "pytest",
                    "tests/unit/",
                    "--cov=src",
                    "--cov-report=json",
                    "--cov-report=term-missing",
                ],
                timeout=300,  # 5分钟超时
            )

            if result:
                # 解析测试结果
                output = result.stdout + result.stderr
                lines = output.split("\n")

                # 查找覆盖率信息
                for line in lines:
                    if "TOTAL" in line and "%" in line:
                        try:
                            parts = line.split()
                            if len(parts) >= 4:
                                coverage_part = parts[3]
                                coverage = float(coverage_part.replace("%", ""))
                                metrics.test_coverage = coverage
                                break
                        except (ValueError, IndexError):
                            continue

                # 查找测试通过率
                passed = 0
                failed = 0
                total = 0

                for line in lines:
                    if "passed" in line and "failed" in line and "error" in line:
                        try:
                            parts = line.split()
                            for part in parts:
                                if part.isdigit():
                                    total += int(part)
                                elif part.endswith("passed"):
                                    passed += int(part.replace("passed", ""))
                                elif part.endswith("failed"):
                                    failed += int(part.replace("failed", ""))
                                elif part.endswith("error"):
                                    failed += int(part.replace("error", ""))
                        except ValueError:
                            continue

                if total > 0:
                    metrics.test_pass_rate = (passed / total) * 100

                logger.info(
                    f"测试指标收集完成: 覆盖率 {metrics.test_coverage}%, 通过率 {metrics.test_pass_rate}%"
                )

        except Exception as e:
            logger.error(f"测试指标收集失败: {e}")
            metrics.test_coverage = 0
            metrics.test_pass_rate = 0

    async def _collect_security_metrics(self, metrics: QualityMetrics):
        """收集安全指标"""
        try:
            # 运行Bandit安全扫描
            result = await self._run_command_async(
                ["bandit", "-r", "src/", "-f", "json"], timeout=120
            )

            if result and result.returncode == 0:
                bandit_data = json.loads(result.stdout)
                high_severity = bandit_data["metrics"]["_totals"]["SEVERITY.HIGH"]
                medium_severity = bandit_data["metrics"]["_totals"]["SEVERITY.MEDIUM"]
                low_severity = bandit_data["metrics"]["_totals"]["SEVERITY.LOW"]

                metrics.security_issues = high_severity + medium_severity
                metrics.metrics["security_high"] = high_severity
                metrics.metrics["security_medium"] = medium_severity
                metrics.metrics["security_low"] = low_severity

                logger.info(
                    f"安全扫描完成: 高危 {high_severity}, 中危 {medium_severity}, 低危 {low_severity}"
                )

        except Exception as e:
            logger.error(f"安全指标收集失败: {e}")
            metrics.security_issues = 0

    async def _collect_performance_metrics(self, metrics: QualityMetrics):
        """收集性能指标"""
        try:
            # 运行性能基准测试
            result = await self._run_command_async(
                ["python", "src/monitoring/performance_profiler.py"], timeout=180
            )

            if result and result.returncode == 0:
                # 解析性能基准结果
                output = result.stdout
                if "performance_benchmark_results.json" in output:
                    # 如果生成了结果文件，解析它
                    pass  # 这里可以添加JSON解析逻辑

                # 基于系统资源使用情况计算性能分数
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                # 性能分数计算
                performance_score = 100

                # CPU使用率影响
                if cpu_percent > 80:
                    performance_score -= 20
                elif cpu_percent > 60:
                    performance_score -= 10

                # 内存使用率影响
                if memory.percent > 85:
                    performance_score -= 20
                elif memory.percent > 70:
                    performance_score -= 10

                # 磁盘空间影响
                disk_percent = (disk.used / disk.total) * 100
                if disk_percent > 90:
                    performance_score -= 15

                metrics.performance_score = max(0, performance_score)
                metrics.metrics["cpu_usage"] = cpu_percent
                metrics.metrics["memory_usage"] = memory.percent
                metrics.metrics["disk_usage"] = disk_percent

                logger.info(
                    f"性能指标收集完成: CPU {cpu_percent}%, 内存 {memory.percent}%, 磁盘 {disk_percent:.1f}%"
                )

        except Exception as e:
            logger.error(f"性能指标收集失败: {e}")
            metrics.performance_score = 70

    async def _collect_technical_debt(self, metrics: QualityMetrics):
        """收集技术债务指标"""
        try:
            # 估算技术债务分数
            debt_score = 0

            # 基于代码质量问题的债务
            if "code_quality_score" in metrics.metrics:
                quality_score = metrics.metrics["code_quality_score"]
                if quality_score < 80:
                    debt_score += (80 - quality_score) * 2

            # 基于测试覆盖率的债务
            if metrics.test_coverage < 70:
                debt_score += (70 - metrics.test_coverage) * 1.5

            # 基于安全问题的债务
            if metrics.security_issues > 0:
                debt_score += metrics.security_issues * 5

            # 基于复杂度的债务（简化计算）
            complexity_score = await self._calculate_complexity_score()
            if complexity_score > 100:
                debt_score += (complexity_score - 100) * 0.5

            metrics.technical_debt = debt_score
            metrics.metrics["complexity_score"] = complexity_score

            logger.info(f"技术债务估算完成: {debt_score:.1f} 分")

        except Exception as e:
            logger.error(f"技术债务收集失败: {e}")
            metrics.technical_debt = 0

    async def _collect_build_status(self, metrics: QualityMetrics):
        """收集构建状态"""
        try:
            # 检查最近的构建状态
            build_success = await self._check_build_status()
            metrics.build_status = "success" if build_success else "failed"

            logger.info(f"构建状态检查完成: {metrics.build_status}")

        except Exception as e:
            logger.error(f"构建状态检查失败: {e}")
            metrics.build_status = "unknown"

    async def _run_command_async(
        self, cmd: list[str], timeout: int = 60
    ) -> subprocess.CompletedProcess | None:
        """异步运行命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
            )

        except TimeoutError:
            logger.error(f"命令执行超时: {' '.join(cmd)}")
            return None
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            return None

    async def _calculate_complexity_score(self) -> float:
        """计算代码复杂度分数"""
        try:
            # 简化的复杂度计算
            # 实际项目中可以使用radon等工具
            total_files = 0
            total_lines = 0

            for py_file in self.project_root.rglob("*.py"):
                if "test" not in str(py_file):  # 排除测试文件
                    total_files += 1
                    try:
                        lines = len(py_file.read_text(encoding="utf-8").split("\n"))
                        total_lines += lines
                    except:
                        pass

            if total_files == 0:
                return 0

            avg_lines_per_file = total_lines / total_files

            # 复杂度评分（简化版）
            complexity_score = avg_lines_per_file / 5  # 每5行1分
            return min(200, complexity_score)  # 限制最高200分

        except Exception as e:
            logger.error(f"复杂度计算失败: {e}")
            return 0

    def _calculate_overall_score(self, metrics: QualityMetrics) -> float:
        """计算综合质量分数"""
        weights = {
            "code_quality": 0.25,
            "test_coverage": 0.20,
            "security": 0.20,
            "performance": 0.15,
            "technical_debt": 0.20,
        }

        # 代码质量分数
        code_quality = metrics.metrics.get("code_quality_score", 50)

        # 测试覆盖率分数
        coverage_score = min(100, metrics.test_coverage * 1.25)  # 80%覆盖率 = 100分

        # 安全分数（安全问题越少分数越高）
        security_issues = metrics.security_issues
        security_score = max(0, 100 - security_issues * 10)

        # 性能分数
        performance_score = metrics.performance_score

        # 技术债务分数（债务越少分数越高）
        debt_score = max(0, 100 - metrics.technical_debt)

        overall_score = (
            code_quality * weights["code_quality"]
            + coverage_score * weights["test_coverage"]
            + security_score * weights["security"]
            + performance_score * weights["performance"]
            + debt_score * weights["technical_debt"]
        )

        return round(overall_score, 1)

    async def generate_quality_report(self) -> dict[str, Any]:
        """生成质量报告"""
        metrics = await self.collect_all_metrics()

        report = {
            "timestamp": metrics.timestamp.isoformat(),
            "overall_score": metrics.code_quality_score,
            "status": self._get_quality_status(metrics.code_quality_score),
            "metrics": {
                "code_quality": {
                    "score": metrics.metrics.get("code_quality_score", 0),
                    "errors": metrics.metrics.get("ruff_errors", 0),
                    "warnings": metrics.metrics.get("ruff_warnings", 0),
                },
                "testing": {
                    "coverage": metrics.test_coverage,
                    "pass_rate": metrics.test_pass_rate,
                },
                "security": {
                    "total_issues": metrics.security_issues,
                    "high_severity": metrics.metrics.get("security_high", 0),
                    "medium_severity": metrics.metrics.get("security_medium", 0),
                    "low_severity": metrics.metrics.get("security_low", 0),
                },
                "performance": {
                    "score": metrics.performance_score,
                    "cpu_usage": metrics.metrics.get("cpu_usage", 0),
                    "memory_usage": metrics.metrics.get("memory_usage", 0),
                    "disk_usage": metrics.metrics.get("disk_usage", 0),
                },
                "technical_debt": {
                    "score": metrics.technical_debt,
                    "complexity": metrics.metrics.get("complexity_score", 0),
                },
                "build": {"status": metrics.build_status},
            },
            "recommendations": self._generate_recommendations(metrics),
            "trends": self._analyze_trends(),
        }

        # 保存报告
        report_file = (
            self.reports_dir
            / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"质量报告已生成: {report_file}")
        return report

    def _get_quality_status(self, score: float) -> str:
        """根据分数获取质量状态"""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "acceptable"
        elif score >= 60:
            return "poor"
        else:
            return "critical"

    def _generate_recommendations(self, metrics: QualityMetrics) -> list[str]:
        """生成改进建议"""
        recommendations = []

        if metrics.code_quality_score < 80:
            recommendations.append("建议修复代码质量问题，运行 'make fix-code'")

        if metrics.test_coverage < 30:
            recommendations.append("测试覆盖率不足30%，建议增加单元测试")

        if metrics.security_issues > 0:
            recommendations.append(
                f"发现 {metrics.security_issues} 个安全问题，建议立即修复"
            )

        if metrics.performance_score < 70:
            recommendations.append("性能分数较低，建议进行性能优化")

        if metrics.technical_debt > 50:
            recommendations.append("技术债务较高，建议进行代码重构")

        if metrics.build_status != "success":
            recommendations.append("构建失败，请检查CI/CD配置")

        if not recommendations:
            recommendations.append("质量指标良好，继续保持！")

        return recommendations

    def _analyze_trends(self) -> dict[str, Any]:
        """分析质量趋势"""
        if len(self.metrics_history) < 2:
            return {"message": "数据不足，无法分析趋势"}

        recent_metrics = self.metrics_history[-7:]  # 最近7天
        previous_metrics = (
            self.metrics_history[-14:-7] if len(self.metrics_history) >= 14 else []
        )

        if not previous_metrics:
            return {"message": "历史数据不足，无法分析趋势"}

        recent_avg = sum(m.code_quality_score for m in recent_metrics) / len(
            recent_metrics
        )
        previous_avg = sum(m.code_quality_score for m in previous_metrics) / len(
            previous_metrics
        )

        trend = "stable"
        if recent_avg > previous_avg + 5:
            trend = "improving"
        elif recent_avg < previous_avg - 5:
            trend = "declining"

        return {
            "trend": trend,
            "recent_average": round(recent_avg, 1),
            "previous_average": round(previous_avg, 1),
            "change": round(recent_avg - previous_avg, 1),
            "data_points": len(self.metrics_history),
        }

    async def start_monitoring(self, interval_minutes: int = 60):
        """启动持续监控"""
        logger.info(f"启动质量监控，间隔: {interval_minutes} 分钟")

        while True:
            try:
                await self.generate_quality_report()
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("质量监控已停止")
                break
            except Exception as e:
                logger.error(f"监控过程中出错: {e}")
                await asyncio.sleep(300)  # 出错后等待5分钟再重试


async def main():
    """主函数"""
    monitor = QualityMonitor()

    # 生成一次质量报告
    report = await monitor.generate_quality_report()

    print("\n" + "=" * 60)
    print("🏗️ 项目质量监控报告")
    print("=" * 60)
    print(f"⏰ 时间: {report['timestamp']}")
    print(f"📊 综合评分: {report['overall_score']} ({report['status']})")
    print(f"🧪 测试覆盖率: {report['metrics']['testing']['coverage']:.1f}%")
    print(f"🔒 安全问题: {report['metrics']['security']['total_issues']}")
    print(f"⚡ 性能分数: {report['metrics']['performance']['score']:.1f}")
    print("=" * 60)

    print("\n💡 改进建议:")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"{i}. {rec}")

    print(f"\n📈 趋势分析: {report['trends']}")

    # 启动持续监控（可选）
    # await monitor.start_monitoring(interval_minutes=60)


if __name__ == "__main__":
    asyncio.run(main())
