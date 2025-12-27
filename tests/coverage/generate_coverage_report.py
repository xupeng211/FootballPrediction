#!/usr/bin/env python3
"""
Sprint 7 测试覆盖率报告生成器

生成全面的测试覆盖率报告，包括：
1. 核心算法覆盖率分析（目标>90%）
2. 集成测试覆盖率指标
3. 性能测试覆盖率评估
4. 覆盖率趋势分析
5. 覆盖率徽章生成
6. 覆盖率回归检测

使用方法:
  python generate_coverage_report.py --full-report
  python generate_coverage_report.py --trend-analysis
  python generate_coverage_report.py --badge-generation

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Testing Coverage)
"""

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import coverage

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class CoverageMetrics:
    """覆盖率指标数据类"""

    total_statements: int
    covered_statements: int
    missing_statements: int
    coverage_percentage: float
    file_path: str
    module_name: str
    function_coverage: dict[str, float]
    line_coverage: dict[int, bool]


@dataclass
class CoverageThresholds:
    """覆盖率阈值配置"""

    core_algorithms_min: float = 90.0
    integration_tests_min: float = 80.0
    overall_min: float = 85.0
    performance_tests_min: float = 70.0


class CoverageReportGenerator:
    """测试覆盖率报告生成器"""

    def __init__(self, output_dir: str = "coverage_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.thresholds = CoverageThresholds()

        # 核心算法模块列表
        self.core_algorithm_modules = [
            "src/ml/inference/predictor",
            "src/ml/features/extractor",
            "src/ml/features/h2h_calculator",
            "src/ml/features/advanced_feature_transformer",
            "src/ml/models/xgboost_classifier",
            "src/services/prediction_service",
            "src/services/inference_service_v3",
        ]

        # 集成测试模块列表
        self.integration_modules = [
            "src/services/collection_service",
            "src/services/high_performance_inference",
            "src/database/db_pool",
            "src/api/predictions/predict_router",
        ]

        # 性能测试相关模块
        self.performance_modules = [
            "src/utils/performance_decorators",
            "src/database/performance_monitor",
            "src/utils/intelligent_logging",
        ]

    async def generate_full_coverage_report(self) -> dict[str, Any]:
        """生成完整的覆盖率报告"""
        logger.info("🔍 开始生成完整覆盖率报告")

        # 1. 运行覆盖率测试
        coverage_data = await self._run_coverage_tests()

        # 2. 分析核心算法覆盖率
        core_coverage = await self._analyze_core_algorithm_coverage(coverage_data)

        # 3. 分析集成测试覆盖率
        integration_coverage = await self._analyze_integration_coverage(coverage_data)

        # 4. 分析性能测试覆盖率
        performance_coverage = await self._analyze_performance_coverage(coverage_data)

        # 5. 生成覆盖率趋势分析
        trend_analysis = await self._analyze_coverage_trends()

        # 6. 检测覆盖率回归
        regression_detection = await self._detect_coverage_regressions(coverage_data)

        # 7. 生成HTML报告
        html_report = await self._generate_html_report(
            {
                "core_coverage": core_coverage,
                "integration_coverage": integration_coverage,
                "performance_coverage": performance_coverage,
                "trend_analysis": trend_analysis,
                "regression_detection": regression_detection,
                "overall_coverage": coverage_data["overall_coverage"],
            }
        )

        # 8. 生成覆盖率徽章
        badge_data = await self._generate_coverage_badge(coverage_data["overall_coverage"])

        # 9. 保存报告
        report_file = await self._save_coverage_report(
            {
                "timestamp": datetime.now().isoformat(),
                "core_coverage": core_coverage,
                "integration_coverage": integration_coverage,
                "performance_coverage": performance_coverage,
                "trend_analysis": trend_analysis,
                "regression_detection": regression_detection,
                "overall_coverage": coverage_data["overall_coverage"],
                "html_report": html_report,
                "badge_data": badge_data,
            }
        )

        logger.info(f"✅ 覆盖率报告生成完成: {report_file}")

        return {
            "success": True,
            "report_file": str(report_file),
            "overall_coverage": coverage_data["overall_coverage"],
            "core_coverage_met": core_coverage["average_coverage"] >= self.thresholds.core_algorithms_min,
            "integration_coverage_met": integration_coverage["average_coverage"]
            >= self.thresholds.integration_tests_min,
            "regressions_detected": len(regression_detection["regressions"]),
            "badge_generated": badge_data["generated"],
        }

    async def _run_coverage_tests(self) -> dict[str, Any]:
        """运行覆盖率测试"""
        logger.info("🧪 运行覆盖率测试")

        # 创建Coverage对象
        cov = coverage.Coverage(
            source=["src"],
            omit=[
                "*/tests/*",
                "*/venv/*",
                "*/env/*",
                "*/__pycache__/*",
                "*/migrations/*",
                "*/conftest.py",
            ],
        )

        # 开始覆盖率收集
        cov.start()

        try:
            # 运行所有Sprint 7相关测试
            test_modules = [
                "tests/unit/test_elo_rating_system.py",
                "tests/unit/test_poisson_features.py",
                "tests/unit/test_odds_movement_features.py",
                "tests/integration/test_service_integration.py",
                "tests/performance/",
            ]

            # 运行pytest
            result = pytest.main(["--tb=short", "-v", *test_modules])

            if result != 0:
                logger.warning(f"⚠️ 测试执行完成但有失败，退出码: {result}")

        finally:
            # 停止覆盖率收集
            cov.stop()
            cov.save()

        # 生成覆盖率数据
        coverage_data = cov.get_data()

        # 计算总体覆盖率
        total_statements = 0
        covered_statements = 0

        file_analysis = {}

        for filename in coverage_data.measured_files():
            if "src" in filename:
                analysis = cov.analysis2(filename)
                file_statements = len(analysis[1])  # 所有语句
                covered_file_statements = len(analysis[1] - analysis[2])  # 已覆盖语句

                total_statements += file_statements
                covered_statements += covered_file_statements

                file_analysis[filename] = {
                    "total_statements": file_statements,
                    "covered_statements": covered_file_statements,
                    "coverage_percentage": (
                        (covered_file_statements / file_statements * 100) if file_statements > 0 else 0
                    ),
                    "missing_lines": list(analysis[2]),
                }

        overall_coverage = (covered_statements / total_statements * 100) if total_statements > 0 else 0

        return {
            "overall_coverage": overall_coverage,
            "total_statements": total_statements,
            "covered_statements": covered_statements,
            "file_analysis": file_analysis,
            "raw_data": coverage_data,
        }

    async def _analyze_core_algorithm_coverage(self, coverage_data: dict[str, Any]) -> dict[str, Any]:
        """分析核心算法覆盖率"""
        logger.info("🎯 分析核心算法覆盖率")

        core_files_coverage = {}
        total_statements = 0
        covered_statements = 0

        for module in self.core_algorithm_modules:
            # 转换模块路径为文件路径
            file_path = module.replace(".", "/") + ".py"
            matching_files = [f for f in coverage_data["file_analysis"].keys() if file_path in f]

            if matching_files:
                file_data = coverage_data["file_analysis"][matching_files[0]]
                core_files_coverage[module] = file_data
                total_statements += file_data["total_statements"]
                covered_statements += file_data["covered_statements"]
            else:
                core_files_coverage[module] = {
                    "total_statements": 0,
                    "covered_statements": 0,
                    "coverage_percentage": 0,
                    "missing_lines": [],
                    "error": "File not found",
                }

        average_coverage = (covered_statements / total_statements * 100) if total_statements > 0 else 0

        # 检查是否达到阈值
        threshold_met = average_coverage >= self.thresholds.core_algorithms_min

        # 详细分析每个模块
        detailed_analysis = {}
        for module, data in core_files_coverage.items():
            if data["coverage_percentage"] < self.thresholds.core_algorithms_min:
                detailed_analysis[module] = {
                    "status": "below_threshold",
                    "coverage": data["coverage_percentage"],
                    "gap": self.thresholds.core_algorithms_min - data["coverage_percentage"],
                    "priority": ("high" if data["coverage_percentage"] < 70 else "medium"),
                }
            else:
                detailed_analysis[module] = {
                    "status": "meets_threshold",
                    "coverage": data["coverage_percentage"],
                    "gap": 0,
                    "priority": "low",
                }

        return {
            "average_coverage": average_coverage,
            "threshold_met": threshold_met,
            "threshold_target": self.thresholds.core_algorithms_min,
            "total_statements": total_statements,
            "covered_statements": covered_statements,
            "module_coverage": core_files_coverage,
            "detailed_analysis": detailed_analysis,
        }

    async def _analyze_integration_coverage(self, coverage_data: dict[str, Any]) -> dict[str, Any]:
        """分析集成测试覆盖率"""
        logger.info("🔗 分析集成测试覆盖率")

        integration_files_coverage = {}
        total_statements = 0
        covered_statements = 0

        for module in self.integration_modules:
            file_path = module.replace(".", "/") + ".py"
            matching_files = [f for f in coverage_data["file_analysis"].keys() if file_path in f]

            if matching_files:
                file_data = coverage_data["file_analysis"][matching_files[0]]
                integration_files_coverage[module] = file_data
                total_statements += file_data["total_statements"]
                covered_statements += file_data["covered_statements"]

        average_coverage = (covered_statements / total_statements * 100) if total_statements > 0 else 0
        threshold_met = average_coverage >= self.thresholds.integration_tests_min

        return {
            "average_coverage": average_coverage,
            "threshold_met": threshold_met,
            "threshold_target": self.thresholds.integration_tests_min,
            "total_statements": total_statements,
            "covered_statements": covered_statements,
            "module_coverage": integration_files_coverage,
        }

    async def _analyze_performance_coverage(self, coverage_data: dict[str, Any]) -> dict[str, Any]:
        """分析性能测试覆盖率"""
        logger.info("⚡ 分析性能测试覆盖率")

        performance_files_coverage = {}
        total_statements = 0
        covered_statements = 0

        for module in self.performance_modules:
            file_path = module.replace(".", "/") + ".py"
            matching_files = [f for f in coverage_data["file_analysis"].keys() if file_path in f]

            if matching_files:
                file_data = coverage_data["file_analysis"][matching_files[0]]
                performance_files_coverage[module] = file_data
                total_statements += file_data["total_statements"]
                covered_statements += file_data["covered_statements"]

        average_coverage = (covered_statements / total_statements * 100) if total_statements > 0 else 0
        threshold_met = average_coverage >= self.thresholds.performance_tests_min

        return {
            "average_coverage": average_coverage,
            "threshold_met": threshold_met,
            "threshold_target": self.thresholds.performance_tests_min,
            "total_statements": total_statements,
            "covered_statements": covered_statements,
            "module_coverage": performance_files_coverage,
        }

    async def _analyze_coverage_trends(self) -> dict[str, Any]:
        """分析覆盖率趋势"""
        logger.info("📈 分析覆盖率趋势")

        # 获取历史覆盖率数据
        historical_data = await self._load_historical_coverage_data()

        if not historical_data:
            return {
                "trend": "no_data",
                "message": "No historical coverage data available",
                "data_points": 0,
            }

        # 分析趋势
        sorted_data = sorted(historical_data, key=lambda x: x["timestamp"])
        coverage_values = [d["overall_coverage"] for d in sorted_data]

        # 计算趋势方向
        if len(coverage_values) >= 3:
            recent_avg = sum(coverage_values[-3:]) / 3
            earlier_avg = sum(coverage_values[:-3]) / max(len(coverage_values) - 3, 1)

            if recent_avg > earlier_avg + 2:
                trend = "improving"
            elif recent_avg < earlier_avg - 2:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # 计算变化率
        if len(coverage_values) >= 2:
            latest_change = coverage_values[-1] - coverage_values[-2]
            change_rate = (latest_change / coverage_values[-2] * 100) if coverage_values[-2] > 0 else 0
        else:
            change_rate = 0

        return {
            "trend": trend,
            "data_points": len(coverage_values),
            "latest_coverage": coverage_values[-1] if coverage_values else 0,
            "average_coverage": (sum(coverage_values) / len(coverage_values) if coverage_values else 0),
            "highest_coverage": max(coverage_values) if coverage_values else 0,
            "lowest_coverage": min(coverage_values) if coverage_values else 0,
            "recent_change": (coverage_values[-1] - coverage_values[-2] if len(coverage_values) >= 2 else 0),
            "change_rate_percent": change_rate,
            "time_span_days": (
                (sorted_data[-1]["timestamp"] - sorted_data[0]["timestamp"]).days if len(sorted_data) > 1 else 0
            ),
        }

    async def _detect_coverage_regressions(self, coverage_data: dict[str, Any]) -> dict[str, Any]:
        """检测覆盖率回归"""
        logger.info("🔍 检测覆盖率回归")

        # 获取历史数据
        historical_data = await self._load_historical_coverage_data()

        if not historical_data:
            return {
                "regressions": [],
                "message": "No historical data for regression detection",
            }

        latest_data = max(historical_data, key=lambda x: x["timestamp"])
        regressions = []

        # 检查总体覆盖率回归
        if coverage_data["overall_coverage"] < latest_data["overall_coverage"] - 5:  # 5%阈值
            regressions.append(
                {
                    "type": "overall",
                    "current_coverage": coverage_data["overall_coverage"],
                    "previous_coverage": latest_data["overall_coverage"],
                    "regression_amount": latest_data["overall_coverage"] - coverage_data["overall_coverage"],
                    "severity": (
                        "high" if latest_data["overall_coverage"] - coverage_data["overall_coverage"] > 10 else "medium"
                    ),
                }
            )

        # 检查模块级别回归
        for module in self.core_algorithm_modules:
            file_path = module.replace(".", "/") + ".py"
            matching_files = [f for f in coverage_data["file_analysis"].keys() if file_path in f]

            if matching_files and "module_coverage" in latest_data:
                current_coverage = coverage_data["file_analysis"][matching_files[0]]["coverage_percentage"]
                previous_coverage = latest_data.get("module_coverage", {}).get(module, {}).get("coverage_percentage", 0)

                if current_coverage < previous_coverage - 10:  # 10%阈值
                    regressions.append(
                        {
                            "type": "module",
                            "module": module,
                            "current_coverage": current_coverage,
                            "previous_coverage": previous_coverage,
                            "regression_amount": previous_coverage - current_coverage,
                            "severity": ("high" if previous_coverage - current_coverage > 20 else "medium"),
                        }
                    )

        return {
            "regressions": regressions,
            "regression_count": len(regressions),
            "latest_comparison_date": latest_data["timestamp"].isoformat(),
            "overall_regression_detected": any(r["type"] == "overall" for r in regressions),
        }

    async def _generate_html_report(self, report_data: dict[str, Any]) -> str:
        """生成HTML覆盖率报告"""
        logger.info("📄 生成HTML覆盖率报告")

        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sprint 7 测试覆盖率报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; }}
        .section {{ margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        .coverage-high {{ color: #28a745; }}
        .coverage-medium {{ color: #ffc107; }}
        .coverage-low {{ color: #dc3545; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s ease; }}
        .module-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .module-table th, .module-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        .module-table th {{ background: #f8f9fa; font-weight: 600; }}
        .status-badge {{ padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.9em; }}
        .status-pass {{ background: #28a745; }}
        .status-fail {{ background: #dc3545; }}
        .status-warning {{ background: #ffc107; color: #000; }}
        .trend-indicator {{ font-size: 1.2em; margin: 0 5px; }}
        .regression-alert {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .footer {{ text-align: center; margin-top: 40px; padding: 20px; color: #666; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Sprint 7 测试覆盖率报告</h1>
            <p>生成时间: {timestamp}</p>
            <p>足球预测系统 - 核心算法与集成测试覆盖率分析</p>
        </div>

        <!-- 总体覆盖率概览 -->
        <div class="section">
            <h2>📊 总体覆盖率概览</h2>
            <div style="text-align: center; margin: 30px 0;">
                <div class="metric">
                    <div class="metric-value {overall_coverage_class}">{overall_coverage:.1f}%</div>
                    <div class="metric-label">总体覆盖率</div>
                </div>
                <div class="metric">
                    <div class="metric-value {core_coverage_class}">{core_coverage:.1f}%</div>
                    <div class="metric-label">核心算法覆盖率</div>
                </div>
                <div class="metric">
                    <div class="metric-value {integration_coverage_class}">{integration_coverage:.1f}%</div>
                    <div class="metric-label">集成测试覆盖率</div>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {overall_coverage:.1f}%"></div>
            </div>
        </div>

        <!-- 核心算法覆盖率详情 -->
        <div class="section">
            <h2>🎯 核心算法覆盖率详情</h2>
            <table class="module-table">
                <thead>
                    <tr>
                        <th>模块</th>
                        <th>覆盖率</th>
                        <th>状态</th>
                        <th>优先级</th>
                    </tr>
                </thead>
                <tbody>
                    {core_module_rows}
                </tbody>
            </table>
        </div>

        <!-- 集成测试覆盖率详情 -->
        <div class="section">
            <h2>🔗 集成测试覆盖率详情</h2>
            <table class="module-table">
                <thead>
                    <tr>
                        <th>模块</th>
                        <th>覆盖率</th>
                        <th>语句数</th>
                        <th>已覆盖</th>
                    </tr>
                </thead>
                <tbody>
                    {integration_module_rows}
                </tbody>
            </table>
        </div>

        <!-- 覆盖率趋势分析 -->
        <div class="section">
            <h2>📈 覆盖率趋势分析</h2>
            <div style="text-align: center; margin: 20px 0;">
                <div class="metric">
                    <div class="metric-value">{trend_indicator}</div>
                    <div class="metric-label">趋势方向</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{trend_change:+.1f}%</div>
                    <div class="metric-label">近期变化</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{trend_data_points}</div>
                    <div class="metric-label">数据点数</div>
                </div>
            </div>
        </div>

        <!-- 回归检测结果 -->
        {regression_section}

        <div class="footer">
            <p>📝 报告由 Sprint 7 测试覆盖率生成器自动生成</p>
            <p>🚀 Football Prediction System v2.0 - Production Ready</p>
        </div>
    </div>
</body>
</html>
        """

        # 准备数据
        overall_coverage = report_data["overall_coverage"]
        core_coverage = report_data["core_coverage"]["average_coverage"]
        integration_coverage = report_data["integration_coverage"]["average_coverage"]

        # 覆盖率等级样式
        def get_coverage_class(coverage):
            if coverage >= 90:
                return "coverage-high"
            elif coverage >= 75:
                return "coverage-medium"
            else:
                return "coverage-low"

        # 生成核心算法模块行
        core_module_rows = ""
        for module, analysis in report_data["core_coverage"]["detailed_analysis"].items():
            status_class = "status-pass" if analysis["status"] == "meets_threshold" else "status-fail"
            status_text = "✅ 达标" if analysis["status"] == "meets_threshold" else "❌ 未达标"
            priority_text = {"high": "高", "medium": "中", "low": "低"}.get(analysis["priority"], "低")

            module_name = module.split(".")[-1] if "." in module else module
            core_module_rows += f"""
                    <tr>
                        <td>{module_name}</td>
                        <td>{analysis["coverage"]:.1f}%</td>
                        <td><span class="status-badge {status_class}">{status_text}</span></td>
                        <td>{priority_text}</td>
                    </tr>
            """

        # 生成集成测试模块行
        integration_module_rows = ""
        for module, data in report_data["integration_coverage"]["module_coverage"].items():
            module_name = module.split(".")[-1] if "." in module else module
            integration_module_rows += f"""
                    <tr>
                        <td>{module_name}</td>
                        <td>{data["coverage_percentage"]:.1f}%</td>
                        <td>{data["total_statements"]}</td>
                        <td>{data["covered_statements"]}</td>
                    </tr>
            """

        # 趋势分析数据
        trend_analysis = report_data["trend_analysis"]
        trend_indicators = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️",
            "no_data": "❓",
        }
        trend_indicator = trend_indicators.get(trend_analysis["trend"], "❓")
        trend_change = trend_analysis.get("recent_change", 0)
        trend_data_points = trend_analysis["data_points"]

        # 回归检测部分
        regression_section = ""
        if report_data["regression_detection"]["regressions"]:
            regression_rows = ""
            for regression in report_data["regression_detection"]["regressions"]:
                severity_class = "high" if regression["severity"] == "high" else "medium"
                regression_rows += f"""
                    <div class="regression-alert">
                        <strong>{regression["type"].title()} 回归检测到:</strong><br>
                        当前覆盖率: {regression["current_coverage"]:.1f}%<br>
                        之前覆盖率: {regression["previous_coverage"]:.1f}%<br>
                        回退幅度: {regression["regression_amount"]:.1f}% (严重程度: {severity_class})
                    </div>
                """

            regression_section = f"""
                <div class="section">
                    <h2>⚠️ 回归检测结果</h2>
                    {regression_rows}
                </div>
            """

        # 填充模板
        html_content = html_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            overall_coverage=overall_coverage,
            overall_coverage_class=get_coverage_class(overall_coverage),
            core_coverage=core_coverage,
            core_coverage_class=get_coverage_class(core_coverage),
            integration_coverage=integration_coverage,
            integration_coverage_class=get_coverage_class(integration_coverage),
            core_module_rows=core_module_rows,
            integration_module_rows=integration_module_rows,
            trend_indicator=trend_indicator,
            trend_change=trend_change,
            trend_data_points=trend_data_points,
            regression_section=regression_section,
        )

        # 保存HTML报告
        html_file = self.output_dir / f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_file)

    async def _generate_coverage_badge(self, overall_coverage: float) -> dict[str, Any]:
        """生成覆盖率徽章"""
        logger.info("🏆 生成覆盖率徽章")

        # 确定徽章颜色
        if overall_coverage >= 90:
            color = "#28a745"  # 绿色
            status = "Excellent"
        elif overall_coverage >= 80:
            color = "#ffc107"  # 黄色
            status = "Good"
        elif overall_coverage >= 70:
            color = "#fd7e14"  # 橙色
            status = "Fair"
        else:
            color = "#dc3545"  # 红色
            status = "Poor"

        # SVG徽章模板
        svg_template = """
<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="120" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h55v20H0z"/>
    <path fill="{color}" d="M55 0h65v20H55z"/>
    <path fill="url(#b)" d="M0 0h120v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="27.5" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="27.5" y="14">coverage</text>
    <text x="87.5" y="15" fill="#010101" fill-opacity=".3">{coverage:.1f}%</text>
    <text x="87.5" y="14">{coverage:.1f}%</text>
  </g>
</svg>
        """

        svg_content = svg_template.format(coverage=overall_coverage, color=color)

        # 保存徽章
        badge_file = self.output_dir / "coverage_badge.svg"
        with open(badge_file, "w", encoding="utf-8") as f:
            f.write(svg_content)

        # 保存JSON格式的徽章数据
        badge_data = {
            "schemaVersion": 1,
            "label": "coverage",
            "message": f"{overall_coverage:.1f}%",
            "color": color.replace("#", ""),
            "status": status,
            "generated_at": datetime.now().isoformat(),
        }

        badge_json_file = self.output_dir / "coverage_badge.json"
        with open(badge_json_file, "w", encoding="utf-8") as f:
            json.dump(badge_data, f, indent=2)

        return {
            "generated": True,
            "svg_file": str(badge_file),
            "json_file": str(badge_json_file),
            "coverage": overall_coverage,
            "color": color,
            "status": status,
        }

    async def _save_coverage_report(self, report_data: dict[str, Any]) -> Path:
        """保存覆盖率报告"""
        logger.info("💾 保存覆盖率报告")

        # 保存完整的JSON报告
        report_file = self.output_dir / f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        # 更新历史数据
        await self._update_historical_coverage_data(
            {
                "timestamp": datetime.now(),
                "overall_coverage": report_data["overall_coverage"],
                "core_coverage": report_data["core_coverage"]["average_coverage"],
                "integration_coverage": report_data["integration_coverage"]["average_coverage"],
                "module_coverage": report_data["core_coverage"]["module_coverage"],
            }
        )

        return report_file

    async def _load_historical_coverage_data(self) -> list[dict[str, Any]]:
        """加载历史覆盖率数据"""
        history_file = self.output_dir / "coverage_history.json"

        if not history_file.exists():
            return []

        try:
            with open(history_file, encoding="utf-8") as f:
                data = json.load(f)

            # 转换时间戳字符串为datetime对象
            for item in data:
                item["timestamp"] = datetime.fromisoformat(item["timestamp"])

            return data
        except Exception as e:
            logger.warning(f"加载历史覆盖率数据失败: {e}")
            return []

    async def _update_historical_coverage_data(self, new_data: dict[str, Any]):
        """更新历史覆盖率数据"""
        logger.info("📝 更新历史覆盖率数据")

        history_file = self.output_dir / "coverage_history.json"
        existing_data = await self._load_historical_coverage_data()

        # 添加新数据
        existing_data.append(new_data)

        # 只保留最近30天的数据
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered_data = [item for item in existing_data if item["timestamp"] > cutoff_date]

        # 保存更新后的数据
        with open(history_file, "w", encoding="utf-8") as f:
            # 转换datetime对象为字符串
            json_data = []
            for item in filtered_data:
                item_copy = item.copy()
                item_copy["timestamp"] = item_copy["timestamp"].isoformat()
                json_data.append(item_copy)

            json.dump(json_data, f, indent=2)

    async def generate_trend_analysis_only(self) -> dict[str, Any]:
        """仅生成趋势分析报告"""
        logger.info("📈 生成覆盖率趋势分析报告")

        trend_analysis = await self._analyze_coverage_trends()

        # 保存趋势分析报告
        trend_report_file = self.output_dir / f"coverage_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(trend_report_file, "w", encoding="utf-8") as f:
            json.dump(trend_analysis, f, indent=2, default=str)

        return {
            "success": True,
            "trend_report_file": str(trend_report_file),
            "trend_analysis": trend_analysis,
        }

    async def generate_badge_only(self) -> dict[str, Any]:
        """仅生成覆盖率徽章"""
        logger.info("🏆 生成覆盖率徽章")

        # 获取最新的覆盖率数据
        historical_data = await self._load_historical_coverage_data()

        if not historical_data:
            # 如果没有历史数据，运行一次覆盖率测试
            coverage_data = await self._run_coverage_tests()
            overall_coverage = coverage_data["overall_coverage"]
        else:
            latest_data = max(historical_data, key=lambda x: x["timestamp"])
            overall_coverage = latest_data["overall_coverage"]

        badge_data = await self._generate_coverage_badge(overall_coverage)

        return {
            "success": True,
            "badge_data": badge_data,
            "coverage_used": overall_coverage,
        }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 7 测试覆盖率报告生成器")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 完整报告命令
    full_parser = subparsers.add_parser("full-report", help="生成完整覆盖率报告")
    full_parser.add_argument("--output-dir", default="coverage_reports", help="输出目录")

    # 趋势分析命令
    trend_parser = subparsers.add_parser("trend-analysis", help="生成覆盖率趋势分析")
    trend_parser.add_argument("--output-dir", default="coverage_reports", help="输出目录")

    # 徽章生成命令
    badge_parser = subparsers.add_parser("badge-generation", help="生成覆盖率徽章")
    badge_parser.add_argument("--output-dir", default="coverage_reports", help="输出目录")

    args = parser.parse_args()

    generator = CoverageReportGenerator(args.output_dir)

    try:
        if args.command == "full-report":
            result = await generator.generate_full_coverage_report()

            print("\n✅ 覆盖率报告生成完成!")
            print(f"报告文件: {result['report_file']}")
            print(f"总体覆盖率: {result['overall_coverage']:.1f}%")
            print(f"核心算法覆盖率达标: {'是' if result['core_coverage_met'] else '否'}")
            print(f"集成测试覆盖率达标: {'是' if result['integration_coverage_met'] else '否'}")
            print(f"检测到回归: {result['regressions_detected']} 个")
            print(f"徽章生成: {'是' if result['badge_generated'] else '否'}")

            return result

        elif args.command == "trend-analysis":
            result = await generator.generate_trend_analysis_only()

            print("\n📈 趋势分析报告生成完成!")
            print(f"报告文件: {result['trend_report_file']}")

            trend = result["trend_analysis"]
            print(f"趋势方向: {trend['trend']}")
            print(f"数据点数: {trend['data_points']}")
            print(f"最新覆盖率: {trend['latest_coverage']:.1f}%")

            if trend["data_points"] > 0:
                print(f"平均覆盖率: {trend['average_coverage']:.1f}%")
                print(f"最高覆盖率: {trend['highest_coverage']:.1f}%")
                print(f"最低覆盖率: {trend['lowest_coverage']:.1f}%")

            return result

        elif args.command == "badge-generation":
            result = await generator.generate_badge_only()

            print("\n🏆 覆盖率徽章生成完成!")
            print(f"SVG文件: {result['badge_data']['svg_file']}")
            print(f"JSON文件: {result['badge_data']['json_file']}")
            print(f"覆盖率: {result['coverage_used']:.1f}%")
            print(f"状态: {result['badge_data']['status']}")

            return result

        else:
            parser.print_help()
            return None

    except Exception as e:
        logger.error(f"执行失败: {e}")
        print(f"❌ 执行失败: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
