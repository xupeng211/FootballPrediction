#!/usr/bin/env python3
"""
简化的模型训练脚本 - 从CSV数据直接训练

使用现有的processed_features.csv直接训练XGBoost模型，
绕过复杂的数据库连接问题，快速生成可用模型。
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入机器学习库
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


class SimpleModelTrainer:
    """简化模型训练器"""

    def __init__(
        self, model_path: str = "/app/data/models/football_prediction_model.pkl"
    ):
        self.model_path = model_path
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_columns = []
        self.model = None
        self.training_stats = {}

    def load_and_prepare_data(
        self, csv_path: str = "/app/data/processed_features.csv"
    ) -> pd.DataFrame:
        """加载并准备训练数据"""
        logger.info(f"正在加载数据: {csv_path}")

        try:
            df = pd.read_csv(csv_path)
            logger.info(f"成功加载数据: {df.shape[0]} 行, {df.shape[1]} 列")

            # 基础数据清洗
            # 移除缺失值过多的行
            df_clean = df.dropna(subset=["home_xg", "away_xg", "match_result"])

            # 特征工程 - 创建更多有用的特征
            df_clean["xg_ratio"] = df_clean["home_xg"] / (
                df_clean["away_xg"] + 0.01
            )  # 避免0除
            df_clean["total_xg"] = df_clean["home_xg"] + df_clean["away_xg"]
            df_clean["xg_difference"] = df_clean["home_xg"] - df_clean["away_xg"]

            # 创建目标标签
            label_mapping = {"Home": 0, "Draw": 1, "Away": 2}
            df_clean["target"] = df_clean["match_result"].map(label_mapping)

            # 移除没有标签的数据
            df_clean = df_clean.dropna(subset=["target"])

            logger.info(f"数据清洗后: {df_clean.shape[0]} 行")
            logger.info(f"标签分布: {df_clean['target'].value_counts().to_dict()}")

            return df_clean

        except Exception as e:
            logger.error(f"数据加载失败: {e}")
            raise

    def select_features(self, df: pd.DataFrame) -> List[str]:
        """选择用于训练的特征"""
        # 基础特征列
        base_features = ["home_xg", "away_xg", "total_xg", "xg_difference", "xg_ratio"]

        # 扩展特征 - 使用所有可用的数值特征
        numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()

        # 过滤掉不需要的列
        exclude_columns = [
            "id",
            "fotmob_id",
            "home_score",
            "away_score",
            "target",
            "result_numeric",  # 如果存在的话
        ]

        available_features = []
        for col in numeric_features:
            if col not in exclude_columns and col in df.columns:
                try:
                    # 检查列是否可以转换为float
                    df[col].astype(float)
                    available_features.append(col)
                except (ValueError, TypeError):
                    continue

        # 合并基础特征和可用特征
        self.feature_columns = list(set(base_features + available_features))
        logger.info(
            f"选择了 {len(self.feature_columns)} 个特征: {self.feature_columns}"
        )

        return self.feature_columns

    def train_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """训练XGBoost模型"""
        logger.info("开始训练模型...")

        # 选择特征
        feature_cols = self.select_features(df)
        X = df[feature_cols].copy()
        y = df["target"].copy()

        # 处理缺失值
        X = X.fillna(X.mean())

        # 编码标签
        y_encoded = self.label_encoder.fit_transform(y)

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )

        # 特征缩放
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # 创建并训练XGBoost模型
        self.model = xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
        )

        # 训练模型
        self.model.fit(X_train_scaled, y_train)

        # 预测和评估
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        # 详细评估报告
        class_names = self.label_encoder.classes_
        report = classification_report(
            y_test, y_pred, target_names=class_names, output_dict=True
        )

        # 训练统计信息
        self.training_stats = {
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(feature_cols),
            "accuracy": accuracy,
            "class_report": report,
            "feature_importance": dict(
                zip(feature_cols, self.model.feature_importances_)
            ),
            "training_time": datetime.now().isoformat(),
            "model_parameters": {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
            },
        }

        logger.info(f"模型训练完成! 准确率: {accuracy:.4f}")
        logger.info(f"训练样本: {len(X_train)}, 测试样本: {len(X_test)}")

        return self.training_stats

    def save_model(self):
        """保存训练好的模型和预处理组件"""
        logger.info(f"正在保存模型到: {self.model_path}")

        # 确保目录存在
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # 保存模型和组件
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "label_encoder": self.label_encoder,
            "feature_columns": self.feature_columns,
            "training_stats": self.training_stats,
            "model_version": "1.0.0",
            "created_at": datetime.now().isoformat(),
        }

        with open(self.model_path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info("模型保存成功!")

        # 保存模型元数据
        metadata_path = self.model_path.replace(".pkl", "_metadata.json")
        import json

        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "model_path": self.model_path,
                    "feature_count": len(self.feature_columns),
                    "accuracy": self.training_stats["accuracy"],
                    "training_samples": self.training_stats["training_samples"],
                    "created_at": model_data["created_at"],
                },
                f,
                indent=2,
            )

        logger.info(f"模型元数据已保存到: {metadata_path}")

    def print_training_summary(self):
        """打印训练总结"""
        stats = self.training_stats

        print("\n" + "=" * 60)
        print("🏆 足球预测模型训练完成")
        print("=" * 60)

        print(f"\n📊 模型性能:")
        print(f"   准确率: {stats['accuracy']:.4f} ({stats['accuracy']*100:.2f}%)")
        print(f"   训练样本: {stats['training_samples']:,}")
        print(f"   测试样本: {stats['test_samples']:,}")
        print(f"   特征数量: {stats['feature_count']}")

        print(f"\n📈 各类别性能:")
        for class_name, metrics in stats["class_report"].items():
            if isinstance(metrics, dict) and "f1-score" in metrics:
                print(
                    f"   {class_name:10}: F1={metrics['f1-score']:.3f}, "
                    f"Precision={metrics['precision']:.3f}, "
                    f"Recall={metrics['recall']:.3f}"
                )

        print(f"\n🔧 Top 10 重要特征:")
        feature_importance = sorted(
            stats["feature_importance"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        for i, (feature, importance) in enumerate(feature_importance, 1):
            print(f"   {i:2d}. {feature:25}: {importance:.4f}")

        print(f"\n💾 模型已保存到: {self.model_path}")
        print("=" * 60)


async def main():
    """主训练流程"""
    try:
        # 创建训练器
        trainer = SimpleModelTrainer()

        # 加载数据
        df = trainer.load_and_prepare_data()

        if len(df) < 50:
            logger.error("数据量太少，无法进行有效训练")
            return 1

        # 训练模型
        trainer.train_model(df)

        # 保存模型
        trainer.save_model()

        # 打印总结
        trainer.print_training_summary()

        return 0

    except Exception as e:
        logger.error(f"训练过程失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
