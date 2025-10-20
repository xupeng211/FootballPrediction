#!/usr/bin/env python3
"""
覆盖率趋势追踪器
自动生成趋势报告
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def get_current_coverage():
    """获取当前覆盖率"""
    try:
        # 确保coverage数据是最新的
        subprocess.run(["coverage", "json"], capture_output=True, check=True)

        with open("coverage.json", "r") as f:
            data = json.load(f)

        return data["totals"]["percent_covered"]
    except Exception as e:
        print(f"获取覆盖率失败: {e}")
        return None


def load_trend_data():
    """加载历史趋势数据"""
    trend_file = Path("docs/_reports/coverage/coverage_trend.json")

    if trend_file.exists():
        with open(trend_file, "r") as f:
            return json.load(f)
    else:
        return []


def save_trend_data(trend_data):
    """保存趋势数据"""
    trend_file = Path("docs/_reports/coverage/coverage_trend.json")
    trend_file.parent.mkdir(parents=True, exist_ok=True)

    with open(trend_file, "w") as f:
        json.dump(trend_data, f, indent=2, ensure_ascii=False)


def record_coverage():
    """记录当前覆盖率"""
    coverage = get_current_coverage()

    if coverage is None:
        print("无法获取覆盖率数据")
        return

    # 加载历史数据
    trend_data = load_trend_data()

    # 添加新数据点
    new_point = {
        "timestamp": datetime.now().isoformat(),
        "coverage": coverage,
        "phase": "Phase 5",
    }

    trend_data.append(new_point)

    # 只保留最近30天的数据
    cutoff_date = datetime.now() - timedelta(days=30)
    trend_data = [
        point
        for point in trend_data
        if datetime.fromisoformat(point["timestamp"]) > cutoff_date
    ]

    # 保存数据
    save_trend_data(trend_data)

    print(f"✅ 记录覆盖率: {coverage:.2f}%")
    return trend_data


def generate_trend_report(trend_data):
    """生成趋势报告"""
    if not trend_data:
        print("没有趋势数据")
        return

    print(f"\n{'='*60}")
    print(f"📈 覆盖率趋势报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # 最新覆盖率
    latest = trend_data[-1]
    print(f"\n🎯 当前覆盖率: {latest['coverage']:.2f}%")

    if len(trend_data) > 1:
        # 计算变化
        previous = trend_data[-2]
        change = latest["coverage"] - previous["coverage"]
        print(f"📊 相比上次: {change:+.2f}%")

        # 计算最大值和最小值
        coverages = [point["coverage"] for point in trend_data]
        max_coverage = max(coverages)
        min_coverage = min(coverages)

        print(f"📈 最高覆盖率: {max_coverage:.2f}%")
        print(f"📉 最低覆盖率: {min_coverage:.2f}%")

        # 计算平均增长率
        if len(trend_data) > 1:
            total_growth = latest["coverage"] - trend_data[0]["coverage"]
            avg_growth = total_growth / (len(trend_data) - 1)
            print(f"📊 平均增长率: {avg_growth:+.2f}%/次")

    # 显示历史记录
    print("\n📜 历史记录（最近10次）:")
    print("   时间                     覆盖率    阶段")
    print("   ------------------------------------------------")

    for point in trend_data[-10:]:
        timestamp = datetime.fromisoformat(point["timestamp"])
        time_str = timestamp.strftime("%m-%d %H:%M")
        coverage = point["coverage"]
        phase = point.get("phase", "Unknown")
        print(f"   {time_str}    {coverage:>6.2f}%   {phase}")


def generate_trend_chart(trend_data):
    """生成趋势图表"""
    if not trend_data or len(trend_data) < 2:
        print("数据不足，无法生成图表")
        return

    # 准备数据
    timestamps = [datetime.fromisoformat(point["timestamp"]) for point in trend_data]
    coverages = [point["coverage"] for point in trend_data]

    # 创建图表
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, coverages, marker="o", linewidth=2, markersize=6)

    # 设置标题和标签
    plt.title("测试覆盖率趋势图", fontsize=16, pad=20)
    plt.xlabel("时间", fontsize=12)
    plt.ylabel("覆盖率 (%)", fontsize=12)

    # 设置网格
    plt.grid(True, alpha=0.3)

    # 格式化x轴
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.gcf().autofmt_xdate()

    # 添加里程碑线
    plt.axhline(y=25, color="orange", linestyle="--", alpha=0.7, label="CI门槛 (25%)")
    plt.axhline(y=30, color="yellow", linestyle="--", alpha=0.7, label="及格线 (30%)")
    plt.axhline(
        y=40, color="lightgreen", linestyle="--", alpha=0.7, label="良好线 (40%)"
    )
    plt.axhline(y=50, color="green", linestyle="--", alpha=0.7, label="优秀线 (50%)")

    # 添加图例
    plt.legend(loc="upper left")

    # 添加数据标签
    for i, (timestamp, coverage) in enumerate(zip(timestamps, coverages)):
        if i == 0 or i == len(timestamps) - 1 or coverage % 10 < 1:
            plt.annotate(
                f"{coverage:.1f}%",
                (timestamp, coverage),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
            )

    # 保存图表
    chart_path = Path("docs/_reports/coverage/coverage_trend.png")
    chart_path.parent.mkdir(parents=True, exist_ok=True)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"\n📊 趋势图表已保存到: {chart_path}")


def generate_html_report(trend_data):
    """生成HTML报告"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试覆盖率趋势报告</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px;
            padding: 15px;
            background-color: #f0f0f0;
            border-radius: 5px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        img {{
            max-width: 100%;
            margin-top: 20px;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 测试覆盖率趋势报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{trend_data[-1]['coverage']:.2f}%</div>
                <div class="metric-label">当前覆盖率</div>
            </div>
"""

    if len(trend_data) > 1:
        change = trend_data[-1]["coverage"] - trend_data[-2]["coverage"]
        change_color = "#4CAF50" if change >= 0 else "#f44336"
        html_content += f"""
            <div class="metric">
                <div class="metric-value" style="color: {change_color}">{change:+.2f}%</div>
                <div class="metric-label">相比上次</div>
            </div>
"""

    html_content += """
        </div>

        <h2>📊 趋势图表</h2>
        <img src="coverage_trend.png" alt="覆盖率趋势图">

        <h2>📜 历史记录</h2>
        <table>
            <thead>
                <tr>
                    <th>时间</th>
                    <th>覆盖率</th>
                    <th>阶段</th>
                </tr>
            </thead>
            <tbody>
"""

    for point in reversed(trend_data[-20:]):  # 最近20条记录
        timestamp = datetime.fromisoformat(point["timestamp"])
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        coverage = point["coverage"]
        phase = point.get("phase", "Unknown")

        html_content += f"""
                <tr>
                    <td>{time_str}</td>
                    <td>{coverage:.2f}%</td>
                    <td>{phase}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    # 保存HTML报告
    html_path = Path("docs/_reports/coverage/coverage_trend.html")
    html_path.parent.mkdir(parents=True, exist_ok=True)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"📄 HTML报告已保存到: {html_path}")


def main():
    """主函数"""
    print("🔄 开始生成覆盖率趋势报告...")

    # 记录当前覆盖率
    trend_data = record_coverage()

    if not trend_data:
        print("❌ 无法获取趋势数据")
        return

    # 生成文本报告
    generate_trend_report(trend_data)

    # 生成图表（如果有matplotlib）
    try:
        generate_trend_chart(trend_data)
    except ImportError:
        print("\n⚠️ matplotlib未安装，跳过图表生成")
        print("   安装命令: pip install matplotlib")

    # 生成HTML报告
    generate_html_report(trend_data)

    print("\n✅ 趋势报告生成完成！")
    print("\n📁 报告位置:")
    print("   - JSON数据: docs/_reports/coverage/coverage_trend.json")
    print("   - HTML报告: docs/_reports/coverage/coverage_trend.html")
    print("   - 趋势图表: docs/_reports/coverage/coverage_trend.png")


if __name__ == "__main__":
    main()
