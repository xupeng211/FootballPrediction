#!/usr/bin/env python3
"""
自动化测试质量报告生成器
生成包含覆盖率、性能、趋势的综合报告
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.monitoring.test_quality_monitor import TestQualityMonitor
from tests.monitoring.coverage_optimization import CoverageOptimizer


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.output_dir = self.project_root / "reports" / "test-quality"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_full_report(self) -> Dict[str, Any]:
        """生成完整的测试质量报告"""
        print("🚀 开始生成测试质量报告...")

        # 1. 收集质量指标
        print("\n1️⃣ 收集测试质量指标...")
        monitor = TestQualityMonitor(str(self.project_root))
        quality_report = monitor.generate_quality_report()

        # 2. 分析覆盖率
        print("\n2️⃣ 分析覆盖率...")
        optimizer = CoverageOptimizer(str(self.project_root))
        coverage_analysis = optimizer.run_coverage_analysis()

        # 3. 生成优化计划
        print("\n3️⃣ 生成优化计划...")
        optimization_plan = optimizer.create_optimization_plan()

        # 4. 收集历史趋势
        print("\n4️⃣ 分析历史趋势...")
        trends = self._analyze_trends()

        # 5. 生成综合报告
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "report_version": "1.0"
            },
            "executive_summary": self._generate_executive_summary(quality_report, coverage_analysis),
            "quality_metrics": quality_report,
            "coverage_analysis": coverage_analysis,
            "optimization_plan": optimization_plan,
            "trends": trends,
            "recommendations": self._generate_recommendations(quality_report, coverage_analysis, optimization_plan),
            "action_items": self._generate_action_items(optimization_plan)
        }

        # 保存报告
        self._save_report(report)

        # 生成HTML报告
        self._generate_html_report(report)

        # 生成Markdown报告
        self._generate_markdown_report(report)

        return report

    def _generate_executive_summary(self, quality_report: Dict, coverage_analysis: Dict) -> Dict[str, Any]:
        """生成执行摘要"""
        quality_score = quality_report.get("quality_score", {}).get("total_score", 0)
        quality_grade = quality_report.get("quality_score", {}).get("grade", "N/A")
        overall_coverage = quality_report.get("coverage", {}).get("overall_coverage", 0)

        # 计算趋势
        trend = "stable"
        if "trends" in quality_report:
            if quality_report["trends"].get("coverage_trend") == "improving":
                trend = "improving"
            elif quality_report["trends"].get("coverage_trend") == "degrading":
                trend = "degrading"

        return {
            "quality_score": quality_score,
            "quality_grade": quality_grade,
            "overall_coverage": overall_coverage,
            "trend": trend,
            "status": self._get_status(quality_score, overall_coverage),
            "key_findings": [
                f"测试质量评分: {quality_score}/100 ({quality_grade}级)",
                f"整体覆盖率: {overall_coverage:.1f}%",
                f"趋势: {trend}",
                f"低覆盖率模块: {len(coverage_analysis.get('low_coverage_modules', []))}"
            ]
        }

    def _get_status(self, quality_score: float, coverage: float) -> str:
        """获取总体状态"""
        if quality_score >= 85 and coverage >= 25:
            return "优秀"
        elif quality_score >= 70 and coverage >= 20:
            return "良好"
        elif quality_score >= 60 and coverage >= 15:
            return "需要改进"
        else:
            return "紧急改进"

    def _analyze_trends(self) -> Dict[str, Any]:
        """分析历史趋势"""
        history_file = self.project_root / "tests" / "metrics" / "history.json"

        if not history_file.exists():
            return {"message": "无历史数据"}

        with open(history_file) as f:
            history = json.load(f)

        # 获取最近30天的数据
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_history = [
            record for record in history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_date
        ]

        if len(recent_history) < 2:
            return {"message": "数据不足"}

        # 计算趋势
        coverage_trend = []
        score_trend = []

        for record in recent_history:
            if "coverage" in record and "overall_coverage" in record["coverage"]:
                coverage_trend.append(record["coverage"]["overall_coverage"])
            if "quality_score" in record:
                score_trend.append(record["quality_score"])

        return {
            "period": "最近30天",
            "data_points": len(recent_history),
            "coverage_trend": self._calculate_trend(coverage_trend),
            "score_trend": self._calculate_trend(score_trend),
            "average_coverage": sum(coverage_trend) / len(coverage_trend) if coverage_trend else 0,
            "average_score": sum(score_trend) / len(score_trend) if score_trend else 0
        }

    def _calculate_trend(self, data: List[float]) -> Dict[str, Any]:
        """计算趋势"""
        if len(data) < 2:
            return {"status": "stable", "change": 0}

        start = data[0]
        end = data[-1]
        change = ((end - start) / start * 100) if start > 0 else 0

        if change > 5:
            status = "improving"
        elif change < -5:
            status = "degrading"
        else:
            status = "stable"

        return {
            "status": status,
            "change": change,
            "start_value": start,
            "end_value": end
        }

    def _generate_recommendations(self, quality_report: Dict, coverage_analysis: Dict, optimization_plan: Dict) -> List[Dict[str, Any]]:
        """生成建议"""
        recommendations = []

        # 质量相关建议
        if quality_report.get("quality_score", {}).get("total_score", 0) < 80:
            recommendations.append({
                "category": "质量",
                "priority": "high",
                "title": "提升测试质量评分",
                "description": "当前测试质量评分低于80分，需要重点关注",
                "actions": [
                    "增加测试覆盖率",
                    "提高测试稳定性",
                    "优化测试性能"
                ]
            })

        # 覆盖率相关建议
        overall_coverage = quality_report.get("coverage", {}).get("overall_coverage", 0)
        if overall_coverage < 20:
            recommendations.append({
                "category": "覆盖率",
                "priority": "critical",
                "title": "提高代码覆盖率",
                "description": f"当前覆盖率{overall_coverage:.1f}%低于20%基线",
                "actions": [
                    "为未覆盖的函数添加测试",
                    "覆盖条件分支",
                    "使用参数化测试"
                ]
            })

        # 低覆盖率模块建议
        low_modules = coverage_analysis.get("low_coverage_modules", [])
        if low_modules:
            recommendations.append({
                "category": "覆盖率",
                "priority": "high",
                "title": "处理低覆盖率模块",
                "description": f"有{len(low_modules)}个模块覆盖率低于25%",
                "actions": [
                    f"重点优化: {', '.join(low_modules[:3])}",
                    "使用覆盖率优化工具生成测试模板"
                ]
            })

        # 性能建议
        if quality_report.get("performance", {}).get("total_time", 0) > 60:
            recommendations.append({
                "category": "性能",
                "priority": "medium",
                "title": "优化测试执行时间",
                "description": "测试执行时间超过60秒",
                "actions": [
                    "使用并行测试执行",
                    "优化慢速测试",
                    "使用更快的Mock策略"
                ]
            })

        return recommendations

    def _generate_action_items(self, optimization_plan: Dict) -> List[Dict[str, Any]]:
        """生成行动项"""
        action_items = []

        # 从优化计划中提取行动项
        if "phases" in optimization_plan:
            for i, phase in enumerate(optimization_plan["phases"], 1):
                action_items.append({
                    "phase": f"阶段{i}: {phase['name']}",
                    "modules": phase.get("modules", []),
                    "estimated_effort": phase.get("estimated_effort", "未知"),
                    "target_increase": phase.get("target_increase", 0),
                    "actions": phase.get("actions", []),
                    "deadline": self._calculate_deadline(i)
                })

        # 添加常规行动项
        action_items.extend([
            {
                "phase": "持续改进",
                "actions": [
                    "每周运行质量监控",
                    "审查失败的测试",
                    "更新测试文档"
                ],
                "frequency": "weekly"
            },
            {
                "phase": "团队培训",
                "actions": [
                    "分享测试最佳实践",
                    "代码审查培训",
                    "新测试工具介绍"
                ],
                "frequency": "monthly"
            }
        ])

        return action_items

    def _calculate_deadline(self, phase: int) -> str:
        """计算截止日期"""
        days_ahead = phase * 7  # 每阶段一周
        deadline = datetime.now() + timedelta(days=days_ahead)
        return deadline.strftime("%Y-%m-%d")

    def _save_report(self, report: Dict[str, Any]):
        """保存JSON报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"test_quality_report_{timestamp}.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"✅ JSON报告已保存: {json_file}")

    def _generate_html_report(self, report: Dict[str, Any]):
        """生成HTML报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.output_dir / f"test_quality_report_{timestamp}.html"

        html_content = self._create_html_template(report)

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ HTML报告已保存: {html_file}")

    def _create_html_template(self, report: Dict[str, Any]) -> str:
        """创建HTML模板"""
        exec_summary = report["executive_summary"]
        quality_metrics = report["quality_metrics"]
        recommendations = report["recommendations"]

        # 状态颜色映射
        status_colors = {
            "优秀": "#28a745",
            "良好": "#17a2b8",
            "需要改进": "#ffc107",
            "紧急改进": "#dc3545"
        }

        status_color = status_colors.get(exec_summary["status"], "#6c757d")

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试质量报告 - Football Prediction</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background: #fff;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .header p {{
            color: #666;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: #fff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .summary-card h3 {{
            color: #666;
            margin-bottom: 10px;
            font-size: 0.9rem;
            text-transform: uppercase;
        }}

        .summary-card .value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: {status_color};
            margin-bottom: 5px;
        }}

        .summary-card .grade {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            background: {status_color};
            color: white;
            font-weight: bold;
        }}

        .section {{
            background: #fff;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}

        .recommendations {{
            list-style: none;
        }}

        .recommendation-item {{
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #007bff;
            background: #f8f9fa;
        }}

        .recommendation-item h4 {{
            color: #495057;
            margin-bottom: 5px;
        }}

        .priority-critical {{
            border-left-color: #dc3545;
        }}

        .priority-high {{
            border-left-color: #ffc107;
        }}

        .priority-medium {{
            border-left-color: #17a2b8;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}

            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 测试质量报告</h1>
            <p>Football Prediction Project - {exec_summary.get('generated_at', '').split('T')[0]}</p>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <h3>质量评分</h3>
                <div class="value">{exec_summary['quality_score']}</div>
                <span class="grade">{exec_summary['quality_grade']}</span>
            </div>

            <div class="summary-card">
                <h3>代码覆盖率</h3>
                <div class="value">{exec_summary['overall_coverage']:.1f}%</div>
                <div style="color: #666;">{exec_summary['trend']}</div>
            </div>

            <div class="summary-card">
                <h3>总体状态</h3>
                <div class="value" style="font-size: 1.5rem;">{exec_summary['status']}</div>
            </div>

            <div class="summary-card">
                <h3>低覆盖率模块</h3>
                <div class="value">{len(coverage_analysis.get('low_coverage_modules', []))}</div>
                <div style="color: #666;">需要关注</div>
            </div>
        </div>

        <div class="section">
            <h2>📋 关键发现</h2>
            <ul style="list-style: none; padding: 0;">
                {"".join([f'<li style="padding: 8px 0;">• {finding}</li>' for finding in exec_summary['key_findings']])}
            </ul>
        </div>

        <div class="section">
            <h2>💡 改进建议</h2>
            <div class="recommendations">
                {"".join([self._format_recommendation(rec) for rec in recommendations])}
            </div>
        </div>

        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>自动化测试质量监控系统</p>
        </div>
    </div>
</body>
</html>
        """
        return html

    def _format_recommendation(self, rec: Dict[str, Any]) -> str:
        """格式化建议"""
        priority_class = f"priority-{rec.get('priority', 'medium')}"
        actions = "".join([f"<li>{action}</li>" for action in rec.get('actions', [])])

        return f"""
        <div class="recommendation-item {priority_class}">
            <h4>{rec['title']}</h4>
            <p>{rec['description']}</p>
            <ul style="margin-top: 10px; padding-left: 20px;">
                {actions}
            </ul>
        </div>
        """

    def _generate_markdown_report(self, report: Dict[str, Any]):
        """生成Markdown报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = self.output_dir / f"test_quality_report_{timestamp}.md"

        exec_summary = report["executive_summary"]
        recommendations = report["recommendations"]

        md_content = f"""# 测试质量报告

