#!/usr/bin/env python3
"""
V26.8 联赛专项模型训练器
======================

针对单个联赛训练专项 XGBoost 模型，捕捉该联赛的独特风格特征。

Usage:
    python scripts/train_v26_8_league.py --league epl
    python scripts/train_v26_8_league.py --league serie_a --test-size 200

Author: ML Architect
Date: 2025-12-28
Phase: 10.1 - 联赛分治策略
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.utils.class_weight import compute_class_weight

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# V26.8 特征集（与 V26.7 相同，确保特征一致性）
V26_8_FEATURES = [
    # 滚动特征 (8个)
    "rolling_xg_home",
    "rolling_xg_away",
    "rolling_shots_on_target_home",
    "rolling_shots_on_target_away",
    "rolling_possession_home",
    "rolling_possession_away",
    "rolling_team_rating_home",
    "rolling_team_rating_away",
    # 积分榜特征 (7个)
    "home_table_position",
    "away_table_position",
    "table_position_diff",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    # 高级特征 (4个)
    "raw_elo_gap",
    "adjusted_elo_gap",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
]

# 标签映射
LABEL_MAPPING = {"away": 0, "draw": 1, "home": 2}
REVERSE_MAPPING = {0: "Away", 1: "Draw", 2: "Home"}

# 联赛配置
LEAGUE_CONFIG = {
    "epl": {
        "id": 47,
        "name": "Premier League",
        "file_suffix": "EPL",
        "model_suffix": "epl",
    },
    "bund": {
        "id": 54,
        "name": "Bundesliga",
        "file_suffix": "BUNDESLIGA",
        "model_suffix": "bund",
    },
    "laliga": {
        "id": 55,
        "name": "La Liga",
        "file_suffix": "LALIGA",
        "model_suffix": "la_liga",
    },
    "ligue1": {
        "id": 61,
        "name": "Ligue 1",
        "file_suffix": "LIGUE1",
        "model_suffix": "ligue1",
    },
    "seriea": {
        "id": 135,
        "name": "Serie A",
        "file_suffix": "SERIEA",
        "model_suffix": "serie_a",
    },
}


class V26_8_LeagueTrainer:
    """V26.8 联赛专项模型训练器"""

    def __init__(
        self,
        league: str,
        data_path: str = None,
        output_dir: str = "model_zoo",
    ):
        """
        初始化训练器

        Args:
            league: 联赛代码 (epl, seriea, laliga, bund, ligue1)
            data_path: 数据文件路径（默认自动检测）
            output_dir: 模型输出目录
        """
        if league not in LEAGUE_CONFIG:
            raise ValueError(f"不支持的联赛: {league}. 支持的联赛: {list(LEAGUE_CONFIG.keys())}")

        self.league = league
        self.league_config = LEAGUE_CONFIG[league]
        self.league_name = self.league_config["name"]

        # 自动检测数据路径
        if data_path is None:
            data_path = f"data/processed/leagues/V26_8_{self.league_config['file_suffix']}_TRAINING.parquet"

        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)

        self.df = None
        self.X = None
        self.y = None
        self.model = None
        self.feature_names = V26_8_FEATURES

        logger.info(f"初始化 V26.8 {self.league_name} 专项模型训练器")

    def load_data(self) -> pd.DataFrame:
        """加载联赛训练数据"""
        logger.info(f"加载数据: {self.data_path}")

        if not self.data_path.exists():
            logger.error(f"❌ 数据文件不存在: {self.data_path}")
            logger.error(f"请先运行: python scripts/league_data_shaper.py")
            raise FileNotFoundError(f"数据文件不存在: {self.data_path}")

        self.df = pd.read_parquet(self.data_path)
        logger.info(f"✅ 数据加载完成: {len(self.df)} 场 {self.league_name} 比赛")
        logger.info(f"   时间范围: {self.df['match_time'].min()} ~ {self.df['match_time'].max()}")

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

        # 计算 Class Weights
        self.class_weights = self._compute_class_weights()

        return self.X, self.y

    def _compute_class_weights(self) -> dict[int, float]:
        """计算类别权重，平衡平局预测"""
        logger.info("计算 Class Weights...")

        # 计算样本权重
        class_weights = compute_class_weight(
            class_weight="balanced",
            classes=np.array([0, 1, 2]),
            y=self.y.values
        )

        # 联赛专项调整：不同联赛的平局倾向不同
        draw_ratio = (self.y == 1).sum() / len(self.y)

        # 平局较多的联赛（意甲）增加权重，平局较少的联赛减少权重
        if draw_ratio > 0.30:  # 平局率 > 30%
            class_weights[1] *= 1.3  # 大幅增强
            logger.info(f"   检测到高平局率联赛 ({draw_ratio*100:.1f}%)，增强平局权重")
        elif draw_ratio < 0.20:  # 平局率 < 20%
            class_weights[1] *= 1.1  # 轻微增强
            logger.info(f"   检测到低平局率联赛 ({draw_ratio*100:.1f}%)，轻微增强平局权重")
        else:
            class_weights[1] *= 1.2  # 标准增强
            logger.info(f"   标准平局率联赛 ({draw_ratio*100:.1f}%)，标准平局权重")

        weight_dict = {0: class_weights[0], 1: class_weights[1], 2: class_weights[2]}

        logger.info(f"   Class Weights: Away={weight_dict[0]:.2f}, Draw={weight_dict[1]:.2f}, Home={weight_dict[2]:.2f}")

        return weight_dict

    def train(
        self,
        test_size: int = 200,
        n_estimators: int = 300,
        max_depth: int = 5,
        learning_rate: float = 0.05,
    ) -> xgb.XGBClassifier:
        """训练 XGBoost 模型"""
        logger.info("=" * 70)
        logger.info(f"开始训练 V26.8 {self.league_name} 专项模型")
        logger.info("=" * 70)

        # 根据数据量调整测试集大小
        actual_test_size = min(test_size, int(len(self.X) * 0.2))

        # 时间序列分割
        X_train = self.X.iloc[:-actual_test_size]
        y_train = self.y.iloc[:-actual_test_size]
        X_test = self.X.iloc[-actual_test_size:]
        y_test = self.y.iloc[-actual_test_size:]

        logger.info(f"   训练集: {len(X_train)} 场")
        logger.info(f"   测试集: {len(X_test)} 场")

        # 计算样本权重
        sample_weights = y_train.map(self.class_weights).values

        # XGBoost 参数（联赛专项微调）
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
        self.model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)

        # 评估
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average='macro')

        logger.info("=" * 70)
        logger.info(f"✅ {self.league_name} 专项模型训练完成")
        logger.info(f"   测试准确率: {accuracy * 100:.2f}%")
        logger.info(f"   F1 (macro): {f1_macro:.4f}")
        logger.info(f"")

        # 计算各结果类别的准确率
        for i, label in enumerate(["Away", "Draw", "Home"]):
            mask = y_test == i
            if mask.sum() > 0:
                class_acc = accuracy_score(y_test[mask], y_pred[mask])
                logger.info(f"   {label} 准确率: {class_acc * 100:.2f}%")

        logger.info(f"\n分类报告:")
        print(classification_report(y_test, y_pred, target_names=["Away", "Draw", "Home"]))

        # 预测分布分析
        unique, counts = np.unique(y_pred, return_counts=True)
        logger.info(f"\n预测分布:")
        for i, count in zip(unique, counts):
            pct = count / len(y_pred) * 100
            logger.info(f"   {REVERSE_MAPPING[i]}: {count} ({pct:.1f}%)")

        # 特征重要性分析
        feature_importance = self.model.feature_importances_
        importance_df = pd.DataFrame({
            "feature": self.feature_names,
            "importance": feature_importance
        }).sort_values("importance", ascending=False)

        logger.info(f"\n{self.league_name} 特征重要性 Top 10:")
        for _, row in importance_df.head(10).iterrows():
            logger.info(f"  {row['feature']:30s}: {row['importance']:.4f}")

        # 保存特征重要性
        self.feature_importance_ = importance_df

        return self.model

    def save(self, output_path: str = None) -> str:
        """保存模型和元数据"""
        import joblib

        if output_path is None:
            output_path = self.output_dir / f"v26.8_{self.league_config['model_suffix']}_production.pkl"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "model": self.model,
            "feature_columns": self.feature_names,
            "feature_count": len(self.feature_names),
            "label_mapping": LABEL_MAPPING,
            "reverse_mapping": REVERSE_MAPPING,
            "model_type": f"v26_8_{self.league_config['model_suffix']}",
            "version": "26.8",
            "league": self.league,
            "league_name": self.league_name,
            "league_id": self.league_config["id"],
            "creation_date": datetime.now().isoformat(),
            "training_samples": len(self.X),
            "anti_leakage": True,
            "fully_aligned": True,
            "class_weights": self.class_weights,
            "feature_importance": self.feature_importance_.to_dict("records") if hasattr(self, "feature_importance_") else None,
        }

        joblib.dump(model_data, output_path)
        logger.info(f"✅ 模型已保存: {output_path}")

        # 保存元数据
        metadata_path = str(output_path).replace(".pkl", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(model_data, f, indent=2, default=str)
        logger.info(f"✅ 元数据已保存: {metadata_path}")

        return str(output_path)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="V26.8 联赛专项模型训练器")
    parser.add_argument(
        "--league",
        type=str,
        required=True,
        choices=list(LEAGUE_CONFIG.keys()),
        help="联赛代码 (epl, seriea, laliga, bund, ligue1)",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="数据文件路径（默认自动检测）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="model_zoo",
        help="模型输出目录",
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=200,
        help="测试集大小",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=300,
        help="XGBoost n_estimators",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="XGBoost max_depth",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.05,
        help="XGBoost learning_rate",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info(f"V26.8 {LEAGUE_CONFIG[args.league]['name']} 专项模型训练")
    logger.info("=" * 70)

    trainer = V26_8_LeagueTrainer(
        league=args.league,
        data_path=args.data_path,
        output_dir=args.output_dir,
    )
    trainer.load_data()
    trainer.prepare_features()
    trainer.train(
        test_size=args.test_size,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
    )
    trainer.save()

    logger.info("=" * 70)
    logger.info("✅ V26.8 训练完成！")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
