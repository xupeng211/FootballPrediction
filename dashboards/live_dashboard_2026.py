#!/usr/bin/env python3
"""
2026 实战收益可视化面板 (Live Performance Dashboard)
======================================================

功能:
1. 实时 ROI 曲线 - 展示资金变动情况
2. 今日信号列表 - 高价值投注机会
3. 胜率分布统计 - Home/Draw/Away 命中比例
4. 详细投注记录 - 可筛选的历史数据
5. 风险评估板块 - 最大回撤、破产风险、止损预警
6. 模型漂移检测 - 回测 vs 实战胜率对比

运行方式:
    streamlit run dashboards/live_dashboard_2026.py

    或指定端口:
    streamlit run dashboards/live_dashboard_2026.py --server.port 8501

Author: Senior Full-Stack Engineer & Data Visualization Expert
Version: 2.0.0 - 风控增强版
Date: 2025-12-31
"""

import logging
import os
import sys
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 风控常量配置
# ============================================================================

# 回测基准胜率（V26.8 模型历史表现）
BACKTEST_WIN_RATE = 0.56  # 56%
BACKTEST_SAMPLE_SIZE = 9305  # 回测样本数

# 止损阈值
STOP_LOSS_7DAY_ROI = -0.15  # 7天 ROI < -15% 触发止损
STOP_LOSS_30DAY_ROI = -0.25  # 30天 ROI < -25% 触发强制止损

# 风险等级阈值
RISK_LEVEL_LOW = 0.05  # 破产风险 < 5%
RISK_LEVEL_MEDIUM = 0.15  # 破产风险 5-15%
RISK_LEVEL_HIGH = 0.30  # 破产风险 > 15%

