#!/usr/bin/env python3
"""
V26.4 ML Engine - 统一机器学习引擎
=====================================

整合:
- V17.0 滚动特征工程和 XGBoost 模型训练
- V26.4 Predictor 类 (统一推理接口)
- 特征适配层集成
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


# ============================================================================
# V26.4 Predictor - 统一推理接口
# ============================================================================

class Predictor:
    """
    V26.4 统一推理类

    职责:
    - 加载和管理训练好的模型
    - 集成特征适配层
    - 提供统一的预测接口
    - 支持多种模型类型
    """

    # 预测结果映射
    LABEL_MAPPING = {0: "Away", 1: "Draw", 2: "Home"}

    def __init__(self, model_path: str | None = None, model_type: str = "v26_mini"):
        """
        初始化预测器

        Args:
            model_path: 模型文件路径，为 None 则使用默认路径
            model_type: 模型类型 (v26_mini, v19_rolling, v26_5_production, v26_6_pre_match, v26_7_aligned)
        """
        import joblib

        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = []

        # 加载特征适配器
        from src.ml.feature_adapter import FeatureAdapterFactory, ModelType

        if model_type == "v26_mini":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_MINI)
        elif model_type == "v19_rolling":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V19_ROLLING)
        elif model_type == "v26_5_production":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_5_PRODUCTION)
        elif model_type == "v26_6_pre_match":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_6_PRE_MATCH)
        elif model_type == "v26_7_aligned":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_6_PRE_MATCH)  # Reuse V26_6 adapter
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        # 加载模型
        if model_path is None:
            model_path = self._get_default_model_path(model_type)

        if os.path.exists(model_path):
            self._load_model(model_path)
        else:
            logger.warning(f"模型文件不存在: {model_path}，将创建新的微型模型")
            self._create_mini_model()

    def _get_default_model_path(self, model_type: str) -> str:
        """获取默认模型路径"""
        if model_type == "v26_mini":
            return "model_zoo/v26.5_mini.pkl"
        elif model_type == "v19_rolling":
            return "model_zoo/v19.4_draw_sensitivity_model.pkl"
        elif model_type == "v26_5_production":
            return "model_zoo/v26.5_production.pkl"
        elif model_type == "v26_6_pre_match":
            return "model_zoo/v26.6_pre_match.pkl"
        elif model_type == "v26_7_aligned":
            return "model_zoo/v26.7_aligned_production.pkl"
        return "model_zoo/v26.5_mini.pkl"

    def _load_model(self, model_path: str):
        """加载模型文件"""
        import joblib

        logger.info(f"加载模型: {model_path}")
        model_data = joblib.load(model_path)

        # 处理不同的模型格式
        if isinstance(model_data, dict):
            self.model = model_data.get("model")
            self.scaler = model_data.get("scaler")
            self.feature_names = model_data.get("feature_columns", [])
        else:
            self.model = model_data
            self.scaler = None
            self.feature_names = list(self.model.feature_names_in_) if hasattr(self.model, "feature_names_in_") else []

        logger.info(f"✅ 模型加载成功，特征数: {len(self.feature_names)}")

    def _create_mini_model(self):
        """创建微型模型（用于测试）"""
        import xgboost as xgb
        import numpy as np
        from sklearn.preprocessing import StandardScaler

        logger.info("创建微型 V26.4 模型...")

        # V26 微型特征集
        mini_features = self.adapter.get_required_features()

        # 创建简单的训练数据
        np.random.seed(42)
        n_samples = 100
        X = np.random.randn(n_samples, len(mini_features))
        y = np.random.randint(0, 3, n_samples)

        # 训练微型模型
        params = {
            "n_estimators": 50,
            "max_depth": 3,
            "learning_rate": 0.1,
            "objective": "multi:softprob",
            "num_class": 3,
            "random_state": 42,
        }

        self.model = xgb.XGBClassifier(**params)
        self.model.fit(X, y)

        # 创建 scaler
        self.scaler = StandardScaler()
        self.scaler.fit(X)

        self.feature_names = mini_features

        # 保存模型
        self.save()

        logger.info("✅ 微型模型创建完成")

    def predict(self, raw_match_data: dict) -> dict:
        """
        对原始比赛数据进行预测

        Args:
            raw_match_data: V25.1 提取的原始特征字典

        Returns:
            预测结果字典，包含 prediction, probabilities, confidence
        """
        if self.model is None:
            raise ValueError("模型未加载")

        # 1. 特征适配
        adaptation_result = self.adapter.adapt(raw_match_data)

        if not adaptation_result.success:
            raise ValueError(f"特征适配失败: {adaptation_result.errors}")

        features_df = adaptation_result.features

        # 2. 特征标准化
        if self.scaler:
            features_scaled = self.scaler.transform(features_df)
        else:
            features_scaled = features_df.values

        # 3. 模型预测
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        return {
            "prediction": self.LABEL_MAPPING[prediction],
            "probabilities": {
                "Away": float(probabilities[0]),
                "Draw": float(probabilities[1]),
                "Home": float(probabilities[2]),
            },
            "confidence": float(probabilities.max()),
            "model_type": self.model_type,
        }

    def predict_batch(self, raw_match_data_list: list[dict]) -> list[dict]:
        """
        批量预测

        Args:
            raw_match_data_list: 原始比赛数据列表

        Returns:
            预测结果列表
        """
        return [self.predict(data) for data in raw_match_data_list]

    def save(self, path: str | None = None):
        """保存模型"""
        import joblib

        if path is None:
            path = self._get_default_model_path(self.model_type)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_columns": self.feature_names,
            "model_type": self.model_type,
            "version": "26.4",
        }

        joblib.dump(model_data, path)
        logger.info(f"✅ 模型已保存: {path}")

    @classmethod
    def create_v26_mini(cls) -> "Predictor":
        """创建 V26.5 微型预测器"""
        predictor = cls(model_type="v26_mini")
        predictor._create_mini_model()
        return predictor

    @classmethod
    def create_v26_5_production(cls) -> "Predictor":
        """创建 V26.5 生产预测器（加载真实训练的模型）"""
        predictor = cls(model_type="v26_5_production")
        return predictor

    @classmethod
    def create_v26_6_pre_match(cls) -> "Predictor":
        """创建 V26.6 真赛前预测器（无数据泄露）"""
        predictor = cls(model_type="v26_6_pre_match")
        return predictor

    @classmethod
    def create_v26_7_aligned(cls) -> "Predictor":
        """创建 V26.7 对齐预测器（训练-推理完全对齐）"""
        predictor = cls(model_type="v26_7_aligned")
        return predictor


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
