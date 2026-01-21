#!/usr/bin/env python3
"""
V41.300 "Pilot Algorithm" - XGBoost 1X2 预测模型训练器
==========================================================

核心任务: 训练第一个简单的预测模型，验证 599 维特征对预测准确率的贡献。

训练流程:
    1. 加载特征矩阵和标签向量
    2. 划分训练集/测试集 (80/20)
    3. 使用 XGBoost 训练多分类模型
    4. 评估准确率、精确率、召回率、F1 分数
    5. 输出 Top 5 重要特征

输出规格:
    - Baseline Accuracy: [X%]
    - Top 5 Important Features: [特征列表]
    - Confusion Matrix: [混淆矩阵]

Author: Senior ML Engineer
Version: V41.300 (Pilot Algorithm - Model Training)
Date: 2026-01-21
"""

# ============================================================================
# 标准库导入
# ============================================================================
import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# 第三方库导入
# ============================================================================
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
import xgboost as xgb
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# V41.300 训练结果数据类
# ============================================================================


@dataclass
class TrainingResult:
    """V41.300 训练结果"""

    # 模型
    model: xgb.XGBClassifier

    # 数据集信息
    n_samples: int
    n_features: int
    n_train: int
    n_test: int

    # 训练指标
    train_accuracy: float
    test_accuracy: float
    cv_accuracy_mean: float
    cv_accuracy_std: float

    # 详细分类指标
    precision_h: float
    precision_d: float
    precision_a: float
    recall_h: float
    recall_d: float
    recall_a: float
    f1_h: float
    f1_d: float
    f1_a: float
    f1_macro: float

    # 特征重要性
    feature_importance: pd.DataFrame

    # 混淆矩阵
    confusion_matrix: np.ndarray

    # 训练时间
    training_time_ms: float

    def get_top_features(self, n: int = 5) -> list[tuple[str, float]]:
        """获取 Top N 重要特征"""
        return self.feature_importance.head(n).to_records(index=False).tolist()

    def __str__(self) -> str:
        top5 = self.get_top_features(5)
        top5_str = "\n    ".join([f"{i+1}. {name} ({score:.4f})" for i, (name, score) in enumerate(top5)])

        return (
            f"V41.300 XGBoost 训练报告:\n"
            f"  数据集: {self.n_samples} 样本, {self.n_features} 特征\n"
            f"  训练集: {self.n_train} 样本 | 测试集: {self.n_test} 样本\n"
            f"\n"
            f"  模型性能:\n"
            f"    训练准确率: {self.train_accuracy:.4f}\n"
            f"    测试准确率: {self.test_accuracy:.4f}\n"
            f"    5折交叉验证: {self.cv_accuracy_mean:.4f} (+/- {self.cv_accuracy_std:.4f})\n"
            f"\n"
            f"  分类报告 (F1-Score):\n"
            f"    主胜 (H): {self.f1_h:.4f}\n"
            f"    平局 (D): {self.f1_d:.4f}\n"
            f"    客胜 (A): {self.f1_a:.4f}\n"
            f"    宏平均: {self.f1_macro:.4f}\n"
            f"\n"
            f"  Top 5 重要特征:\n"
            f"    {top5_str}\n"
            f"\n"
            f"  训练耗时: {self.training_time_ms:.0f}ms"
        )


# ============================================================================
# V41.300 XGBoost 训练器
# ============================================================================


