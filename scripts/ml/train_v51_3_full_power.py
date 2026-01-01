#!/usr/bin/env python3
"""
V51.3 Full Power Model Trainer
==============================

V51.3 升级内容:
1. 补全 58 维特征计算 (修复 clean_sheets, matches_30days, venue_bias)
2. 修正标签映射为 XGBoost 标准: {'A': 0, 'D': 1, 'H': 2}
3. 严格时序划分训练集/测试集
4. 完整特征重要性排名

Author: Chief ML Architect
Version: V51.3
Date: 2025-12-31
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder, StandardScaler

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
        logging.FileHandler(LOG_DIR / "v51_3_training.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# V51.3 Enhanced Feature Calculator
# ============================================================================

class V53FeatureCalculator:
    """
    V51.3 增强特征计算器 - 补全所有 58 个特征
    """

    # V51.3 完整特征列表 (58 维)
    ALL_FEATURES = [
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

        # 主客场特征 (16 维)
        "home_home_win_rate", "home_home_goals_scored",
        "home_home_goals_conceded", "home_home_clean_sheets",  # V51.3: 补全
        "home_away_win_rate", "home_away_goals_scored",
        "home_away_goals_conceded", "home_away_clean_sheets",  # V51.3: 补全
        "away_home_win_rate", "away_home_goals_scored",
        "away_home_goals_conceded", "away_home_clean_sheets",  # V51.3: 补全
        "away_away_win_rate", "away_away_goals_scored",
        "away_away_goals_conceded", "away_away_clean_sheets",  # V51.3: 补全
        "home_advantage", "venue_bias",  # V51.3: 补全 venue_bias

        # 疲劳度 (10 维)
        "home_fatigue_index", "away_fatigue_index", "fatigue_diff",
        "home_rest_days", "away_rest_days", "rest_days_diff",
        "home_matches_7days", "away_matches_7days",
        "home_matches_30days", "away_matches_30days",  # V51.3: 补全

        # 趋势 (6 维 - 编码后)
        "home_recent_trend_encoded", "away_recent_trend_encoded",
    ]

    def __init__(self):
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def get_team_history(
        self,
        team_name: str,
        before_match_time: datetime,
        venue: str | None = None,
        limit: int = 30,
        conn=None,
    ) -> pd.DataFrame:
        """获取球队历史比赛"""
        should_close = conn is None
        if conn is None:
            conn = self.get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        m.match_id,
                        m.match_date,
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score,
                        m.status
                    FROM matches m
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date < %s
                """

                params = [before_match_time]

                if venue == "home":
                    query += " AND m.home_team = %s"
                    params.append(team_name)
                elif venue == "away":
                    query += " AND m.away_team = %s"
                    params.append(team_name)
                else:
                    query += " AND (m.home_team = %s OR m.away_team = %s)"
                    params.extend([team_name, team_name])

                query += " ORDER BY m.match_date DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, params)
                rows = cur.fetchall()

                if not rows:
                    return pd.DataFrame()

                df = pd.DataFrame([dict(row) for row in rows])
                df["is_home"] = df["home_team"] == team_name

                # 计算比分
                df["team_score"] = df.apply(
                    lambda row: row["home_score"] if row["is_home"] else row["away_score"],
                    axis=1,
                )
                df["opponent_score"] = df.apply(
                    lambda row: row["away_score"] if row["is_home"] else row["home_score"],
                    axis=1,
                )

                # 计算积分
                df["points"] = df.apply(
                    lambda row: (
                        3 if row["team_score"] > row["opponent_score"]
                        else 1 if row["team_score"] == row["opponent_score"]
                        else 0
                    ),
                    axis=1,
                )

                # 计算零封 (clean sheets)
                df["clean_sheet"] = df["opponent_score"] == 0

                return df

        finally:
            if should_close:
                conn.close()

    def extract_stats_from_raw(self, match_id: str, is_home: bool, conn=None) -> dict:
        """从 raw_match_data 提取统计指标"""
        should_close = conn is None
        if conn is None:
            conn = self.get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT raw_data FROM raw_match_data WHERE match_id = %s
                """, (match_id,))
                row = cur.fetchone()

                if not row or not row["raw_data"]:
                    return {}

                raw_data = row["raw_data"]
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)

                stats_data = raw_data.get("stats", {})
                if not stats_data:
                    return {}

                idx = 0 if is_home else 1
                stats = {}

                # 提取各项统计
                for metric in ["xg", "shots_on_target", "possession", "team_rating"]:
                    if metric in stats_data:
                        arr = stats_data[metric]
                        if isinstance(arr, list) and len(arr) > idx:
                            try:
                                stats[metric] = float(arr[idx])
                            except (ValueError, TypeError):
                                pass

                return stats

        finally:
            if should_close:
                conn.close()

    def calculate_clean_sheets(self, history_df: pd.DataFrame) -> float:
        """计算零封率"""
        if history_df.empty:
            return 0.0
        return float(history_df["clean_sheet"].sum() / len(history_df))

    def calculate_matches_in_period(
        self, history_df: pd.DataFrame, before_match_time: datetime, days: int
    ) -> int:
        """计算指定天数内的比赛数"""
        if history_df.empty:
            return 0

        cutoff_date = before_match_time - timedelta(days=days)
        match_dates = pd.to_datetime(history_df["match_date"])
        return int((match_dates >= cutoff_date).sum())

    def compute_full_features(
        self,
        match_id: str,
        match_date: datetime,
        home_team: str,
        away_team: str,
        conn=None,
    ) -> dict:
        """
        计算完整的 58 维特征
        """
        features = {}

        # 主队历史
        home_history_all = self.get_team_history(home_team, match_date, conn=conn)
        home_history_home = self.get_team_history(home_team, match_date, venue="home", conn=conn)
        home_history_away = self.get_team_history(home_team, match_date, venue="away", conn=conn)

        # 客队历史
        away_history_all = self.get_team_history(away_team, match_date, conn=conn)
        away_history_home = self.get_team_history(away_team, match_date, venue="home", conn=conn)
        away_history_away = self.get_team_history(away_team, match_date, venue="away", conn=conn)

        # 实力特征 (滚动统计)
        for prefix, history in [("home", home_history_all), ("away", away_history_all)]:
            # 从 raw_data 提取统计
            stats_list = []
            for _, row in history.head(10).iterrows():
                stats = self.extract_stats_from_raw(row["match_id"], prefix == "home", conn)
                stats_list.append(stats)

            stats_df = pd.DataFrame(stats_list)

            for metric in ["xg", "shots_on_target", "possession"]:
                if metric in stats_df.columns:
                    values = stats_df[metric].dropna()
                    if len(values) > 0:
                        features[f"{prefix}_rolling_{metric}"] = float(values.mean())
                        features[f"{prefix}_rolling_{metric}_std"] = float(values.std()) if len(values) > 1 else 0.0
                    else:
                        features[f"{prefix}_rolling_{metric}"] = 0.0
                        features[f"{prefix}_rolling_{metric}_std"] = 0.0
                else:
                    features[f"{prefix}_rolling_{metric}"] = 0.0
                    features[f"{prefix}_rolling_{metric}_std"] = 0.0

            # team_rating 特殊处理（可能不存在）
            if "team_rating" in stats_df.columns:
                values = stats_df["team_rating"].dropna()
                if len(values) > 0:
                    features[f"{prefix}_rolling_team_rating"] = float(values.mean())
                    features[f"{prefix}_rolling_team_rating_std"] = float(values.std()) if len(values) > 1 else 0.0
                else:
                    features[f"{prefix}_rolling_team_rating"] = 0.0
                    features[f"{prefix}_rolling_team_rating_std"] = 0.0
            else:
                # 如果 raw_data 中没有 team_rating，使用替代指标
                features[f"{prefix}_rolling_team_rating"] = float(history["points"].head(10).mean()) * 10
                features[f"{prefix}_rolling_team_rating_std"] = float(history["points"].head(10).std()) * 10

        # 差值特征
        features["rolling_xg_diff"] = features.get("home_rolling_xg", 0) - features.get("away_rolling_xg", 0)
        features["rolling_possession_diff"] = features.get("home_rolling_possession", 0) - features.get("away_rolling_possession", 0)

        # 即时状态特征
        for prefix, history in [("home", home_history_all), ("away", away_history_all)]:
            recent = history.head(3)
            features[f"{prefix}_recent_form_points"] = float(recent["points"].sum())
            features[f"{prefix}_recent_goals_scored"] = float(recent["team_score"].sum())
            features[f"{prefix}_recent_goals_conceded"] = float(recent["opponent_score"].sum())
            features[f"{prefix}_recent_win_rate"] = float((recent["points"] == 3).sum() / len(recent)) if len(recent) > 0 else 0.0

            # 趋势
            if len(recent) >= 2:
                recent_points = recent["points"].tolist()
                if recent_points[0] > recent_points[-1]:
                    trend = 2  # ascending
                elif recent_points[0] < recent_points[-1]:
                    trend = 0  # descending
                else:
                    trend = 1  # stable
            else:
                trend = 1  # stable
            features[f"{prefix}_recent_trend_encoded"] = float(trend)

        features["recent_form_diff"] = features.get("home_recent_form_points", 0) - features.get("away_recent_form_points", 0)
        features["momentum_gap"] = features.get("home_recent_win_rate", 0) - features.get("away_recent_win_rate", 0)

        # 主客场特征（包括 clean_sheets）
        for prefix, home_hist, away_hist in [
            ("home", home_history_home, home_history_away),
            ("away", away_history_home, away_history_away),
        ]:
            # 主场数据
            if not home_hist.empty:
                features[f"{prefix}_home_win_rate"] = float((home_hist["points"] == 3).sum() / len(home_hist))
                features[f"{prefix}_home_goals_scored"] = float(home_hist["team_score"].mean())
                features[f"{prefix}_home_goals_conceded"] = float(home_hist["opponent_score"].mean())
                features[f"{prefix}_home_clean_sheets"] = self.calculate_clean_sheets(home_hist)
            else:
                features[f"{prefix}_home_win_rate"] = 0.0
                features[f"{prefix}_home_goals_scored"] = 0.0
                features[f"{prefix}_home_goals_conceded"] = 0.0
                features[f"{prefix}_home_clean_sheets"] = 0.0

            # 客场数据
            if not away_hist.empty:
                features[f"{prefix}_away_win_rate"] = float((away_hist["points"] == 3).sum() / len(away_hist))
                features[f"{prefix}_away_goals_scored"] = float(away_hist["team_score"].mean())
                features[f"{prefix}_away_goals_conceded"] = float(away_hist["opponent_score"].mean())
                features[f"{prefix}_away_clean_sheets"] = self.calculate_clean_sheets(away_hist)
            else:
                features[f"{prefix}_away_win_rate"] = 0.0
                features[f"{prefix}_away_goals_scored"] = 0.0
                features[f"{prefix}_away_goals_conceded"] = 0.0
                features[f"{prefix}_away_clean_sheets"] = 0.0

        # home_advantage 和 venue_bias
        if not home_history_home.empty and not away_history_away.empty:
            home_team_home_advantage = float((home_history_home["points"] == 3).sum() / len(home_history_home))
            away_team_away_disadvantage = float((away_history_away["points"] == 3).sum() / len(away_history_away))
            features["home_advantage"] = home_team_home_advantage - away_team_away_disadvantage

            # venue_bias: 主队主场优势 vs 客队客场优势
            away_team_away_advantage = float((away_history_away["points"] == 3).sum() / len(away_history_away)) if not away_history_away.empty else 0.0
            features["venue_bias"] = home_team_home_advantage - away_team_away_advantage
        else:
            features["home_advantage"] = 0.0
            features["venue_bias"] = 0.0

        # 疲劳度特征（7天和30天）
        for prefix, history in [("home", home_history_all), ("away", away_history_all)]:
            features[f"{prefix}_matches_7days"] = self.calculate_matches_in_period(history, match_date, 7)
            features[f"{prefix}_matches_30days"] = self.calculate_matches_in_period(history, match_date, 30)

            # 疲劳度指数 (基于30天内比赛数)
            features[f"{prefix}_fatigue_index"] = min(features[f"{prefix}_matches_30days"] / 30.0, 1.0)

            # 休息天数
            if not history.empty:
                try:
                    last_match_date = pd.to_datetime(history.iloc[0]["match_date"])
                    if pd.notna(last_match_date):
                        features[f"{prefix}_rest_days"] = float((match_date - last_match_date).days)
                    else:
                        features[f"{prefix}_rest_days"] = 999.0
                except Exception:
                    features[f"{prefix}_rest_days"] = 999.0
            else:
                features[f"{prefix}_rest_days"] = 999.0

        features["fatigue_diff"] = features.get("home_fatigue_index", 0) - features.get("away_fatigue_index", 0)
        features["rest_days_diff"] = features.get("home_rest_days", 0) - features.get("away_rest_days", 0)

        return features


# ============================================================================
# V51.3 Model Trainer
# ============================================================================

class V53ModelTrainer:
    """V51.3 模型训练器 - 使用标准标签映射"""

    # V51.3: XGBoost 标准标签映射
    LABEL_MAPPING = {"A": 0, "D": 1, "H": 2}  # 字母顺序 = XGBoost 标准
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

    def __init__(self):
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }
        self.calculator = V53FeatureCalculator()

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def extract_training_data(self, limit: int = 10000) -> pd.DataFrame:
        """提取训练数据"""
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
                        m.away_score,
                        m.league_name
                    FROM matches m
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                    ORDER BY m.match_date ASC
                    LIMIT %s
                """, (limit,))

                rows = cur.fetchall()
                df = pd.DataFrame([dict(row) for row in rows])
                logger.info(f"提取 {len(df)} 场比赛")
                return df

        finally:
            conn.close()

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有比赛的特征"""
        conn = self.get_connection()
        try:
            features_list = []

            for idx, row in df.iterrows():
                if (idx + 1) % 100 == 0:
                    logger.info(f"已处理 {idx + 1}/{len(df)} 场")

                try:
                    features = self.calculator.compute_full_features(
                        row["match_id"],
                        row["match_date"],
                        row["home_team"],
                        row["away_team"],
                        conn=conn,
                    )
                    features["match_id"] = row["match_id"]
                    features_list.append(features)
                except Exception as e:
                    logger.warning(f"计算特征失败 {row['match_id']}: {e}")
                    continue

            # 转换为 DataFrame
            feature_df = pd.DataFrame(features_list)

            # 填充缺失值
            feature_df = feature_df.fillna(0)

            # 确保所有特征都存在
            for feat in V53FeatureCalculator.ALL_FEATURES:
                if feat not in feature_df.columns:
                    feature_df[feat] = 0.0

            # 选择特征列
            feature_df = feature_df[["match_id"] + V53FeatureCalculator.ALL_FEATURES]

            logger.info(f"特征矩阵形状: {feature_df.shape}")
            return feature_df

        finally:
            conn.close()

    def train_model(
        self,
        df: pd.DataFrame,
        feature_df: pd.DataFrame,
        test_split_date: str = "2025-01-01"
    ):
        """训练 V51.3 模型"""
        # 合并数据
        merged = df.merge(feature_df, on="match_id")

        # 构造标签
        merged["result"] = merged.apply(
            lambda row: (
                "H" if row["home_score"] > row["away_score"]
                else "D" if row["home_score"] == row["away_score"]
                else "A"
            ),
            axis=1
        )

        # 时空划分
        train_mask = pd.to_datetime(merged["match_date"]) < test_split_date
        test_mask = pd.to_datetime(merged["match_date"]) >= test_split_date

        train_df = merged[train_mask]
        test_df = merged[test_mask]

        logger.info(f"训练集: {len(train_df)} 场")
        logger.info(f"测试集: {len(test_df)} 场")

        # 准备特征矩阵
        feature_cols = V53FeatureCalculator.ALL_FEATURES
        X_train = train_df[feature_cols].values
        y_train = train_df["result"].map(self.LABEL_MAPPING).values
        X_test = test_df[feature_cols].values
        y_test = test_df["result"].map(self.LABEL_MAPPING).values

        # 标准化
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # 训练模型
        logger.info("开始训练 V51.3 模型...")
        model = xgb.XGBClassifier(**self.XGB_PARAMS)
        model.fit(X_train_scaled, y_train, verbose=True)

        # 评估
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info(f"测试集准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")

        # 特征重要性
        importance = model.feature_importances_
        feature_importance = {
            name: float(score)
            for name, score in zip(feature_cols, importance)
        }
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

        logger.info("\n特征重要性 Top 15:")
        for i, (name, score) in enumerate(list(feature_importance.items())[:15]):
            logger.info(f"  {i+1:2}. {name:40} {score:.4f}")

        # 保存模型
        model_dir = PROJECT_ROOT / "model_zoo"
        model_dir.mkdir(exist_ok=True)
        model_path = model_dir / "v51_3_full_power_model.pkl"

        import joblib
        model_data = {
            "model": model,
            "feature_names": feature_cols,
            "scaler": scaler,
            "label_mapping": self.LABEL_MAPPING,
            "reverse_mapping": self.REVERSE_MAPPING,
            "xgb_params": self.XGB_PARAMS,
            "feature_importance": feature_importance,
            "metadata": {
                "version": "V51.3",
                "training_date": datetime.now().isoformat(),
                "test_accuracy": float(accuracy),
            },
        }
        joblib.dump(model_data, model_path)

        logger.info(f"\n✓ 模型已保存: {model_path}")

        return model, accuracy, feature_importance


def main():
    """主入口"""
    logger.info("=" * 70)
    logger.info("V51.3 Full Power Model Training")
    logger.info("=" * 70)

    trainer = V53ModelTrainer()

    # 1. 提取比赛数据
    logger.info("\n步骤 1: 提取比赛数据")
    df = trainer.extract_training_data(limit=10000)

    # 2. 计算所有特征
    logger.info("\n步骤 2: 计算 58 维特征")
    feature_df = trainer.compute_all_features(df)

    # 3. 训练模型
    logger.info("\n步骤 3: 训练 V51.3 模型")
    model, accuracy, importance = trainer.train_model(df, feature_df)

    logger.info("\n" + "=" * 70)
    logger.info("V51.3 训练完成！")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
