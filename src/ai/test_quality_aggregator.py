#!/usr/bin/env python3
"""
风险控制质量聚合器 - 整合所有测试结果，提供综合质量评估
"""

import json
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics

# 导入其他测试模块
from src.ai.mutation_tester import SelectiveMutationTester
from src.ai.flaky_test_detector import SmartFlakyTestDetector
from src.ai.performance_benchmark import RelativePerformanceBenchmark

logger = logging.getLogger(__name__)

@dataclass
class QualityAggregationConfig:
    """质量聚合配置"""
    # 权重配置
    mutation_weight: float = 0.3  # 突变测试权重
    flaky_weight: float = 0.25   # Flaky测试权重
    performance_weight: float = 0.2  # 性能测试权重
    coverage_weight: float = 0.25  # 覆盖率权重

    # 质量阈值
    excellent_threshold: float = 0.85  # 优秀阈值
    good_threshold: float = 0.70      # 良好阈值
    acceptable_threshold: float = 0.55  # 可接受阈值

    # 风险控制
    max_execution_time: int = 600  # 最大执行时间（10分钟）
    enable_mutation: bool = True   # 启用突变测试
    enable_flaky: bool = True      # 启用Flaky测试
    enable_performance: bool = True # 启用性能测试
    enable_coverage: bool = True   # 启用覆盖率测试

    # CI集成
    non_blocking_mode: bool = True  # 非阻塞模式
    fail_fast: bool = False        # 快速失败

