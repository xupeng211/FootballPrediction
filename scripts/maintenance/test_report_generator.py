#!/usr/bin/env python3
"""
测试报告自动生成器
Test Report Auto Generator

自动生成测试健康报告，包括HTML、JSON、Markdown等格式的报告。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class ReportData:
    """报告数据结构"""
    generated_at: str
    test_health_summary: Dict[str, Any]
    test_metrics: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    trends: Dict[str, Any]
    recommendations: List[str]
    summary: Dict[str, Any]

class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

        # 报告输出目录
        self.reports_dir = project_root / "reports" / "test_health"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 监控数据文件
        self.metrics_file = project_root / "logs" / "test_monitoring" / "test_health_metrics.json"
        self.alerts_file = project_root / "logs" / "test_monitoring" / "test_health_alerts.json"

    def _load_monitoring_data(self) -> Tuple[List[Dict], List[Dict]]:
        """加载监控数据"""
        metrics = []
        alerts = []

        # 加载测试指标
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    metrics = json.load(f)
            except Exception as e:
                print(f"⚠️  加载测试指标失败: {e}")

        # 加载警报数据
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    alerts = json.load(f)
            except Exception as e:
                print(f"⚠️  加载警报数据失败: {e}")

        return metrics, alerts

    def _generate_summary(self, metrics: List[Dict], alerts: List[Dict]) -> Dict[str, Any]:
        """生成报告摘要"""
        if not metrics:
            return {
                "total_metrics": 0,
                "latest_health_score": 0,
                "latest_coverage": 0.0,
                "total_alerts": 0,
                "critical_alerts": 0,
                "warning_alerts": 0,
                "status": "no_data"
            }

        latest_metric = metrics[-1]

        # 统计警报
        critical_count = len([a for a in alerts if a.get("severity") == "critical"])
        warning_count = len([a for a in alerts if a.get("severity") == "warning"])
        total_count = len(alerts)

        # 计算趋势
        if len(metrics) >= 2:
            recent_score = metrics[-1]["health_score"]
            previous_score = metrics[-2]["health_score"]
            trend = "improving" if recent_score > previous_score else "declining" if recent_score < previous_score else "stable"
        else:
            trend = "stable"

        # 确定状态
        if latest_metric["health_score"] >= 90:
            status = "excellent"
        elif latest_metric["health_score"] >= 70:
            status = "good"
        elif latest_metric["health_score"] >= 50:
            status = "fair"
        else:
            status = "poor"

        return {
            "total_metrics": len(metrics),
            "latest_health_score": latest_metric["health_score"],
            "latest_coverage": latest_metric["coverage_percentage"],
            "total_tests": latest_metric["total_tests"],
            "passed_tests": latest_metric["passed_tests"],
            "failed_tests": latest_metric["failed_tests"],
            "total_alerts": total_count,
            "critical_alerts": critical_count,
            "warning_alerts": warning_count,
            "trend": trend,
            "status": status,
            "last_check": latest_metric["timestamp"]
        }

    def _generate_recommendations(self, metrics: List[Dict], alerts: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if not metrics:
            return ["📊 建议先运行测试健康监控以收集数据"]

        latest_metric = metrics[-1]

        # 基于覆盖率提供建议
        if latest_metric["coverage_percentage"] < 10:
            recommendations.append("📈 测试覆盖率过低，建议增加单元测试覆盖率")
            recommendations.append("🧪 运行 `python3 scripts/maintenance/coverage_improvement_executor.py` 提升覆盖率")
        elif latest_metric["coverage_percentage"] < 20:
            recommendations.append("📈 覆盖率有提升空间，建议继续增加测试用例")
        elif latest_metric["coverage_percentage"] < 50:
            recommendations.append("📈 覆盖率良好，建议关注核心业务逻辑测试")

        # 基于测试执行提供建议
        if latest_metric["failed_tests"] > 0:
            recommendations.append("🔧 存在失败的测试，建议优先修复")

        if latest_metric["error_tests"] > 0:
            recommendations.append("🚨 存在错误测试，建议检查测试环境和依赖")

        # 基于健康评分提供建议
        if latest_metric["health_score"] < 70:
            recommendations.append("⚠️ 测试健康评分较低，建议全面检查测试系统")
        elif latest_metric["health_score"] < 85:
            recommendations.append("✅ 测试系统良好，建议定期运行健康检查")

        # 基于警报提供建议
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        if critical_alerts:
            recommendations.append("🚨 存在严重警报，建议立即处理")
            for alert in critical_alerts:
                recommendations.append(f"   - {alert['title']}: {alert['message']}")

        # 基于趋势提供建议
        if len(metrics) >= 3:
            recent_scores = [m["health_score"] for m in metrics[-3:]]
            if all(score < 70 for score in recent_scores):
                recommendations.append("📉 测试健康评分持续下降，建议进行深度分析")
            elif all(score > 85 for score in recent_scores):
                recommendations.append("📈 测试健康评分持续改善，继续保持！")

        return recommendations

    def _generate_trends_analysis(self, metrics: List[Dict]) -> Dict[str, Any]:
        """生成趋势分析"""
        if len(metrics) < 2:
            return {"message": "数据不足，无法生成趋势分析"}

        # 获取最近7天的数据
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_metrics = [
            m for m in metrics
            if datetime.fromisoformat(m["timestamp"]) > cutoff_date
        ]

        if len(recent_metrics) < 2:
            return {"message": "最近7天数据不足"}

        # 计算趋势
        health_scores = [m["health_score"] for m in recent_metrics]
        coverage_rates = [m["coverage_percentage"] for m in recent_metrics]

        health_trend = "improving" if health_scores[-1] > health_scores[0] else "declining" if health_scores[-1] < health_scores[0] else "stable"
        coverage_trend = "improving" if coverage_rates[-1] > coverage_rates[0] else "declining" if coverage_rates[-1] < coverage_rates[0] else "stable"

        return {
            "period_days": 7,
            "data_points": len(recent_metrics),
            "health_score": {
                "current": health_scores[-1],
                "average": sum(health_scores) / len(health_scores),
                "min": min(health_scores),
                "max": max(health_scores),
                "trend": health_trend,
                "change": health_scores[-1] - health_scores[0]
            },
            "coverage": {
                "current": coverage_rates[-1],
                "average": sum(coverage_rates) / len(coverage_rates),
                "min": min(coverage_rates),
                "max": max(coverage_rates),
                "trend": coverage_trend,
                "change": coverage_rates[-1] - coverage_rates[0]
            }
        }

    def generate_html_report(self) -> Path:
        """生成HTML格式报告"""
        print("📄 生成HTML报告...")

        # 加载数据
        metrics, alerts = self._load_monitoring_data()

        # 生成报告数据
        summary = self._generate_summary(metrics, alerts)
        trends = self._generate_trends_analysis(metrics)
        recommendations = self._generate_recommendations(metrics, alerts)

        report_data = ReportData(
            generated_at=datetime.now().isoformat(),
            test_health_summary=summary,
            test_metrics=metrics[-5:],  # 最近5次
            alerts=alerts[-10:],     # 最近10个警报
            trends=trends,
            recommendations=recommendations,
            summary=summary
        )

        # 生成HTML内容
        html_content = self._create_html_content(report_data)

        # 保存HTML报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.reports_dir / f"test_health_report_{timestamp}.html"

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ HTML报告已生成: {html_file}")
        return html_file

    def _create_html_content(self, data: ReportData) -> str:
        """创建HTML内容"""
        # 状态颜色映射
        status_colors = {
            "excellent": "#28a745",
            "good": "#17a2b8",
            "fair": "#ffc107",
            "poor": "#dc3545",
            "no_data": "#6c757d"
        }

        # 获取状态颜色
        status_color = status_colors.get(data.summary.get("status", "no_data"), "#6c757d")

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试健康报告 - {data.generated_at[:10]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            color: #6c757d;
            margin: 10px 0 0 0;
            font-size: 1.1em;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            background-color: {status_color};
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .metric-card h3 {{
            margin: 0 0 10px 0;
            color: #495057;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .alerts-section {{
            margin-bottom: 30px;
        }}
        .alert {{
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            border-left: 4px solid;
        }}
        .alert.critical {{
            background: #f8d7da;
            border-color: #dc3545;
        }}
        .alert.warning {{
            background: #fff3cd;
            border-color: #ffc107;
        }}
        .alert.info {{
            background: #d1ecf1;
            border-color: #17a2b8;
        }}
        .recommendations {{
            background: #e8f5e8;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .recommendations h3 {{
            margin: 0 0 15px 0;
            color: #155724;
        }}
        .recommendations ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .recommendations li {{
            margin-bottom: 5px;
        }}
        .trends {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .trends h3 {{
            margin: 0 0 15px 0;
            color: #495057;
        }}
        .trend-item {{
            margin-bottom: 10px;
        }}
        .trend-label {{
            font-weight: bold;
            color: #495057;
        }}
        .trend-value {{
            color: #2c3e50;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 测试健康报告</h1>
            <p>生成时间: {data.generated_at}</p>
            <span class="status-badge" style="background-color: {status_color};">
                {data.summary.get("status", "no_data").upper()}
            </span>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>🏥 健康评分</h3>
                <div class="metric-value">{data.summary.get("latest_health_score", 0)}</div>
                <div class="metric-label">健康评分 (0-100)</div>
            </div>

            <div class="metric-card">
                <h3>📈 覆盖率</h3>
                <div class="metric-value">{data.summary.get("latest_coverage", 0):.1f}%</div>
                <div class="metric-label">测试覆盖率</div>
            </div>

            <div class="metric-card">
                <h3>🧪 测试总数</h3>
                <div class="metric-value">{data.summary.get("total_tests", 0)}</div>
                <div class="metric-label">总测试数</div>
            </div>

            <div class="metric-card">
                <h3>✅ 通过率</h3>
                <div class="metric-value">
                    {((data.summary.get("passed_tests", 0) / max(data.summary.get("total_tests", 1), 1)) * 100):.1f}%
                </div>
                <div class="metric-label">测试通过率</div>
            </div>

            <div class="metric-card">
                <h3>🚨 警报数量</h3>
                <div class="metric-value">{data.summary.get("total_alerts", 0)}</div>
                <div class="metric-label">总警报数</div>
            </div>

            <div class="metric-card">
                <h3>⚠️ 严重警报</h3>
                <div class="metric-value">{data.summary.get("critical_alerts", 0)}</div>
                <div class="metric-label">严重警报数</div>
            </div>
        </div>

        <div class="recommendations">
            <h3>💡 改进建议</h3>
            <ul>
                {"".join([f"<li>{rec}</li>" for rec in data.recommendations])}
            </ul>
        </div>

        <div class="alerts-section">
            <h3>🚨 最近警报</h3>
            {"".join([self._format_alert_html(alert) for alert in data.alerts[:5]])}
        </div>

        <div class="trends">
            <h3>📈 趋势分析</h3>
            {self._format_trends_html(data.trends)}
        </div>

        <div class="footer">
            <p>报告由 FootballPrediction 测试健康监控系统自动生成</p>
            <p>生成时间: {data.generated_at}</p>
        </div>
    </div>
</body>
</html>
        """
        return html

    def _format_alert_html(self, alert: Dict[str, Any]) -> str:
        """格式化警报为HTML"""
        severity_class = alert.get("severity", "info")
        return f"""
        <div class="alert {severity_class}">
            <strong>{alert.get("title", "未知警报")}</strong><br>
            {alert.get("message", "")}<br>
            <small>时间: {alert.get("timestamp", "")}</small>
        </div>
        """

    def _format_trends_html(self, trends: Dict[str, Any]) -> str:
        """格式化趋势为HTML"""
        if "message" in trends:
            return f"<p>{trends['message']}</p>"

        html_parts = []

        for key, data in trends.items():
            if isinstance(data, dict) and "trend" in data:
                trend_icon = "📈" if data["trend"] == "improving" else "📉" if data["trend"] == "declining" else "➡️"
                change_text = f" (+{data.get('change', 0):+d})" if data.get('change', 0) > 0 else f" ({data.get('change', 0):+d})" if data.get('change', 0) < 0 else ""

                html_parts.append(f"""
                <div class="trend-item">
                    <span class="trend-label">{trend_icon} {key.title().replace('_', ' ')}:</span>
                    <span class="trend-value">{data.get('current', 0):.1f}{change_text}</span>
                </div>
                """)

        return "".join(html_parts)

    def generate_json_report(self) -> Path:
        """生成JSON格式报告"""
        print("📄 生成JSON报告...")

        # 加载数据
        metrics, alerts = self._load_monitoring_data()

        # 生成报告数据
        summary = self._generate_summary(metrics, alerts)
        trends = self._generate_trends_analysis(metrics)
        recommendations = self._generate_recommendations(metrics, alerts)

        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator": "TestReportGenerator v1.0",
                "project_root": str(self.project_root)
            },
            "test_health_summary": summary,
            "test_metrics": metrics,
            "alerts": alerts,
            "trends_analysis": trends,
            "recommendations": recommendations,
            "data_sources": {
                "metrics_file": str(self.metrics_file),
                "alerts_file": str(self.alerts_file)
            }
        }

        # 保存JSON报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.reports_dir / f"test_health_report_{timestamp}.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"✅ JSON报告已生成: {json_file}")
        return json_file

    def generate_markdown_report(self) -> Path:
        """生成Markdown格式报告"""
        print("📄 生成Markdown报告...")

        # 加载数据
        metrics, alerts = self._load_monitoring_data()

        # 生成报告数据
        summary = self._generate_summary(metrics, alerts)
        trends = self._generate_trends_analysis(metrics)
        recommendations = self.generate_recommendations(metrics, alerts)

        # 创建Markdown内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status_emoji = {
            "excellent": "🟢",
            "good": "🟡",
            "fair": "🟠",
            "poor": "🔴",
            "no_data": "⚪"
        }

        status_emoji = status_emoji.get(summary.get("status", "no_data"), "⚪")

        markdown_content = f"""# 🧪 测试健康报告

**生成时间**: {timestamp}
**项目根目录**: {self.project_root}
**报告状态**: {status_emoji} {summary.get('status', 'no_data').upper()}

## 📊 测试健康摘要

| 指标 | 当前值 | 说明 |
|------|--------|------|
| 🏥 健康评分 | {summary.get('latest_health_score', 0)} | 0-100分制 |
| 📈 覆盖率 | {summary.get('latest_coverage', 0):.1f}% | 测试覆盖率 |
| 🧪 测试总数 | {summary.get('total_tests', 0)} | 总测试数量 |
| ✅ 通过测试 | {summary.get('passed_tests', 0)} | 通过的测试数 |
| ❌ 失败测试 | {summary.get('failed_tests', 0)} | 失败的测试数 |
| ⚠️ 错误测试 | {summary.get('error_tests', 0)} | 错误的测试数 |
| 🚨 总警报 | {summary.get('total_alerts', 0)} | 总警报数量 |
| 🔥 严重警报 | {summary.get('critical_alerts', 0)} | 严重警报数量 |
| 📈 趋势 | {summary.get('trend', 'stable')} | 健康评分趋势 |

## 💡 改进建议

{chr(10).join(f"- {rec}" for rec in recommendations)}

## 📈 趋势分析

{self._format_trends_markdown(trends)}

## 🚨 最近警报

{chr(10).join([f"- **{alert.get('title', '未知')}**: {alert.get('message', '')} ({alert.get('timestamp', '')})" for alert in alerts[:5]])}

---
*报告由 FootballPrediction 测试健康监控系统自动生成*
*生成时间: {timestamp}*
*工具版本: TestReportGenerator v1.0*
"""

        # 保存Markdown报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = self.reports_dir / f"test_health_report_{timestamp}.md"

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"✅ Markdown报告已生成: {md_file}")
        return md_file

    def _format_trends_markdown(self, trends: Dict[str, Any]) -> str:
        """格式化趋势为Markdown"""
        if "message" in trends:
            return f"📊 {trends['message']}"

        lines = []
        for key, data in trends.items():
            if isinstance(data, dict) and "trend" in data:
                trend_emoji = "📈" if data["trend"] == "improving" else "📉" if data["trend"] == "declining" else "➡️"
                change_text = f" (+{data.get('change', 0):+d})" if data.get('change', 0) > 0 else f" ({data.get('change', 0):+d})" if data.get('change', 0) < 0 else ""

                lines.append(f"- **{trend_emoji} {key.title().replace('_', ' ')}**: {data.get('current', 0):.1f}{change_text}")

        return "\n".join(lines)

    def generate_recommendations(self, metrics: List[Dict], alerts: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if not metrics:
            return ["暂无测试数据，建议先运行测试并收集指标"]

        latest_metrics = metrics[-1] if metrics else {}

        # 基于覆盖率的建议
        coverage = latest_metrics.get("coverage_percentage", 0)
        if coverage < 10:
            recommendations.append("🚨 覆盖率过低(<10%)，建议立即补充核心模块测试")
        elif coverage < 30:
            recommendations.append("📈 覆盖率偏低(<30%)，建议重点提升核心功能测试覆盖")
        elif coverage < 60:
            recommendations.append("✅ 覆盖率尚可(30-60%)，继续完善边界条件测试")
        else:
            recommendations.append("🎉 覆盖率良好(>60%)，保持现有测试质量")

        # 基于失败率的建议
        total_tests = latest_metrics.get("total_tests", 0)
        failed_tests = latest_metrics.get("failed_tests", 0)
        error_tests = latest_metrics.get("error_tests", 0)

        if total_tests > 0:
            fail_rate = ((failed_tests + error_tests) / total_tests) * 100
            if fail_rate > 20:
                recommendations.append("🚨 测试失败率过高(>20%)，优先修复失败的测试")
            elif fail_rate > 10:
                recommendations.append("⚠️ 测试失败率偏高(>10%)，需要关注测试稳定性")
            elif fail_rate > 5:
                recommendations.append("✅ 测试失败率可接受(<10%)，继续监控")

        # 基于警报的建议
        critical_alerts = [a for a in alerts if a.get("severity") == "critical" and not a.get("resolved", True)]
        if critical_alerts:
            recommendations.append(f"🚨 存在{len(critical_alerts)}个未解决的严重警报，需要立即处理")

        # 基于健康评分的建议
        health_score = latest_metrics.get("health_score", 0)
        if health_score < 50:
            recommendations.append("🚨 测试健康状况较差(<50分)，需要全面改进测试策略")
        elif health_score < 70:
            recommendations.append("📊 测试健康状况中等(50-70分)，有较大改进空间")
        elif health_score < 85:
            recommendations.append("✅ 测试健康状况良好(70-85分)，继续保持")
        else:
            recommendations.append("🎉 测试健康状况优秀(>85分)，作为团队标杆")

        # 基于测试执行时间的建议
        execution_time = latest_metrics.get("execution_time_seconds", 0)
        if execution_time > 300:
            recommendations.append("⏱️ 测试执行时间过长(>5分钟)，考虑优化测试性能")

        # 基于测试数量的建议
        if total_tests < 50:
            recommendations.append("🧪 测试数量较少(<50个)，建议增加测试用例覆盖更多场景")
        elif total_tests > 500:
            recommendations.append("📊 测试数量较多(>500个)，确保测试效率和可维护性")

        # 基于错误测试的建议
        if error_tests > 0:
            recommendations.append(f"🐛 存在{error_tests}个错误测试，可能是代码或测试配置问题")

        if not recommendations:
            recommendations.append("✅ 测试状况良好，继续保持当前质量标准")

        return recommendations

    def generate_all_reports(self) -> Dict[str, Path]:
        """生成所有格式的报告"""
        print("🚀 开始生成测试健康报告...")

        reports = {}

        try:
            # 生成HTML报告
            reports["html"] = self.generate_html_report()
        except Exception as e:
            print(f"❌ HTML报告生成失败: {e}")

        try:
            # 生成JSON报告
            reports["json"] = self.generate_json_report()
        except Exception as e:
            print(f"❌ JSON报告生成失败: {e}")

        try:
            # 生成Markdown报告
            reports["markdown"] = self.generate_markdown_report()
        except Exception as e:
            print(f"❌ Markdown报告生成失败: {e}")

        return reports

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FootballPrediction 测试报告自动生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python3 test_report_generator.py                    # 生成所有格式报告
  python3 test_report_generator.py --html             # 仅生成HTML报告
  python3 test_report_generator.py --json             # 仅生成JSON报告
  python3 test_report_generator.py --markdown         # 仅生成Markdown报告
        """
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径 (默认: 自动检测)"
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="仅生成HTML格式报告"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="仅生成JSON格式报告"
    )

    parser.add_argument(
        "--markdown",
        action="store_true",
        help="仅生成Markdown格式报告"
    )

    args = parser.parse_args()

    # 创建报告生成器实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    generator = TestReportGenerator(project_root)

    try:
        if args.html:
            # 仅生成HTML报告
            html_file = generator.generate_html_report()
            print(f"\n📄 HTML报告已生成: {html_file}")

        elif args.json:
            # 仅生成JSON报告
            json_file = generator.generate_json_report()
            print(f"\n📄 JSON报告已生成: {json_file}")

        elif args.markdown:
            # 仅生成Markdown报告
            md_file = generator.generate_markdown_report()
            print(f"\n📄 Markdown报告已生成: {md_file}")

        else:
            # 生成所有格式的报告
            reports = generator.generate_all_reports()
            print(f"\n📊 报告生成完成:")
            for format_type, file_path in reports.items():
                print(f"  - {format_type.upper()}: {file_path}")

            print(f"\n📁 报告目录: {generator.reports_dir}")
            print("💡 所有报告文件已保存，可通过浏览器或文档查看器查看")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()