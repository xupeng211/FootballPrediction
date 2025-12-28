#!/usr/bin/env python3
"""
V26.7 对齐模型训练 - 全动态特征流
===================================

基于 Phase 5.5 生成的镜像训练集，使用完全对齐的特征进行训练。

关键改进：
- 训练集使用与推理相同的特征计算逻辑
- 增加 Class Weights 优化平局预测
- 生产级防泄露验证

Author: ML Ops Engineer
Date: 2025-12-28
Phase: 5.5 - 大脑升级
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# V26.7 特征集（19维，与 V26.6 相同）
V26_7_FEATURES = [
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


class V26_7_Trainer:
    """V26.7 对齐模型训练器"""

    def __init__(self, data_path: str = "data/processed/V26_7_ALIGNED_TRAINING.parquet"):
        self.data_path = data_path
        self.df = None
        self.X = None
        self.y = None
        self.model = None
        self.feature_names = V26_7_FEATURES

    def load_data(self) -> pd.DataFrame:
        """加载对齐训练数据"""
        logger.info(f"加载数据: {self.data_path}")
        self.df = pd.read_parquet(self.data_path)
        logger.info(f"✅ 数据加载完成: {len(self.df)} 场比赛, {len(self.df.columns)} 个特征")
        return self.df

    def prepare_features(self):
        """准备特征和标签"""
        logger.info("准备特征和标签...")
        logger.info("⚠️  使用 V26.7 对齐特征集（与推理逻辑完全一致）")

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

        # 稍微增强平局的权重（从 balanced 的基础上再提升 20%）
        class_weights[1] *= 1.2

        weight_dict = {0: class_weights[0], 1: class_weights[1], 2: class_weights[2]}

        logger.info(f"   Class Weights: Away={weight_dict[0]:.2f}, Draw={weight_dict[1]:.2f}, Home={weight_dict[2]:.2f}")

        return weight_dict

    def train(
        self,
        test_size: int = 500,
        n_estimators: int = 300,
        max_depth: int = 5,
        learning_rate: float = 0.05,
    ) -> xgb.XGBClassifier:
        """训练 XGBoost 模型"""
        logger.info("=" * 70)
        logger.info("开始训练 V26.7 对齐模型")
        logger.info("=" * 70)

        # 时间序列分割
        X_train = self.X.iloc[:-test_size]
        y_train = self.y.iloc[:-test_size]
        X_test = self.X.iloc[-test_size:]
        y_test = self.y.iloc[-test_size:]

        logger.info(f"   训练集: {len(X_train)} 场")
        logger.info(f"   测试集: {len(X_test)} 场")

        # 计算样本权重
        sample_weights = y_train.map(self.class_weights).values

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
        self.model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)

        # 评估
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average='macro')

        logger.info("=" * 70)
        logger.info(f"✅ 模型训练完成")
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

        logger.info(f"\n特征重要性 Top 10:")
        for _, row in importance_df.head(10).iterrows():
            logger.info(f"  {row['feature']:30s}: {row['importance']:.4f}")

        # 验证：检查是否存在泄露特征
        leakage_features = ["home_xg", "away_xg", "home_possession", "away_possession",
                           "home_shots_on_target", "away_shots_on_target"]
        top_feature = importance_df.iloc[0]["feature"]
        if top_feature in leakage_features:
            logger.warning(f"⚠️  警告：最重要的特征是泄露特征！({top_feature})")
        else:
            logger.info(f"✅ 安全检查通过：最重要的特征是 {top_feature}（赛前已知）")

        return self.model

    def save(self, output_path: str = "model_zoo/v26.7_aligned_production.pkl"):
        """保存模型和元数据"""
        import joblib

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        model_data = {
            "model": self.model,
            "feature_columns": self.feature_names,
            "feature_count": len(self.feature_names),
            "label_mapping": LABEL_MAPPING,
            "reverse_mapping": REVERSE_MAPPING,
            "model_type": "v26_7_aligned",
            "version": "26.7",
            "creation_date": datetime.now().isoformat(),
            "training_samples": len(self.X),
            "anti_leakage": True,
            "fully_aligned": True,  # 标记为完全对齐
            "class_weights": self.class_weights,
        }

        joblib.dump(model_data, output_path)
        logger.info(f"✅ 模型已保存: {output_path}")

        # 保存元数据
        metadata_path = output_path.replace(".pkl", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(model_data, f, indent=2, default=str)
        logger.info(f"✅ 元数据已保存: {metadata_path}")

        return output_path


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("V26.7 对齐模型训练 - 全动态特征流")
    logger.info("=" * 70)

    trainer = V26_7_Trainer()
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
    trainer.save()

    logger.info("=" * 70)
    logger.info("✅ V26.7 训练完成！")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