class TestQualityAggregator:
    """测试质量聚合器"""

    def __init__(self, config: Optional[QualityAggregationConfig] = None):
        self.config = config or QualityAggregationConfig()
        self.results_dir = Path("docs/_reports/quality")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.quality_history_file = self.results_dir / "quality_history.json"

        # 初始化测试器
        self.mutation_tester = SelectiveMutationTester() if self.config.enable_mutation else None
        self.flaky_detector = SmartFlakyTestDetector() if self.config.enable_flaky else None
        self.performance_benchmark = RelativePerformanceBenchmark() if self.config.enable_performance else None

    def run_comprehensive_quality_check(self, incremental: bool = True) -> Dict:
        """运行综合质量检查"""
        start_time = time.time()

        # 初始化结果
        quality_results = {
            "timestamp": datetime.now().isoformat(),
            "execution_mode": "incremental" if incremental else "full",
            "components": {},
            "overall_score": 0,
            "quality_grade": "unknown",
            "recommendations": [],
            "risks": [],
            "execution_time": 0
        }

        logger.info("Starting comprehensive quality check...")

        # 执行各项测试
        test_results = {}

        # 1. 突变测试
        if self.config.enable_mutation:
            try:
                logger.info("Running mutation testing...")
                mutation_result = self.mutation_tester.run_mutation_tests(incremental=incremental)
                test_results["mutation"] = self._analyze_mutation_result(mutation_result)
                logger.info(f"Mutation testing completed in {mutation_result.get('execution_time', 0):.1f}s")
            except Exception as e:
                logger.error(f"Mutation testing failed: {e}")
                test_results["mutation"] = {"error": str(e), "score": 0}

        # 2. Flaky测试
        if self.config.enable_flaky:
            try:
                logger.info("Running flaky test detection...")
                flaky_result = self.flaky_detector.detect_flaky_tests(incremental=incremental)
                test_results["flaky"] = self._analyze_flaky_result(flaky_result)
                logger.info(f"Flaky test detection completed in {flaky_result.get('execution_time', 0):.1f}s")
            except Exception as e:
                logger.error(f"Flaky test detection failed: {e}")
                test_results["flaky"] = {"error": str(e), "score": 0}

        # 3. 性能测试
        if self.config.enable_performance:
            try:
                logger.info("Running performance benchmark...")
                perf_result = self.performance_benchmark.run_performance_benchmarks(update_baselines=False)
                test_results["performance"] = self._analyze_performance_result(perf_result)
                logger.info(f"Performance benchmark completed in {perf_result.get('execution_time', 0):.1f}s")
            except Exception as e:
                logger.error(f"Performance benchmark failed: {e}")
                test_results["performance"] = {"error": str(e), "score": 0}

        # 4. 覆盖率测试
        if self.config.enable_coverage:
            try:
                logger.info("Running coverage analysis...")
                coverage_result = self._run_coverage_analysis()
                test_results["coverage"] = self._analyze_coverage_result(coverage_result)
                logger.info("Coverage analysis completed")
            except Exception as e:
                logger.error(f"Coverage analysis failed: {e}")
                test_results["coverage"] = {"error": str(e), "score": 0}

        # 检查总超时
        if time.time() - start_time > self.config.max_execution_time:
            logger.warning(f"Quality check timed out after {self.config.max_execution_time}s")
            quality_results["timeout"] = True
            if self.config.fail_fast:
                quality_results["error"] = "Quality check timed out"
                return quality_results

        # 计算综合得分
        overall_score = self._calculate_overall_score(test_results)
        quality_results["overall_score"] = overall_score
        quality_results["components"] = test_results

        # 评估质量等级
        quality_results["quality_grade"] = self._evaluate_quality_grade(overall_score)

        # 生成建议和风险
        quality_results["recommendations"] = self._generate_recommendations(test_results, overall_score)
        quality_results["risks"] = self._identify_risks(test_results)

        # 计算执行时间
        quality_results["execution_time"] = time.time() - start_time

        # 保存结果
        self._save_quality_results(quality_results)

        # 更新历史数据
        self._update_quality_history(quality_results)

        return quality_results

    def _analyze_mutation_result(self, result: Dict) -> Dict:
        """分析突变测试结果"""
        if "error" in result:
            return {"error": result["error"], "score": 0}

        mutation_data = result.get("results", {})
        total_mutants = mutation_data.get("total", 0)
        killed_mutants = mutation_data.get("killed", 0)

        score = killed_mutants / total_mutants if total_mutants > 0 else 0

        return {
            "score": score,
            "total_mutants": total_mutants,
            "killed_mutants": killed_mutants,
            "survived_mutants": mutation_data.get("survived", 0),
            "mutation_score": mutation_data.get("score", 0),
            "execution_time": result.get("execution_time", 0)
        }

    def _analyze_flaky_result(self, result: Dict) -> Dict:
        """分析Flaky测试结果"""
        if "error" in result:
            return {"error": result["error"], "score": 0}

        summary = result.get("summary", {})
        total_tests = summary.get("total_tests", 0)
        flaky_tests = summary.get("flaky_tests", 0)

        # Flaky测试分数：1 - (flaky_tests / total_tests)
        score = 1 - (flaky_tests / total_tests) if total_tests > 0 else 1

        return {
            "score": score,
            "total_tests": total_tests,
            "flaky_tests": flaky_tests,
            "external_tests": summary.get("external_tests", 0),
            "execution_time": summary.get("execution_time", 0)
        }

    def _analyze_performance_result(self, result: Dict) -> Dict:
        """分析性能测试结果"""
        if "error" in result:
            return {"error": result["error"], "score": 0}

        summary = result.get("summary", {})
        total_functions = summary.get("total_functions", 0)
        successful_functions = summary.get("successful_functions", 0)
        alerts = summary.get("alerts", [])

        # 性能分数：成功函数比例减去警报影响
        success_rate = successful_functions / total_functions if total_functions > 0 else 0
        alert_penalty = min(len(alerts) * 0.1, 0.5)  # 每个警报扣0.1分，最多扣0.5分
        score = max(0, success_rate - alert_penalty)

        return {
            "score": score,
            "total_functions": total_functions,
            "successful_functions": successful_functions,
            "failed_functions": summary.get("failed_functions", 0),
            "alerts_count": len(alerts),
            "critical_alerts": len([a for a in alerts if a.get('type') == 'critical']),
            "execution_time": summary.get("execution_time", 0)
        }

    def _run_coverage_analysis(self) -> Dict:
        """运行覆盖率分析"""
        try:
            # 使用现有的覆盖率测试命令
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=src", "--cov-report=json", "--cov-report=term-missing"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd="."
            )

            if result.returncode == 0:
                # 解析覆盖率结果
                coverage_file = Path("coverage.json")
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                    return {"success": True, "data": coverage_data}
                else:
                    return {"success": False, "error": "Coverage report not found"}
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_coverage_result(self, result: Dict) -> Dict:
        """分析覆盖率结果"""
        if not result.get("success"):
            return {"error": result.get("error", "Unknown error"), "score": 0}

        coverage_data = result.get("data", {})
        total_covered = coverage_data.get("totals", {}).get("covered_lines", 0)
        total_lines = coverage_data.get("totals", {}).get("num_statements", 0)

        coverage_pct = total_covered / total_lines if total_lines > 0 else 0

        return {
            "score": coverage_pct,
            "total_lines": total_lines,
            "covered_lines": total_covered,
            "coverage_pct": coverage_pct * 100
        }

    def _calculate_overall_score(self, test_results: Dict) -> float:
        """计算综合得分"""
        weighted_scores = []

        if "mutation" in test_results:
            weighted_scores.append(test_results["mutation"]["score"] * self.config.mutation_weight)

        if "flaky" in test_results:
            weighted_scores.append(test_results["flaky"]["score"] * self.config.flaky_weight)

        if "performance" in test_results:
            weighted_scores.append(test_results["performance"]["score"] * self.config.performance_weight)

        if "coverage" in test_results:
            weighted_scores.append(test_results["coverage"]["score"] * self.config.coverage_weight)

        return sum(weighted_scores) if weighted_scores else 0

    def _evaluate_quality_grade(self, score: float) -> str:
        """评估质量等级"""
        if score >= self.config.excellent_threshold:
            return "excellent"
        elif score >= self.config.good_threshold:
            return "good"
        elif score >= self.config.acceptable_threshold:
            return "acceptable"
        else:
            return "poor"

    def _generate_recommendations(self, test_results: Dict, overall_score: float) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 突变测试建议
        if "mutation" in test_results:
            mutation = test_results["mutation"]
            if mutation.get("score", 0) < 0.6:
                recommendations.append("加强突变测试，增加测试用例覆盖率")
            if mutation.get("survived_mutants", 0) > 5:
                recommendations.append(f"修复{mutation['survived_mutants']}个存活突变，提高测试质量")

        # Flaky测试建议
        if "flaky" in test_results:
            flaky = test_results["flaky"]
            if flaky.get("flaky_tests", 0) > 0:
                recommendations.append(f"修复{flaky['flaky_tests']}个Flaky测试，提高测试稳定性")

        # 性能测试建议
        if "performance" in test_results:
            perf = test_results["performance"]
            if perf.get("critical_alerts", 0) > 0:
                recommendations.append("解决性能退化问题，优化关键函数执行时间")
            if perf.get("failed_functions", 0) > 0:
                recommendations.append(f"修复{perf['failed_functions']}个性能测试失败")

        # 覆盖率建议
        if "coverage" in test_results:
            coverage = test_results["coverage"]
            if coverage.get("coverage_pct", 0) < 80:
                recommendations.append("提高代码覆盖率，添加更多测试用例")

        # 整体建议
        if overall_score >= self.config.excellent_threshold:
            recommendations.append("代码质量优秀，继续保持当前标准")
        elif overall_score >= self.config.good_threshold:
            recommendations.append("代码质量良好，有改进空间")
        elif overall_score >= self.config.acceptable_threshold:
            recommendations.append("代码质量可接受，建议优先修复关键问题")
        else:
            recommendations.append("代码质量需要显著提升，建议制定质量改进计划")

        return recommendations

    def _identify_risks(self, test_results: Dict) -> List[Dict]:
        """识别风险"""
        risks = []

        # 突变测试风险
        if "mutation" in test_results:
            mutation = test_results["mutation"]
            if mutation.get("score", 0) < 0.4:
                risks.append({
                    "type": "high",
                    "category": "test_quality",
                    "message": "突变测试分数过低，测试质量存在严重风险"
                })

        # Flaky测试风险
        if "flaky" in test_results:
            flaky = test_results["flaky"]
            if flaky.get("flaky_tests", 0) > 2:
                risks.append({
                    "type": "medium",
                    "category": "test_stability",
                    "message": f"发现{flaky['flaky_tests']}个Flaky测试，影响测试稳定性"
                })

        # 性能风险
        if "performance" in test_results:
            perf = test_results["performance"]
            if perf.get("critical_alerts", 0) > 0:
                risks.append({
                    "type": "high",
                    "category": "performance",
                    "message": f"发现{perf['critical_alerts']}个严重性能问题"
                })

        # 覆盖率风险
        if "coverage" in test_results:
            coverage = test_results["coverage"]
            if coverage.get("coverage_pct", 0) < 60:
                risks.append({
                    "type": "medium",
                    "category": "coverage",
                    "message": "代码覆盖率过低，存在测试盲区"
                })

        return risks

    def _save_quality_results(self, results: Dict):
        """保存质量检查结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"quality_report_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 更新最新结果
        latest_file = self.results_dir / "latest_quality_report.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Quality report saved to {result_file}")

    def _update_quality_history(self, results: Dict):
        """更新质量历史数据"""
        history = []
        if self.quality_history_file.exists():
            try:
                with open(self.quality_history_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load quality history: {e}")

        # 添加新结果（保留最近50条记录）
        history.append({
            "timestamp": results["timestamp"],
            "overall_score": results["overall_score"],
            "quality_grade": results["quality_grade"],
            "execution_time": results["execution_time"]
        })

        history = history[-50:]  # 保留最近50条记录

        with open(self.quality_history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def generate_quality_report(self) -> str:
        """生成质量报告"""
        latest_file = self.results_dir / "latest_quality_report.json"
        if not latest_file.exists():
            return "No quality report available"

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            grade_emoji = {
                "excellent": "🌟",
                "good": "✅",
                "acceptable": "⚠️",
                "poor": "❌"
            }

            report = f"""
