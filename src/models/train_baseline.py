#!/usr/bin/env python3
"""
Phase 3 基线模型训练器
首席 AI 科学家: 机器学习专家

Purpose: 训练XGBoost基线预测模型
使用特征工程数据进行模型训练和评估
"""

import logging
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Any
from datetime import datetime

# 机器学习库
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    classification_report,
    confusion_matrix,
)
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.features.pipeline import FeaturePipeline

logger = logging.getLogger(__name__)


class BaselineTrainer:
    """
    XGBoost基线模型训练器

    功能：
    1. 调用特征流水线获取数据
    2. 时间切分训练集和测试集
    3. 训练XGBoost分类模型
    4. 评估模型性能 (Accuracy, LogLoss)
    5. 输出详细的训练报告
    """

    def __init__(self):
        """初始化训练器"""
        self.feature_pipeline = FeaturePipeline()
        self.model = None
        self.label_encoder = LabelEncoder()

        logger.info("✅ 基线训练器初始化成功")

    def prepare_data(
        self, train_end_date: str = "2024-05-01"
    ) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
        """
        准备训练和测试数据

        Args:
            train_end_date: 训练集结束日期

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        logger.info("🔄 开始准备训练数据...")

        try:
            # 构建特征数据集
            df, feature_cols = self.feature_pipeline.build_features(window=5)

            # 时间切分
            train_df, test_df = self.feature_pipeline.split_data(df, train_end_date)

            # 选择特征列
            X_train = train_df[feature_cols].fillna(0)
            X_test = test_df[feature_cols].fillna(0)

            # 准备目标变量
            y_train = train_df["result"].values
            y_test = test_df["result"].values

            # 移除包含NaN的样本
            train_mask = ~(X_train.isna().any(axis=1) | pd.isna(y_train))
            test_mask = ~(X_test.isna().any(axis=1) | pd.isna(y_test))

            X_train = X_train[train_mask]
            y_train = y_train[train_mask]
            X_test = X_test[test_mask]
            y_test = y_test[test_mask]

            logger.info("✅ 数据准备完成:")
            logger.info(f"   训练集: {X_train.shape[0]} 样本, {X_train.shape[1]} 特征")
            logger.info(f"   测试集: {X_test.shape[0]} 样本, {X_test.shape[1]} 特征")
            logger.info(f"   特征列: {len(feature_cols)} 个")

            # 显示目标变量分布
            unique_train, counts_train = np.unique(y_train, return_counts=True)
            unique_test, counts_test = np.unique(y_test, return_counts=True)

            logger.info(f"   训练集分布: {dict(zip(unique_train, counts_train, strict=False))}")
            logger.info(f"   测试集分布: {dict(zip(unique_test, counts_test, strict=False))}")

            return X_train, X_test, y_train, y_test

        except Exception as e:
            logger.error(f"❌ 数据准备失败: {e}")
            raise

    def train_model(
        self, X_train: pd.DataFrame, y_train: np.ndarray
    ) -> xgb.XGBClassifier:
        """
        训练XGBoost模型

        Args:
            X_train: 训练特征
            y_train: 训练标签

        Returns:
            训练好的XGBoost模型
        """
        logger.info("🚀 开始训练XGBoost模型...")

        # XGBoost参数配置
        params = {
            "objective": "multi:softprob",  # 多分类
            "num_class": 3,  # 3分类 (客胜/平/主胜)
            "eval_metric": "mlogloss",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": -1,
        }

        # 创建模型
        model = xgb.XGBClassifier(**params)

        # 训练模型
        model.fit(X_train, y_train, eval_set=[(X_train, y_train)], verbose=False)

        logger.info("✅ 模型训练完成")
        logger.info(f"   树的数量: {model.n_estimators}")
        logger.info(f"   最大深度: {model.max_depth}")

        self.model = model
        return model

    def evaluate_model(
        self, model: xgb.XGBClassifier, X_test: pd.DataFrame, y_test: np.ndarray
    ) -> dict[str, float]:
        """
        评估模型性能

        Args:
            model: 训练好的模型
            X_test: 测试特征
            y_test: 测试标签

        Returns:
            评估指标字典
        """
        logger.info("📊 开始模型评估...")

        # 预测
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)
        logloss = log_loss(y_test, y_pred_proba)

        # 详细报告
        class_names = ["客胜(0)", "平局(1)", "主胜(2)"]
        report = classification_report(
            y_test, y_pred, target_names=class_names, output_dict=True
        )

        # 混淆矩阵
        cm = confusion_matrix(y_test, y_pred)

        logger.info("📈 评估结果:")
        logger.info(f"   准确率 (Accuracy): {accuracy:.4f} ({accuracy*100:.2f}%)")
        logger.info(f"   对数损失 (LogLoss): {logloss:.4f}")

        # 各类别准确率
        for i, class_name in enumerate(class_names):
            if str(i) in report:
                class_acc = report[str(i)]["precision"]
                logger.info(f"   {class_name} 准确率: {class_acc:.4f}")

        # 特征重要性
        feature_importance = pd.DataFrame(
            {"feature": X_test.columns, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

        logger.info("\n🔝 Top 10 重要特征:")
        for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
            logger.info(f"   {i+1:2d}. {row['feature']:30s}: {row['importance']:.4f}")

        # 保存结果
        results = {
            "accuracy": accuracy,
            "logloss": logloss,
            "classification_report": report,
            "confusion_matrix": cm,
            "feature_importance": feature_importance,
        }

        return results

    def save_results(
        self, results: dict[str, Any], model_name: str = "baseline_xgboost"
    ) -> None:
        """
        保存训练结果和模型

        Args:
            results: 评估结果
            model_name: 模型名称
        """
        logger.info("💾 保存训练结果...")

        # 创建输出目录
        output_dir = Path("results") / model_name
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存评估报告
        report_path = output_dir / f"report_{timestamp}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Phase 3 基线模型训练报告\n")
            f.write(f"生成时间: {datetime.now()}\n")
            f.write(f"模型名称: {model_name}\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"准确率: {results['accuracy']:.4f}\n")
            f.write(f"对数损失: {results['logloss']:.4f}\n\n")

            f.write("分类报告:\n")
            for class_name, metrics in results["classification_report"].items():
                if isinstance(metrics, dict):
                    f.write(f"  {class_name}:\n")
                    for metric, value in metrics.items():
                        f.write(f"    {metric}: {value:.4f}\n")

        # 保存特征重要性
        importance_path = output_dir / f"feature_importance_{timestamp}.csv"
        results["feature_importance"].to_csv(importance_path, index=False)

        # 保存模型
        if self.model:
            model_path = output_dir / f"model_{timestamp}.json"
            self.model.save_model(str(model_path))

        logger.info(f"✅ 结果已保存到: {output_dir}")

    def run_training(
        self, train_end_date: str = "2024-05-01", save_results: bool = True
    ) -> dict[str, float]:
        """
        运行完整的训练流程

        Args:
            train_end_date: 训练集结束日期
            save_results: 是否保存结果

        Returns:
            评估指标
        """
        logger.info("🎯 开始Phase 3基线模型训练流程...")

        try:
            # 1. 准备数据
            X_train, X_test, y_train, y_test = self.prepare_data(train_end_date)

            # 2. 训练模型
            model = self.train_model(X_train, y_train)

            # 3. 评估模型
            results = self.evaluate_model(model, X_test, y_test)

            # 4. 保存结果
            if save_results:
                self.save_results(results)

            # 5. 输出总结
            print("\n" + "=" * 80)
            print("🎉 Phase 3 基线模型训练完成!")
            print(
                f"📊 模型准确率: {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)"
            )
            print(f"📊 对数损失: {results['logloss']:.4f}")
            print("=" * 80)

            return {"accuracy": results["accuracy"], "logloss": results["logloss"]}

        except Exception as e:
            logger.error(f"❌ 训练流程失败: {e}")
            raise


def main():
    """主函数 - 运行基线模型训练"""
    logging.basicConfig(
        level=logging.INFO,
        format="🧠 %(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("🚀 Phase 3 基线模型训练系统启动")

    try:
        trainer = BaselineTrainer()
        metrics = trainer.run_training(
            train_end_date="2025-10-01", save_results=True  # 调整为合适的时间切分
        )

        logger.info("🎯 训练任务成功完成!")
        return metrics

    except Exception as e:
        logger.error(f"❌ 训练任务失败: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
