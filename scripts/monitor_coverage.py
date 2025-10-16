#!/usr/bin/env python3
"""持续监控测试覆盖率
定期运行并生成覆盖率报告"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

class CoverageMonitor:
    """覆盖率监控器"""

    def __init__(self, report_dir="coverage_reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        self.data_file = self.report_dir / "coverage_history.json"

    def run_coverage_check(self):
        """运行覆盖率检查"""
        print("🔍 运行测试覆盖率检查")
        print("=" * 60)

        # 运行测试并收集覆盖率
        cmd = [
            "python", "-m", "pytest",
            "tests/unit/utils/test_helpers.py",
            "tests/unit/utils/test_string_utils.py::TestStringUtilsTruncate",
            "tests/unit/utils/test_dict_utils.py::TestDictOperations::test_get_dict_value",
            "tests/unit/utils/test_predictions_tdd.py",
            "--cov=src.utils",
            "--cov-report=term-missing",
            "--cov-report=json",
            "--cov-report=html",
            "--tb=no",
            "-q"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 解析结果
        if result.returncode == 0:
            coverage_data = self._parse_coverage_report(result.stdout)
            self._save_coverage_data(coverage_data)
            return coverage_data
        else:
            print("❌ 覆盖率检查失败")
            print(result.stderr)
            return None

    def _parse_coverage_report(self, output):
        """解析覆盖率报告"""
        lines = output.split('\n')
        coverage_data = {}

        for line in lines:
            if 'TOTAL' in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage_data['total'] = {
                        'statements': int(parts[1]),
                        'missing': int(parts[2]),
                        'branches': int(parts[3]),
                        'cover_percent': float(parts[4].rstrip('%'))
                    }
                    break

        # 解析具体模块的覆盖率
        for line in lines:
            if 'src/utils/' in line and '.py' in line:
                parts = line.split()
                if len(parts) >= 5:
                    module_name = parts[0].replace('src/utils/', '').replace('.py', '')
                    coverage_data[module_name] = {
                        'statements': int(parts[1]),
                        'missing': int(parts[2]),
                        'branches': int(parts[3]),
                        'cover_percent': float(parts[4].rstrip('%'))
                    }

        return coverage_data

    def _save_coverage_data(self, data):
        """保存覆盖率数据"""
        # 加载历史数据
        history = self._load_history()

        # 添加新数据
        record = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        history.append(record)

        # 只保留最近30条记录
        history = history[-30:]

        # 保存历史数据
        with open(self.data_file, 'w') as f:
            json.dump(history, f, indent=2)

        print(f"✅ 覆盖率数据已保存: {self.data_file}")

    def _load_history(self):
        """加载历史数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def generate_trend_report(self):
        """生成趋势报告"""
        history = self._load_history()

        if len(history) < 2:
            print("⚠️ 数据不足，无法生成趋势报告")
            return

        print("\n📈 覆盖率趋势报告")
        print("=" * 60)

        # 获取最新数据
        latest = history[-1]
        previous = history[-2]

        if 'data' in latest and 'total' in latest['data']:
            latest_total = latest['data']['total']['cover_percent']
            previous_total = previous['data']['total']['cover_percent'] if 'data' in previous and 'total' in previous['data'] else 0

            change = latest_total - previous_total
            trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"

            print(f"当前覆盖率: {latest_total:.1f}%")
            print(f"上一次覆盖率: {previous_total:.1f}%")
            print(f"变化: {trend} {change:+.1f}%")

            # 显示各模块覆盖率
            print("\n模块覆盖率:")
            for module, data in latest['data'].items():
                if module != 'total':
                    status = "✅" if data['cover_percent'] >= 50 else "⚠️" if data['cover_percent'] >= 30 else "❌"
                    print(f"  {status} {module}: {data['cover_percent']:.1f}%")

            # 设置覆盖率警告阈值
            if latest_total < 30:
                print("\n⚠️ 警告：覆盖率低于30%")
            elif latest_total < 50:
                print("\n💡 提示：距离50%目标还有提升空间")
            else:
                print("\n✅ 优秀！覆盖率达标")

    def check_regression(self, threshold=5.0):
        """检查覆盖率回归"""
        history = self._load_history()

        if len(history) < 7:
            return False

        # 计算最近7天的平均覆盖率
        recent_coverage = []
        for record in history[-7:]:
            if 'data' in record and 'total' in record['data']:
                recent_coverage.append(record['data']['total']['cover_percent'])

        if recent_coverage:
            avg_coverage = sum(recent_coverage) / len(recent_coverage)
            latest = history[-1]['data']['total']['cover_percent']

            if latest < avg_coverage - threshold:
                print(f"\n❌ 警告：覆盖率下降 {avg_coverage - latest:.1f}%")
                print(f"   最近7天平均: {avg_coverage:.1f}%")
                print(f"   当前覆盖率: {latest:.1f}%")
                return True

        return False

    def generate_html_report(self):
        """生成HTML报告"""
        html_file = self.report_dir / "coverage_dashboard.html"

        history = self._load_history()
        if not history:
            print("⚠️ 没有历史数据")
            return

        # 准备数据
        timestamps = [r['timestamp'] for r in history]
        coverages = [r['data'].get('total', {}).get('cover_percent', 0) for r in history]

        # 生成HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>测试覆盖率监控面板</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ flex: 1; padding: 20px; background: #f8f9fa; border-radius: 5px; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .chart {{ margin: 30px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .bad {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 测试覆盖率监控面板</h1>
        <p>最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{coverages[-1]:.1f}%</div>
                <div class="stat-label">当前覆盖率</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(history)}</div>
                <div class="stat-label">记录数量</div>
            </div>
        </div>

        <div class="chart">
            <canvas id="coverageChart" width="400" height="200"></canvas>
        </div>

        <h2>模块覆盖率详情</h2>
        <table>
            <tr>
                <th>模块</th>
                <th>覆盖率</th>
                <th>状态</th>
            </tr>