## 📊 综合质量评估报告

### 整体质量
- **质量等级**: {grade_emoji.get(results.get('quality_grade', 'unknown'), '❓')} {results.get('quality_grade', 'unknown').upper()}
- **综合得分**: {results.get('overall_score', 0):.2%}
- **执行时间**: {results.get('execution_time', 0):.1f}秒
- **执行模式**: {results.get('execution_mode', 'unknown')}

### 各项指标得分
"""

            # 添加各项指标详情
            components = results.get("components", {})
            for component, data in components.items():
                if "error" not in data:
                    score = data.get("score", 0)
                    report += f"- **{component.title()}**: {score:.2%}\n"

            # 添加建议
            recommendations = results.get("recommendations", [])
            if recommendations:
                report += "\n### 🎯 改进建议\n"
                for rec in recommendations[:3]:  # 只显示前3个
                    report += f"- {rec}\n"

            # 添加风险
            risks = results.get("risks", [])
            if risks:
                report += "\n### ⚠️ 风险提示\n"
                for risk in risks:
                    risk_emoji = "🚨" if risk.get("type") == "high" else "⚠️"
                    report += f"- {risk_emoji} {risk.get('message', 'Unknown risk')}\n"

            return report

        except Exception as e:
            logger.error(f"Failed to generate quality report: {e}")
            return "Failed to generate quality report"

    def get_ci_status(self) -> Dict:
        """获取CI状态"""
        latest_file = self.results_dir / "latest_quality_report.json"
        if not latest_file.exists():
            return {"status": "no_data", "should_fail": False}

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            quality_grade = results.get("quality_grade", "unknown")
            overall_score = results.get("overall_score", 0)

            # CI失败条件
            should_fail = (
                quality_grade == "poor" or
                (quality_grade == "acceptable" and not self.config.non_blocking_mode) or
                overall_score < self.config.acceptable_threshold
            )

            return {
                "status": quality_grade,
                "score": overall_score,
                "should_fail": should_fail,
                "non_blocking": self.config.non_blocking_mode
            }

        except Exception as e:
            logger.error(f"Failed to get CI status: {e}")
            return {"status": "error", "should_fail": False}


def main():
    """主函数 - 用于测试"""
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description="Test Quality Aggregator")
    parser.add_argument("--incremental", action="store_true", default=True,
                       help="Run incremental quality check")
    parser.add_argument("--full", action="store_true",
                       help="Run full quality check")
    parser.add_argument("--report-only", action="store_true",
                       help="Only show quality report")
    parser.add_argument("--ci-status", action="store_true",
                       help="Show CI status")

    args = parser.parse_args()

    aggregator = TestQualityAggregator()

    if args.report_only:
        print(aggregator.generate_quality_report())
        return

    if args.ci_status:
        status = aggregator.get_ci_status()
        print(f"CI Status: {status}")
        return

    incremental_mode = args.incremental and not args.full
    results = aggregator.run_comprehensive_quality_check(incremental=incremental_mode)
    print(aggregator.generate_quality_report())


if __name__ == "__main__":
    main()