## 执行摘要

- **质量评分**: {exec_summary['quality_score']}/100 ({exec_summary['quality_grade']}级)
- **代码覆盖率**: {exec_summary['overall_coverage']:.1f}%
- **趋势**: {exec_summary['trend']}
- **状态**: {exec_summary['status']}

## 关键发现

{chr(10).join([f"- {finding}" for finding in exec_summary['key_findings']])}

## 改进建议

{chr(10).join([self._format_md_recommendation(rec) for rec in recommendations])}

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"✅ Markdown报告已保存: {md_file}")

    def _format_md_recommendation(self, rec: Dict[str, Any]) -> str:
        """格式化Markdown建议"""
        return f"""
### {rec['title']} ({rec['priority'].upper()})

{rec['description']}

**行动项**:
{chr(10).join([f"- {action}" for action in rec.get('actions', [])])}
"""

    def print_summary(self, report: Dict[str, Any]):
        """打印报告摘要"""
        exec_summary = report["executive_summary"]

        print("\n" + "="*60)
        print("📊 测试质量报告摘要")
        print("="*60)

        print(f"\n🎯 质量评分: {exec_summary['quality_score']}/100 ({exec_summary['quality_grade']})")
        print(f"📈 覆盖率: {exec_summary['overall_coverage']:.1f}%")
        print(f"📊 趋势: {exec_summary['trend']}")
        print(f"✨ 状态: {exec_summary['status']}")

        print(f"\n📋 关键发现:")
        for finding in exec_summary['key_findings']:
            print(f"  • {finding}")

        if report['recommendations']:
            print(f"\n💡 优先建议:")
            for rec in report['recommendations'][:3]:
                print(f"  • {rec['title']}")

        print("\n" + "="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试质量报告生成器")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")

    args = parser.parse_args()

    # 创建报告生成器
    generator = TestReportGenerator()

    # 生成报告
    report = generator.generate_full_report()

    # 打印摘要
    if not args.quiet:
        generator.print_summary(report)

    return report


if __name__ == "__main__":
    main()