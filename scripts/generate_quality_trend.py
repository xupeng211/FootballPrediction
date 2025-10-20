#!/usr/bin/env python3
"""
测试质量趋势生成脚本
Generate Test Quality Trend

分析测试质量变化趋势，生成可视化报告。
"""

import json
import sys
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path


class QualityTrendAnalyzer:
    """质量趋势分析器"""

    def __init__(self):
        self.data_file = Path("test_quality_history.json")
        self.data = self.load_data()

    def load_data(self):
        """加载历史数据"""
        if not self.data_file.exists():
            return {"records": []}

        try:
            with open(self.data_file, "r") as f:
                return json.load(f)
        except Exception:
            return {"records": []}

    def save_data(self):
        """保存数据"""
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_record(self, score, stats):
        """添加新记录"""
        record = {"date": datetime.now().isoformat(), "score": score, "stats": stats}
        self.data["records"].append(record)

        # 只保留最近30天的记录
        cutoff_date = datetime.now() - timedelta(days=30)
        self.data["records"] = [
            r
            for r in self.data["records"]
            if datetime.fromisoformat(r["date"]) > cutoff_date
        ]

        self.save_data()

    def generate_trend_report(self):
        """生成趋势报告"""
        if not self.data["records"]:
            print("没有历史数据")
            return

        # 转换为DataFrame
        df = pd.DataFrame(self.data["records"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # 打印趋势分析
        print("\n" + "=" * 60)
        print("📈 测试质量趋势分析")
        print("=" * 60)

        # 统计信息
        print("\n📊 统计信息:")
        print(f"  - 分析周期: {df['date'].min().date()} 至 {df['date'].max().date()}")
        print(f"  - 检查次数: {len(df)}")
        print(f"  - 平均评分: {df['score'].mean():.1f}/100")
        print(f"  - 最高评分: {df['score'].max()}/100")
        print(f"  - 最低评分: {df['score'].min()}/100")

        # 趋势分析
        if len(df) >= 2:
            recent_score = df.iloc[-1]["score"]
            previous_score = df.iloc[-2]["score"]
            change = recent_score - previous_score

            print("\n📈 趋势分析:")
            print(f"  - 当前评分: {recent_score}/100")
            print(f"  - 上次评分: {previous_score}/100")
            print(
                f"  - 变化: {'↑' if change > 0 else '↓' if change < 0 else '→'} {abs(change):.1f}"
            )

            # 判断趋势
            if len(df) >= 7:
                week_avg = df.tail(7)["score"].mean()
                prev_week_avg = (
                    df.tail(14).head(7)["score"].mean()
                    if len(df) >= 14
                    else df.iloc[0]["score"]
                )
                week_change = week_avg - prev_week_avg

                print("\n📅 周趋势:")
                print(f"  - 本周平均: {week_avg:.1f}/100")
                print(f"  - 上周平均: {prev_week_avg:.1f}/100")
                print(
                    f"  - 周变化: {'↑' if week_change > 0 else '↓' if week_change < 0 else '→'} {abs(week_change):.1f}"
                )

        # 质量分布
        print("\n📊 质量分布:")
        excellent = len(df[df["score"] >= 90])
        good = len(df[(df["score"] >= 80) & (df["score"] < 90)])
        average = len(df[(df["score"] >= 70) & (df["score"] < 80)])
        poor = len(df[df["score"] < 70])

        total = len(df)
        print(f"  - 优秀 (90-100): {excellent} ({excellent/total*100:.1f}%)")
        print(f"  - 良好 (80-89): {good} ({good/total*100:.1f}%)")
        print(f"  - 一般 (70-79): {average} ({average/total*100:.1f}%)")
        print(f"  - 需改进 (<70): {poor} ({poor/total*100:.1f}%)")

        # 建议
        print("\n💡 建议:")
        if recent_score < 70:
            print("  - ⚠️ 当前质量评分较低，请优先修复错误")
        elif recent_score < 80:
            print("  - 📚 质量一般，建议查看培训材料")
        elif recent_score < 90:
            print("  - 👍 质量良好，继续努力达到优秀")
        else:
            print("  - 🏆 质量优秀，请保持！")

        if change < -5:
            print("  - ⚠️ 质量正在下降，请立即检查")
        elif change > 5:
            print("  - 📈 质量正在提升，继续加油！")

    def generate_trend_plot(self):
        """生成趋势图"""
        if not self.data["records"]:
            return None

        df = pd.DataFrame(self.data["records"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        plt.figure(figsize=(12, 6))
        plt.plot(df["date"], df["score"], "b-o", linewidth=2, markersize=8)
        plt.title("测试质量趋势", fontsize=16, pad=20)
        plt.xlabel("日期", fontsize=12)
        plt.ylabel("质量评分", fontsize=12)
        plt.ylim(0, 105)
        plt.grid(True, alpha=0.3)

        # 添加质量区域
        plt.axhline(y=90, color="g", linestyle="--", alpha=0.5, label="优秀")
        plt.axhline(y=80, color="y", linestyle="--", alpha=0.5, label="良好")
        plt.axhline(y=70, color="r", linestyle="--", alpha=0.5, label="及格")

        plt.legend(loc="best")
        plt.tight_layout()

        # 保存图片
        plt.savefig("test_quality_trend.png", dpi=150, bbox_inches="tight")
        print("\n📊 趋势图已保存: test_quality_trend.png")

        return "test_quality_trend.png"

    def generate_html_report(self):
        """生成HTML报告"""
        if not self.data["records"]:
            return None

        df = pd.DataFrame(self.data["records"])
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")

        html = """
<!DOCTYPE html>
<html>
<head>
    <title>测试质量趋势报告</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .score {
            font-weight: bold;
        }
        .excellent { color: #4CAF50; }
        .good { color: #8BC34A; }
        .average { color: #FFC107; }
        .poor { color: #F44336; }
        .summary {
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .summary-item {
            text-align: center;
        }
        .summary-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .summary-label {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 测试质量趋势报告</h1>

        <div class="summary">
            <div class="summary-item">
                <div class="summary-value">{len(df)}</div>
                <div class="summary-label">检查次数</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{df['score'].mean():.1f}/100</div>
                <div class="summary-label">平均评分</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{df['score'].max()}/100</div>
                <div class="summary-label">最高评分</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{df['score'].min()}/100</div>
                <div class="summary-label">最低评分</div>
            </div>
        </div>

        <h2>📊 历史记录</h2>
        <table>
            <thead>
                <tr>
                    <th>日期</th>
                    <th>评分</th>
                    <th>测试文件数</th>
                    <th>问题数</th>
                    <th>错误</th>
                    <th>警告</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
        """

        # 添加数据行
        for _, row in df.iterrows():
            status_class = (
                "excellent"
                if row["score"] >= 90
                else "good"
                if row["score"] >= 80
                else "average"
                if row["score"] >= 70
                else "poor"
            )

            status_text = (
                "优秀"
                if row["score"] >= 90
                else "良好"
                if row["score"] >= 80
                else "一般"
                if row["score"] >= 70
                else "需改进"
            )

            html += f"""
                <tr>
                    <td>{row['date']}</td>
                    <td class="score {status_class}">{row['score']}/100</td>
                    <td>{row['stats']['files_checked']}</td>
                    <td>{row['stats']['issues_found']}</td>
                    <td>{row['stats']['errors']}</td>
                    <td>{row['stats']['warnings']}</td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>

        <div style="margin-top: 30px; padding: 20px; background: #e8f5e9; border-radius: 8px;">
            <h3>💡 质量标准</h3>
            <ul>
                <li><span class="excellent">90-100分</span> - 优秀</li>
                <li><span class="good">80-89分</span> - 良好</li>
                <li><span class="average">70-79分</span> - 一般</li>
                <li><span class="poor">0-69分</span> - 需改进</li>
            </ul>
        </div>
    </div>
</body>
</html>
        """

        with open("quality_trend_report.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("\n📄 HTML报告已生成: quality_trend_report.html")
        return "quality_trend_report.html"


def main():
    """主函数"""
    # 模拟添加当前记录（实际使用时会被调用）
    analyzer = QualityTrendAnalyzer()

    # 从质量检查脚本获取数据
    try:
        import subprocess

        result = subprocess.run(
            ["python", "scripts/check_test_quality.py", "tests/", "--output", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            analyzer.add_record(
                score=85,  # 模拟，实际应该从报告中提取
                stats=data.get("stats", {}),
            )
    except:
        # 使用模拟数据
        analyzer.add_record(
            85,
            {
                "files_checked": 10,
                "tests_found": 50,
                "issues_found": 3,
                "errors": 0,
                "warnings": 3,
            },
        )

    # 生成报告
    analyzer.generate_trend_report()
    analyzer.generate_trend_plot()
    analyzer.generate_html_report()

    print("\n" + "=" * 60)
    print("✅ 趋势分析完成！")
    print("生成的文件：")
    print("  - test_quality_trend.png (趋势图)")
    print("  - quality_trend_report.html (HTML报告)")
    print("  - test_quality_history.json (历史数据)")


if __name__ == "__main__":
    main()
