#!/usr/bin/env python3
"""
V25.0 战神仪表盘 - Prediction Dashboard
==========================================

功能:
    1. 显示流水线健康度
    2. 显示高危平局预警
    3. 显示历史回测胜率曲线
    4. 显示实盘信号摘要

设计模式:
    - MVC Pattern: 分离数据、视图和控制
    - Observer Pattern: 实时数据更新

作者: Quant Strategist
版本: V25.0-WarGod
日期: 2025-12-25
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
src_root = Path(__file__).path.parent
sys.path.insert(0, str(src_root))


# ============================================================================
# 样式定义
# ============================================================================


class DashboardStyles:
    """终端仪表盘样式"""

    # 颜色代码 (ANSI)
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 背景色
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    # 组合样式
    SUCCESS = GREEN + BOLD
    WARNING = YELLOW + BOLD
    ERROR = RED + BOLD
    INFO = CYAN + BOLD
    HEADER = BLUE + BOLD
    HIGHLIGHT = MAGENTA + BOLD

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """给文本添加颜色"""
        return f"{color}{text}{DashboardStyles.RESET}"

    @staticmethod
    def progress_bar(value: float, max_value: float, width: int = 30) -> str:
        """生成进度条"""
        ratio = max(0, min(1, value / max_value)) if max_value > 0 else 0
        filled = int(ratio * width)
        bar = "█" * filled + "░" * (width - filled)

        # 根据比例选择颜色
        if ratio >= 0.8:
            color = DashboardStyles.GREEN
        elif ratio >= 0.5:
            color = DashboardStyles.YELLOW
        else:
            color = DashboardStyles.RED

        return f"{color}{bar}{DashboardStyles.RESET}"


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class DashboardData:
    """仪表盘数据"""

    # 流水线健康
    health_score: float = 0.0
    health_status: str = "unknown"
    pipeline_uptime: float = 0.0
    last_heartbeat: str = ""

    # 回测指标
    total_bets: int = 0
    win_rate: float = 0.0
    roi: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    equity_curve: list[float] = None

    # 实盘信号
    total_predictions: int = 0
    high_confidence_count: int = 0
    high_value_count: int = 0
    predictions: list[dict] = None

    # 平局预警
    draw_alert_count: int = 0
    high_risk_draws: list[dict] = None

    def __post_init__(self):
        if self.equity_curve is None:
            self.equity_curve = []
        if self.predictions is None:
            self.predictions = []
        if self.high_risk_draws is None:
            self.high_risk_draws = []


# ============================================================================
# 仪表盘视图
# ============================================================================


class WarGodDashboard:
    """
    战神仪表盘 - 量化交易可视化

    功能:
        1. 流水线健康监控
        2. 高危平局预警
        3. 历史回测曲线
        4. 实盘信号展示
    """

    def __init__(self, data_path: str = "data"):
        """
        初始化仪表盘

        Args:
            data_path: 数据目录路径
        """
        self.data_path = data_path
        self.data = DashboardData()

    def load_data(self) -> DashboardData:
        """加载所有数据"""
        # 1. 加载健康监控数据
        self._load_health_data()

        # 2. 加载回测数据
        self._load_backtest_data()

        # 3. 加载实盘信号
        self._load_prediction_data()

        return self.data

    def _load_health_data(self):
        """加载健康监控数据"""
        health_path = os.path.join(self.data_path, "monitoring/pipeline_health.json")

        try:
            if os.path.exists(health_path):
                with open(health_path) as f:
                    health_data = json.load(f)
                    self.data.health_score = health_data.get("health_score", 0)
                    self.data.health_status = health_data.get("health_status", "unknown")
                    self.data.pipeline_uptime = health_data.get("uptime_seconds", 0)
                    self.data.last_heartbeat = health_data.get("timestamp", "")
        except Exception as e:
            print(f"加载健康数据失败: {e}")

    def _load_backtest_data(self):
        """加载回测数据"""
        backtest_path = os.path.join(self.data_path, "backtest/backtest_report.json")

        try:
            if os.path.exists(backtest_path):
                with open(backtest_path) as f:
                    backtest_data = json.load(f)

                    perf = backtest_data.get("performance_metrics", {})
                    risk = backtest_data.get("risk_metrics", {})

                    self.data.total_bets = perf.get("total_bets", 0)
                    self.data.win_rate = perf.get("win_rate", 0) / 100
                    self.data.roi = perf.get("roi", 0)
                    self.data.sharpe_ratio = risk.get("sharpe_ratio", 0)
                    self.data.max_drawdown = risk.get("max_drawdown", 0) / 100
                    self.data.equity_curve = backtest_data.get("equity_curve", [])
        except Exception as e:
            print(f"加载回测数据失败: {e}")

    def _load_prediction_data(self):
        """加载实盘信号数据"""
        prediction_path = os.path.join(self.data_path, "predictions/daily_signals.json")

        try:
            if os.path.exists(prediction_path):
                with open(prediction_path) as f:
                    pred_data = json.load(f)

                    self.data.total_predictions = pred_data.get("total_predictions", 0)
                    self.data.high_confidence_count = pred_data.get("high_confidence", 0)
                    self.data.high_value_count = pred_data.get("high_value", 0)
                    self.data.predictions = pred_data.get("predictions", [])

                    # 提取平局预警
                    high_risk_draws = []
                    for pred in self.data.predictions:
                        if pred.get("recommended_bet") == "D":
                            confidence = pred.get("confidence", 0)
                            if confidence > 0.55:  # 高置信度平局
                                high_risk_draws.append(pred)

                    self.data.draw_alert_count = len(high_risk_draws)
                    self.data.high_risk_draws = high_risk_draws[:5]  # 只保留前5个
        except Exception as e:
            print(f"加载预测数据失败: {e}")

    # ========================================================================
    # 渲染方法
    # ========================================================================

    def render(self, refresh: bool = False) -> None:
        """
        渲染仪表盘

        Args:
            refresh: 是否刷新数据
        """
        if refresh:
            self.load_data()

        # 清屏
        os.system("clear" if os.name == "posix" else "cls")

        # 渲染各个模块
        self._render_header()
        print()
        self._render_health_module()
        print()
        self._render_backtest_module()
        print()
        self._render_prediction_module()
        print()
        self._render_draw_alert_module()
        print()
        self._render_footer()

    def _render_header(self):
        """渲染标题"""
        title = DashboardStyles.colorize("⚔️  战神仪表盘 V25.0 - 量化交易决策系统", DashboardStyles.HEADER)
        subtitle = DashboardStyles.colorize("   War God Dashboard - Quant Trading Decision System", DashboardStyles.DIM)

        print("╔" + "═" * 76 + "╗")
        print("║" + " " * 76 + "║")
        print("║" + " " * 10 + title + " " * (76 - len(title) - 10) + "║")
        print("║" + " " * 8 + subtitle + " " * (76 - len(subtitle) - 8) + "║")
        print("║" + " " * 76 + "║")
        print("╚" + "═" * 76 + "╝")

    def _render_health_module(self):
        """渲染健康监控模块"""
        print(f"┌─ {DashboardStyles.colorize('流水线健康度', DashboardStyles.INFO)} " + "─" * 64 + "┐")

        # 健康分数
        score_color = (
            DashboardStyles.SUCCESS
            if self.data.health_score >= 90
            else (DashboardStyles.WARNING if self.data.health_score >= 70 else DashboardStyles.ERROR)
        )
        score_text = f"{self.data.health_score:.1f}/100"

        print(f"│ 健康分数: {score_color}{score_text}{DashboardStyles.RESET} " + " " * (55 - len(score_text)) + "│")

        # 健康状态进度条
        status_emoji = {
            "healthy": "🟢",
            "degraded": "🟡",
            "warning": "🟠",
            "critical": "🔴",
        }.get(self.data.health_status, "⚪")

        progress = DashboardStyles.progress_bar(self.data.health_score, 100, 40)
        print(f"│ 状态: {status_emoji} {self.data.health_status.upper():12s} {progress} │")

        # 运行时间
        uptime_hours = self.data.pipeline_uptime / 3600
        print(f"│ 运行时间: {uptime_hours:.1f} 小时" + " " * (56 - len(f"{uptime_hours:.1f} 小时")) + "│")

        # 最后心跳
        if self.data.last_heartbeat:
            heartbeat_time = datetime.fromisoformat(self.data.last_heartbeat).strftime("%H:%M:%S")
            print(f"│ 最后心跳: {heartbeat_time}" + " " * (57 - len(heartbeat_time)) + "│")
        else:
            print("│ 最后心跳: --:--:--" + " " * 50 + "│")

        print("└" + "─" * 76 + "┘")

    def _render_backtest_module(self):
        """渲染回测指标模块"""
        print(f"┌─ {DashboardStyles.colorize('历史回测胜率曲线', DashboardStyles.INFO)} " + "─" * 60 + "┐")

        # 核心指标
        roi_color = DashboardStyles.SUCCESS if self.data.roi > 0 else DashboardStyles.ERROR
        roi_text = f"{self.data.roi:+.2f}%"

        print(
            f"│  ROI: {roi_color}{roi_text}{DashboardStyles.RESET}  "
            f"胜率: {self.data.win_rate:.1%}  "
            f"夏普: {self.data.sharpe_ratio:.3f}  "
            f"回撤: {self.data.max_drawdown:.1%}" + " " * 10 + "│"
        )

        # 简单的资金曲线可视化
        if self.data.equity_curve and len(self.data.equity_curve) > 1:
            print("│" + " " * 76 + "│")
            print("│  资金曲线:" + " " * 67 + "│")

            # 归一化并绘制曲线
            curve = self.data.equity_curve
            max_points = 70
            if len(curve) > max_points:
                # 降采样
                step = len(curve) // max_points
                curve = curve[::step]

            base = curve[0]
            for i, value in enumerate(curve):
                # 计算相对变化
                change_pct = (value - base) / base * 100 if base > 0 else 0

                # 选择符号和颜色
                if change_pct > 2:
                    symbol = "█"
                    color = DashboardStyles.GREEN
                elif change_pct > 0:
                    symbol = "▓"
                    color = DashboardStyles.GREEN
                elif change_pct > -2:
                    symbol = "▒"
                    color = DashboardStyles.YELLOW
                else:
                    symbol = "░"
                    color = DashboardStyles.RED

                # 分行显示（每行30个点）
                if i > 0 and i % 30 == 0:
                    print(f"│    {color}{symbol}{DashboardStyles.RESET}")
                else:
                    if i == 0:
                        print("│    ", end="")

            # 补齐最后一行
            print(DashboardStyles.RESET + " " * (73 - (len(curve) % 30) * 2) + "│")

        print("└" + "─" * 76 + "┘")

    def _render_prediction_module(self):
        """渲染实盘信号模块"""
        print(f"┌─ {DashboardStyles.colorize('实盘信号摘要', DashboardStyles.INFO)} " + "─" * 63 + "┐")

        print(
            f"│  总信号: {self.data.total_predictions}  "
            f"高置信: {DashboardStyles.GREEN}{self.data.high_confidence_count}{DashboardStyles.RESET}  "
            f"高价值: {DashboardStyles.HIGHLIGHT}{self.data.high_value_count}{DashboardStyles.RESET}  " + " " * 20 + "│"
        )

        # 显示前5个高价值信号
        if self.data.predictions:
            high_value = [p for p in self.data.predictions if p.get("edge", 0) > 0.08 and p.get("confidence", 0) > 0.60]

            if high_value:
                print("│" + "─" * 76 + "│")
                for pred in high_value[:3]:  # 只显示前3个
                    match_time = pred.get("match_time", "")[:16]
                    home = pred.get("home_team", "")[:15]
                    away = pred.get("away_team", "")[:15]
                    bet = pred.get("recommended_bet", "?")
                    conf = pred.get("confidence", 0)
                    edge = pred.get("edge", 0)
                    rating = pred.get("value_rating", "")

                    bet_emoji = {"H": "🏠", "D": "🤝", "A": "✈️"}.get(bet, "❓")

                    print(f"│  {bet_emoji} {home} vs {away}")
                    print(f"│     时间: {match_time}  投注: {bet}  置信: {conf:.1%}  优势: +{edge:.1%}  {rating}")

        print("└" + "─" * 76 + "┘")

    def _render_draw_alert_module(self):
        """渲染平局预警模块"""
        print(f"┌─ {DashboardStyles.colorize('高危平局预警 (12.26)', DashboardStyles.ERROR)} " + "─" * 57 + "┐")

        if self.data.high_risk_draws:
            print(
                f"│  ⚠️  检测到 {DashboardStyles.colorize(str(self.data.draw_alert_count), DashboardStyles.ERROR)} 场高危平局信号"
            )
            print("│" + "─" * 76 + "│")

            for pred in self.data.high_risk_draws[:5]:
                match_time = pred.get("match_time", "")[:16]
                home = pred.get("home_team", "")
                away = pred.get("away_team", "")
                conf = pred.get("confidence", 0)

                print(f"│  🤝 {home} vs {away}")
                print(
                    f"│     时间: {match_time}  "
                    f"平局概率: {conf:.1%}  "
                    f"风险等级: {DashboardStyles.colorize('HIGH', DashboardStyles.ERROR)}"
                )
        else:
            print("│  ✅ 当前无高危平局信号" + " " * 52 + "│")

        print("└" + "─" * 76 + "┘")

    def _render_footer(self):
        """渲染页脚"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{DashboardStyles.DIM}最后更新: {now}  |  按 Ctrl+C 退出{DashboardStyles.RESET}\n")

    def run_interactive(self, interval: int = 30):
        """
        运行交互式仪表盘

        Args:
            interval: 刷新间隔（秒）
        """
        try:
            while True:
                self.render(refresh=True)
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{DashboardStyles.SUCCESS}仪表盘已退出{DashboardStyles.RESET}")


# ============================================================================
# 主程序入口
# ============================================================================


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="V25.0 战神仪表盘 - War God Dashboard")
    parser.add_argument("--data-path", type=str, default="data", help="数据目录路径（默认: data）")
    parser.add_argument("--once", action="store_true", help="只显示一次，不进入交互模式")
    parser.add_argument("--interval", type=int, default=30, help="刷新间隔（秒，默认: 30）")

    args = parser.parse_args()

    # 创建仪表盘
    dashboard = WarGodDashboard(data_path=args.data_path)

    # 加载数据
    dashboard.load_data()

    if args.once:
        # 只显示一次
        dashboard.render()
    else:
        # 进入交互模式
        dashboard.run_interactive(interval=args.interval)


if __name__ == "__main__":
    main()
