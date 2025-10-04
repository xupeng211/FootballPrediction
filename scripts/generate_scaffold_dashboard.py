#!/usr/bin/env python3
"""
生成脚手架评估仪表板
"""

from pathlib import Path
from datetime import datetime

def generate_dashboard():
    """生成评估仪表板HTML"""

    dashboard_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FootballPrediction 脚手架评估仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .score-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .score {{
            font-size: 72px;
            font-weight: bold;
            margin: 0;
        }}
        .grade {{
            font-size: 36px;
            margin: 10px 0;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .risk-list {{
            background: #fff5f5;
            border: 1px solid #fed7d7;
            border-radius: 8px;
            padding: 20px;
        }}
        .risk-item {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        .risk-level {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .critical {{ background: #e53e3e; }}
        .high {{ background: #dd6b20; }}
        .medium {{ background: #d69e2e; }}
        .low {{ background: #38a169; }}
        .action-items {{
            background: #f0fff4;
            border: 1px solid #9ae6b4;
            border-radius: 8px;
            padding: 20px;
            margin-top: 30px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ FootballPrediction 脚手架评估仪表板</h1>

        <div class="score-card">
            <div class="score">70</div>
            <div class="grade">C+</div>
            <div>总体评分</div>
            <div style="font-size: 14px; opacity: 0.9;">评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="metrics">
            <div class="metric">
                <div class="metric-value">45,464</div>
                <div class="metric-label">代码行数</div>
            </div>
            <div class="metric">
                <div class="metric-value">21</div>
                <div class="metric-label">模块数量</div>
            </div>
            <div class="metric">
                <div class="metric-value">42%</div>
                <div class="metric-label">测试覆盖率</div>
            </div>
            <div class="metric">
                <div class="metric-value">248</div>
                <div class="metric-label">文档数量</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h3>各维度评分</h3>
                <canvas id="radarChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>风险分布</h3>
                <canvas id="riskChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h3>项目质量指标</h3>
            <canvas id="qualityChart"></canvas>
        </div>

        <div class="risk-list">
            <h3>🚨 关键风险</h3>
            <div class="risk-item">
                <div class="risk-level critical"></div>
                <div><strong>依赖管理缺失</strong> - 无根requirements.txt，影响部署</div>
            </div>
            <div class="risk-item">
                <div class="risk-level high"></div>
                <div><strong>测试覆盖率低</strong> - 42%远低于80%的CI要求</div>
            </div>
            <div class="risk-item">
                <div class="risk-level high"></div>
                <div><strong>存在语法错误</strong> - 12个文件需要修复</div>
            </div>
            <div class="risk-item">
                <div class="risk-level medium"></div>
                <div><strong>安全配置需改进</strong> - 321个文件含敏感信息</div>
            </div>
        </div>

        <div class="action-items">
            <h3>📋 立即行动项</h3>
            <ul>
                <li>🔥 <strong>紧急</strong>: 创建requirements.txt文件</li>
                <li>🔧 <strong>紧急</strong>: 修复12个语法错误文件</li>
                <li>📊 <strong>短期</strong>: 提升测试覆盖率至60%</li>
                <li>🔒 <strong>短期</strong>: 实施自动化安全扫描</li>
            </ul>
        </div>

        <div class="footer">
            <p>📊 由 FootballPrediction 项目健康度监控系统生成</p>
            <p>下次评估: 2025-10-11 或完成关键改进后</p>
        </div>
    </div>

    <script>
        // 雷达图
        const radarCtx = document.getElementById('radarChart').getContext('2d');
        new Chart(radarCtx, {{
            type: 'radar',
            data: {{
                labels: ['项目结构', '配置文件', '依赖管理', '测试覆盖', 'CI/CD', '文档质量', '代码质量', '安全配置'],
                datasets: [{{
                    label: '当前评分',
                    data: [90, 80, 40, 40, 95, 95, 70, 70],
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                }}]
            }},
            options: {{
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});

        // 风险分布图
        const riskCtx = document.getElementById('riskChart').getContext('2d');
        new Chart(riskCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['严重', '高', '中', '低'],
                datasets: [{{
                    data: [1, 2, 1, 0],
                    backgroundColor: ['#e53e3e', '#dd6b20', '#d69e2e', '#38a169']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});

        // 质量指标图
        const qualityCtx = document.getElementById('qualityChart').getContext('2d');
        new Chart(qualityCtx, {{
            type: 'bar',
            data: {{
                labels: ['类型注解', '代码规范', '测试覆盖', '安全评分'],
                datasets: [{{
                    label: '当前值',
                    data: [75, 85, 42, 70],
                    backgroundColor: ['#4299e1', '#48bb78', '#ed8936', '#9f7aea']
                }}, {{
                    label: '目标值',
                    data: [90, 90, 80, 90],
                    backgroundColor: ['#cbd5e0', '#c6f6d5', '#feebc8', '#e9d8fd']
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    # 保存仪表板
    dashboard_path = Path("docs/_reports/scaffold_dashboard.html")
    dashboard_path.parent.mkdir(exist_ok=True)

    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)

    print(f"✅ 仪表板已生成: {dashboard_path}")
    print(f"📊 请在浏览器中打开: file://{dashboard_path.absolute()}")

if __name__ == "__main__":
    generate_dashboard()