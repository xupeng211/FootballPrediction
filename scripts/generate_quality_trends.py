#!/usr/bin/env python3
"""
质量趋势分析器 - 分析历史质量数据并生成趋势报告和可视化图表
"""

import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


class QualityTrendAnalyzer:
    """质量趋势分析器"""

    def __init__(self):
        plt.style.use('seaborn-v0_8')
        plt.rcParams['font.family'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def load_quality_history(self, history_path: str) -> pd.DataFrame:
        """加载质量历史数据"""
        try:
            df = pd.read_csv(history_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            return df
        except FileNotFoundError:
            print(f"❌ 质量历史文件未找到: {history_path}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 加载质量历史数据失败: {e}")
            return pd.DataFrame()

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理和预处理数据"""
        if df.empty:
            return df

        # 移除重复的时间戳
        df = df.drop_duplicates(subset=['timestamp'])

        # 处理缺失值
        numeric_columns = df.select_dtypes(include=['number']).columns
        for col in numeric_columns:
            df[col] = df[col].ffill().bfill()

        # 移除异常值（使用IQR方法）
        for col in ['coverage_percent', 'quality_score']:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

        return df

    def generate_coverage_trend(self, df: pd.DataFrame, output_path: str) -> None:
        """生成覆盖率趋势图"""
        if df.empty or 'coverage_percent' not in df.columns:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        # 绘制覆盖率趋势
        ax.plot(df['timestamp'], df['coverage_percent'],
                marker='o', linewidth=2, markersize=4,
                color='#2ecc71', label='测试覆盖率')

        # 添加目标线
        if len(df) > 0:
            target_40 = 40.0
            target_80 = 80.0
            ax.axhline(y=target_40, color='orange', linestyle='--',
                      alpha=0.7, label='开发目标 (40%)')
            ax.axhline(y=target_80, color='red', linestyle='--',
                      alpha=0.7, label='生产目标 (80%)')

        # 标注重要点
        if len(df) > 1:
            # 找到最大提升
            df['coverage_diff'] = df['coverage_percent'].diff()
            max_improvement = df['coverage_diff'].max()
            if max_improvement > 0:
                max_row = df[df['coverage_diff'] == max_improvement].iloc[0]
                ax.annotate(f'最大提升\n+{max_improvement:.1f}%',
                           xy=(max_row['timestamp'], max_row['coverage_percent']),
                           xytext=(10, 30), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        ax.set_xlabel('时间')
        ax.set_ylabel('覆盖率 (%)')
        ax.set_title('测试覆盖率趋势分析')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 覆盖率趋势图已生成: {output_path}")

    def generate_quality_score_trend(self, df: pd.DataFrame, output_path: str) -> None:
        """生成质量分数趋势图"""
        if df.empty or 'quality_score' not in df.columns:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        # 绘制质量分数趋势
        ax.plot(df['timestamp'], df['quality_score'],
                marker='s', linewidth=2, markersize=4,
                color='#3498db', label='质量分数')

        # 添加目标线和警戒线
        target_scores = [80, 60, 40]
        colors = ['green', 'orange', 'red']
        labels = ['优秀 (80)', '良好 (60)', '及格 (40)']

        for score, color, label in zip(target_scores, colors, labels):
            ax.axhline(y=score, color=color, linestyle='--',
                      alpha=0.7, label=label)

        ax.set_xlabel('时间')
        ax.set_ylabel('质量分数')
        ax.set_title('项目质量分数趋势分析')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 质量分数趋势图已生成: {output_path}")

    def generate_comprehensive_trend(self, df: pd.DataFrame, output_path: str) -> None:
        """生成综合质量趋势图"""
        if df.empty:
            return

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # 1. 覆盖率趋势
        if 'coverage_percent' in df.columns:
            ax1.plot(df['timestamp'], df['coverage_percent'],
                    marker='o', color='#2ecc71', linewidth=2)
            ax1.axhline(y=40, color='orange', linestyle='--', alpha=0.7)
            ax1.set_title('测试覆盖率')
            ax1.set_ylabel('覆盖率 (%)')
            ax1.grid(True, alpha=0.3)

        # 2. 质量分数趋势
        if 'quality_score' in df.columns:
            ax2.plot(df['timestamp'], df['quality_score'],
                    marker='s', color='#3498db', linewidth=2)
            ax2.axhline(y=60, color='orange', linestyle='--', alpha=0.7)
            ax2.set_title('质量分数')
            ax2.set_ylabel('分数')
            ax2.grid(True, alpha=0.3)

        # 3. 测试文件数量
        if 'auto_generated_tests' in df.columns:
            ax3.plot(df['timestamp'], df['auto_generated_tests'],
                    marker='^', color='#e74c3c', linewidth=2)
            ax3.set_title('自动生成测试文件')
            ax3.set_ylabel('文件数量')
            ax3.grid(True, alpha=0.3)

        # 4. AI修复成功率
        if 'ai_fix_success_rate' in df.columns:
            ax4.plot(df['timestamp'], df['ai_fix_success_rate'],
                    marker='d', color='#9b59b6', linewidth=2)
            ax4.set_title('AI修复成功率')
            ax4.set_ylabel('成功率 (%)')
            ax4.grid(True, alpha=0.3)

        # 格式化所有子图的x轴
        for ax in [ax1, ax2, ax3, ax4]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.suptitle('项目质量综合趋势分析', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 综合质量趋势图已生成: {output_path}")

    def calculate_trend_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算趋势指标"""
        if df.empty:
            return {}

        metrics = {}

        # 覆盖率趋势
        if 'coverage_percent' in df.columns and len(df) > 1:
            coverage_values = df['coverage_percent'].dropna()
            if len(coverage_values) > 1:
                first_value = coverage_values.iloc[0]
                last_value = coverage_values.iloc[-1]
                total_change = last_value - first_value
                avg_value = coverage_values.mean()

                # 计算趋势斜率
                x = pd.to_numeric(df['timestamp']).astype('int64') // 10**9
                y = coverage_values
                slope = pd.Series([x[i]*y[i] for i in range(len(x))]).cov(pd.Series(x)) / x.var()

                metrics['coverage'] = {
                    'first_value': first_value,
                    'last_value': last_value,
                    'total_change': total_change,
                    'change_percentage': (total_change / first_value * 100) if first_value > 0 else 0,
                    'average_value': avg_value,
                    'trend_slope': slope,
                    'trend_direction': 'improving' if slope > 0 else 'declining' if slope < 0 else 'stable'
                }

        # 质量分数趋势
        if 'quality_score' in df.columns and len(df) > 1:
            quality_values = df['quality_score'].dropna()
            if len(quality_values) > 1:
                first_value = quality_values.iloc[0]
                last_value = quality_values.iloc[-1]
                total_change = last_value - first_value
                avg_value = quality_values.mean()

                metrics['quality_score'] = {
                    'first_value': first_value,
                    'last_value': last_value,
                    'total_change': total_change,
                    'change_percentage': (total_change / first_value * 100) if first_value > 0 else 0,
                    'average_value': avg_value
                }

        return metrics

    def generate_trend_report(self, df: pd.DataFrame, metrics: Dict[str, Any], output_path: str) -> None:
        """生成趋势分析报告"""
        report_lines = []
        report_lines.append("# 📈 质量趋势分析报告")
        report_lines.append("")
        report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**数据期间**: {df['timestamp'].min().strftime('%Y-%m-%d')} 至 {df['timestamp'].max().strftime('%Y-%m-%d')}")
        report_lines.append(f"**数据点数**: {len(df)}")
        report_lines.append("")

        # 总体趋势摘要
        report_lines.append("## 📊 趋势摘要")
        report_lines.append("")

        if 'coverage' in metrics:
            cov_metrics = metrics['coverage']
            trend_emoji = "📈" if cov_metrics['trend_direction'] == 'improving' else "📉" if cov_metrics['trend_direction'] == 'declining' else "➡️"

            report_lines.append(f"### 🧪 测试覆盖率趋势 {trend_emoji}")
            report_lines.append(f"- **初始值**: {cov_metrics['first_value']:.1f}%")
            report_lines.append(f"- **当前值**: {cov_metrics['last_value']:.1f}%")
            report_lines.append(f"- **总变化**: {cov_metrics['total_change']:+.1f}% ({cov_metrics['change_percentage']:+.1f}%)")
            report_lines.append(f"- **平均值**: {cov_metrics['average_value']:.1f}%")
            report_lines.append(f"- **趋势方向**: {cov_metrics['trend_direction']}")
            report_lines.append("")

        if 'quality_score' in metrics:
            qs_metrics = metrics['quality_score']
            report_lines.append(f"### 🎯 质量分数趋势")
            report_lines.append(f"- **初始值**: {qs_metrics['first_value']:.1f}/100")
            report_lines.append(f"- **当前值**: {qs_metrics['last_value']:.1f}/100")
            report_lines.append(f"- **总变化**: {qs_metrics['total_change']:+.1f} ({qs_metrics['change_percentage']:+.1f}%)")
            report_lines.append(f"- **平均值**: {qs_metrics['average_value']:.1f}/100")
            report_lines.append("")

        # 关键发现
        report_lines.append("## 🔍 关键发现")
        report_lines.append("")

        if 'coverage' in metrics:
            cov_metrics = metrics['coverage']
            if cov_metrics['total_change'] > 5:
                report_lines.append("- ✅ **覆盖率显著提升**: 测试覆盖率提升了 {:.1f}%，表现出良好的质量改进趋势".format(cov_metrics['total_change']))
            elif cov_metrics['total_change'] < -5:
                report_lines.append("- ⚠️  **覆盖率下降**: 测试覆盖率下降了 {:.1f}%，需要关注测试质量".format(abs(cov_metrics['total_change'])))
            else:
                report_lines.append("- ➡️ **覆盖率稳定**: 测试覆盖率变化较小，保持在 {:.1f}% 左右".format(cov_metrics['average_value']))

        # 建议和改进措施
        report_lines.append("")
        report_lines.append("## 💡 改进建议")
        report_lines.append("")

        if 'coverage' in metrics and cov_metrics['last_value'] < 40:
            report_lines.append("- **继续提升覆盖率**: 当前覆盖率为 {:.1f}%，建议继续补充测试以达到40%的开发目标".format(cov_metrics['last_value']))

        if 'quality_score' in metrics:
            qs_metrics = metrics['quality_score']
            if qs_metrics['last_value'] < 60:
                report_lines.append("- **提升代码质量**: 当前质量分数为 {:.1f}/100，建议加强代码质量检查和重构".format(qs_metrics['last_value']))

        report_lines.append("- **定期监控**: 建议保持每日质量数据收集，持续跟踪改进效果")
        report_lines.append("- **趋势分析**: 定期分析质量趋势，及时发现潜在问题")

        # 数据质量说明
        report_lines.append("")
        report_lines.append("## 📋 数据说明")
        report_lines.append("")
        report_lines.append("- 数据来源: 自动化质量系统每日收集")
        report_lines.append("- 更新频率: 每日自动更新")
        report_lines.append("- 数据完整性: 基于现有快照数据，可能存在缺失")
        report_lines.append("- 可视化图表: 见生成的PNG文件")

        # 保存报告
        report_content = "\n".join(report_lines)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"✅ 趋势分析报告已生成: {output_path}")
        except Exception as e:
            print(f"❌ 保存趋势报告失败: {e}")

    def analyze_trends(self, history_path: str, output_dir: str = ".") -> None:
        """执行完整的趋势分析"""
        print("🔍 开始质量趋势分析...")

        # 加载数据
        df = self.load_quality_history(history_path)
        if df.empty:
            print("❌ 无法加载质量历史数据，分析终止")
            return

        # 清理数据
        df = self.clean_data(df)
        if df.empty:
            print("❌ 数据清理后无有效数据，分析终止")
            return

        print(f"📊 加载了 {len(df)} 个质量数据点")

        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成各种图表
        self.generate_coverage_trend(df, str(output_path / "coverage_trend.png"))
        self.generate_quality_score_trend(df, str(output_path / "quality_score_trend.png"))
        self.generate_comprehensive_trend(df, str(output_path / "comprehensive_trends.png"))

        # 计算趋势指标
        metrics = self.calculate_trend_metrics(df)

        # 生成趋势报告
        self.generate_trend_report(df, metrics, str(output_path / "quality-trends-report.md"))

        print("✅ 质量趋势分析完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成质量趋势分析报告')
    parser.add_argument('history_path', help='质量历史CSV文件路径')
    parser.add_argument('--output-dir', '-o', default='.',
                       help='输出目录 (默认: 当前目录)')

    args = parser.parse_args()

    analyzer = QualityTrendAnalyzer()
    analyzer.analyze_trends(args.history_path, args.output_dir)


if __name__ == "__main__":
    main()