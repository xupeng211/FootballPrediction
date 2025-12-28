#!/usr/bin/env python3
"""
V17.0 ML 训练引擎
整合滚动特征工程和 XGBoost 模型训练
"""

import json
import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class V17MLEngine:
    """
    V17.0 ML 训练引擎

    职责:
    - 滚动特征计算和管理
    - XGBoost 模型训练
    - 模型评估和保存
    """

    # V17.0 滚动特征列表（16维）
    ROLLING_FEATURES = [
        "home_rolling_xg",
        "home_rolling_xg_std",
        "home_rolling_shots_on_target",
        "home_rolling_shots_on_target_std",
        "home_rolling_possession",
        "home_rolling_possession_std",
        "home_rolling_team_rating",
        "home_rolling_team_rating_std",
        "away_rolling_xg",
        "away_rolling_xg_std",
        "away_rolling_shots_on_target",
        "away_rolling_shots_on_target_std",
        "away_rolling_possession",
        "away_rolling_possession_std",
        "away_rolling_team_rating",
        "away_rolling_team_rating_std",
    ]

    CORE_METRICS = ["xg", "shots_on_target", "possession", "team_rating"]

    # 默认 XGBoost 参数（与 V17.0 一致）
    DEFAULT_XGB_PARAMS = {
        "n_estimators": 200,
        "max_depth": 4,
        "learning_rate": 0.05,
        "min_child_weight": 3,
        "reg_alpha": 0.5,
        "reg_lambda": 1.0,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, db_config: dict | None = None):
        """
        初始化 ML 引擎

        Args:
            db_config: 数据库配置（如未提供，从 config_unified 获取）
        """
        if db_config is None:
            # V20.8 SRE 硬化: 从统一配置获取数据库参数，零硬编码
            from src.config_unified import get_settings

            settings = get_settings()
            db_config = {
                "host": settings.database.host,
                "port": settings.database.port,
                "database": settings.database.name,
                "user": settings.database.user,
                "password": settings.database.password.get_secret_value(),
            }

        self.db_config = db_config

        self.label_mapping = {"A": 0, "D": 1, "H": 2}
        self.reverse_mapping = {0: "A", 1: "D", 2: "H"}
        self.model = None
        self.feature_names = None

    def get_connection(self):
        """获取数据库连接"""
        import psycopg2

        return psycopg2.connect(**self.db_config)

    def _parse_stats(self, stats_str: str) -> dict:
        """解析 player_stats JSON"""
        try:
            if isinstance(stats_str, str):
                return json.loads(stats_str)
            return stats_str
        except:
            return {}

    # ========================================================================
    # 滚动特征计算
    # ========================================================================

    def extract_match_data(self, season: str = "23/24") -> pd.DataFrame:
        """从数据库提取比赛数据"""
        from psycopg2.extras import RealDictCursor

        logger.info("📊 提取比赛数据")

        conn = None
        try:
            conn = self.get_connection()

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        external_id,
                        home_team,
                        away_team,
                        match_time,
                        home_score,
                        away_score,
                        actual_result,
                        player_stats
                    FROM matches
                    WHERE season = %s
                        AND player_stats IS NOT NULL
                    ORDER BY match_time ASC
                """,
                    (season,),
                )

                rows = cur.fetchall()
                df = pd.DataFrame([dict(row) for row in rows])
                df["parsed_stats"] = df["player_stats"].apply(self._parse_stats)

                logger.info(f"✅ 提取了 {len(df)} 场比赛")
                return df

        finally:
            if conn:
                conn.close()

    def build_team_history(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """构建球队历史数据"""
        team_history = {}
        all_teams = set(df["home_team"].unique()) | set(df["away_team"].unique())

        for team in all_teams:
            home_matches = df[df["home_team"] == team][["external_id", "match_time", "parsed_stats"]].copy()
            away_matches = df[df["away_team"] == team][["external_id", "match_time", "parsed_stats"]].copy()

            home_matches["is_home"] = True
            away_matches["is_home"] = False

            home_matches = home_matches.rename(columns={"parsed_stats": "stats"})
            away_matches = away_matches.rename(columns={"parsed_stats": "stats"})

            team_matches = pd.concat([home_matches, away_matches], ignore_index=True)
            team_matches = team_matches.sort_values("match_time").reset_index(drop=True)

            team_history[team] = team_matches

        return team_history

    def calculate_single_rolling_feature(
        self, team_history: dict[str, pd.DataFrame], home_team: str, away_team: str, match_time: str, window: int = 10
    ) -> dict[str, float]:
        """
        计算单场比赛的滚动特征

        Returns:
            包含 16 个滚动特征的字典
        """
        home_hist = team_history[home_team]
        home_before = home_hist[home_hist["match_time"] < match_time].tail(window)

        away_hist = team_history[away_team]
        away_before = away_hist[away_hist["match_time"] < match_time].tail(window)

        features = {"home_matches_count": len(home_before), "away_matches_count": len(away_before)}

        # 计算主队滚动特征
        for metric in self.CORE_METRICS:
            home_values = []
            for _, row in home_before.iterrows():
                stats = row.get("stats", {})
                val = stats.get(f"home_{metric}" if row["is_home"] else f"away_{metric}")
                if val is not None:
                    try:
                        home_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if home_values:
                features[f"home_rolling_{metric}"] = np.mean(home_values)
                features[f"home_rolling_{metric}_std"] = np.std(home_values)
            else:
                features[f"home_rolling_{metric}"] = 0.0
                features[f"home_rolling_{metric}_std"] = 0.0

        # 计算客队滚动特征
        for metric in self.CORE_METRICS:
            away_values = []
            for _, row in away_before.iterrows():
                stats = row.get("stats", {})
                val = stats.get(f"home_{metric}" if row["is_home"] else f"away_{metric}")
                if val is not None:
                    try:
                        away_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if away_values:
                features[f"away_rolling_{metric}"] = np.mean(away_values)
                features[f"away_rolling_{metric}_std"] = np.std(away_values)
            else:
                features[f"away_rolling_{metric}"] = 0.0
                features[f"away_rolling_{metric}_std"] = 0.0

        return features

    def build_rolling_features(self, df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        """
        构建完整的滚动特征数据集

        Args:
            df: 原始比赛数据
            window: 滚动窗口大小

        Returns:
            滚动特征 DataFrame
        """
        logger.info(f"📊 计算滚动特征 (window={window})")

        team_history = self.build_team_history(df)
        rolling_features = []

        for idx, row in df.iterrows():
            features = self.calculate_single_rolling_feature(
                team_history, row["home_team"], row["away_team"], row["match_time"], window
            )
            features["match_id"] = row["external_id"]
            rolling_features.append(features)

            if (idx + 1) % 50 == 0:
                logger.info(f"  进度: {idx + 1}/{len(df)}")

        rolling_df = pd.DataFrame(rolling_features)
        logger.info(f"✅ 滚动特征计算完成: {len(rolling_df)} 场")

        return rolling_df

    # ========================================================================
    # 模型训练
    # ========================================================================

    def prepare_dataset(
        self, df: pd.DataFrame, rolling_df: pd.DataFrame, min_history: int = 5
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        准备训练数据集

        Args:
            df: 原始比赛数据
            rolling_df: 滚动特征数据
            min_history: 最小历史比赛数

        Returns:
            特征矩阵 X 和标签 y
        """
        logger.info("📊 准备训练数据集")

        # 合并数据
        merged_df = df.merge(rolling_df, left_on="external_id", right_on="match_id", how="inner")

        # 过滤有效数据
        valid_mask = (merged_df["home_matches_count"] >= min_history) & (merged_df["away_matches_count"] >= min_history)

        X = merged_df.loc[valid_mask, self.ROLLING_FEATURES].copy()
        y = merged_df.loc[valid_mask, "actual_result"].map(self.label_mapping)

        logger.info(f"✅ 有效样本: {len(X)}")
        logger.info(f"   过滤掉: {len(merged_df) - len(X)} 场 (历史不足)")

        return X, y

    def train(self, X: pd.DataFrame, y: pd.Series, train_size: int = 300, **xgb_params):
        """
        训练 XGBoost 模型

        Args:
            X: 特征矩阵
            y: 标签
            train_size: 训练集大小
            **xgb_params: XGBoost 超参数

        Returns:
            训练好的模型
        """
        import xgboost as xgb

        logger.info("📊 训练 XGBoost 模型")

        # 时间序列分割
        X_train = X.iloc[:train_size]
        y_train = y[:train_size]
        X_test = X.iloc[train_size:]
        y_test = y[train_size:]

        logger.info(f"   训练集: {len(X_train)} 场")
        logger.info(f"   测试集: {len(X_test)} 场")

        # 合并参数
        params = {**self.DEFAULT_XGB_PARAMS, **xgb_params}

        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, verbose=False)

        self.model = model
        self.feature_names = self.ROLLING_FEATURES

        # 快速评估
        from sklearn.metrics import accuracy_score

        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        logger.info(f"✅ 模型训练完成，测试准确率: {accuracy * 100:.2f}%")

        return model

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """评估模型性能"""
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

        y_pred = self.model.predict(X_test)

        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "f1_macro": f1_score(y_test, y_pred, average="macro"),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        }

    def save(self, output_dir: str = "model_zoo"):
        """保存模型到 model_zoo 目录"""
        import joblib

        os.makedirs(output_dir, exist_ok=True)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = os.path.join(output_dir, f"rolling_model_{timestamp}.pkl")
        joblib.dump(self.model, model_path)
        logger.info(f"✅ 模型已保存: {model_path}")

        metadata = {
            "model_type": "XGBoost",
            "features": self.ROLLING_FEATURES,
            "feature_count": len(self.ROLLING_FEATURES),
            "label_mapping": self.label_mapping,
            "reverse_mapping": self.reverse_mapping,
            "creation_date": datetime.now().isoformat(),
        }

        metadata_path = model_path.replace(".pkl", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✅ 元数据已保存: {metadata_path}")

    def load(self, model_path: str | None = None):
        """加载模型"""
        import joblib

        self.model = joblib.load(model_path)
        logger.info(f"✅ 模型已加载: {model_path}")

        # 加载元数据
        metadata_path = model_path.replace(".pkl", "_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                metadata = json.load(f)
                self.feature_names = metadata.get("features", self.ROLLING_FEATURES)
                self.label_mapping = metadata.get("label_mapping", self.label_mapping)
                self.reverse_mapping = metadata.get("reverse_mapping", self.reverse_mapping)

    def predict(self, features: dict[str, float]) -> dict:
        """
        预测单场比赛

        Args:
            features: 滚动特征字典（16 个特征）

        Returns:
            预测结果字典
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用 train() 或 load()")

        # 准备输入
        X = pd.DataFrame([features])[self.ROLLING_FEATURES]

        # 预测
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]

        return {
            "prediction": self.reverse_mapping[prediction],
            "probabilities": {"Away": probabilities[0], "Draw": probabilities[1], "Home": probabilities[2]},
            "confidence": float(probabilities.max()),
        }


def main():
    """主函数 - 用于测试"""
    engine = V17MLEngine()

    # 提取数据
    df = engine.extract_match_data()
    rolling_df = engine.build_rolling_features(df, window=10)

    # 准备数据集
    merged_df = df.merge(rolling_df, left_on="external_id", right_on="match_id", how="inner")
    X, y = engine.prepare_dataset(merged_df, rolling_df)

    # 训练模型
    engine.train(X, y, train_size=300)

    # 保存模型
    engine.save()

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