# 漂移检测阈值
DRIFT_WARNING_THRESHOLD = 0.05  # 胜率偏差 > 5%
DRIFT_CRITICAL_THRESHOLD = 0.10  # 胜率偏差 > 10%

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="2026 实战预测面板",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS（包含风控模块样式）
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6c757d;
    }
    .positive { color: #28a745; }
    .negative { color: #dc3545; }
    .warning { color: #ffc107; }
    .stPlotlyChart { width: 100%; }

    /* 系统状态指示灯 */
    .status-indicator {
        display: inline-block;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    .status-green {
        background-color: #28a745;
        box-shadow: 0 0 0 4px rgba(40, 167, 69, 0.2);
    }
    .status-yellow {
        background-color: #ffc107;
        box-shadow: 0 0 0 4px rgba(255, 193, 7, 0.2);
    }
    .status-red {
        background-color: #dc3545;
        box-shadow: 0 0 0 4px rgba(220, 53, 69, 0.2);
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    /* 风控卡片 */
    .risk-card {
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border-left: 5px solid;
    }
    .risk-low {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left-color: #28a745;
    }
    .risk-medium {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border-left-color: #ffc107;
    }
    .risk-high {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-left-color: #dc3545;
    }

    /* 漂移警告 */
    .drift-warning {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .drift-critical {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* 止损横幅 */
    .stop-loss-banner {
        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# 数据加载函数
# ============================================================================


@st.cache_data(ttl=300)  # 缓存 5 分钟
def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


@st.cache_data(ttl=300)
def load_predictions():
    """加载预测数据"""
    prediction_file = PROJECT_ROOT / "predictions" / "v26_smart_predict_results.csv"

    if not prediction_file.exists():
        return pd.DataFrame()

    df = pd.read_csv(prediction_file)

    # 解析数值列
    def parse_percentage(val):
        if pd.isna(val):
            return 0.0
        if isinstance(val, str):
            return float(val.rstrip("%")) / 100.0
        return val / 100.0 if val > 1 else val

    df["confidence_pct"] = df["confidence"].apply(parse_percentage)
    df["prob_home_pct"] = df["prob_home"].apply(parse_percentage)
    df["prob_draw_pct"] = df["prob_draw"].apply(parse_percentage)
    df["prob_away_pct"] = df["prob_away"].apply(parse_percentage)
    df["expected_roi_pct"] = df["expected_roi"].apply(parse_percentage)

    # 解析日期
    df["match_date_dt"] = pd.to_datetime(df["match_date"])

    # 确定是否为高价值
    df["is_high_value_bool"] = (
        (df["confidence_pct"] > 0.60) &
        (df["expected_roi_pct"] > 0.05)
    )

    return df


@st.cache_data(ttl=60)  # 缓存 1 分钟
def load_match_results():
    """加载比赛结果"""
    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.home_score,
                    m.away_score,
                    m.status,
                    m.league_name
                FROM matches m
                WHERE m.status = 'finished'
                  AND m.home_score IS NOT NULL
                  AND m.away_score IS NOT NULL
                  AND m.match_date >= '2026-01-01'
                ORDER BY m.match_date DESC
            """)
            results = cursor.fetchall()
            return pd.DataFrame(results) if results else pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def calculate_ledger(predictions_df: pd.DataFrame, results_df: pd.DataFrame):
    """计算盈亏台账"""
    if predictions_df.empty or results_df.empty:
        return pd.DataFrame()

    # 合并预测和结果
    merged = predictions_df.merge(
        results_df[["match_id", "home_score", "away_score"]],
        on="match_id",
        how="left"
    )

    # 确定实际结果
    def get_actual_result(row):
        if pd.notna(row["home_score"]) and pd.notna(row["away_score"]):
            if row["home_score"] > row["away_score"]:
                return "Home"
            elif row["home_score"] < row["away_score"]:
                return "Away"
            else:
                return "Draw"
        return None

    merged["actual_result"] = merged.apply(get_actual_result, axis=1)
    merged["is_finished"] = merged["actual_result"].notna()

    # 计算盈亏
    UNIT_STAKE = 10

    def calculate_profit(row):
        if not row["is_finished"] or row["actual_result"] is None:
            return None, None, None, False

        prediction = row["prediction"]
        actual = row["actual_result"]

        won = (prediction == actual)

        # 计算赔率
        if prediction == "Home":
            prob = row["prob_home_pct"]
        elif prediction == "Draw":
            prob = row["prob_draw_pct"]
        else:
            prob = row["prob_away_pct"]

        if prob > 0:
            odds = 1.0 / prob
        else:
            odds = 1.0

        stake = UNIT_STAKE
        if won:
            profit = stake * (odds - 1)
            return_stake = stake + profit
        else:
            profit = -stake
            return_stake = 0

        return profit, return_stake, won, True

    merged[["profit", "return_stake", "won", "has_result"]] = merged.apply(
        lambda row: pd.Series(calculate_profit(row)),
        axis=1
    )

    # 只保留有结果的记录
    ledger = merged[merged["has_result"] == True].copy()

    if ledger.empty:
        return pd.DataFrame()

    # 按日期排序
    ledger = ledger.sort_values("match_date_dt")

    # 计算累计盈亏
    ledger["cumulative_pnl"] = ledger["profit"].cumsum()

    return ledger


# ============================================================================
# 风控指标计算函数
# ============================================================================


def calculate_max_drawdown(ledger_df: pd.DataFrame) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
    """
    计算最大回撤

    Args:
        ledger_df: 包含 cumulative_pnl 列的数据框

    Returns:
        (最大回撤比例, 回撤开始日期, 回撤结束日期)
    """
    if ledger_df.empty or "cumulative_pnl" not in ledger_df.columns:
        return 0.0, None, None

    # 按日期汇总累计盈亏
    daily_cumsum = ledger_df.groupby(ledger_df["match_date_dt"].dt.date)["cumulative_pnl"].max()

    if len(daily_cumsum) < 2:
        return 0.0, None, None

    # 计算回撤
    cumsum_values = daily_cumsum.values
    running_max = np.maximum.accumulate(cumsum_values)
    drawdown = (cumsum_values - running_max) / (running_max + 1e-6)  # 避免除零

    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]

    # 找到回撤结束日期（恢复点）
    end_idx = max_dd_idx
    while end_idx < len(drawdown) - 1 and drawdown[end_idx + 1] < 0:
        end_idx += 1

    # 回撤开始日期（最高点之前的最高点）
    start_idx = np.argmax(cumsum_values[:max_dd_idx + 1])

    start_date = pd.to_datetime(daily_cumsum.index[start_idx])
    end_date = pd.to_datetime(daily_cumsum.index[end_idx])

    return max_dd, start_date, end_date


def calculate_risk_of_ruin(ledger_df: pd.DataFrame, bankroll: float = 1000.0) -> float:
    """
    计算破产风险概率 (Risk of Ruin)

    使用经典 RoR 公式:
    RoR = ((1 - edge) / (1 + edge)) ^ (bankroll / unit_stake)

    其中 edge = (win_rate * avg_odds) - 1

    Args:
        ledger_df: 投注记录
        bankroll: 初始资金

    Returns:
        破产风险概率 (0-1)
    """
    if ledger_df.empty:
        return 0.0

    total_bets = len(ledger_df)
    if total_bets < 10:  # 样本太少
        return 0.5  # 默认中等风险

    # 计算实际胜率
    win_rate = ledger_df["won"].sum() / total_bets

    # 计算平均赔率
    UNIT_STAKE = 10

    def get_odds(row):
        if row["won"]:
            return row["return_stake"] / UNIT_STAKE
        else:
            return 0

    avg_odds = ledger_df.apply(get_odds, axis=1).mean()

    # 计算 edge (期望收益)
    edge = (win_rate * avg_odds) - 1

    # 如果 edge 为负，破产风险很高
    if edge <= 0:
        return 0.8

    # 计算 RoR
    # 使用保守估计：bankroll / average_stake
    avg_stake = UNIT_STAKE
    units = bankroll / avg_stake

    risk_of_ruin = ((1 - edge) / (1 + edge)) ** units

    return min(risk_of_ruin, 0.99)  # 上限 99%


def calculate_period_roi(ledger_df: pd.DataFrame, days: int) -> float:
    """
    计算指定时间窗口的 ROI

    Args:
        ledger_df: 投注记录
        days: 天数

    Returns:
        ROI (百分比)
    """
    if ledger_df.empty:
        return 0.0

    cutoff_date = datetime.now() - timedelta(days=days)
    period_df = ledger_df[ledger_df["match_date_dt"] >= cutoff_date]

    if period_df.empty:
        return 0.0

    total_profit = period_df["profit"].sum()
    total_stake = len(period_df) * 10  # UNIT_STAKE = 10

    return (total_profit / total_stake * 100) if total_stake > 0 else 0.0


def detect_model_drift(ledger_df: pd.DataFrame, backtest_win_rate: float = BACKTEST_WIN_RATE) -> Dict:
    """
    检测模型漂移

    对比回测胜率与实战胜率，计算统计显著性

    Args:
        ledger_df: 投注记录
        backtest_win_rate: 回测胜率

    Returns:
        包含漂移信息的字典
    """
    if ledger_df.empty:
        return {
            "has_drift": False,
            "drift_magnitude": 0.0,
            "live_win_rate": 0.0,
            "backtest_win_rate": backtest_win_rate,
            "significance": "unknown"
        }

    total_bets = len(ledger_df)
    live_wins = ledger_df["won"].sum()
    live_win_rate = live_wins / total_bets if total_bets > 0 else 0

    drift_magnitude = live_win_rate - backtest_win_rate

    # 计算 Z-score (检验显著性)
    # H0: 实战胜率 = 回测胜率
    # z = (p_observed - p_expected) / sqrt(p_expected * (1 - p_expected) / n)

    if total_bets > 30:
        se = math.sqrt(backtest_win_rate * (1 - backtest_win_rate) / total_bets)
        z_score = drift_magnitude / se if se > 0 else 0

        # p-value (双尾检验)
        import scipy.stats as stats
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        if p_value < 0.01:
            significance = "critical"  # 99% 置信度
        elif p_value < 0.05:
            significance = "significant"  # 95% 置信度
        else:
            significance = "normal"
    else:
        significance = "insufficient_data"

    return {
        "has_drift": abs(drift_magnitude) > DRIFT_WARNING_THRESHOLD,
        "drift_magnitude": drift_magnitude,
        "live_win_rate": live_win_rate,
        "backtest_win_rate": backtest_win_rate,
        "significance": significance,
        "sample_size": total_bets
    }


# ============================================================================
# 绘图函数
# ============================================================================


def plot_roi_curve(ledger_df: pd.DataFrame):
    """绘制 ROI 曲线（带回撤标记）"""
    if ledger_df.empty:
        st.info("暂无数据可显示")
        return

    # 按日期汇总
    daily_pnl = ledger_df.groupby(ledger_df["match_date_dt"].dt.date).agg({
        "profit": "sum",
        "won": "sum",
        "return_stake": "sum",
    }).reset_index()
    daily_pnl.columns = ["date", "profit", "wins", "return_stake"]
    daily_pnl["cumulative_pnl"] = daily_pnl["profit"].cumsum()

    # 计算最大回撤
    max_dd, dd_start, dd_end = calculate_max_drawdown(ledger_df)

    # 创建图表
    fig = go.Figure()

    # 添加累计盈亏曲线
    fig.add_trace(go.Scatter(
        x=daily_pnl["date"],
        y=daily_pnl["cumulative_pnl"],
        mode="lines+markers",
        name="累计盈亏",
        line=dict(color="#1f77b4", width=3),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.1)"
    ))

    # 标记最大回撤区域
    if max_dd < -0.05:  # 回撤超过 5% 才标记
        fig.add_vrect(
            x0=dd_start, x1=dd_end,
            fillcolor="rgba(220, 53, 69, 0.2)",
            layer="below", line_width=0,
            annotation_text=f"最大回撤: {max_dd:.1%}",
            annotation_position="top left"
        )

    # 添加零线
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title=f"📈 2026 实战累计盈亏曲线 (最大回撤: {max_dd:.1%})",
        xaxis_title="日期",
        yaxis_title="累计盈亏 (点)",
        hovermode="x unified",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 显示统计表格
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_bets = len(ledger_df)
        st.metric("总投注数", f"{total_bets} 注")
    with col2:
        total_wins = ledger_df["won"].sum()
        win_rate = total_wins / total_bets if total_bets > 0 else 0
        st.metric("命中率", f"{win_rate:.1%}")
    with col3:
        total_pnl = ledger_df["profit"].sum()
        delta = f"{total_pnl:+.0f}"
        st.metric("净盈亏", delta, delta=f"{delta}")
    with col4:
        roi = (total_pnl / (total_bets * 10) * 100) if total_bets > 0 else 0
        roi_class = "positive" if roi >= 0 else "negative"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {roi_class}">{roi:+.1f}%</div>
            <div class="metric-label">投资回报率 (ROI)</div>
        </div>
        """, unsafe_allow_html=True)


def plot_win_rate_distribution(ledger_df: pd.DataFrame):
    """绘制胜率分布饼图"""
    if ledger_df.empty:
        st.info("暂无数据可显示")
        return

    # 按预测结果统计
    prediction_counts = ledger_df["prediction"].value_counts()
    won_by_prediction = ledger_df[ledger_df["won"] == True].groupby("prediction").size()

    labels = ["Home", "Draw", "Away"]
    sizes = []
    colors = []

    for pred in labels:
        if pred in prediction_counts:
            total = prediction_counts[pred]
            won = won_by_prediction.get(pred, 0)
            win_rate = won / total if total > 0 else 0
            sizes.append(total)
        else:
            sizes.append(0)

    # 颜色映射
    color_map = {
        "Home": "#ff6b6b",
        "Draw": "#4ecdc4",
        "Away": "#45b7d1"
    }
    colors = [color_map.get(label, "#95a5a6") for label in labels]

    # 创建饼图
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=sizes,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont_size=14,
    )])

    fig.update_layout(
        title="🎯 预测分布",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(fig, use_container_width=True)

    # 显示详细统计
    with col2:
        st.subheader("📊 命中统计")

        for pred in labels:
            if pred in prediction_counts:
                total = prediction_counts[pred]
                won = won_by_prediction.get(pred, 0)
                win_rate = won / total if total > 0 else 0

                # 根据预测类型选择图标
                icon = {"Home": "🏠", "Draw": "🤝", "Away": "✈️"}.get(pred, "•")

                st.markdown(f"""
                <div style="padding: 10px; margin: 5px 0; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid {color_map.get(pred, '#gray')};">
                    <div style="font-size: 1.2rem; font-weight: bold;">
                        {icon} {pred}
                    </div>
                    <div style="font-size: 0.9rem; color: #6c757d;">
                        投注: {total} 注 | 命中: {won} 注 | 命中率: <span style="color: {'#28a745' if win_rate > 0.5 else '#dc3545'};">{win_rate:.1%}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def display_risk_assessment(ledger_df: pd.DataFrame):
    """显示风险评估板块"""
    st.subheader("⚠️ 风险评估")

    if ledger_df.empty:
        st.info("暂无数据可进行风险评估")
        return

    # 计算各项风险指标
    max_dd, dd_start, dd_end = calculate_max_drawdown(ledger_df)
    risk_of_ruin = calculate_risk_of_ruin(ledger_df)
    roi_7d = calculate_period_roi(ledger_df, 7)
    roi_30d = calculate_period_roi(ledger_df, 30)

    # 确定风险等级
    if risk_of_ruin < RISK_LEVEL_LOW:
        risk_level = "low"
        risk_text = "低风险"
        risk_emoji = "✅"
        risk_desc = "破产风险较低，可继续当前策略"
    elif risk_of_ruin < RISK_LEVEL_MEDIUM:
        risk_level = "medium"
        risk_text = "中等风险"
        risk_emoji = "⚠️"
        risk_desc = "破产风险中等，建议适当降低仓位"
    else:
        risk_level = "high"
        risk_text = "高风险"
        risk_emoji = "🚨"
        risk_desc = "破产风险较高，强烈建议暂停投注"

    # 两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        # 风险等级卡片
        st.markdown(f"""
        <div class="risk-card risk-{risk_level}">
            <h3>{risk_emoji} 风险等级: {risk_text}</h3>
            <p style="margin-bottom: 0.5rem;"><strong>破产风险概率:</strong> {risk_of_ruin:.1%}</p>
            <p style="margin-bottom: 0.5rem;"><strong>最大回撤:</strong> {max_dd:.1%}</p>
            <p style="margin-bottom: 0.5rem;"><strong>回撤期间:</strong> {dd_start.strftime('%Y-%m-%d')} 至 {dd_end.strftime('%Y-%m-%d') if dd_start and dd_end else 'N/A'}</p>
            <p style="margin: 0; color: #6c757d; font-size: 0.9rem;">{risk_desc}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 时间窗口 ROI
        st.markdown("""
        <div class="risk-card risk-low">
            <h3>📊 时间窗口表现</h3>
        """, unsafe_allow_html=True)

        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            roi_7d_class = "positive" if roi_7d >= 0 else "negative"
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 1.5rem; font-weight: bold;" class="{roi_7d_class}">{roi_7d:+.1f}%</div>
                <div style="font-size: 0.8rem; color: #6c757d;">近 7 天 ROI</div>
            </div>
            """, unsafe_allow_html=True)

        with metric_col2:
            roi_30d_class = "positive" if roi_30d >= 0 else "negative"
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 1.5rem; font-weight: bold;" class="{roi_30d_class}">{roi_30d:+.1f}%</div>
                <div style="font-size: 0.8rem; color: #6c757d;">近 30 天 ROI</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # 止损警告
    if roi_7d < STOP_LOSS_7DAY_ROI:
        st.markdown(f"""
        <div class="stop-loss-banner">
            <h2>🛑 止损警告: 策略检修中，建议暂停实战</h2>
            <p style="margin: 0.5rem 0;">近 7 天 ROI 为 {roi_7d:.1f}%，低于止损阈值 {STOP_LOSS_7DAY_ROI*100:.0f}%</p>
            <p style="margin: 0;">建议: 停止投注 → 分析原因 → 优化模型 → 验证后重启</p>
        </div>
        """, unsafe_allow_html=True)
    elif roi_30d < STOP_LOSS_30DAY_ROI:
        st.markdown(f"""
        <div class="stop-loss-banner">
            <h2>🚨 强制止损: 立即停止实战</h2>
            <p style="margin: 0.5rem 0;">近 30 天 ROI 为 {roi_30d:.1f}%，低于强制止损阈值 {STOP_LOSS_30DAY_ROI*100:.0f}%</p>
            <p style="margin: 0;">要求: 立即停止 → 深度复盘 → 重新训练 → 完整验证</p>
        </div>
        """, unsafe_allow_html=True)

    # 详细风险指标
    with st.expander("📋 详细风险指标说明", expanded=False):
        st.markdown("""
        **最大回撤 (Max Drawdown)**
        - 定义: 资金从历史最高点跌落的最大幅度
        - 公式: (峰值 - 谷值) / 峰值
        - 建议: 控制在 20% 以内

        **破产风险概率 (Risk of Ruin)**
        - 定义: 在给定初始资金和策略下，资金归零的概率
        - 公式: RoR = ((1 - edge) / (1 + edge)) ^ (bankroll / unit_stake)
        - 建议: 保持在 10% 以下

        **时间窗口 ROI**
        - 近 7 天: 短期表现，快速响应策略变化
        - 近 30 天: 中期表现，评估策略稳定性
        - 止损阈值: 7天 < -15%, 30天 < -25%
        """)


def display_model_drift_detection(ledger_df: pd.DataFrame):
    """显示模型漂移检测"""
    st.subheader("🔬 模型漂移检测")

    if ledger_df.empty:
        st.info("暂无数据可进行漂移检测")
        return

    drift_info = detect_model_drift(ledger_df)

    live_wr = drift_info["live_win_rate"]
    backtest_wr = drift_info["backtest_win_rate"]
    drift_mag = drift_info["drift_magnitude"]

    # 计算样本统计
    total_bets = drift_info["sample_size"]
    expected_wins = backtest_wr * total_bets
    actual_wins = live_wr * total_bets
    diff_wins = actual_wins - expected_wins

    # 确定警告级别
    if drift_info["significance"] == "critical":
        drift_class = "drift-critical"
        drift_emoji = "🚨"
        drift_text = "严重漂移"
    elif drift_info["significance"] == "significant":
        drift_class = "drift-warning"
        drift_emoji = "⚠️"
        drift_text = "显著漂移"
    else:
        drift_class = "risk-low"
        drift_emoji = "✅"
        drift_text = "模型稳定"

    # 漂移检测卡片
    st.markdown(f"""
    <div class="{drift_class}">
        <h3>{drift_emoji} {drift_text}</h3>
        <div style="display: flex; justify-content: space-around; margin: 1rem 0;">
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold;">{backtest_wr:.1%}</div>
                <div style="font-size: 0.8rem; color: #6c757d;">回测胜率</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">→</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold;">{live_wr:.1%}</div>
                <div style="font-size: 0.8rem; color: #6c757d;">实战胜率</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: bold;" class="{'positive' if drift_mag >= 0 else 'negative'}">{drift_mag:+.1%}</div>
                <div style="font-size: 0.8rem; color: #6c757d;">偏差幅度</div>
            </div>
        </div>
        <p style="margin: 0;"><strong>样本量:</strong> {total_bets} 注 |
        <strong>预期命中:</strong> {expected_wins:.0f} 注 |
        <strong>实际命中:</strong> {actual_wins:.0f} 注 ({diff_wins:+.0f} 差异)</p>
    </div>
    """, unsafe_allow_html=True)

    # 详细说明
    if abs(drift_mag) > DRIFT_WARNING_THRESHOLD:
        if drift_mag < 0:
            st.warning(f"""
            ⚠️ 模型表现低于回测基准 {abs(drift_mag):.1%}

            **可能原因**:
            1. 市场环境变化（球队实力、战术调整）
            2. 数据特征分布偏移
            3. 模型过拟合回测数据
            4. 运气不佳（短期波动）

            **建议操作**:
            1. 收集更多样本数据继续观察
            2. 检查最近比赛的特征分布
            3. 考虑降低投注金额
            4. 如偏差持续扩大，重新训练模型
            """)
        else:
            st.success(f"""
            ✅ 模型表现优于回测基准 {drift_mag:.1%}

            **可能原因**:
            1. 市场环境有利
            2. 运气较好（短期波动）
            3. 模型实际表现优于历史

            **注意**:
            - 保持警惕，不要过度自信
            - 继续监控长期表现
            - 避免突然增加投注金额
            """)


def display_system_status(ledger_df: pd.DataFrame) -> str:
    """
    显示系统状态指示灯

    Returns:
        状态等级: "green", "yellow", "red"
    """
    if ledger_df.empty:
        status = "yellow"
        status_text = "⏳ 等待数据"
        status_desc = "暂无投注数据"
    else:
        roi_7d = calculate_period_roi(ledger_df, 7)
        drift_info = detect_model_drift(ledger_df)

        # 判断状态
        if roi_7d < STOP_LOSS_7DAY_ROI or drift_info["significance"] == "critical":
            status = "red"
            status_text = "🔴 需要关注"
            status_desc = f"7天ROI {roi_7d:.1f}% 或存在严重漂移"
        elif roi_7d < 0 or drift_info["significance"] == "significant":
            status = "yellow"
            status_text = "⚠️ 需要警惕"
            status_desc = f"7天ROI {roi_7d:.1f}% 或存在显著漂移"
        else:
            status = "green"
            status_text = "✅ 运行正常"
            status_desc = f"7天ROI {roi_7d:.1f}%"

    # 显示状态栏
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 2rem;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center;">
                <span class="status-indicator status-{status}"></span>
                <span style="font-size: 1.2rem; font-weight: bold;">{status_text}</span>
            </div>
            <div style="color: #6c757d;">{status_desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    return status


def display_high_value_signals(predictions_df: pd.DataFrame):
    """显示高价值信号列表"""
    st.subheader("🔥 今日高价值信号")

    # 筛选未来的高价值比赛
    today = datetime.now().date()
    future_high_value = predictions_df[
        (predictions_df["is_high_value_bool"] == True) &
        (predictions_df["match_date_dt"].dt.date >= today)
    ].copy()

    if future_high_value.empty:
        st.info("📭 今日暂无高价值信号")
        return

    # 按日期分组
    future_high_value["date_only"] = future_high_value["match_date_dt"].dt.date
    grouped = future_high_value.groupby("date_only")

    for date, group in grouped:
        with st.expander(f"📅 {date} ({len(group)} 场)", expanded=True):
            for _, row in group.iterrows():
                # 预测图标
                pred_icon = {"Home": "🏠", "Draw": "🤝", "Away": "✈️"}.get(row["prediction"], "•")

                # 置信度颜色
                conf_color = "#28a745" if row["confidence_pct"] >= 0.65 else "#ffc107" if row["confidence_pct"] >= 0.60 else "#dc3545"

                # 时间
                match_time = row["match_date_dt"].strftime("%H:%M")

                # 联赛简称
                league_short = {"Premier League": "EPL", "La Liga": "LL", "Bundesliga": "BL",
                               "Serie A": "SA", "Ligue 1": "L1"}.get(row["league"], row["league"][:3])

                st.markdown(f"""
                <div style="padding: 12px; margin: 8px 0; background-color: #ffffff; border-radius: 8px; border: 1px solid #dee2e6; border-left: 4px solid {conf_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 0.85rem; color: #6c757d;">{league_short} | {match_time}</div>
                            <div style="font-size: 1.1rem; font-weight: bold; margin-top: 4px;">
                                {row["home_team"]} vs {row["away_team"]}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.3rem;">{pred_icon}</div>
                            <div style="font-size: 0.9rem; color: {conf_color}; font-weight: bold;">
                                {row["confidence"]}
                            </div>
                            <div style="font-size: 0.8rem; color: #6c757d;">
                                预期 ROI: {row["expected_roi"]}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def display_ledger_table(ledger_df: pd.DataFrame):
    """显示投注记录表格"""
    st.subheader("📋 详细投注记录")

    if ledger_df.empty:
        st.info("暂无投注记录")
        return

    # 准备显示数据
    display_df = ledger_df[[
        "match_date_dt", "league", "home_team", "away_team",
        "prediction", "actual_result", "confidence", "won", "profit"
    ]].copy()

    display_df["日期"] = display_df["match_date_dt"].dt.strftime("%m-%d %H:%M")
    display_df["对阵"] = display_df["home_team"] + " vs " + display_df["away_team"]
    display_df["预测"] = display_df["prediction"]
    display_df["实际"] = display_df["actual_result"]
    display_df["置信度"] = display_df["confidence"]
    display_df["结果"] = display_df["won"].apply(lambda x: "✅" if x else "❌")
    display_df["盈亏"] = display_df["profit"].apply(lambda x: f"{'🟢' if x >= 0 else '🔴'} {x:+.0f}")

    display_df = display_df[["日期", "league", "对阵", "预测", "实际", "置信度", "结果", "盈亏"]]
    display_df.columns = ["日期", "联赛", "对阵", "预测", "实际", "置信度", "结果", "盈亏"]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================================
# 主应用
# ============================================================================


def main():
    """主应用"""

    # 侧边栏
    with st.sidebar:
        st.image("https://via.placeholder.com/100x100/1f77b4/ffffff?text=⚽", width=100)
        st.title("⚽ FootballPrediction")
        st.markdown("---")

        # 数据刷新
        if st.button("🔄 刷新数据", use_container_width=True):
            st.cache_data.clear()
            st.success("数据已刷新！")
            st.rerun()

        st.markdown("---")

        # 过滤器
        st.subheader("🔍 数据筛选")

        # 日期范围
        min_date = datetime(2026, 1, 1).date()
        max_date = datetime.now().date()

        date_range = st.date_range(
            "选择日期范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        # 联赛筛选
        predictions_df = load_predictions()
        if not predictions_df.empty:
            available_leagues = predictions_df["league"].unique().tolist()
            selected_leagues = st.multiselect(
                "选择联赛",
                available_leagues,
                default=available_leagues,
            )

            # 最小置信度
            min_confidence = st.slider(
                "最小置信度",
                min_value=0.0,
                max_value=1.0,
                value=0.50,
                step=0.05,
                format="%.0f%%"
            )

        st.markdown("---")

        # 风控设置
        st.subheader("⚙️ 风控设置")

        show_advanced_risk = st.checkbox("显示高级风险指标", value=False)

        if show_advanced_risk:
            st.markdown("""
            <div style="padding: 10px; background-color: #f8f9fa; border-radius: 8px; font-size: 0.8rem;">
            <strong>止损阈值</strong><br>
            • 7天 ROI: < -15% → 暂停实战<br>
            • 30天 ROI: < -25% → 强制停止<br>
            <br>
            <strong>漂移阈值</strong><br>
            • 警告: 偏差 > 5%<br>
            • 严重: 偏差 > 10%<br>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #6c757d; font-size: 0.8rem;">
            <b>V26.8 Production</b><br>
            联赛专项模型 + V30.0 赔率特征<br>
            <br>
            © 2026 FootballPrediction
        </div>
        """, unsafe_allow_html=True)

    # 主标题
    st.markdown('<div class="main-header">⚽ 2026 实战预测面板</div>', unsafe_allow_html=True)

    # 加载数据
    with st.spinner("加载数据中..."):
        predictions_df = load_predictions()
        results_df = load_match_results()
        ledger_df = calculate_ledger(predictions_df, results_df)

    # 应用过滤器
    if not predictions_df.empty and "selected_leagues" in locals():
        filtered_predictions = predictions_df[
            predictions_df["league"].isin(selected_leagues) &
            (predictions_df["confidence_pct"] >= min_confidence)
        ]
        filtered_ledger = ledger_df[
            ledger_df["match_date_dt"].dt.date.between(date_range[0], date_range[1])
        ] if not ledger_df.empty else pd.DataFrame()
    else:
        filtered_predictions = predictions_df
        filtered_ledger = ledger_df

    # 系统状态指示灯
    system_status = display_system_status(filtered_ledger)

    # 红灯状态时显示警告横幅
    if system_status == "red" and not filtered_ledger.empty:
        roi_7d = calculate_period_roi(filtered_ledger, 7)
        st.markdown(f"""
        <div style="background-color: #dc3545; color: white; padding: 1rem; border-radius: 8px; text-align: center; margin-bottom: 1.5rem;">
            <strong style="font-size: 1.1rem;">🛑 策略检修中，建议暂停实战</strong>
            <br>
            <span style="font-size: 0.9rem;">当前7天ROI为 {roi_7d:.1f}%，请分析原因后再继续</span>
        </div>
        """, unsafe_allow_html=True)

    # 顶部指标卡片
    st.markdown("---")

    if not filtered_ledger.empty:
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            total_bets = len(filtered_ledger)
            st.metric("投注数", f"{total_bets}")

        with col2:
            total_wins = filtered_ledger["won"].sum()
            win_rate = total_wins / total_bets if total_bets > 0 else 0
            st.metric("命中率", f"{win_rate:.1%}")

        with col3:
            total_pnl = filtered_ledger["profit"].sum()
            st.metric("净盈亏", f"{total_pnl:+.0f} 点")

        with col4:
            roi = (total_pnl / (total_bets * 10) * 100) if total_bets > 0 else 0
            delta_color = "normal" if roi >= 0 else "inverse"
            st.metric("ROI", f"{roi:+.1f}%", delta_color=delta_color)

        with col5:
            avg_confidence = filtered_ledger["confidence_pct"].mean()
            st.metric("平均置信度", f"{avg_confidence:.1%}")

    # 主要图表 - 新增风险评估标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 ROI 曲线",
        "🎯 胜率分布",
        "⚠️ 风险评估",
        "🔬 模型漂移",
        "🔥 今日信号"
    ])

    with tab1:
        plot_roi_curve(filtered_ledger)

    with tab2:
        plot_win_rate_distribution(filtered_ledger)

    with tab3:
        display_risk_assessment(filtered_ledger)

    with tab4:
        display_model_drift_detection(filtered_ledger)

    with tab5:
        display_high_value_signals(filtered_predictions)

    # 底部：详细投注记录
    st.markdown("---")
    display_ledger_table(filtered_ledger)


if __name__ == "__main__":
    main()
