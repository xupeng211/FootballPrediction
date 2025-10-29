#!/usr/bin/env python3
"""
高级质量度量集成
Advanced Quality Metrics Integration

将高级度量指标集成到现有质量监控系统中
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from src.core.logging_system import get_logger
from src.metrics.advanced_analyzer import AdvancedMetricsAnalyzer

logger = get_logger(__name__)


class QualityMetricsIntegrator:
    """质量度量集成器"""

    def __init__(self):
        self.analyzer = AdvancedMetricsAnalyzer()
        self.logger = get_logger(self.__class__.__name__)

    def enhance_quality_report(self, existing_report: Dict[str, Any]) -> Dict[str, Any]:
        """增强现有质量报告"""
        try:
            # 获取高级度量数据
            project_root = Path(__file__).parent.parent.parent
            advanced_metrics = self.analyzer.run_full_analysis(project_root)

            # 合并到现有报告
            enhanced_report = existing_report.copy()
            enhanced_report["advanced_metrics"] = advanced_metrics

            # 重新计算综合分数（包含高级度量）
            enhanced_overall_score = self._calculate_enhanced_overall_score(enhanced_report)
            enhanced_report["enhanced_overall_score"] = enhanced_overall_score

            # 添加高级度量摘要
            enhanced_report["advanced_summary"] = self._create_advanced_summary(advanced_metrics)

            self.logger.info("高级度量集成完成")
            return enhanced_report

        except Exception as e:
            self.logger.error(f"集成高级度量失败: {e}")
            return existing_report

    def _calculate_enhanced_overall_score(self, report: Dict[str, Any]) -> float:
        """计算增强的综合分数"""
        scores = []

        # 原始质量分数
        original_score = report.get("overall_score", 0)
        scores.append(original_score)

        # 高级度量分数
        advanced_score = report.get("advanced_metrics", {}).get("overall_advanced_score", 0)
        scores.append(advanced_score)

        # 代码质量分数
        code_quality_score = report.get("code_quality_score", 0)
        scores.append(code_quality_score)

        # 安全分数
        security_score = report.get("security_score", 0)
        scores.append(security_score)

        # 计算加权平均（高级度量权重更高）
        if scores:
            # 原始分数 30%，高级度量 40%，代码质量 15%，安全 15%
            weights = [0.3, 0.4, 0.15, 0.15]
            weighted_score = sum(score * weight for score, weight in zip(scores, weights))
            return round(weighted_score, 2)

        return 0.0

    def _create_advanced_summary(self, advanced_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """创建高级度量摘要"""
        summary = {}

        # 复杂度摘要
        complexity = advanced_metrics.get("complexity_metrics", {}).get("summary", {})
        if complexity:
            summary["complexity"] = {
                "avg_cyclomatic_complexity": complexity.get("avg_cyclomatic_complexity", 0),
                "avg_cognitive_complexity": complexity.get("avg_cognitive_complexity", 0),
                "avg_maintainability_index": complexity.get("avg_maintainability_index", 0),
                "max_nesting_depth": complexity.get("max_nesting_depth", 0),
                "total_functions": complexity.get("total_functions", 0),
                "total_classes": complexity.get("total_classes", 0),
            }

        # 技术债务摘要
        debt = advanced_metrics.get("technical_debt", {})
        if debt:
            summary["technical_debt"] = {
                "debt_score": debt.get("debt_score", 0),
                "code_smells_count": len(debt.get("code_smells", [])),
                "duplicate_code_count": len(debt.get("duplicate_code", [])),
                "long_methods_count": len(debt.get("long_methods", [])),
                "large_classes_count": len(debt.get("large_classes", [])),
                "security_issues_count": len(debt.get("security_issues", [])),
            }

        # 性能摘要
        performance = advanced_metrics.get("performance_metrics", {})
        if performance:
            system_metrics = performance.get("system", {})
            summary["performance"] = {
                "cpu_percent": system_metrics.get("cpu_percent", 0),
                "memory_percent": system_metrics.get("memory", {}).get("percent", 0),
                "disk_percent": system_metrics.get("disk", {}).get("percent", 0),
                "process_count": system_metrics.get("process_count", 0),
            }

        # 生成建议
        summary["recommendations"] = self._generate_recommendations(summary)

        return summary

    def _generate_recommendations(self, summary: Dict[str, Any]) -> list:
        """生成改进建议"""
        recommendations = []

        # 复杂度建议
        complexity = summary.get("complexity", {})
        if complexity.get("avg_cyclomatic_complexity", 0) > 10:
            recommendations.append(
                {
                    "type": "complexity",
                    "priority": "high",
                    "message": "平均圈复杂度过高，建议重构复杂函数",
                }
            )

        if complexity.get("max_nesting_depth", 0) > 5:
            recommendations.append(
                {
                    "type": "complexity",
                    "priority": "medium",
                    "message": "嵌套深度过深，建议提取子函数减少嵌套",
                }
            )

        # 技术债务建议
        debt = summary.get("technical_debt", {})
        if debt.get("debt_score", 100) < 70:
            recommendations.append(
                {
                    "type": "technical_debt",
                    "priority": "high",
                    "message": "技术债务分数较低，建议优先处理代码异味和安全问题",
                }
            )

        if debt.get("security_issues_count", 0) > 0:
            recommendations.append(
                {
                    "type": "security",
                    "priority": "critical",
                    "message": f'发现{debt["security_issues_count"]}个安全问题，需要立即处理',
                }
            )

        # 性能建议
        performance = summary.get("performance", {})
        if performance.get("cpu_percent", 0) > 80:
            recommendations.append(
                {
                    "type": "performance",
                    "priority": "medium",
                    "message": "CPU使用率较高，建议优化算法或增加缓存",
                }
            )

        if performance.get("memory_percent", 0) > 80:
            recommendations.append(
                {
                    "type": "performance",
                    "priority": "medium",
                    "message": "内存使用率较高，建议检查内存泄漏",
                }
            )

        return recommendations


def enhance_quality_guardian():
    """为质量守护系统添加高级度量功能"""
    # 这里可以修改 scripts/quality_guardian.py 来集成高级度量
    # 为了避免修改现有文件，我们创建一个包装器
    pass


def main():
    """主函数，用于测试集成"""
    integrator = QualityMetricsIntegrator()

    # 模拟现有质量报告
    existing_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_score": 9.6,
        "coverage_percentage": 84.4,
        "code_quality_score": 10.0,
        "security_score": 10.0,
        "ruff_errors": 0,
        "mypy_errors": 0,
        "file_count": 542,
    }

    # 增强报告
    enhanced_report = integrator.enhance_quality_report(existing_report)

    print("🔍 高级质量度量集成测试")
    print("=" * 50)
    print(f"原始综合分数: {existing_report['overall_score']}")
    print(f"增强综合分数: {enhanced_report.get('enhanced_overall_score', 0)}")
    print(
        f"高级度量分数: {enhanced_report.get('advanced_metrics', {}).get('overall_advanced_score', 0)}"
    )

    # 显示高级摘要
    summary = enhanced_report.get("advanced_summary", {})
    if "complexity" in summary:
        complexity = summary["complexity"]
        print("\n📊 复杂度指标:")
        print(f"  平均圈复杂度: {complexity.get('avg_cyclomatic_complexity', 0):.1f}")
        print(f"  平均可维护性指数: {complexity.get('avg_maintainability_index', 0):.1f}")

    if "technical_debt" in summary:
        debt = summary["technical_debt"]
        print("\n⚠️ 技术债务:")
        print(f"  债务分数: {debt.get('debt_score', 0):.1f}")
        print(f"  代码异味: {debt.get('code_smells_count', 0)}")
        print(f"  安全问题: {debt.get('security_issues_count', 0)}")

    # 显示建议
    recommendations = summary.get("recommendations", [])
    if recommendations:
        print(f"\n💡 改进建议 ({len(recommendations)}条):")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"  {i}. [{rec['priority'].upper()}] {rec['message']}")

    print("\n✅ 高级度量集成测试完成")


if __name__ == "__main__":
    main()
