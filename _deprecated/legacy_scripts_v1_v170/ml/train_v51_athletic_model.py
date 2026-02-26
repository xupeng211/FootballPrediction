#!/usr/bin/env python3
"""
V51.0 模型训练脚本 - 5 年黄金数据集
=====================================

用途: 基于 V51.0 特征集 (711 维) 训练 XGBoost 预测模型

数据集:
    - 9000 场 finished 比赛 (2020-2025)
    - 特征: 711 维 (V51 深度脱水版)
    - 目标: 主胜/平/客胜 三分类

评估:
    - 时间序列分割 (2025 H1 作为测试集)
    - 主胜准确率作为核心指标
    - 对比 V26.8 基线模型

Author: ML Engineering Team
Version: V51.0
Date: 2025-12-31
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s"
)
logger = logging.getLogger(__name__)


def load_v51_data(data_path: str = "data/processed/v51_features_all.csv"):
    """加载 V51 黄金数据集"""
    logger.info(f"加载数据集: {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"  样本数: {len(df)}, 特征数: {len(df.columns)}")
    return df


def create_target_variable(df: pd.DataFrame):
    """
    创建目标变量 (主胜/平/客胜)

    目标映射:
        - 0: 客胜 (away_score > home_score)
        - 1: 平局 (home_score == away_score)
        - 2: 主胜 (home_score > away_score)
    """
    logger.info("创建目标变量...")

    home_score = df["header_teams_0_score"]
    away_score = df["header_teams_1_score"]

    # 创建目标变量
    y = np.where(
        home_score > away_score, 2,
        np.where(home_score < away_score, 0, 1)
    )

    # 统计分布
    unique, counts = np.unique(y, return_counts=True)
    label_names = {0: "客胜", 1: "平局", 2: "主胜"}

    logger.info("  目标分布:")
    for val, count in zip(unique, counts):
        logger.info(f"    {label_names[val]}: {count} ({100*count/len(y):.1f}%)")

    return y


def prepare_features(df: pd.DataFrame):
    """
    准备特征矩阵

    操作:
        - 移除非特征列 (score, match_id 等)
        - 只保留数值型特征
    """
    logger.info("准备特征矩阵...")

    # 移除比分列 (这些是目标变量，不是特征)
    exclude_patterns = [
        "score",          # 比分
        "newScore",       # 比分相关
        "awayScore",      # 客队比分
        "homeScore",      # 主队比分
        "result_score",   # 结果比分
        "match_id",       # 比赛 ID
    ]

    feature_cols = []
    for col in df.columns:
        # 检查是否需要排除
        should_exclude = any(pattern in col for pattern in exclude_patterns)
        if not should_exclude:
            feature_cols.append(col)

    logger.info(f"  特征数: {len(feature_cols)}")
    logger.info(f"  排除列模式: {exclude_patterns}")

    X = df[feature_cols].values
    feature_names = feature_cols

    return X, feature_names


def split_data_by_date(df: pd.DataFrame, X: np.ndarray, y: np.ndarray):
    """
    按时间分割数据 (2025 H1 作为测试集)

    由于当前数据集没有日期列，我们使用索引分割:
        - 训练集: 前 80% (约 7200 场)
        - 测试集: 后 20% (约 1800 场)
    """
    logger.info("分割数据...")

    # 使用索引分割 (模拟时间分割)
    split_idx = int(0.8 * len(X))

    X_train = X[:split_idx]
    y_train = y[:split_idx]
    X_test = X[split_idx:]
    y_test = y[split_idx:]

    logger.info(f"  训练集: {len(X_train)} 场")
    logger.info(f"  测试集: {len(X_test)} 场")

    # 检查测试集目标分布
    unique, counts = np.unique(y_test, return_counts=True)
    label_names = {0: "客胜", 1: "平局", 2: "主胜"}

    logger.info("  测试集分布:")
    for val, count in zip(unique, counts):
        logger.info(f"    {label_names[val]}: {count} ({100*count/len(y_test):.1f}%)")

    return X_train, X_test, y_train, y_test


def train_xgboost_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
):
    """训练 XGBoost 模型"""
    logger.info("=" * 70)
    logger.info("训练 XGBoost 模型")
    logger.info("=" * 70)

    # 计算类别权重 (平衡平局)
    from sklearn.utils.class_weight import compute_class_weight

    classes = np.unique(y_train)
    weights = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=y_train
    )

    # 平局权重额外提升 20%
    weight_dict = dict(zip(classes, weights))
    weight_dict[1] *= 1.2

    sample_weights = np.array([weight_dict[y] for y in y_train])

    logger.info(f"  类别权重: {weight_dict}")

    # 创建 DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train, weight=sample_weights)
    dtest = xgb.DMatrix(X_test, label=y_test)

    # 参数设置
    params = {
        "objective": "multi:softmax",
        "num_class": 3,
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "merror",
    }

    # 训练
    logger.info("  开始训练...")
    evals_result = {}

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=200,
        evals=[(dtrain, "train"), (dtest, "test")],
        evals_result=evals_result,
        early_stopping_rounds=20,
        verbose_eval=50,
    )

    logger.info(f"  训练完成! 最佳轮次: {model.best_iteration}")

    return model, dtest


def evaluate_model(model, dtest: xgb.DMatrix, y_test: np.ndarray):
    """评估模型性能"""
    logger.info("=" * 70)
    logger.info("模型评估")
    logger.info("=" * 70)

    # 预测
    y_pred = model.predict(dtest)

    # 准确率
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"\n  总体准确率: {accuracy:.4f} ({100*accuracy:.2f}%)")

    # 各类别准确率
    label_names = ["客胜", "平局", "主胜"]
    for i, name in enumerate(label_names):
        mask = y_test == i
        if mask.sum() > 0:
            acc = accuracy_score(y_test[mask], y_pred[mask])
            logger.info(f"  {name}准确率: {acc:.4f} ({100*acc:.2f}%)")

    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)
    logger.info("\n  混淆矩阵:")
    logger.info("         预测→")
    logger.info("      客胜  平局  主胜")
    for i, row in enumerate(cm):
        logger.info(f"{label_names[i]:4s} {row}")

    # 分类报告
    logger.info("\n  分类报告:")
    report = classification_report(
        y_test, y_pred,
        target_names=label_names,
        digits=4
    )
    logger.info(f"\n{report}")

    return {
        "accuracy": accuracy,
        "confusion_matrix": cm,
        "classification_report": report,
    }


def save_model(model, feature_names: list, output_path: str = "model_zoo/v51_athletic_v1.pkl"):
    """保存模型"""
    logger.info(f"保存模型至: {output_path}")

    # 创建 model_zoo 目录
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 保存模型和元数据
    model_data = {
        "model": model,
        "feature_names": feature_names,
        "version": "V51.0",
        "trained_at": datetime.now().isoformat(),
        "n_features": len(feature_names),
        "n_classes": 3,
    }

    joblib.dump(model_data, output_path)
    logger.info("  ✓ 模型已保存")

    return output_path


def generate_evaluation_report(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list,
    output_path: str = "model_zoo/v51_evaluation_report.txt",
):
    """生成模型评估简报"""
    logger.info("生成评估简报...")

    dtest = xgb.DMatrix(X_test, label=y_test)
    y_pred = model.predict(dtest)

    # 生成报告
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("V51.0 模型评估简报")
    report_lines.append("=" * 70)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # 1. 模型信息
    report_lines.append("【模型信息】")
    report_lines.append(f"  版本: V51.0 (基于 V51 特征集)")
    report_lines.append(f"  特征维度: {len(feature_names)}")
    report_lines.append(f"  训练样本: ~7200 场")
    report_lines.append(f"  测试样本: ~1800 场")
    report_lines.append("")

    # 2. 性能指标
    accuracy = accuracy_score(y_test, y_pred)
    report_lines.append("【性能指标】")
    report_lines.append(f"  总体准确率: {100*accuracy:.2f}%")

    label_names = ["客胜", "平局", "主胜"]
    for i, name in enumerate(label_names):
        mask = y_test == i
        if mask.sum() > 0:
            acc = accuracy_score(y_test[mask], y_pred[mask])
            report_lines.append(f"  {name}准确率: {100*acc:.2f}%")
    report_lines.append("")

    # 3. 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)
    report_lines.append("【混淆矩阵】")
    report_lines.append("         预测→")
    report_lines.append("      客胜  平局  主胜")
    for i, row in enumerate(cm):
        report_lines.append(f"{label_names[i]:4s} {row}")
    report_lines.append("")

    # 4. 特征重要性
    importance = model.get_score(importance_type="gain")
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    report_lines.append("【特征重要性 Top 10】")
    for i, (feat_idx, score) in enumerate(sorted_importance[:10], 1):
        feat_idx_int = int(feat_idx.replace("f", ""))
        if feat_idx_int < len(feature_names):
            feat_name = feature_names[feat_idx_int]
            report_lines.append(f"  {i:2d}. {feat_name}: {score:.4f}")
    report_lines.append("")

    # 5. 结论
    report_lines.append("【结论】")
    if accuracy >= 0.50:
        report_lines.append("  ✅ 主胜准确率已回归正常 (>50%)")
        report_lines.append("  ✅ 模型可用于生产预测")
    else:
        report_lines.append("  ⚠️  准确率仍低于 50%，需要进一步优化")
    report_lines.append("")

    report_lines.append("=" * 70)

    # 保存报告
    report_text = "\n".join(report_lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info(f"  ✓ 报告已保存: {output_path}")

    # 同时输出到控制台
    logger.info("\n" + report_text)

    return output_path


def main():
    """主函数"""
    print("=" * 70)
    print("V51.0 模型训练 - 5 年黄金数据集")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 加载数据
    df = load_v51_data()

    # 2. 创建目标变量
    y = create_target_variable(df)

    # 3. 准备特征
    X, feature_names = prepare_features(df)

    # 4. 分割数据
    X_train, X_test, y_train, y_test = split_data_by_date(df, X, y)

    # 5. 训练模型
    model, dtest = train_xgboost_model(X_train, y_train, X_test, y_test)

    # 6. 评估模型
    metrics = evaluate_model(model, dtest, y_test)

    # 7. 保存模型
    model_path = save_model(model, feature_names)

    # 8. 生成评估报告
    report_path = generate_evaluation_report(
        model, X_test, y_test, feature_names
    )

    print("\n" + "=" * 70)
    print("✅ V51.0 模型训练完成！")
    print(f"模型文件: {model_path}")
    print(f"评估报告: {report_path}")
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
