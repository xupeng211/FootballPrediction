#!/usr/bin/env python3
"""
测试质量仪表板
提供Web界面查看测试质量指标和趋势
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import argparse

try:
    from flask import Flask, render_template_string, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not available, dashboard will run in static mode")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class TestQualityDashboard:
    """测试质量仪表板"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent.parent
        self.metrics_dir = self.project_root / "tests" / "metrics"
        self.templates = self._create_templates()

    def _create_templates(self) -> Dict[str, str]:
        """创建HTML模板"""
        return {
            "dashboard": """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试质量仪表板 - Football Prediction</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2rem;
            margin-bottom: 5px;
        }

        .header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        }

        .metric-label {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }

        .metric-trend {
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .trend-up {
            color: #27ae60;
        }

        .trend-down {
            color: #e74c3c;
        }

        .trend-stable {
            color: #f39c12;
        }

        .charts-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .chart-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        .chart-card h3 {
            margin-bottom: 20px;
            color: #2c3e50;
            font-size: 1.2rem;
        }

        .chart-container {
            position: relative;
            height: 300px;
        }

        .recommendations {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        .recommendations h3 {
            margin-bottom: 15px;
            color: #2c3e50;
        }

        .recommendation-item {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: start;
            gap: 10px;
        }

        .recommendation-item:last-child {
            border-bottom: none;
        }

        .recommendation-icon {
            font-size: 1.2rem;
            margin-top: 2px;
        }

        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
            font-size: 1.1rem;
            color: #666;
        }

        .error {
            background: #fee;
            color: #c33;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }

        .quality-grade {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1rem;
        }

        .grade-A {
            background: #d4edda;
            color: #155724;
        }

        .grade-B {
            background: #cce5ff;
            color: #004085;
        }

        .grade-C {
            background: #fff3cd;
            color: #856404;
        }

        .grade-D {
            background: #f8d7da;
            color: #721c24;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .charts-container {
                grid-template-columns: 1fr;
            }

            .header {
                padding: 15px 20px;
            }

            .header h1 {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 测试质量仪表板</h1>
        <p>Football Prediction Project - 实时测试质量监控</p>
    </div>

    <div class="container">
        <div id="metrics-container" class="metrics-grid">
            <div class="loading">加载测试指标...</div>
        </div>

        <div class="charts-container">
            <div class="chart-card">
                <h3>📈 覆盖率趋势</h3>
                <div class="chart-container">
                    <canvas id="coverageChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h3>⚡ 执行时间趋势</h3>
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
        </div>

        <div class="recommendations">
            <h3>💡 改进建议</h3>
            <div id="recommendations-list">
                <div class="loading">加载建议...</div>
            </div>
        </div>
    </div>

    <script>
        // 加载数据
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/dashboard-data');
                const data = await response.json();

                if (data.error) {
                    showError(data.error);
                    return;
                }

                renderMetrics(data.metrics);
                renderCharts(data.charts);
                renderRecommendations(data.recommendations);

            } catch (error) {
                showError('加载仪表板数据失败: ' + error.message);
            }
        }

        function showError(message) {
            document.getElementById('metrics-container').innerHTML =
                `<div class="error">${message}</div>`;
        }

        function renderMetrics(metrics) {
            const container = document.getElementById('metrics-container');

            const gradeClass = `grade-${metrics.quality_grade}`;
            const trendIcon = {
                'improving': '📈',
                'degrading': '📉',
                'stable': '➡️'
            }[metrics.coverage_trend] || '➡️';

            container.innerHTML = `
                <div class="metric-card">
                    <div class="metric-label">总体质量评分</div>
                    <div class="metric-value">
                        <span class="quality-grade ${gradeClass}">${metrics.quality_grade}</span>
                    </div>
                    <div class="metric-value">${metrics.quality_score}/100</div>
                    <div class="metric-trend">基于覆盖率、性能、稳定性</div>
                </div>

                <div class="metric-card">
                    <div class="metric-label">测试覆盖率</div>
                    <div class="metric-value">${metrics.coverage}%</div>
                    <div class="metric-trend trend-${metrics.coverage_trend}">
                        ${trendIcon} ${metrics.coverage_trend === 'improving' ? '提升中' :
                              metrics.coverage_trend === 'degrading' ? '下降中' : '稳定'}
                    </div>
                </div>

                <div class="metric-card">
                    <div class="metric-label">执行时间</div>
                    <div class="metric-value">${metrics.execution_time}s</div>
                    <div class="metric-trend trend-${metrics.performance_trend}">
                        ${metrics.performance_trend === 'improving' ? '⚡ 更快了' :
                          metrics.performance_trend === 'degrading' ? '⚠️ 变慢了' : '➡️ 稳定'}
                    </div>
                </div>

                <div class="metric-card">
                    <div class="metric-label">测试稳定性</div>
                    <div class="metric-value">${metrics.stability}%</div>
                    <div class="metric-trend">最近7天平均</div>
                </div>

                <div class="metric-card">
                    <div class="metric-label">总测试数</div>
                    <div class="metric-value">${metrics.total_tests}</div>
                    <div class="metric-trend">单元测试</div>
                </div>

                <div class="metric-card">
                    <div class="metric-label">成功率</div>
                    <div class="metric-value">${metrics.success_rate}%</div>
                    <div class="metric-trend">最近运行</div>
                </div>
            `;
        }

        function renderCharts(charts) {
            // 覆盖率趋势图
            const coverageCtx = document.getElementById('coverageChart').getContext('2d');
            new Chart(coverageCtx, {
                type: 'line',
                data: {
                    labels: charts.coverage.labels,
                    datasets: [{
                        label: '覆盖率 (%)',
                        data: charts.coverage.data,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });

            // 性能趋势图
            const performanceCtx = document.getElementById('performanceChart').getContext('2d');
            new Chart(performanceCtx, {
                type: 'line',
                data: {
                    labels: charts.performance.labels,
                    datasets: [{
                        label: '执行时间 (秒)',
                        data: charts.performance.data,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return value + 's';
                                }
                            }
                        }
                    }
                }
            });
        }

        function renderRecommendations(recommendations) {
            const container = document.getElementById('recommendations-list');

            if (recommendations.length === 0) {
                container.innerHTML = '<p>✅ 所有质量指标都良好！</p>';
                return;
            }

            container.innerHTML = recommendations.map(rec => `
                <div class="recommendation-item">
                    <div class="recommendation-icon">${rec.icon}</div>
                    <div>
                        <strong>${rec.title}</strong>
                        <p style="margin-top: 5px; color: #666;">${rec.description}</p>
                    </div>
                </div>
            `).join('');
        }

        // 自动刷新（每5分钟）
        setInterval(loadDashboardData, 5 * 60 * 1000);

        // 初始加载
        loadDashboardData();
    </script>
</body>
</html>
            """
        }

    def load_latest_report(self) -> Dict[str, Any]:
        """加载最新的测试报告"""
        report_files = list(self.metrics_dir.glob("report_*.json"))
        if not report_files:
            return {"error": "没有找到测试报告"}

        # 获取最新的报告
        latest_report = max(report_files, key=lambda p: p.stat().st_mtime)

        with open(latest_report, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_history_data(self) -> List[Dict[str, Any]]:
        """加载历史数据"""
        history_file = self.metrics_dir / "history.json"
        if not history_file.exists():
            return []

        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        # 加载最新报告
        latest_report = self.load_latest_report()
        if "error" in latest_report:
            return latest_report

        # 加载历史数据
        history = self.load_history_data()

        # 提取指标
        metrics = {
            "quality_score": latest_report["quality_score"]["total_score"],
            "quality_grade": latest_report["quality_score"]["grade"],
            "coverage": latest_report.get("coverage", {}).get("overall_coverage", 0),
            "execution_time": latest_report.get("performance", {}).get("total_time", 0),
            "stability": latest_report.get("stability", {}).get("stability_score", 0) * 100,
            "total_tests": latest_report.get("performance", {}).get("test_count", 0),
            "success_rate": latest_report.get("performance", {}).get("passed", 0) / max(1, latest_report.get("performance", {}).get("test_count", 1)) * 100,
            "coverage_trend": latest_report.get("trends", {}).get("coverage_trend", "stable"),
            "performance_trend": latest_report.get("trends", {}).get("performance_trend", "stable")
        }

        # 准备图表数据
        charts = {
            "coverage": {
                "labels": [],
                "data": []
            },
            "performance": {
                "labels": [],
                "data": []
            }
        }

        # 处理历史数据
        if history:
            for record in history[-7:]:  # 最近7天
                date_str = record["timestamp"][:10]  # YYYY-MM-DD
                charts["coverage"]["labels"].append(date_str)
                charts["performance"]["labels"].append(date_str)

                if "coverage" in record:
                    charts["coverage"]["data"].append(record["coverage"].get("overall_coverage", 0))
                else:
                    charts["coverage"]["data"].append(0)

                if "performance" in record:
                    charts["performance"]["data"].append(record["performance"].get("total_time", 0))
                else:
                    charts["performance"]["data"].append(0)

        # 处理建议
        recommendations = []
        for rec in latest_report.get("recommendations", []):
            icon = "📊" if "覆盖率" in rec else "⚡" if "时间" in rec else "⚠️"
            recommendations.append({
                "icon": icon,
                "title": rec.split(":")[0],
                "description": rec.split(":", 1)[1] if ":" in rec else rec
            })

        return {
            "metrics": metrics,
            "charts": charts,
            "recommendations": recommendations,
            "last_updated": latest_report["timestamp"]
        }

    def generate_static_report(self, output_file: str = "test_quality_dashboard.html"):
        """生成静态HTML报告"""
        print("📊 生成测试质量仪表板...")

        # 获取数据
        data = self.get_dashboard_data()

        if "error" in data:
            print(f"❌ 错误: {data['error']}")
            return

        # 生成HTML
        html_template = self.templates["dashboard"]

        # 将数据嵌入到JavaScript中
        data_script = f"""
        <script>
            window.dashboardData = {json.dumps(data)};

            // 重写loadDashboardData函数以使用嵌入的数据
            async function loadDashboardData() {{
                renderMetrics(window.dashboardData.metrics);
                renderCharts(window.dashboardData.charts);
                renderRecommendations(window.dashboardData.recommendations);
            }}
        </script>
        """

        # 修改模板以支持静态数据
        html_template = html_template.replace(
            "</body>",
            data_script + "</body>"
        )

        # 写入文件
        output_path = self.project_root / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)

        print(f"✅ 仪表板已生成: {output_path}")
        print(f"🌐 在浏览器中打开: file://{output_path.absolute()}")

    def create_app(self):
        """创建Flask应用（如果可用）"""
        if not FLASK_AVAILABLE:
            return None

        app = Flask(__name__)
        CORS(app)

        @app.route('/')
        def dashboard():
            return self.templates["dashboard"]

        @app.route('/api/dashboard-data')
        def api_dashboard_data():
            return jsonify(self.get_dashboard_data())

        return app

    def run_server(self, host='0.0.0.0', port=8080, debug=False):
        """运行仪表板服务器"""
        app = self.create_app()
        if not app:
            print("❌ Flask未安装，无法运行服务器")
            print("💡 运行: pip install flask flask-cors")
            return

        print(f"🚀 启动测试质量仪表板服务器...")
        print(f"📍 地址: http://{host}:{port}")
        print(f"🕒 按 Ctrl+C 停止服务器")

        app.run(host=host, port=port, debug=debug)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试质量仪表板")
    parser.add_argument("--static", "-s", action="store_true",
                       help="生成静态HTML报告")
    parser.add_argument("--output", "-o", default="test_quality_dashboard.html",
                       help="输出文件名（仅静态模式）")
    parser.add_argument("--serve", action="store_true",
                       help="运行Web服务器")
    parser.add_argument("--host", default="0.0.0.0",
                       help="服务器主机地址")
    parser.add_argument("--port", "-p", type=int, default=8080,
                       help="服务器端口")
    parser.add_argument("--debug", action="store_true",
                       help="调试模式")
    parser.add_argument("--project-root", default=None,
                       help="项目根目录路径")

    args = parser.parse_args()

    # 创建仪表板
    dashboard = TestQualityDashboard(args.project_root)

    if args.static or not args.serve:
        # 静态模式（默认）
        dashboard.generate_static_report(args.output)
    else:
        # 服务器模式
        dashboard.run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()