#!/usr/bin/env python3
"""
代码质量指标监控系统
长期跟踪和报告代码质量趋势
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


class QualityMonitor:
    def __init__(self):
        self.data_file = Path('quality_metrics_history.json')
        self.metrics = self.load_historical_data()

    def load_historical_data(self) -> dict:
        """加载历史质量数据"""
        if self.data_file.exists():
            with open(self.data_file) as f:
                return json.load(f)
        return {'history': [], 'baseline': None}

    def save_metrics(self):
        """保存质量指标数据"""
        with open(self.data_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def collect_current_metrics(self) -> dict:
        """收集当前的质量指标"""
        timestamp = datetime.now().isoformat()

        # 收集各种质量指标
        metrics = {
            'timestamp': timestamp,
            'syntax_errors': self.count_syntax_errors(),
            'b904_errors': self.count_b904_errors(),
            'e402_errors': self.count_e402_errors(),
            'type_errors': self.count_type_errors(),
            'test_coverage': self.get_test_coverage(),
            'code_lines': self.count_code_lines(),
            'python_files': self.count_python_files()
        }

        return metrics

    def count_syntax_errors(self) -> int:
        """统计语法错误数量"""
        try:
            result = subprocess.run(
                'python -m py_compile src/**/*.py 2>&1',
                shell=True,
                capture_output=True,
                text=True
            )
            # 计算语法错误行数
            return len([line for line in result.stderr.split('\n')
                       if 'SyntaxError' in line or 'IndentationError' in line])
        except:
            return 0

    def count_b904_errors(self) -> int:
        """统计B904错误数量"""
        try:
            result = subprocess.run(
                'ruff check src/ --select=B904',
                shell=True,
                capture_output=True,
                text=True
            )
            return len([line for line in result.stdout.split('\n') if line.strip()])
        except:
            return 0

    def count_e402_errors(self) -> int:
        """统计E402错误数量"""
        try:
            result = subprocess.run(
                'ruff check src/ --select=E402',
                shell=True,
                capture_output=True,
                text=True
            )
            return len([line for line in result.stdout.split('\n') if line.strip()])
        except:
            return 0

    def count_type_errors(self) -> int:
        """统计类型错误数量"""
        try:
            result = subprocess.run(
                'mypy src/ --ignore-missing-imports',
                shell=True,
                capture_output=True,
                text=True
            )
            return len([line for line in result.stderr.split('\n')
                       if line.strip() and not line.startswith('note:')])
        except:
            return 0

    def get_test_coverage(self) -> float:
        """获取测试覆盖率百分比"""
        try:
            result = subprocess.run(
                'pytest tests/unit/utils/ --cov=src.utils --cov-report=term-missing --tb=no',
                shell=True,
                capture_output=True,
                text=True
            )

            # 从输出中提取覆盖率百分比
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    parts = line.split()
                    for part in parts:
                        if '%' in part and part != '100%':
                            try:
                                return float(part.replace('%', ''))
                            except:
                                pass
            return 0.0
        except:
            return 0.0

    def count_code_lines(self) -> int:
        """统计代码行数"""
        try:
            result = subprocess.run(
                'find src/ -name "*.py" -exec wc -l {} + | tail -1',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                return int(result.stdout.strip().split()[0])
            return 0
        except:
            return 0

    def count_python_files(self) -> int:
        """统计Python文件数量"""
        try:
            result = subprocess.run(
                'find src/ -name "*.py" | wc -l',
                shell=True,
                capture_output=True,
                text=True
            )
            return int(result.stdout.strip())
        except:
            return 0

    def record_metrics(self):
        """记录当前质量指标"""
        current_metrics = self.collect_current_metrics()

        # 添加到历史记录
        self.metrics['history'].append(current_metrics)

        # 保留最近100条记录
        if len(self.metrics['history']) > 100:
            self.metrics['history'] = self.metrics['history'][-100:]

        # 设置基线（如果是第一次）
        if not self.metrics['baseline']:
            self.metrics['baseline'] = current_metrics

        self.save_metrics()
        return current_metrics

    def generate_trend_report(self) -> dict:
        """生成趋势报告"""
        if not self.metrics['history']:
            return {'error': '没有历史数据'}

        latest = self.metrics['history'][-1]
        baseline = self.metrics['baseline']

        # 计算趋势
        trends = {}
        for key in ['syntax_errors', 'b904_errors', 'e402_errors', 'type_errors']:
            if key in latest and key in baseline:
                change = latest[key] - baseline[key]
                percent_change = (change / baseline[key] * 100) if baseline[key] > 0 else 0
                trends[key] = {
                    'current': latest[key],
                    'baseline': baseline[key],
                    'change': change,
                    'percent_change': percent_change,
                    'trend': 'improving' if change < 0 else 'worsening' if change > 0 else 'stable'
                }

        if 'test_coverage' in latest and 'test_coverage' in baseline:
            change = latest['test_coverage'] - baseline['test_coverage']
            trends['test_coverage'] = {
                'current': latest['test_coverage'],
                'baseline': baseline['test_coverage'],
                'change': change,
                'trend': 'improving' if change > 0 else 'worsening' if change < 0 else 'stable'
            }

        return {
            'generated_at': datetime.now().isoformat(),
            'data_points': len(self.metrics['history']),
            'trends': trends,
            'latest_metrics': latest,
            'overall_quality_score': self.calculate_quality_score(latest)
        }

    def calculate_quality_score(self, metrics: dict) -> float:
        """计算综合质量分数 (0-100)"""
        score = 100.0

        # 语法错误权重 (20%)
        if metrics.get('syntax_errors', 0) > 0:
            score -= 20

        # B904错误权重 (15%)
        b904 = metrics.get('b904_errors', 0)
        if b904 > 0:
            score -= min(15, b904 * 0.3)

        # E402错误权重 (15%)
        e402 = metrics.get('e402_errors', 0)
        if e402 > 0:
            score -= min(15, e402 * 0.1)

        # 类型错误权重 (10%)
        type_errors = metrics.get('type_errors', 0)
        if type_errors > 0:
            score -= min(10, type_errors * 0.2)

        # 测试覆盖率权重 (40%)
        coverage = metrics.get('test_coverage', 0)
        coverage_score = min(40, coverage * 0.4)
        score += coverage_score - 40

        return max(0, min(100, score))

    def generate_dashboard_html(self) -> str:
        """生成简单的HTML dashboard"""
        report = self.generate_trend_report()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>代码质量监控面板</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .good {{ border-left: 4px solid #28a745; }}
                .warning {{ border-left: 4px solid #ffc107; }}
                .bad {{ border-left: 4px solid #dc3545; }}
                .score {{ font-size: 2em; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🔍 代码质量监控面板</h1>
            <p>生成时间: {report['generated_at']}</p>
            <p>数据点数: {report['data_points']}</p>

            <div class="metric good">
                <h2>📊 综合质量分数</h2>
                <div class="score">{report['overall_quality_score']:.1f}/100</div>
            </div>

            <h2>📈 质量趋势</h2>
        """

        for metric, data in report['trends'].items():
            trend_icon = {'improving': '📈', 'worsening': '📉', 'stable': '➡️'}.get(data['trend'], '❓')
            css_class = {'improving': 'good', 'worsening': 'bad', 'stable': 'good'}.get(data['trend'], 'warning')

            html += f"""
            <div class="metric {css_class}">
                <h3>{trend_icon} {metric.replace('_', ' ').title()}</h3>
                <p>当前: {data.get('current', 'N/A')}</p>
                <p>基线: {data.get('baseline', 'N/A')}</p>
                <p>变化: {data.get('change', 'N/A')} ({data.get('percent_change', 0):.1f}%)</p>
                <p>趋势: {data['trend']}</p>
            </div>
            """

        html += """
        </body>
        </html>
        """

        # 保存HTML报告
        with open('quality_dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html)

        return html

def main():
    """主函数"""
    print("🚀 启动代码质量监控系统...")

    monitor = QualityMonitor()

    # 收集当前指标
    print("📊 收集质量指标...")
    current_metrics = monitor.record_metrics()

    print(f"✅ 质量指标已记录: {current_metrics['timestamp']}")
    print(f"   - 语法错误: {current_metrics['syntax_errors']}")
    print(f"   - B904错误: {current_metrics['b904_errors']}")
    print(f"   - E402错误: {current_metrics['e402_errors']}")
    print(f"   - 类型错误: {current_metrics['type_errors']}")
    print(f"   - 测试覆盖率: {current_metrics['test_coverage']}%")
    print(f"   - 代码行数: {current_metrics['code_lines']}")

    # 生成趋势报告
    print("📈 生成趋势报告...")
    report = monitor.generate_trend_report()

    print(f"🎯 综合质量分数: {report['overall_quality_score']:.1f}/100")

    # 生成HTML dashboard
    print("🌐 生成监控面板...")
    monitor.generate_dashboard_html()

    print("✅ 质量监控完成")
    print("📄 文件生成:")
    print("   - quality_metrics_history.json (历史数据)")
    print("   - quality_dashboard.html (可视化面板)")

if __name__ == "__main__":
    main()
