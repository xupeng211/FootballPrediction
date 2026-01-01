#!/usr/bin/env python3
"""
V51.4 严苛盲测引擎 - 彻底验证模型真实盈利能力
====================================================

审计标准:
1. 硬数据分割: 2021-2023 训练，2024 完全盲测
2. 特征脱水: 移除 home_advantage 和 venue_bias
3. 滑点惩罚: 赔率下调 3%
4. 真实验证: 拒绝过拟合幻象

Author: Quant Risk Controller
Version: V51.4-Rigorous
Date: 2025-12-31
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# 配置日志
# ============================================================================

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "v51_4_rigorous_backtest.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# V51.4 特征列表（脱水版）
# ============================================================================

# V51.4 特征列表：移除 home_advantage 和 venue_bias
V51_4_FEATURES = [
    # 实力底蕴 (16 维)
    "home_rolling_xg", "home_rolling_xg_std",
    "home_rolling_shots_on_target", "home_rolling_shots_on_target_std",
    "home_rolling_possession", "home_rolling_possession_std",
    "home_rolling_team_rating", "home_rolling_team_rating_std",
    "away_rolling_xg", "away_rolling_xg_std",
    "away_rolling_shots_on_target", "away_rolling_shots_on_target_std",
    "away_rolling_possession", "away_rolling_possession_std",
    "away_rolling_team_rating", "away_rolling_team_rating_std",
    "rolling_xg_diff", "rolling_possession_diff",

    # 即时状态 (10 维)
    "home_recent_form_points", "home_recent_goals_scored",
    "home_recent_goals_conceded", "home_recent_win_rate",
    "away_recent_form_points", "away_recent_goals_scored",
    "away_recent_goals_conceded", "away_recent_win_rate",
    "recent_form_diff", "momentum_gap",

    # 主客场特征 (14 维 - 移除 home_advantage, venue_bias)
    "home_home_win_rate", "home_home_goals_scored",
    "home_home_goals_conceded", "home_home_clean_sheets",
    "home_away_win_rate", "home_away_goals_scored",
    "home_away_goals_conceded", "home_away_clean_sheets",
    "away_home_win_rate", "away_home_goals_scored",
    "away_home_goals_conceded", "away_home_clean_sheets",
    "away_away_win_rate", "away_away_goals_scored",
    "away_away_goals_conceded", "away_away_clean_sheets",
    # home_advantage - REMOVED
    # venue_bias - REMOVED

    # 疲劳度 (10 维)
    "home_fatigue_index", "away_fatigue_index", "fatigue_diff",
    "home_rest_days", "away_rest_days", "rest_days_diff",
    "home_matches_7days", "away_matches_7days",
    "home_matches_30days", "away_matches_30days",

    # 趋势 (6 维)
    "home_recent_trend_encoded", "away_recent_trend_encoded",
]

logger.info(f"V51.4 特征维度: {len(V51_4_FEATURES)} (已移除 home_advantage, venue_bias)")


# ============================================================================
# 特征计算器 (复用 V51.3 的逻辑)
# ============================================================================

def calculate_features_for_match(
    match_id: str,
    match_date: datetime,
    home_team: str,
    away_team: str,
    conn=None,
) -> dict:
    """
    计算单场比赛的特征（复用 V51.3 逻辑）
    """
    from scripts.ml.train_v51_3_full_power import V53FeatureCalculator

    calculator = V53FeatureCalculator()
    all_features = calculator.compute_full_features(
        match_id, match_date, home_team, away_team, conn
    )

    # 只返回 V51.4 需要的特征
    return {f: all_features.get(f, 0) for f in V51_4_FEATURES}


# ============================================================================
# V51.4 盲测引擎
# ============================================================================

@dataclass
class BlindTestResult:
    """盲测结果"""
    period: str
    total_matches: int
    avg_confidence: float
    high_conf_matches: int

    # 策略结果
    flat_roi: float = 0.0
    flat_win_rate: float = 0.0
    flat_max_drawdown: float = 0.0

    high_conf_roi: float = 0.0
    high_conf_win_rate: float = 0.0
    high_conf_max_drawdown: float = 0.0

    value_roi: float = 0.0
    value_win_rate: float = 0.0
    value_max_drawdown: float = 0.0


class V51RigorousBacktestEngine:
    """V51.4 严苛盲测引擎"""

    # XGBoost 标准标签映射
    LABEL_MAPPING = {"A": 0, "D": 1, "H": 2}
    REVERSE_MAPPING = {0: "A", 1: "D", 2: "H"}

    # XGBoost 参数
    XGB_PARAMS = {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "min_child_weight": 3,
        "gamma": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, initial_capital: float = 500000.0):
        self.initial_capital = initial_capital
        self.settings = get_settings()
        self.model = None
        self.feature_importance = {}

    def get_connection(self):
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    def extract_training_data(self, train_end_date: str = "2025-01-01"):
        """
        提取训练数据 (2020-2024，排除2025盲测数据)
        """
        logger.info("=" * 73)
        logger.info("步骤 1: 提取训练数据 (2020-2024)")
        logger.info("=" * 73)

        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        m.match_id,
                        m.match_date,
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score
                    FROM matches m
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date < %s
                      AND m.match_date >= '2020-01-01'
                    ORDER BY m.match_date ASC
                """, (train_end_date,))

                rows = cur.fetchall()
                df = pd.DataFrame([dict(row) for row in rows])
                logger.info(f"提取训练数据: {len(df)} 场比赛 (2020-2024)")
                return df

        finally:
            conn.close()

    def extract_blind_test_data(self, test_start: str = "2025-01-01", test_end: str = "2026-01-01"):
        """
        提取盲测数据 (2025 - 唯一有赔率的年份)
        """
        logger.info("=" * 73)
        logger.info("步骤 2: 提取盲测数据 (2025)")
        logger.info("=" * 73)

        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        m.match_id,
                        m.home_team,
                        m.away_team,
                        m.match_date,
                        m.home_score,
                        m.away_score,
                        pf.closing_home_odds,
                        pf.closing_draw_odds,
                        pf.closing_away_odds
                    FROM matches m
                    LEFT JOIN prematch_features pf ON m.match_id = pf.match_id
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date >= %s
                      AND m.match_date < %s
                      AND pf.closing_home_odds IS NOT NULL
                      AND pf.closing_away_odds IS NOT NULL
                    ORDER BY m.match_date ASC
                """, (test_start, test_end))

                rows = cur.fetchall()
                df = pd.DataFrame([dict(row) for row in rows])
                logger.info(f"提取盲测数据: {len(df)} 场 2025 年比赛")
                return df

        finally:
            conn.close()

    def compute_features_for_dataset(self, df: pd.DataFrame, desc: str = "特征计算"):
        """
        为数据集计算特征
        """
        logger.info(f"计算 {desc}...")

        conn = self.get_connection()
        try:
            features_list = []

            for idx, row in df.iterrows():
                if (idx + 1) % 50 == 0:
                    logger.info(f"  已处理 {idx + 1}/{len(df)} 场")

                try:
                    features = calculate_features_for_match(
                        row["match_id"],
                        pd.to_datetime(row["match_date"]),
                        row["home_team"],
                        row["away_team"],
                        conn=conn,
                    )
                    features["match_id"] = row["match_id"]
                    features_list.append(features)
                except Exception as e:
                    logger.warning(f"特征计算失败 {row['match_id']}: {e}")
                    # 填充零特征
                    zero_features = {f: 0.0 for f in V51_4_FEATURES}
                    zero_features["match_id"] = row["match_id"]
                    features_list.append(zero_features)

            feature_df = pd.DataFrame(features_list)
            feature_df = feature_df.fillna(0)

            # 确保所有特征存在
            for feat in V51_4_FEATURES:
                if feat not in feature_df.columns:
                    feature_df[feat] = 0.0

            feature_df = feature_df[["match_id"] + V51_4_FEATURES]
            logger.info(f"{desc}完成: {feature_df.shape}")
            return feature_df

        finally:
            conn.close()

    def train_model(self, train_df: pd.DataFrame, feature_df: pd.DataFrame):
        """
        训练 V51.4 模型
        """
        logger.info("=" * 73)
        logger.info("步骤 3: 训练 V51.4 模型（脱水版 56 维特征）")
        logger.info("=" * 73)

        # 合并数据
        merged = train_df.merge(feature_df, on="match_id")

        # 构造标签
        merged["result"] = merged.apply(
            lambda row: (
                "H" if row["home_score"] > row["away_score"]
                else "D" if row["home_score"] == row["away_score"]
                else "A"
            ),
            axis=1
        )

        # 准备训练数据
        X = merged[V51_4_FEATURES].values
        y = merged["result"].map(self.LABEL_MAPPING).values

        logger.info(f"训练集形状: X={X.shape}, y={y.shape}")

        # 训练模型
        model = xgb.XGBClassifier(**self.XGB_PARAMS)
        model.fit(X, y)

        # 训练集准确率
        train_pred = model.predict(X)
        train_acc = accuracy_score(y, train_pred)
        logger.info(f"训练集准确率: {train_acc:.4f}")

        # 保存特征重要性
        self.feature_importance = dict(zip(V51_4_FEATURES, model.feature_importances_))

        self.model = model
        return model

    def apply_slippage_penalty(self, odds: float) -> float:
        """
        应用滑点惩罚 (3%)
        Adjusted_Odds = 1 + (Original_Odds - 1) × 0.97
        """
        return 1 + (odds - 1) * 0.97

    def run_blind_test_strategies(self, test_df: pd.DataFrame, feature_df: pd.DataFrame) -> BlindTestResult:
        """
        执行盲测策略回测
        """
        logger.info("=" * 73)
        logger.info("步骤 4: 执行 2024 年盲测（含 3% 滑点惩罚）")
        logger.info("=" * 73)

        # 合并数据
        merged = test_df.merge(feature_df, on="match_id")

        # 计算 actual_result
        merged["actual_result"] = merged.apply(
            lambda row: (
                "H" if row["home_score"] > row["away_score"]
                else "D" if row["home_score"] == row["away_score"]
                else "A"
            ),
            axis=1
        )

        # 应用滑点惩罚
        merged["adj_home_odds"] = merged["closing_home_odds"].apply(self.apply_slippage_penalty)
        merged["adj_draw_odds"] = merged["closing_draw_odds"].apply(self.apply_slippage_penalty)
        merged["adj_away_odds"] = merged["closing_away_odds"].apply(self.apply_slippage_penalty)

        logger.info(f"盲测数据集: {len(merged)} 场比赛")

        # 初始化策略统计
        flat_stats = {"bets": 0, "wins": 0, "profit": 0, "capital_series": [self.initial_capital]}
        high_conf_stats = {"bets": 0, "wins": 0, "profit": 0, "capital_series": [self.initial_capital]}
        value_stats = {"bets": 0, "wins": 0, "profit": 0, "capital_series": [self.initial_capital]}

        predictions = []

        for idx, row in merged.iterrows():
            # 提取特征
            features = [row.get(f, 0) for f in V51_4_FEATURES]
            X = np.array(features).reshape(1, -1)

            # 模型预测
            proba = self.model.predict_proba(X)[0]  # [A, D, H]
            prob_away, prob_draw, prob_home = proba[0], proba[1], proba[2]

            predicted_idx = np.argmax(proba)
            predicted = self.REVERSE_MAPPING[predicted_idx]
            confidence = float(proba[predicted_idx])

            predictions.append({
                "prob_away": prob_away,
                "prob_draw": prob_draw,
                "prob_home": prob_home,
                "predicted": predicted,
                "confidence": confidence,
            })

            actual = row["actual_result"]
            bet_amount = 1000

            # 策略 A: 平注
            flat_stats["bets"] += 1
            if predicted == actual:
                flat_stats["wins"] += 1
                if actual == "H":
                    profit = bet_amount * (row["adj_home_odds"] - 1)
                elif actual == "D":
                    profit = bet_amount * (row["adj_draw_odds"] - 1)
                else:
                    profit = bet_amount * (row["adj_away_odds"] - 1)
                flat_stats["profit"] += profit
            else:
                flat_stats["profit"] -= bet_amount

            flat_stats["capital_series"].append(flat_stats["capital_series"][-1] + (profit if predicted == actual else -bet_amount))

            # 策略 B: 高置信度 (>55%)
            if confidence > 0.55:
                high_conf_stats["bets"] += 1
                if predicted == actual:
                    high_conf_stats["wins"] += 1
                    if actual == "H":
                        profit = bet_amount * (row["adj_home_odds"] - 1)
                    elif actual == "D":
                        profit = bet_amount * (row["adj_draw_odds"] - 1)
                    else:
                        profit = bet_amount * (row["adj_away_odds"] - 1)
                    high_conf_stats["profit"] += profit
                else:
                    high_conf_stats["profit"] -= bet_amount

                high_conf_stats["capital_series"].append(high_conf_stats["capital_series"][-1] + (profit if predicted == actual else -bet_amount))

            # 策略 C: 价值导向 (EV > 5%)
            ev_home = (prob_home * row["adj_home_odds"]) - 1
            ev_draw = (prob_draw * row["adj_draw_odds"]) - 1
            ev_away = (prob_away * row["adj_away_odds"]) - 1

            max_ev = max(ev_home, ev_draw, ev_away)

            if max_ev > 0.05:
                if max_ev == ev_home:
                    value_bet = "H"
                elif max_ev == ev_draw:
                    value_bet = "D"
                else:
                    value_bet = "A"

                value_stats["bets"] += 1
                if value_bet == actual:
                    value_stats["wins"] += 1
                    if actual == "H":
                        profit = bet_amount * (row["adj_home_odds"] - 1)
                    elif actual == "D":
                        profit = bet_amount * (row["adj_draw_odds"] - 1)
                    else:
                        profit = bet_amount * (row["adj_away_odds"] - 1)
                    value_stats["profit"] += profit
                else:
                    value_stats["profit"] -= bet_amount

                value_stats["capital_series"].append(value_stats["capital_series"][-1] + (profit if value_bet == actual else -bet_amount))

        # 计算指标
        def calc_stats(stats, initial_capital):
            if stats["bets"] == 0:
                return 0, 0, 0
            roi = (stats["profit"] / (stats["bets"] * bet_amount)) * 100
            win_rate = (stats["wins"] / stats["bets"]) * 100

            # 计算最大回撤
            capital_series = np.array(stats["capital_series"])
            running_max = np.maximum.accumulate(capital_series)
            drawdowns = (capital_series - running_max) / running_max * 100
            max_dd = float(np.min(drawdowns))

            return roi, win_rate, max_dd

        flat_roi, flat_win_rate, flat_dd = calc_stats(flat_stats, self.initial_capital)
        high_conf_roi, high_conf_win_rate, high_conf_dd = calc_stats(high_conf_stats, self.initial_capital)
        value_roi, value_win_rate, value_dd = calc_stats(value_stats, self.initial_capital)

        # 整体指标
        avg_conf = np.mean([p["confidence"] for p in predictions])
        high_conf_count = sum(1 for p in predictions if p["confidence"] > 0.55)

        result = BlindTestResult(
            period="2024 (Blind Test)",
            total_matches=len(merged),
            avg_confidence=avg_conf,
            high_conf_matches=high_conf_count,
            flat_roi=flat_roi,
            flat_win_rate=flat_win_rate,
            flat_max_drawdown=flat_dd,
            high_conf_roi=high_conf_roi,
            high_conf_win_rate=high_conf_win_rate,
            high_conf_max_drawdown=high_conf_dd,
            value_roi=value_roi,
            value_win_rate=value_win_rate,
            value_max_drawdown=value_dd,
        )

        return result

    def print_report(self, train_result: BlindTestResult, blind_result: BlindTestResult):
        """打印盲测报告"""
        print("\n" + "=" * 73)
        print("V51.4 严苛盲测审计报告")
        print("=" * 73)

        print("\n【盲测配置】")
        print(f"  训练期间: 2020-01-01 至 2024-12-31")
        print(f"  盲测期间: 2025-01-01 至 2025-12-31")
        print(f"  特征维度: {len(V51_4_FEATURES)} (已移除 home_advantage, venue_bias)")
        print(f"  滑点惩罚: 3%")

        print("\n" + "-" * 73)
        print("策略 A: Flat Betting (平注)")
        print("-" * 73)
        print(f"  盲测样本: {blind_result.total_matches} 场")
        print(f"  胜率: {blind_result.flat_win_rate:.2f}%")
        print(f"  ROI: {blind_result.flat_roi:.2f}%")
        print(f"  最大回撤: {blind_result.flat_max_drawdown:.2f}%")

        print("\n" + "-" * 73)
        print("策略 B: High Confidence (高置信度 >55%)")
        print("-" * 73)
        print(f"  投注场数: {blind_result.high_conf_matches} 场 ({blind_result.high_conf_matches/blind_result.total_matches*100:.1f}%)")
        print(f"  胜率: {blind_result.high_conf_win_rate:.2f}%")
        print(f"  ROI: {blind_result.high_conf_roi:.2f}%")
        print(f"  最大回撤: {blind_result.high_conf_max_drawdown:.2f}%")

        print("\n" + "-" * 73)
        print("策略 C: Value-Oriented (价值导向 EV>5%)")
        print("-" * 73)
        print(f"  盲测 ROI: {blind_result.value_roi:.2f}%")
        print(f"  盲测胜率: {blind_result.value_win_rate:.2f}%")
        print(f"  最大回撤: {blind_result.value_max_drawdown:.2f}%")

        # 特征重要性 Top 15
        print("\n" + "-" * 73)
        print("V51.4 特征重要性 Top 15 (脱水版)")
        print("-" * 73)
        top_features = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:15]
        for i, (feat, imp) in enumerate(top_features, 1):
            print(f"  {i:2d}. {feat:<45} {imp:.4f}")

        # 最终判断
        print("\n" + "=" * 73)
        print("【最终判断】")
        print("=" * 73)

        value_roi = blind_result.value_roi

        if 5 <= value_roi <= 15:
            print("\n  ✅ 模型具备真实泛化能力")
            print(f"     2024 年盲测 ROI: {value_roi:.2f}% 处于合理区间 (5%-15%)")
            print("     建议: 可进入小规模实盘测试")
        elif 0 < value_roi < 5:
            print(f"\n  ⚠️  模型盈利能力微弱")
            print(f"     2024 年盲测 ROI: {value_roi:.2f}% 低于预期")
            print("     建议: 继续优化特征工程")
        elif value_roi <= 0:
            print(f"\n  ❌ V51.3 为过拟合产物")
            print(f"     2024 年盲测 ROI: {value_roi:.2f}% 为负")
            print("     结论: 35% ROI 是训练集记忆效应，不具备实战价值")
        else:  # value_roi > 15
            print(f"\n  ⚠️  盲测 ROI 依然异常高 ({value_roi:.2f}%)")
            print("     可能原因: 1) 数据仍存在泄露 2) 2024数据分布偏差 3) 运气成分")
            print("     建议: 进行更严格的外样本验证（如其他联赛）")

        # 与 V51.3 对比
        print("\n" + "=" * 73)
        print("【V51.3 vs V51.4 对比】")
        print("=" * 73)
        print(f"  V51.3 (2025内测): ROI = 35.95%")
        print(f"  V51.4 (2024盲测): ROI = {blind_result.value_roi:.2f}%")
        print(f"  挤水幅度: {35.95 - blind_result.value_roi:.2f}% 百分点")

        if blind_result.value_roi < 35.95 * 0.3:
            print(f"\n  ⚠️  盲测 ROI 不足 V51.3 的 30%，证实存在严重过拟合")

    def save_report(self, blind_result: BlindTestResult):
        """保存盲测报告"""
        output_path = Path("docs/v51_4_rigorous_blind_test_report.json")

        # 获取 Top 15 特征
        top_features = dict(sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:15])

        report_dict = {
            "report_type": "V51.4_Rigorous_Blind_Test_Audit_Report",
            "report_time": datetime.now().isoformat(),
            "test_config": {
                "train_period": "2020-01-01 to 2024-12-31",
                "blind_test_period": "2025-01-01 to 2025-12-31",
                "n_features": len(V51_4_FEATURES),
                "removed_features": ["home_advantage", "venue_bias"],
                "slippage_penalty": "3%",
            },
            "blind_test_result": {
                "period": blind_result.period,
                "total_matches": blind_result.total_matches,
                "avg_confidence": float(blind_result.avg_confidence),
                "high_confidence_matches": blind_result.high_conf_matches,
                "flat_betting": {
                    "roi_pct": float(blind_result.flat_roi),
                    "win_rate_pct": float(blind_result.flat_win_rate),
                    "max_drawdown_pct": float(blind_result.flat_max_drawdown),
                },
                "high_confidence": {
                    "roi_pct": float(blind_result.high_conf_roi),
                    "win_rate_pct": float(blind_result.high_conf_win_rate),
                    "max_drawdown_pct": float(blind_result.high_conf_max_drawdown),
                },
                "value_oriented": {
                    "roi_pct": float(blind_result.value_roi),
                    "win_rate_pct": float(blind_result.value_win_rate),
                    "max_drawdown_pct": float(blind_result.value_max_drawdown),
                },
            },
            "feature_importance_top15": {k: float(v) for k, v in top_features.items()},
            "conclusion": {
                "has_real_generalization": 5 <= blind_result.value_roi <= 15,
                "is_overfitting": blind_result.value_roi <= 0,
                "v51_3_was_hallucination": blind_result.value_roi < 35.95 * 0.3,
            },
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"报告已保存: {output_path}")

    def run(self):
        """执行完整盲测流程"""
        # 1. 提取训练数据
        train_df = self.extract_training_data()

        # 2. 计算训练特征
        train_features = self.compute_features_for_dataset(train_df, "训练特征")

        # 3. 训练模型
        self.train_model(train_df, train_features)

        # 4. 提取盲测数据
        blind_df = self.extract_blind_test_data()

        if blind_df.empty:
            logger.error("没有找到 2024 年的盲测数据！")
            return None

        # 5. 计算盲测特征
        blind_features = self.compute_features_for_dataset(blind_df, "盲测特征")

        # 6. 执行盲测
        blind_result = self.run_blind_test_strategies(blind_df, blind_features)

        # 7. 打印报告
        self.print_report(None, blind_result)

        # 8. 保存报告
        self.save_report(blind_result)

        return blind_result


def main():
    """主函数"""
    engine = V51RigorousBacktestEngine(initial_capital=500000.0)
    result = engine.run()
    return result


if __name__ == "__main__":
    main()
