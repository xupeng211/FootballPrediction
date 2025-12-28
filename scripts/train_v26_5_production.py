#!/usr/bin/env python3
"""
V26.5 Production Model Training - Real Brain Replacement
=========================================================

使用 V28_REAL_GOLD.parquet (9305+ 场真实比赛) 训练生产级 XGBoost 模型。

数据特征:
- 滚动特征: xG, shots_on_target, possession, team_rating
- 当前比赛特征: xG, possession, shots_on_target, team_rating
- 积分榜特征: table_position, points, form
- 高级特征: ELO, fatigue, incentive

Author: ML Team
Date: 2025-12-28
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# V26.5 Production Feature Set
# ============================================================================

V26_5_FEATURES = [
    # 滚动特征 (8个) - 历史表现
    "rolling_xg_home",
    "rolling_xg_away",
    "rolling_shots_on_target_home",
    "rolling_shots_on_target_away",
    "rolling_possession_home",
    "rolling_possession_away",
    "rolling_team_rating_home",
    "rolling_team_rating_away",
    # 当前比赛特征 (8个) - 本场数据
    "home_xg",
    "away_xg",
    "home_possession",
    "away_possession",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_team_rating",
    "away_team_rating",
    # 积分榜特征 (7个)
    "home_table_position",
    "away_table_position",
    "table_position_diff",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    # 高级特征 (6个)
    "raw_elo_gap",
    "adjusted_elo_gap",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
    "home_relegation_incentive",
]  # 37 features total

# 简化版特征集 (用于 V26MiniAdapter 兼容)
V26_MINI_FEATURES = [
    "home_xg", "away_xg",
    "home_possession", "away_possession",
    "home_shots_on_target", "away_shots_on_target",
    "rolling_xg_home", "rolling_xg_away",
    "rolling_possession_home", "rolling_possession_away",
]

# 标签映射
LABEL_MAPPING = {"away": 0, "draw": 1, "home": 2}
REVERSE_MAPPING = {0: "Away", 1: "Draw", 2: "Home"}


class V26_5_Trainer:
    """V26.5 生产模型训练器"""

    def __init__(self, data_path: str = "data/processed/V28_REAL_GOLD.parquet"):
        self.data_path = data_path
        self.df = None
        self.X = None
        self.y = None
        self.label_encoder = LabelEncoder()
        self.model = None
        self.feature_names = V26_5_FEATURES

    def load_data(self) -> pd.DataFrame:
        """加载训练数据"""
        logger.info(f"加载数据: {self.data_path}")
        self.df = pd.read_parquet(self.data_path)
        logger.info(f"✅ 数据加载完成: {len(self.df)} 场比赛, {len(self.df.columns)} 个特征")
        return self.df

    def prepare_features(self):
        """准备特征和标签"""
        logger.info("准备特征和标签...")

        # 标签编码
        self.df["label"] = self.df["result"].map(LABEL_MAPPING)

        # 检查特征完整性
        missing_features = [f for f in self.feature_names if f not in self.df.columns]
        if missing_features:
            logger.error(f"❌ 缺失特征: {missing_features}")
            raise ValueError(f"缺失特征: {missing_features}")

        # 特征矩阵
        self.X = self.df[self.feature_names].copy()
        self.y = self.df["label"].copy()

        # 处理缺失值
        self.X = self.X.fillna(0)

        logger.info(f"✅ 特征准备完成: {self.X.shape}")
        logger.info(f"   标签分布: {self.y.value_counts().to_dict()}")

        return self.X, self.y

    def train(
        self,
        test_size: int = 500,
        n_estimators: int = 300,
        max_depth: int = 5,
        learning_rate: float = 0.05,
    ) -> xgb.XGBClassifier:
        """训练 XGBoost 模型"""
        logger.info("开始训练 V26.5 生产模型...")

        # 时间序列分割
        X_train = self.X.iloc[:-test_size]
        y_train = self.y.iloc[:-test_size]
        X_test = self.X.iloc[-test_size:]
        y_test = self.y.iloc[-test_size:]

        logger.info(f"   训练集: {len(X_train)} 场")
        logger.info(f"   测试集: {len(X_test)} 场")

        # XGBoost 参数
        params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
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

        self.model = xgb.XGBClassifier(**params)
        self.model.fit(X_train, y_train, verbose=False)

        # 评估
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info(f"✅ 模型训练完成")
        logger.info(f"   测试准确率: {accuracy * 100:.2f}%")
        logger.info(f"\n分类报告:")
        print(classification_report(y_test, y_pred, target_names=["Away", "Draw", "Home"]))

        return self.model

    def save(self, output_path: str = "model_zoo/v26.5_production.pkl"):
        """保存模型和元数据"""
        import joblib

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        model_data = {
            "model": self.model,
            "feature_columns": self.feature_names,
            "feature_count": len(self.feature_names),
            "label_mapping": LABEL_MAPPING,
            "reverse_mapping": REVERSE_MAPPING,
            "model_type": "v26_5_production",
            "version": "26.5",
            "creation_date": datetime.now().isoformat(),
            "training_samples": len(self.X),
        }

        joblib.dump(model_data, output_path)
        logger.info(f"✅ 模型已保存: {output_path}")

        # 保存元数据
        metadata_path = output_path.replace(".pkl", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(model_data, f, indent=2, default=str)
        logger.info(f"✅ 元数据已保存: {metadata_path}")

        return output_path


def train_mini_model():
    """训练微型模型（兼容 V26MiniAdapter）"""
    logger.info("训练 V26.5 Mini 模型（10 特征）...")

    trainer = V26_5_Trainer()
    trainer.load_data()

    # 使用微型特征集
    trainer.feature_names = V26_MINI_FEATURES
    trainer.prepare_features()

    # 训练
    trainer.train(
        test_size=500,
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
    )

    # 保存
    trainer.save("model_zoo/v26.5_mini.pkl")

    return trainer


def train_full_model():
    """训练完整生产模型（37 特征）"""
    logger.info("训练 V26.5 Production 模型（37 特征）...")

    trainer = V26_5_Trainer()
    trainer.load_data()
    trainer.prepare_features()

    # 训练
    trainer.train(
        test_size=500,
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
    )

    # 保存
    trainer.save("model_zoo/v26.5_production.pkl")

    return trainer


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("V26.5 Production Model Training")
    logger.info("=" * 60)

    # 1. 训练微型模型（兼容现有 FeatureAdapter）
    logger.info("\n[Step 1] 训练微型模型...")
    mini_trainer = train_mini_model()

    # 2. 训练完整生产模型
    logger.info("\n[Step 2] 训练完整生产模型...")
    full_trainer = train_full_model()

    logger.info("\n" + "=" * 60)
    logger.info("✅ V26.5 模型训练完成!")
    logger.info("=" * 60)
    logger.info(f"   Mini 模型: model_zoo/v26.5_mini.pkl ({len(V26_MINI_FEATURES)} features)")
    logger.info(f"   完整模型: model_zoo/v26.5_production.pkl ({len(V26_5_FEATURES)} features)")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
