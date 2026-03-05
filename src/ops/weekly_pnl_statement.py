#!/usr/bin/env python3
"""
V19.4 每周实战对账单 (Weekly P&L Statement)
===============================================

自动对比"模型预测"与"真实赛果"，计算本周的真实胜率、真实Yield。

作者: V19.4 风控团队
日期: 2025-12-23
"""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# 设置样式
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")

logger = logging.getLogger(__name__)


class WeeklyPnLGenerator:
    """
    每周实战对账单生成器

    功能:
    1. 从数据库获取本周的预测和实际结果
    2. 计算真实胜率和Yield
    3. 生成可视化报告
    4. 对比模型表现与市场基准
    """

    def __init__(self, db_config: dict | None = None):
        """
        初始化对账单生成器

        Args:
            db_config: 数据库配置
        """
        # 默认数据库配置
        self.db_config = db_config or {
            "host": "localhost",
            "port": 5432,
            "database": "football_db",
            "user": "football_user",
            "password": "",  # V190: 移除硬编码密码，使用环境变量
        }

        # 数据目录
        self.data_dir = Path("/home/user/projects/FootballPrediction/data/pnl")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("每周对账单生成器初始化完成")

    def get_db_connection(self):
        """获取数据库连接"""
        import psycopg2

        return psycopg2.connect(**self.db_config)

    def get_week_predictions(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        获取本周的预测数据

        Args:
            start_date: 周开始日期
            end_date: 周结束日期

        Returns:
            pd.DataFrame: 预测数据
        """
        conn = self.get_db_connection()

        query = """
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_time,
            m.home_score,
            m.away_score,
            m.result_score,
            COALESCE(p.prediction, 'N/A') as predicted_result,
            COALESCE(p.confidence, 0.0) as confidence,
            p.created_at as prediction_time,
            COALESCE(p.odds_h, 0.0) as odds_h,
            COALESCE(p.odds_d, 0.0) as odds_d,
            COALESCE(p.odds_a, 0.0) as odds_a
        FROM matches m
        LEFT JOIN predictions p ON m.match_id = p.match_id
        WHERE m.match_time >= %s
          AND m.match_time <= %s
          AND m.result_score IS NOT NULL
        ORDER BY m.match_time
        """

        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()

        logger.info(f"获取到 {len(df)} 场比赛的预测数据")

        return df

    def calculate_performance_metrics(self, df: pd.DataFrame) -> dict:
        """
        计算绩效指标

        Args:
            df: 预测数据

        Returns:
            Dict: 绩效指标
        """
        if df.empty:
            return {}

        # 过滤有效预测
        valid_df = df[df["predicted_result"] != "N/A"].copy()

        if len(valid_df) == 0:
            return {
                "total_matches": len(df),
                "predicted_matches": 0,
                "accuracy": 0,
                "yield_pct": 0,
                "total_profit": 0,
            }

        # 计算准确率
        valid_df["is_correct"] = valid_df["predicted_result"] == valid_df["result_score"]
        accuracy = valid_df["is_correct"].mean()

        # 计算Yield (假设每场下注1单位)
        valid_df["profit"] = valid_df.apply(self._calculate_profit, axis=1)
        total_profit = valid_df["profit"].sum()
        yield_pct = (total_profit / len(valid_df)) * 100

        # 分类别统计
        results_by_type = {}
        for result_type in ["H", "D", "A"]:
            type_mask = valid_df["predicted_result"] == result_type
            type_correct = valid_df[type_mask]["is_correct"].sum() if type_mask.sum() > 0 else 0
            type_total = type_mask.sum()
            type_accuracy = (type_correct / type_total * 100) if type_total > 0 else 0

            results_by_type[result_type] = {
                "total": type_total,
                "correct": type_correct,
                "accuracy": type_accuracy,
            }

        # 混淆矩阵
        confusion = pd.crosstab(
            valid_df["predicted_result"],
            valid_df["result_score"],
            rownames=["预测"],
            colnames=["实际"],
        )

        return {
            "total_matches": len(df),
            "predicted_matches": len(valid_df),
            "accuracy": accuracy,
            "yield_pct": yield_pct,
            "total_profit": total_profit,
            "results_by_type": results_by_type,
            "confusion_matrix": confusion,
        }

    def _calculate_profit(self, row) -> float:
        """计算单场盈亏"""
        prediction = row["predicted_result"]
        actual = row["result_score"]

        # 获取对应赔率
        if prediction == "H":
            odds = row["odds_h"]
        elif prediction == "D":
            odds = row["odds_d"]
        else:  # 'A'
            odds = row["odds_a"]

        # 如果赔率无效，跳过
        if odds <= 1.0:
            return 0.0

        # 计算盈亏（下注1单位）
        if prediction == actual:
            return odds - 1  # 净收益
        return -1  # 损失本金

    def generate_report(
        self, week_start: datetime | None = None, week_end: datetime | None = None
    ) -> dict:
        """
        生成每周对账报告

        Args:
            week_start: 周开始日期（默认为本周一）
            week_end: 周结束日期（默认为本周日）

        Returns:
            Dict: 报告数据
        """
        # 确定日期范围
        if week_start is None:
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)

        logger.info(f"生成每周报告: {week_start.date()} ~ {week_end.date()}")

        # 获取预测数据
        df = self.get_week_predictions(week_start, week_end)

        # 计算绩效指标
        metrics = self.calculate_performance_metrics(df)

        # 生成报告
        report = {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }

        # 保存报告
        self._save_report(report)

        # 生成可视化
        if not df.empty and df[df["predicted_result"] != "N/A"].shape[0] > 0:
            self._generate_visualizations(df, metrics)

        return report

    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_file = (
            self.data_dir / f"weekly_pnl_{report['week_start']}_to_{report['week_end']}.json"
        )

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"每周报告已保存: {report_file}")

        # 同时保存文本格式
        txt_file = self.data_dir / f"weekly_pnl_{report['week_start']}_to_{report['week_end']}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(self._format_text_report(report))

        logger.info(f"文本报告已保存: {txt_file}")

    def _format_text_report(self, report: dict) -> str:
        """格式化文本报告"""
        m = report["metrics"]

        text = f"""
{"=" * 70}
V19.4 每周实战对账单
{"=" * 70}
📅 报告周期: {report["week_start"]} ~ {report["week_end"]}
⏰ 生成时间: {report["timestamp"]}

{"─" * 70}
📊 基础统计
{"─" * 70}
总比赛场数: {m.get("total_matches", 0)}
预测场次数: {m.get("predicted_matches", 0)}

{"─" * 70}
🎯 预测准确率
{"─" * 70}
整体准确率: {m.get("accuracy", 0) * 100:.2f}%

按结果类型统计:
"""

        if "results_by_type" in m:
            for result_type, stats in m["results_by_type"].items():
                text += f"  {result_type}: {stats['accuracy']:.2f}% ({stats['correct']}/{stats['total']})\n"

        text += f"""
{"─" * 70}
💰 执行绩效 (Yield)
{"─" * 70}
总盈亏: {m.get("total_profit", 0):.2f} 单位
Yield: {m.get("yield_pct", 0):.2f}%

{"─" * 70}
📉 混淆矩阵
{"─" * 70}
"""

        if "confusion_matrix" in m:
            text += str(m["confusion_matrix"])

        text += f"\n{'=' * 70}\n"

        return text

    def _generate_visualizations(self, df: pd.DataFrame, metrics: dict):
        """生成可视化图表"""
        valid_df = df[df["predicted_result"] != "N/A"].copy()

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            f"V19.4 每周实战对账单 ({metrics['week_start']} ~ {metrics['week_end']})",
            fontsize=16,
            fontweight="bold",
        )

        # 1. 累计收益曲线
        ax1 = axes[0, 0]
        valid_df = valid_df.sort_values("match_time").copy()
        valid_df["cumulative_profit"] = valid_df["profit"].cumsum()
        ax1.plot(
            range(len(valid_df)), valid_df["cumulative_profit"], linewidth=2, color="steelblue"
        )
        ax1.axhline(0, color="red", linestyle="--", linewidth=1.5)
        ax1.fill_between(
            range(len(valid_df)),
            valid_df["cumulative_profit"],
            0,
            where=(valid_df["cumulative_profit"] >= 0),
            alpha=0.3,
            color="green",
        )
        ax1.fill_between(
            range(len(valid_df)),
            valid_df["cumulative_profit"],
            0,
            where=(valid_df["cumulative_profit"] < 0),
            alpha=0.3,
            color="red",
        )
        ax1.set_xlabel("比赛序号")
        ax1.set_ylabel("累计收益 (单位)")
        ax1.set_title("累计收益曲线")
        ax1.grid(True, alpha=0.3)

        # 2. 预测结果分布
        ax2 = axes[0, 1]
        prediction_counts = valid_df["predicted_result"].value_counts()
        colors = {"H": "steelblue", "D": "gray", "A": "coral"}
        ax2.bar(
            prediction_counts.index,
            prediction_counts.values,
            color=[colors.get(x, "blue") for x in prediction_counts.index],
        )
        ax2.set_xlabel("预测结果")
        ax2.set_ylabel("场次")
        ax2.set_title("预测结果分布")
        ax2.grid(True, alpha=0.3, axis="y")

        # 3. 混淆矩阵
        ax3 = axes[1, 0]
        if "confusion_matrix" in metrics:
            sns.heatmap(
                metrics["confusion_matrix"],
                annot=True,
                fmt="d",
                cmap="Blues",
                ax=ax3,
                cbar_kws={"label": "场次"},
            )
        ax3.set_title("预测结果混淆矩阵")

        # 4. 每日盈亏
        ax4 = axes[1, 1]
        valid_df["date"] = pd.to_datetime(valid_df["match_time"]).dt.date
        daily_profit = valid_df.groupby("date")["profit"].sum()
        ax4.bar(range(len(daily_profit)), daily_profit.values, color="steelblue")
        ax4.axhline(0, color="red", linestyle="--", linewidth=1)
        ax4.set_xlabel("日期")
        ax4.set_ylabel("盈亏 (单位)")
        ax4.set_title("每日盈亏")
        ax4.grid(True, alpha=0.3, axis="y")

        # 设置x轴标签
        if len(daily_profit) <= 7:
            ax4.set_xticks(range(len(daily_profit)))
            ax4.set_xticklabels([d.strftime("%m-%d") for d in daily_profit.index], rotation=45)

        plt.tight_layout()

        # 保存图表
        chart_file = (
            self.data_dir / f"weekly_pnl_chart_{metrics['week_start']}_to_{metrics['week_end']}.png"
        )
        plt.savefig(chart_file, dpi=150, bbox_inches="tight")
        logger.info(f"可视化图表已保存: {chart_file}")
        plt.close()

    def compare_with_backtest(self, actual_metrics: dict, backtest_path: str) -> dict:
        """
        对比实际表现与回测结果

        Args:
            actual_metrics: 实际绩效指标
            backtest_path: 回测数据文件路径

        Returns:
            Dict: 对比结果
        """
        # 加载回测数据
        backtest_file = Path(backtest_path)
        if not backtest_file.exists():
            logger.warning(f"回测数据文件不存在: {backtest_path}")
            return {}

        with open(backtest_file) as f:
            backtest_data = json.load(f)

        backtest_metrics = backtest_data.get("metrics", {})

        # 对比
        comparison = {
            "backtest_accuracy": backtest_metrics.get("accuracy", 0),
            "actual_accuracy": actual_metrics.get("accuracy", 0),
            "accuracy_diff": actual_metrics.get("accuracy", 0)
            - backtest_metrics.get("accuracy", 0),
            "backtest_yield": backtest_metrics.get("yield_pct", 0),
            "actual_yield": actual_metrics.get("yield_pct", 0),
            "yield_diff": actual_metrics.get("yield_pct", 0) - backtest_metrics.get("yield_pct", 0),
        }

        # 判断是否显著偏离
        comparison["is_significantly_different"] = (
            abs(comparison["accuracy_diff"]) > 0.10  # 准确率偏离超过10%
            or abs(comparison["yield_diff"]) > 0.20  # Yield偏离超过20%
        )

        return comparison


# ============================================
# 便捷函数
# ============================================


def generate_weekly_pnl(week_start: str | None = None, week_end: str | None = None) -> dict:
    """
    生成本周对账单的便捷函数

    Args:
        week_start: 周开始日期 (YYYY-MM-DD)
        week_end: 周结束日期 (YYYY-MM-DD)

    Returns:
        Dict: 报告数据
    """
    generator = WeeklyPnLGenerator()

    start = datetime.strptime(week_start, "%Y-%m-%d") if week_start else None

    end = datetime.strptime(week_end, "%Y-%m-%d") if week_end else None

    return generator.generate_report(start, end)


# ============================================
# 主程序
# ============================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    generator = WeeklyPnLGenerator()

    # 生成本周报告
    report = generator.generate_report()

    # 打印摘要
    if "metrics" in report:
        m = report["metrics"]
