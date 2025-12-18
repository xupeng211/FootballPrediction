#!/usr/bin/env python3
"""
Sprint 7 覆盖率集成脚本

整合所有覆盖率功能，提供统一的入口点：
1. 运行完整的覆盖率测试套件
2. 生成多格式报告（HTML, JSON, XML）
3. 集成到CI/CD流水线
4. 覆盖率趋势监控
5. 自动化覆盖率提升建议

使用方法:
  python coverage_integration.py --run-all
  python coverage_integration.py --ci-mode
  python coverage_integration.py --watch-mode

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Testing Coverage)
"""

import asyncio
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import os

import coverage
import pytest

from generate_coverage_report import CoverageReportGenerator
from coverage_analyzer import CoverageAnalyzer

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CoverageIntegration:
    """覆盖率集成管理器"""

    def __init__(self, output_dir: str = "coverage_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.report_generator = CoverageReportGenerator(str(self.output_dir))
        self.analyzer = CoverageAnalyzer()

        # 覆盖率目标配置
        self.coverage_targets = {
            "overall": 85.0,
            "core_algorithms": 90.0,
            "integration_tests": 80.0,
            "performance_tests": 70.0,
        }

    async def run_complete_coverage_suite(self) -> Dict[str, Any]:
        """运行完整的覆盖率测试套件"""
        logger.info("🚀 开始运行完整覆盖率测试套件")
        start_time = time.time()

        try:
            # 1. 环境检查和准备
            await self._prepare_environment()

            # 2. 运行测试套件
            test_results = await self._run_test_suite()

            # 3. 生成覆盖率报告
            coverage_report = await self._generate_coverage_reports()

            # 4. 深度分析
            deep_analysis = await self.analyzer.deep_coverage_analysis()

            # 5. 生成集成报告
            integration_report = await self._generate_integration_report(
                test_results, coverage_report, deep_analysis
            )

            # 6. 评估目标达成情况
            target_assessment = await self._assess_coverage_targets(coverage_report)

            # 7. 生成CI/CD输出
            ci_output = await self._generate_ci_output(
                integration_report, target_assessment
            )

            execution_time = time.time() - start_time

            logger.info(f"✅ 完整覆盖率测试套件执行完成，耗时: {execution_time:.2f}秒")

            return {
                "success": True,
                "execution_time": execution_time,
                "test_results": test_results,
                "coverage_report": coverage_report,
                "deep_analysis": deep_analysis,
                "integration_report": integration_report,
                "target_assessment": target_assessment,
                "ci_output": ci_output,
            }

        except Exception as e:
            logger.error(f"❌ 覆盖率测试套件执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }

    async def _prepare_environment(self):
        """准备测试环境"""
        logger.info("🔧 准备测试环境")

        # 检查依赖
        try:
            import coverage
            import pytest
            import pytest_asyncio
        except ImportError as e:
            logger.error(f"缺少依赖: {e}")
            raise

        # 清理之前的覆盖率数据
        cov_files = list(Path(".").glob(".coverage*"))
        for cov_file in cov_files:
            cov_file.unlink()

        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "htmlcov").mkdir(exist_ok=True)
        (self.output_dir / "xml").mkdir(exist_ok=True)

    async def _run_test_suite(self) -> Dict[str, Any]:
        """运行测试套件"""
        logger.info("🧪 运行测试套件")

        test_suites = [
            {
                "name": "Core Algorithms",
                "tests": [
                    "tests/unit/test_elo_rating_system.py",
                    "tests/unit/test_poisson_features.py",
                    "tests/unit/test_odds_movement_features.py",
                ],
            },
            {
                "name": "Integration Tests",
                "tests": ["tests/integration/test_service_integration.py"],
            },
            {"name": "Performance Tests", "tests": ["tests/performance/"]},
        ]

        suite_results = {}
        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for suite in test_suites:
            logger.info(f"运行测试套件: {suite['name']}")

            try:
                # 运行pytest
                result = pytest.main(
                    [
                        "--tb=short",
                        "--json-report",
                        f'--json-report-file={self.output_dir}/{suite["name"].lower().replace(" ", "_")}_results.json',
                        "-v",
                        *suite["tests"],
                    ]
                )

                # 读取结果
                result_file = (
                    self.output_dir
                    / f'{suite["name"].lower().replace(" ", "_")}_results.json'
                )
                if result_file.exists():
                    with open(result_file, "r") as f:
                        result_data = json.load(f)

                    suite_results[suite["name"]] = {
                        "exit_code": result,
                        "summary": result_data.get("summary", {}),
                        "tests": result_data.get("tests", []),
                    }

                    if "summary" in result_data:
                        total_passed += result_data["summary"].get("passed", 0)
                        total_failed += result_data["summary"].get("failed", 0)
                        total_skipped += result_data["summary"].get("skipped", 0)

                else:
                    suite_results[suite["name"]] = {
                        "exit_code": result,
                        "summary": {"passed": 0, "failed": 0, "skipped": 0},
                        "tests": [],
                    }

            except Exception as e:
                logger.error(f"测试套件 {suite['name']} 执行失败: {e}")
                suite_results[suite["name"]] = {
                    "exit_code": -1,
                    "error": str(e),
                    "summary": {"passed": 0, "failed": 0, "skipped": 0},
                    "tests": [],
                }

        overall_success = all(
            result.get("exit_code", -1) == 0 for result in suite_results.values()
        )

        return {
            "overall_success": overall_success,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_tests": total_passed + total_failed + total_skipped,
            "suite_results": suite_results,
        }

    async def _generate_coverage_reports(self) -> Dict[str, Any]:
        """生成覆盖率报告"""
        logger.info("📊 生成覆盖率报告")

        # 使用报告生成器生成完整报告
        coverage_result = await self.report_generator.generate_full_coverage_report()

        # 生成额外的XML报告（用于CI集成）
        await self._generate_xml_report()

        # 生成Markdown报告（用于文档）
        await self._generate_markdown_report(coverage_result)

        return coverage_result

    async def _generate_xml_report(self):
        """生成XML格式的覆盖率报告（用于CI工具）"""
        logger.info("📄 生成XML覆盖率报告")

        try:
            cov = coverage.Coverage()
            cov.load()

            # 生成XML报告
            cov.xml_report(outfile=str(self.output_dir / "xml" / "coverage.xml"))

            logger.info("✅ XML覆盖率报告生成完成")

        except Exception as e:
            logger.error(f"XML报告生成失败: {e}")

    async def _generate_markdown_report(self, coverage_result: Dict[str, Any]):
        """生成Markdown格式的覆盖率报告"""
        logger.info("📝 生成Markdown覆盖率报告")

        # 提取关键数据
        overall_coverage = coverage_result["overall_coverage"]
        core_coverage = coverage_result["core_coverage"]["average_coverage"]
        integration_coverage = coverage_result["integration_coverage"][
            "average_coverage"
        ]

        # 生成Markdown内容
        markdown_content = f"""# Sprint 7 测试覆盖率报告

## 📊 覆盖率概览

| 指标 | 覆盖率 | 目标 | 状态 |
|------|--------|------|------|
| 总体覆盖率 | {overall_coverage:.1f}% | {self.coverage_targets['overall']:.1f}% | {'✅' if overall_coverage >= self.coverage_targets['overall'] else '❌'} |
| 核心算法覆盖率 | {core_coverage:.1f}% | {self.coverage_targets['core_algorithms']:.1f}% | {'✅' if core_coverage >= self.coverage_targets['core_algorithms'] else '❌'} |
| 集成测试覆盖率 | {integration_coverage:.1f}% | {self.coverage_targets['integration_tests']:.1f}% | {'✅' if integration_coverage >= self.coverage_targets['integration_tests'] else '❌'} |

## 🎯 核心算法模块详情

"""

        # 添加核心算法模块详情
        for module, analysis in coverage_result["core_coverage"][
            "detailed_analysis"
        ].items():
            status = (
                "✅ 达标" if analysis["status"] == "meets_threshold" else "❌ 未达标"
            )
            priority = {"high": "高", "medium": "中", "low": "低"}.get(
                analysis["priority"], "低"
            )

            markdown_content += f"""### {module.split('.')[-1]}

- 覆盖率: {analysis['coverage']:.1f}%
- 状态: {status}
- 优先级: {priority}
- 差距: {analysis['gap']:.1f}%

"""

        # 添加趋势分析
        if "trend_analysis" in coverage_result:
            trend = coverage_result["trend_analysis"]
            markdown_content += f"""## 📈 覆盖率趋势

- 趋势方向: {trend.get('trend', 'N/A')}
- 数据点数: {trend.get('data_points', 0)}
- 最新覆盖率: {trend.get('latest_coverage', 0):.1f}%
- 变化幅度: {trend.get('change_rate_percent', 0):.2f}%

"""

        # 添加回归检测
        if coverage_result.get("regressions_detected", 0) > 0:
            markdown_content += f"""## ⚠️ 回归检测

检测到 {coverage_result['regressions_detected']} 个覆盖率回归，请查看详细报告。

"""

        markdown_content += f"""
## 📈 生成信息

- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 报告版本: Sprint 7 v1.0.0
- 系统版本: Football Prediction v2.0

## 🔗 相关文件

- [HTML详细报告]({coverage_result.get('html_report', '#')})
- [完整JSON报告]({coverage_result.get('report_file', '#')})
- [覆盖率徽章]({coverage_result.get('badge_data', {}).get('svg_file', '#')})
"""

        # 保存Markdown报告
        markdown_file = (
            self.output_dir
            / f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"✅ Markdown覆盖率报告生成完成: {markdown_file}")

    async def _generate_integration_report(
        self,
        test_results: Dict[str, Any],
        coverage_report: Dict[str, Any],
        deep_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成集成报告"""
        logger.info("🔗 生成集成报告")

        integration_report = {
            "timestamp": datetime.now().isoformat(),
            "test_summary": {
                "total_tests": test_results["total_tests"],
                "passed_tests": test_results["total_passed"],
                "failed_tests": test_results["total_failed"],
                "skipped_tests": test_results["total_skipped"],
                "success_rate": (
                    (test_results["total_passed"] / test_results["total_tests"] * 100)
                    if test_results["total_tests"] > 0
                    else 0
                ),
            },
            "coverage_summary": {
                "overall_coverage": coverage_report["overall_coverage"],
                "core_algorithms_coverage": coverage_report["core_coverage"][
                    "average_coverage"
                ],
                "integration_coverage": coverage_report["integration_coverage"][
                    "average_coverage"
                ],
                "targets_met": {
                    "overall": coverage_report["overall_coverage"]
                    >= self.coverage_targets["overall"],
                    "core_algorithms": coverage_report["core_coverage"][
                        "average_coverage"
                    ]
                    >= self.coverage_targets["core_algorithms"],
                    "integration": coverage_report["integration_coverage"][
                        "average_coverage"
                    ]
                    >= self.coverage_targets["integration_tests"],
                },
            },
            "quality_metrics": {
                "total_modules_analyzed": deep_analysis.get("modules_analyzed", 0),
                "high_risk_areas": deep_analysis.get("risk_analysis", {}).get(
                    "total_high_risk", 0
                ),
                "medium_risk_areas": deep_analysis.get("risk_analysis", {}).get(
                    "total_medium_risk", 0
                ),
                "average_complexity": deep_analysis.get("complexity_analysis", {}).get(
                    "global_average_complexity", 0
                ),
                "improvement_suggestions": deep_analysis.get(
                    "improvement_plan", {}
                ).get("total_improvements", 0),
            },
            "detailed_results": {
                "test_results": test_results,
                "coverage_report": coverage_report,
                "deep_analysis": deep_analysis,
            },
            "recommendations": await self._generate_recommendations(
                test_results, coverage_report, deep_analysis
            ),
        }

        # 保存集成报告
        report_file = (
            self.output_dir
            / f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(integration_report, f, indent=2, default=str, ensure_ascii=False)

        logger.info(f"✅ 集成报告生成完成: {report_file}")

        return integration_report

    async def _assess_coverage_targets(
        self, coverage_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估覆盖率目标达成情况"""
        logger.info("🎯 评估覆盖率目标达成情况")

        targets_status = {}
        all_met = True
        overall_score = 0

        for target_name, target_value in self.coverage_targets.items():
            if target_name == "overall":
                actual_coverage = coverage_report["overall_coverage"]
            elif target_name == "core_algorithms":
                actual_coverage = coverage_report["core_coverage"]["average_coverage"]
            elif target_name == "integration_tests":
                actual_coverage = coverage_report["integration_coverage"][
                    "average_coverage"
                ]
            else:
                actual_coverage = 0

            met = actual_coverage >= target_value
            targets_status[target_name] = {
                "target": target_value,
                "actual": actual_coverage,
                "met": met,
                "gap": max(0, target_value - actual_coverage),
            }

            if not met:
                all_met = False

            # 计算得分
            score = min(actual_coverage / target_value, 1.0) * 100
            overall_score += score

        overall_score = overall_score / len(self.coverage_targets)

        assessment = {
            "all_targets_met": all_met,
            "overall_score": overall_score,
            "targets_status": targets_status,
            "grade": self._calculate_grade(overall_score),
        }

        return assessment

    def _calculate_grade(self, score: float) -> str:
        """计算覆盖率等级"""
        if score >= 95:
            return "A+ (优秀)"
        elif score >= 90:
            return "A (优秀)"
        elif score >= 85:
            return "B+ (良好)"
        elif score >= 80:
            return "B (良好)"
        elif score >= 75:
            return "C+ (一般)"
        elif score >= 70:
            return "C (一般)"
        elif score >= 60:
            return "D (需要改进)"
        else:
            return "F (不合格)"

    async def _generate_recommendations(
        self,
        test_results: Dict[str, Any],
        coverage_report: Dict[str, Any],
        deep_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """生成改进建议"""
        recommendations = []

        # 测试成功率建议
        success_rate = test_results["test_summary"]["success_rate"]
        if success_rate < 95:
            recommendations.append(
                {
                    "category": "测试稳定性",
                    "priority": "high",
                    "description": f"测试成功率较低({success_rate:.1f}%)，需要修复失败的测试用例",
                    "action_items": [
                        "分析并修复失败的测试用例",
                        "检查测试环境的稳定性",
                        "更新测试数据和依赖",
                    ],
                }
            )

        # 覆盖率建议
        if not coverage_report["core_coverage_met"]:
            recommendations.append(
                {
                    "category": "核心算法覆盖率",
                    "priority": "high",
                    "description": f"核心算法覆盖率未达标({coverage_report['core_coverage']['average_coverage']:.1f}%)",
                    "action_items": [
                        "为核心算法函数增加单元测试",
                        "补充边界条件测试",
                        "增加异常处理测试",
                    ],
                }
            )

        # 风险区域建议
        high_risk_count = deep_analysis.get("quality_metrics", {}).get(
            "high_risk_areas", 0
        )
        if high_risk_count > 0:
            recommendations.append(
                {
                    "category": "代码质量",
                    "priority": "medium",
                    "description": f"发现{high_risk_count}个高风险代码区域",
                    "action_items": [
                        "优先为高风险区域编写测试",
                        "考虑重构高复杂度函数",
                        "增加代码审查检查",
                    ],
                }
            )

        # 复杂度建议
        avg_complexity = deep_analysis.get("quality_metrics", {}).get(
            "average_complexity", 0
        )
        if avg_complexity > 8:
            recommendations.append(
                {
                    "category": "代码复杂度",
                    "priority": "medium",
                    "description": f"平均代码复杂度偏高({avg_complexity:.1f})",
                    "action_items": [
                        "重构高复杂度函数",
                        "应用设计模式降低复杂度",
                        "增加单元测试提高可测试性",
                    ],
                }
            )

        return recommendations

    async def _generate_ci_output(
        self, integration_report: Dict[str, Any], target_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成CI/CD输出格式"""
        logger.info("🔧 生成CI/CD输出")

        ci_output = {
            "success": target_assessment["all_targets_met"],
            "metrics": {
                "test_success_rate": integration_report["test_summary"]["success_rate"],
                "overall_coverage": integration_report["coverage_summary"][
                    "overall_coverage"
                ],
                "core_algorithms_coverage": integration_report["coverage_summary"][
                    "core_algorithms_coverage"
                ],
                "integration_coverage": integration_report["coverage_summary"][
                    "integration_coverage"
                ],
            },
            "targets": target_assessment["targets_status"],
            "grade": target_assessment["grade"],
            "summary": {
                "total_tests": integration_report["test_summary"]["total_tests"],
                "failed_tests": integration_report["test_summary"]["failed_tests"],
                "high_risk_areas": integration_report["quality_metrics"][
                    "high_risk_areas"
                ],
                "improvement_suggestions": integration_report["quality_metrics"][
                    "improvement_suggestions"
                ],
            },
            "artifacts": {
                "html_report": str(self.output_dir / "htmlcov" / "index.html"),
                "xml_report": str(self.output_dir / "xml" / "coverage.xml"),
                "badge": str(self.output_dir / "coverage_badge.svg"),
                "integration_report": (
                    str(list(self.output_dir.glob("integration_report_*.json"))[0])
                    if list(self.output_dir.glob("integration_report_*.json"))
                    else None
                ),
            },
        }

        # 生成GitHub Actions输出文件
        await self._generate_github_actions_output(ci_output)

        # 生成环境变量文件
        await self._generate_env_vars(ci_output)

        return ci_output

    async def _generate_github_actions_output(self, ci_output: Dict[str, Any]):
        """生成GitHub Actions输出格式"""
        logger.info("📝 生成GitHub Actions输出")

        # 创建GitHub Actions输出文件
        gh_output_file = self.output_dir / "github_actions_output.txt"

        with open(gh_output_file, "w") as f:
            # 输出覆盖率指标
            f.write(
                f"::set-output name=coverage::{ci_output['metrics']['overall_coverage']:.1f}\n"
            )
            f.write(
                f"::set-output name=core_coverage::{ci_output['metrics']['core_algorithms_coverage']:.1f}\n"
            )
            f.write(
                f"::set-output name=integration_coverage::{ci_output['metrics']['integration_coverage']:.1f}\n"
            )
            f.write(
                f"::set-output name=test_success_rate::{ci_output['metrics']['test_success_rate']:.1f}\n"
            )
            f.write(f"::set-output name=grade::{ci_output['grade']}\n")
            f.write(
                f"::set-output name=targets_met::{str(ci_output['success']).lower()}\n"
            )

            # 输出摘要信息
            f.write("\n# Coverage Summary\n")
            f.write(
                f"- Overall Coverage: {ci_output['metrics']['overall_coverage']:.1f}%\n"
            )
            f.write(
                f"- Core Algorithms: {ci_output['metrics']['core_algorithms_coverage']:.1f}%\n"
            )
            f.write(
                f"- Integration Tests: {ci_output['metrics']['integration_coverage']:.1f}%\n"
            )
            f.write(
                f"- Test Success Rate: {ci_output['metrics']['test_success_rate']:.1f}%\n"
            )
            f.write(f"- Grade: {ci_output['grade']}\n")

    async def _generate_env_vars(self, ci_output: Dict[str, Any]):
        """生成环境变量文件"""
        logger.info("🔧 生成环境变量文件")

        env_file = self.output_dir / "coverage.env"

        with open(env_file, "w") as f:
            f.write(
                f"COVERAGE_OVERALL={ci_output['metrics']['overall_coverage']:.1f}\n"
            )
            f.write(
                f"COVERAGE_CORE={ci_output['metrics']['core_algorithms_coverage']:.1f}\n"
            )
            f.write(
                f"COVERAGE_INTEGRATION={ci_output['metrics']['integration_coverage']:.1f}\n"
            )
            f.write(
                f"TEST_SUCCESS_RATE={ci_output['metrics']['test_success_rate']:.1f}\n"
            )
            f.write(f"COVERAGE_GRADE={ci_output['grade']}\n")
            f.write(f"TARGETS_MET={str(ci_output['success']).lower()}\n")

    async def run_ci_mode(self) -> Dict[str, Any]:
        """运行CI模式（简化版本，专注于关键指标）"""
        logger.info("🚀 运行CI模式")

        try:
            # 快速覆盖率检查
            cov = coverage.Coverage()
            cov.start()

            # 运行关键测试
            critical_tests = [
                "tests/unit/test_elo_rating_system.py",
                "tests/unit/test_poisson_features.py",
                "tests/integration/test_service_integration.py",
            ]

            result = pytest.main(["--tb=short", "-q", *critical_tests])

            cov.stop()
            cov.save()

            # 获取覆盖率数据
            coverage_data = cov.get_data()
            total_statements = (
                coverage_data.n_executed_statements()
                + coverage_data.n_missing_statements()
            )
            overall_coverage = (
                (coverage_data.n_executed_statements() / total_statements * 100)
                if total_statements > 0
                else 0
            )

            ci_result = {
                "success": result == 0
                and overall_coverage >= self.coverage_targets["overall"],
                "exit_code": result,
                "overall_coverage": overall_coverage,
                "target_met": overall_coverage >= self.coverage_targets["overall"],
                "target_gap": max(
                    0, self.coverage_targets["overall"] - overall_coverage
                ),
            }

            # 生成CI输出
            await self._generate_github_actions_output(
                {
                    "success": ci_result["success"],
                    "metrics": {"overall_coverage": overall_coverage},
                    "grade": self._calculate_grade(
                        overall_coverage / self.coverage_targets["overall"] * 100
                    ),
                    "targets_met": ci_result["target_met"],
                }
            )

            return ci_result

        except Exception as e:
            logger.error(f"CI模式执行失败: {e}")
            return {"success": False, "error": str(e), "overall_coverage": 0}

    async def run_watch_mode(self, interval: int = 60) -> None:
        """运行监控模式（持续监控覆盖率变化）"""
        logger.info(f"👁️ 启动监控模式，监控间隔: {interval}秒")

        baseline_coverage = None

        try:
            while True:
                logger.info("🔍 执行覆盖率检查...")

                # 运行快速覆盖率检查
                result = await self.run_ci_mode()

                current_coverage = result["overall_coverage"]

                if baseline_coverage is None:
                    baseline_coverage = current_coverage
                    logger.info(f"📊 建立基线覆盖率: {baseline_coverage:.1f}%")
                else:
                    coverage_change = current_coverage - baseline_coverage
                    if abs(coverage_change) > 1.0:  # 1%变化阈值
                        status = "📈" if coverage_change > 0 else "📉"
                        logger.info(
                            f"{status} 覆盖率变化: {coverage_change:+.1f}% (当前: {current_coverage:.1f}%, 基线: {baseline_coverage:.1f}%)"
                        )

                # 检查目标达成情况
                if not result["target_met"]:
                    logger.warning(
                        f"⚠️ 覆盖率未达标，当前: {current_coverage:.1f}%, 目标: {self.coverage_targets['overall']:.1f}%"
                    )

                # 等待下次检查
                logger.info(f"⏳ 等待 {interval} 秒后进行下次检查...")
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            logger.info("👋 监控模式已停止")
        except Exception as e:
            logger.error(f"监控模式出错: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 7 覆盖率集成脚本")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 完整运行命令
    full_parser = subparsers.add_parser("run-all", help="运行完整的覆盖率测试套件")
    full_parser.add_argument(
        "--output-dir", default="coverage_reports", help="输出目录"
    )

    # CI模式命令
    ci_parser = subparsers.add_parser("ci-mode", help="运行CI模式（快速检查）")

    # 监控模式命令
    watch_parser = subparsers.add_parser("watch-mode", help="运行监控模式（持续监控）")
    watch_parser.add_argument("--interval", type=int, default=60, help="监控间隔（秒）")

    args = parser.parse_args()

    integration = CoverageIntegration(
        args.output_dir if hasattr(args, "output_dir") else "coverage_reports"
    )

    try:
        if args.command == "run-all":
            result = await integration.run_complete_coverage_suite()

            print(f"\n🎉 Sprint 7 覆盖率测试完成!")
            print(f"执行时间: {result['execution_time']:.2f}秒")
            print(
                f"测试成功率: {result['test_results']['test_summary']['success_rate']:.1f}%"
            )
            print(f"总体覆盖率: {result['coverage_report']['overall_coverage']:.1f}%")
            print(
                f"核心算法覆盖率: {result['coverage_report']['core_coverage']['average_coverage']:.1f}%"
            )
            print(
                f"集成测试覆盖率: {result['coverage_report']['integration_coverage']['average_coverage']:.1f}%"
            )
            print(
                f"目标达成: {'✅ 是' if result['target_assessment']['all_targets_met'] else '❌ 否'}"
            )
            print(f"总体评分: {result['target_assessment']['grade']}")

            # 输出关键文件路径
            if "artifacts" in result["ci_output"]:
                print(f"\n📁 生成的文件:")
                for artifact_type, file_path in result["ci_output"][
                    "artifacts"
                ].items():
                    if file_path:
                        print(f"  {artifact_type}: {file_path}")

            return result

        elif args.command == "ci-mode":
            result = await integration.run_ci_mode()

            print(f"\n🚀 CI模式执行完成!")
            print(f"成功率: {'✅' if result['success'] else '❌'}")
            print(f"覆盖率: {result['overall_coverage']:.1f}%")
            print(f"目标达成: {'✅' if result['target_met'] else '❌'}")

            if result["target_gap"] > 0:
                print(f"覆盖率差距: {result['target_gap']:.1f}%")

            return result

        elif args.command == "watch-mode":
            print(f"👁️ 启动监控模式...")
            await integration.run_watch_mode(args.interval)

        else:
            parser.print_help()
            return None

    except KeyboardInterrupt:
        print("\n👋 用户中断操作")
        return None
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        print(f"❌ 执行失败: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