class PilotXGBoostTrainer:
    """
    V41.300 XGBoost 模型训练器

    核心功能:
        1. 加载特征和标签
        2. 训练 XGBoost 多分类模型
        3. 评估模型性能
        4. 输出特征重要性
    """

    # XGBoost 默认参数
    DEFAULT_PARAMS = {
        "objective": "multi:softprob",  # 多分类概率输出
        "num_class": 3,  # 3 类 (H/D/A)
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "random_state": 42,
        "eval_metric": "mlogloss",
        "early_stopping_rounds": 20,
    }

    def __init__(
        self,
        data_dir: str | Path = "data/pilot_v41_300",
        test_size: float = 0.2,
        random_state: int = 42,
        xgb_params: dict | None = None,
    ):
        """
        初始化训练器

        Args:
            data_dir: 数据目录
            test_size: 测试集比例
            random_state: 随机种子
            xgb_params: XGBoost 参数
        """
        self.data_dir = Path(data_dir)
        self.test_size = test_size
        self.random_state = random_state

        # 合并参数
        self.xgb_params = {**self.DEFAULT_PARAMS}
        if xgb_params:
            self.xgb_params.update(xgb_params)

        logger.info(
            "V41.300 XGBoost 训练器初始化完成",
            data_dir=str(self.data_dir),
            test_size=test_size,
        )

    def load_data(self) -> tuple[np.ndarray, np.ndarray, list[str], pd.DataFrame]:
        """
        加载训练数据

        Returns:
            (X, y, feature_names, metadata)
        """
        logger.info("加载训练数据...")

        # 加载特征矩阵
        X_path = self.data_dir / "X_features.npy"
        y_path = self.data_dir / "y_labels.npy"
        fn_path = self.data_dir / "feature_names.json"
        md_path = self.data_dir / "metadata.csv"

        if not all([X_path.exists(), y_path.exists(), fn_path.exists(), md_path.exists()]):
            raise FileNotFoundError(f"数据文件缺失，请先运行特征提取器")

        X = np.load(X_path)
        y = np.load(y_path)

        with open(fn_path) as f:
            feature_names = json.load(f)

        metadata = pd.read_csv(md_path)

        logger.info(
            "数据加载完成",
            X_shape=X.shape,
            y_shape=y.shape,
            n_features=len(feature_names),
        )

        return X, y, feature_names, metadata

    def train(self) -> TrainingResult:
        """
        执行训练流程

        Returns:
            TrainingResult
        """
        start_time = datetime.now()

        # Step 1: 加载数据
        logger.info("Step 1/4: 加载数据")
        X, y, feature_names, metadata = self.load_data()

        # Step 2: 划分训练集和测试集
        logger.info("Step 2/4: 划分训练集/测试集")
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y,  # 分层采样，保持标签分布一致
        )

        logger.info(
            "数据集划分完成",
            n_train=len(X_train),
            n_test=len(X_test),
            train_distribution=f"H={sum(y_train==0)}, D={sum(y_train==1)}, A={sum(y_train==2)}",
            test_distribution=f"H={sum(y_test==0)}, D={sum(y_test==1)}, A={sum(y_test==2)}",
        )

        # Step 3: 训练模型
        logger.info("Step 3/4: 训练 XGBoost 模型")

        # 移除 early_stopping_rounds 用于 fit() (使用 eval_set)
        fit_params = self.xgb_params.copy()
        fit_params.pop("early_stopping_rounds", None)

        model = xgb.XGBClassifier(**fit_params)

        # 训练模型
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # Step 4: 评估模型
        logger.info("Step 4/4: 评估模型")

        # 预测
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)

        # 准确率
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)

        # 交叉验证
        logger.info("执行 5 折交叉验证...")
        cv_scores = cross_val_score(
            model,
            X,
            y,
            cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state),
            scoring="accuracy",
        )
        cv_accuracy_mean = cv_scores.mean()
        cv_accuracy_std = cv_scores.std()

        # 详细分类报告
        report = classification_report(
            y_test,
            y_test_pred,
            target_names=["H", "D", "A"],
            output_dict=True,
            zero_division=0,
        )

        # 特征重要性
        importance = model.feature_importances_
        feature_importance = pd.DataFrame({
            "feature": feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)

        # 混淆矩阵
        cm = confusion_matrix(y_test, y_test_pred)

        # 训练时间
        training_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # 构建结果
        result = TrainingResult(
            model=model,
            n_samples=len(X),
            n_features=X.shape[1],
            n_train=len(X_train),
            n_test=len(X_test),
            train_accuracy=train_accuracy,
            test_accuracy=test_accuracy,
            cv_accuracy_mean=cv_accuracy_mean,
            cv_accuracy_std=cv_accuracy_std,
            precision_h=report["H"]["precision"],
            precision_d=report["D"]["precision"],
            precision_a=report["A"]["precision"],
            recall_h=report["H"]["recall"],
            recall_d=report["D"]["recall"],
            recall_a=report["A"]["recall"],
            f1_h=report["H"]["f1-score"],
            f1_d=report["D"]["f1-score"],
            f1_a=report["A"]["f1-score"],
            f1_macro=report["macro avg"]["f1-score"],
            feature_importance=feature_importance,
            confusion_matrix=cm,
            training_time_ms=training_time_ms,
        )

        logger.info(
            "V41.300 训练完成",
            test_accuracy=test_accuracy,
            cv_accuracy_mean=cv_accuracy_mean,
            training_time_ms=f"{training_time_ms:.0f}",
        )

        return result

    def save_model(self, result: TrainingResult, output_dir: str | Path) -> None:
        """
        保存模型和结果

        Args:
            result: 训练结果
            output_dir: 输出目录
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存模型 (使用 booster.save_model() 避免版本问题)
        model_path = output_dir / "xgboost_model.json"
        result.model.get_booster().save_model(str(model_path))

        # 保存特征重要性
        importance_path = output_dir / "feature_importance.csv"
        result.feature_importance.to_csv(importance_path, index=False)

        # 保存训练报告
        report = {
            "n_samples": result.n_samples,
            "n_features": result.n_features,
            "n_train": result.n_train,
            "n_test": result.n_test,
            "train_accuracy": result.train_accuracy,
            "test_accuracy": result.test_accuracy,
            "cv_accuracy_mean": result.cv_accuracy_mean,
            "cv_accuracy_std": result.cv_accuracy_std,
            "precision_h": result.precision_h,
            "precision_d": result.precision_d,
            "precision_a": result.precision_a,
            "recall_h": result.recall_h,
            "recall_d": result.recall_d,
            "recall_a": result.recall_a,
            "f1_h": result.f1_h,
            "f1_d": result.f1_d,
            "f1_a": result.f1_a,
            "f1_macro": result.f1_macro,
            "top5_features": [
                {"name": name, "importance": float(score)}
                for name, score in result.get_top_features(5)
            ],
            "confusion_matrix": result.confusion_matrix.tolist(),
            "training_time_ms": result.training_time_ms,
        }

        report_path = output_dir / "training_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(
            "模型保存完成",
            model_path=str(model_path),
            report_path=str(report_path),
        )


# ============================================================================
# 命令行入口
# ============================================================================


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V41.300 XGBoost 1X2 预测模型训练器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认参数训练
  python scripts/ai/v41_300_xgboost_trainer.py

  # 自定义测试集比例
  python scripts/ai/v41_300_xgboost_trainer.py --test-size 0.3

  # 调整 XGBoost 参数
  python scripts/ai/v41_300_xgboost_trainer.py --max-depth 8 --n-estimators 300 --learning-rate 0.05

  # 指定数据目录
  python scripts/ai/v41_300_xgboost_trainer.py --data-dir data/pilot_v41_300

  # 指定输出目录
  python scripts/ai/v41_300_xgboost_trainer.py --output models/pilot_v1
        """,
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/pilot_v41_300",
        help="数据目录 (默认: data/pilot_v41_300)",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="测试集比例 (默认: 0.2)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="XGBoost max_depth (默认: 6)",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=200,
        help="XGBoost n_estimators (默认: 200)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.1,
        help="XGBoost learning_rate (默认: 0.1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/pilot_v41_300",
        help="输出目录 (默认: models/pilot_v41_300)",
    )

    args = parser.parse_args()

    # 自定义 XGBoost 参数
    xgb_params = {
        "max_depth": args.max_depth,
        "n_estimators": args.n_estimators,
        "learning_rate": args.learning_rate,
    }

    # 执行训练
    trainer = PilotXGBoostTrainer(
        data_dir=args.data_dir,
        test_size=args.test_size,
        xgb_params=xgb_params,
    )

    result = trainer.train()

    # 输出报告
    print("\n" + "=" * 60)
    print("V41.300 Pilot XGBoost 训练报告")
    print("=" * 60)
    print(result)
    print("=" * 60)

    # 输出混淆矩阵
    print("\n混淆矩阵:")
    print("         预测 H   预测 D   预测 A")
    print(f"实际 H    {result.confusion_matrix[0][0]:4d}    {result.confusion_matrix[0][1]:4d}    {result.confusion_matrix[0][2]:4d}")
    print(f"实际 D    {result.confusion_matrix[1][0]:4d}    {result.confusion_matrix[1][1]:4d}    {result.confusion_matrix[1][2]:4d}")
    print(f"实际 A    {result.confusion_matrix[2][0]:4d}    {result.confusion_matrix[2][1]:4d}    {result.confusion_matrix[2][2]:4d}")
    print("=" * 60)

    # 保存模型
    trainer.save_model(result, args.output)
    print(f"\n模型已保存到: {args.output}/")
    print(f"  - xgboost_model.json: XGBoost 模型文件")
    print(f"  - feature_importance.csv: 特征重要性")
    print(f"  - training_report.json: 训练报告")
    print("\n🎉 V41.300 Pilot 算法完成！")


if __name__ == "__main__":
    main()