"""

        # 添加模块详情
        if history and 'data' in history[-1]:
            for module, data in history[-1]['data'].items():
                if module != 'total':
                    status_class = 'good' if data['cover_percent'] >= 50 else 'warning' if data['cover_percent'] >= 30 else 'bad'
                    status_text = '优秀' if data['cover_percent'] >= 50 else '良好' if data['cover_percent'] >= 30 else '需改进'
                    html_content += f"""
            <tr>
                <td>{module}</td>
                <td>{data['cover_percent']:.1f}%</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
"""

        html_content += """
        </table>
    </div>

    <script>
        // 绘制覆盖率趋势图
        const ctx = document.getElementById('coverageChart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: """ + json.dumps(timestamps[-10:]) + """,
                datasets: [{{
                    label: '覆盖率 (%)',
                    data: """ + json.dumps(coverages[-10:]) + """,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true
                    }}
                }},
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

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ HTML报告已生成: {html_file}")


def main():
    """主函数"""
    monitor = CoverageMonitor()

    print("🚀 测试覆盖率监控系统")
    print("=" * 60)

    # 1. 运行覆盖率检查
    coverage_data = monitor.run_coverage_check()

    if coverage_data:
        # 2. 生成趋势报告
        monitor.generate_trend_report()

        # 3. 检查回归
        monitor.check_regression()

        # 4. 生成HTML报告
        monitor.generate_html_report()

        print("\n✅ 覆盖率监控完成！")
        print(f"\n📁 报告位置: {monitor.report_dir}")
        print("   - coverage_history.json: 历史数据")
        print("   - coverage_dashboard.html: 可视化面板")

    # 5. 创建每日报告
    daily_report = monitor.report_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(daily_report, 'w') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'coverage': coverage_data
        }, f, indent=2)
    print(f"   - {daily_report.name}: 每日报告")


if __name__ == "__main__":
    main()
