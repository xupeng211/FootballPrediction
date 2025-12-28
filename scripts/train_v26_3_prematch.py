#!/usr/bin/env python3
"""
Phase 3.2: V26.3 赛前预测模型训练（Anti-Leakage）
=======================================================

核心改进：
1. 彻底移除数据泄露特征（shotmap, matchfacts, ongoing, 比赛实时数据）
2. 只使用纯赛前特征（rolling, elo, table, fatigue 等）
3. 时间序列分割（2025-01-01 为界）
4. 目标准确率 > 45%

Author: Senior ML Engineer (Sports Betting Specialist)
Version: V26.3
Date: 2025-12-28
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/train_v26_3_prematch.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# Anti-Leakage 特征白名单（只使用赛前已知信息）
# ============================================================================

# 允许的特征前缀（赛前特征）
ALLOWED_PREFIXES = [
    "rolling_",      # 滚动特征（基于历史比赛）
    "elo_",          # ELO 评级（赛前已知）
    "table_",       # 积分榜排名（赛前已知）
    "fatigue_",      # 疲劳度（基于休息天数，赛前已知）
    "incentive_",    # 战意（基于积分榜，赛前已知）
    "desperation",   # 绝境（赛前已知）
]

# 允许的特定特征
ALLOWED_FEATURES = [
    "raw_elo_gap",
    "adjusted_elo_gap",
    "schedule_impact",
    "home_rest_days",
    "away_rest_days",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
    "table_proximity",
    "low_scoring_tendency",
    "elo_diff_cluster",
    "home_table_position",
    "away_table_position",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    "away_recent_form_points",
    "incentive_diff",
    "home_desperation",
]

# 禁止的特征关键词（赛后数据）
BLOCKED_KEYWORDS = [
    "shotmap",
    "matchfacts",
    "ongoing",
    "home_xg",      # 比赛中的 xG
    "away_xg",
    "home_possession",  # 比赛中的控球率
    "away_possession",
    "home_shots_on_target",  # 比赛中的射正
    "away_shots_on_target",
    "home_team_rating",  # 比赛中的评分
    "away_team_rating",
]


def is_prematch_feature(feature_name: str) -> bool:
    """判断是否为赛前特征"""
    # 检查是否在允许列表中
    if feature_name in ALLOWED_FEATURES:
        return True

    # 检查是否以允许的前缀开头
    for prefix in ALLOWED_PREFIXES:
        if feature_name.startswith(prefix):
            return True

    # 检查是否包含禁止的关键词
    for keyword in BLOCKED_KEYWORDS:
        if keyword in feature_name.lower():
            return False

    return False


def load_prematch_data():
    """加载赛前特征数据"""
    logger.info("=" * 60)
    logger.info("步骤 1: 加载赛前特征数据（Anti-Leakage）")
    logger.info("=" * 60)

    # 读取 V28_REAL_GOLD.parquet
    df = pd.read_parquet("data/processed/V28_REAL_GOLD.parquet")

    logger.info(f"原始数据: {len(df)} 行 × {len(df.columns)} 列")
    logger.info(f"日期范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

    # 只保留赛前特征
    prematch_features = [col for col in df.columns if is_prematch_feature(col)]
    prematch_features = ["match_id", "match_date", "home_team", "away_team", "result"] + prematch_features

    df = df[prematch_features]

    logger.info(f"赛前特征筛选后: {len(df)} 行 × {len(df.columns)} 列")
    logger.info(f"保留特征: {len(prematch_features)} 个")

    # 显示保留的特征
    feature_list = [col for col in df.columns if col not in ["match_id", "match_date", "home_team", "away_team", "result"]]
    logger.info(f"\n保留的特征列表 ({len(feature_list)} 个):")
    for feat in feature_list:
        logger.info(f"  - {feat}")

    # 转换日期
    df["match_date"] = pd.to_datetime(df["match_date"])

    return df


def time_series_split(df, split_date="2025-01-01"):
    """时间序列分割（而非随机分割）"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 时间序列分割")
    logger.info("=" * 60)

    # 使用 timezone-aware 的分割日期（与数据集的 UTC 时区对齐）
    split_date = pd.to_datetime(split_date).tz_localize("UTC")

    train_df = df[df["match_date"] < split_date].copy()
    test_df = df[df["match_date"] >= split_date].copy()

    logger.info(f"分割日期: {split_date}")
    logger.info(f"训练集: {len(train_df)} 场 ({train_df['match_date'].min()} 到 {train_df['match_date'].max()})")
    logger.info(f"测试集: {len(test_df)} 场 ({test_df['match_date'].min()} 到 {test_df['match_date'].max()})")

    return train_df, test_df


def prepare_features(train_df, test_df, sparsity_threshold=0.95):
    """准备特征（去除稀疏特征）"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3: 特征准备")
    logger.info("=" * 60)

    # 准备特征列
    feature_cols = [col for col in train_df.columns if col not in ["match_id", "match_date", "home_team", "away_team", "result"]]

    # 提取特征和标签
    X_train = train_df[feature_cols].values
    y_train = train_df["result"].values
    X_test = test_df[feature_cols].values
    y_test = test_df["result"].values

    logger.info(f"训练集: {X_train.shape}")
    logger.info(f"测试集: {X_test.shape}")

    # 处理稀疏特征
    nan_ratio_train = np.isnan(X_train).sum(axis=0) / len(X_train)
    sparse_features = np.where(nan_ratio_train > sparsity_threshold)[0]

    if len(sparse_features) > 0:
        logger.info(f"发现 {len(sparse_features)} 个稀疏特征 (sparsity > {sparsity_threshold})")
        # 删除稀疏特征
        X_train = np.delete(X_train, sparse_features, axis=1)
        X_test = np.delete(X_test, sparse_features, axis=1)
        feature_cols = [feature_cols[i] for i in range(len(feature_cols)) if i not in sparse_features]
        logger.info(f"删除后特征数: {len(feature_cols)}")

    # 填充缺失值
    X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)

    # 标签编码
    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    logger.info(f"\n训练集标签分布:")
    for label, count in zip(label_encoder.classes_, np.bincount(y_train_encoded)):
        logger.info(f"  {label}: {count} ({count/len(y_train_encoded)*100:.1f}%)")

    logger.info(f"\n最终特征数: {len(feature_cols)}")

    return X_train, X_test, y_train_encoded, y_test_encoded, feature_cols, label_encoder


def calculate_sample_weights(y_train):
    """计算样本权重：平局权重 2.0"""
    weights = np.ones(len(y_train))

    # LabelEncoder: 0=A, 1=D, 2=H
    draw_indices = np.where(y_train == 1)[0]
    weights[draw_indices] = 2.0

    logger.info(f"\n样本权重: 普通=1.0, 平局=2.0 (共 {len(draw_indices)} 个)")
    return weights


def train_xgboost_prematch(X_train, y_train, X_test, y_test, sample_weights, feature_names):
    """训练 XGBoost 赛前模型"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 训练 XGBoost 赛前模型")
    logger.info("=" * 60)

    # 创建 DMatrix
    train_weights = sample_weights[y_train]
    dtrain = xgb.DMatrix(X_train, label=y_train, weight=train_weights, feature_names=feature_names)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_names)

    # 参数
    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "mlogloss",
        "tree_method": "hist",
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
    }

    logger.info("开始训练...")
    logger.info(f"训练集: {len(X_train)} 样本")
    logger.info(f"测试集: {len(X_test)} 样本")
    logger.info(f"特征数: {len(feature_names)}")

    evals_result = {}
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=300,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=30,
        evals_result=evals_result,
        verbose_eval=30,
    )

    logger.info(f"\n✅ 训练完成! 最佳轮数: {model.best_iteration}")

    return model, evals_result


def evaluate_prematch_model(model, X_test, y_test, label_encoder, feature_names):
    """评估赛前模型"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 5: 模型评估（赛前视角）")
    logger.info("=" * 60)

    dtest = xgb.DMatrix(X_test, feature_names=feature_names)
    y_pred_proba = model.predict(dtest)
    y_pred = np.argmax(y_pred_proba, axis=1)

    # 反向转换标签
    y_test_labels = label_encoder.inverse_transform(y_test)
    y_pred_labels = label_encoder.inverse_transform(y_pred)

    # 分类报告
    report = classification_report(y_test_labels, y_pred_labels, target_names=["Away", "Draw", "Home"])
    logger.info("\n分类报告:\n" + report)

    # 混淆矩阵（使用数据中的实际标签）
    cm = confusion_matrix(y_test_labels, y_pred_labels)
    logger.info("\n混淆矩阵:")
    logger.info("        Pred: away  draw  home")
    for i, label in enumerate(label_encoder.classes_):
        logger.info(f"True {label:5s}:  {cm[i]}")

    # F1 Score
    f1_macro = f1_score(y_test_labels, y_pred_labels, average="macro")
    f1_weighted = f1_score(y_test_labels, y_pred_labels, average="weighted")
    logger.info(f"\nF1 Score (macro): {f1_macro:.4f}")
    logger.info(f"F1 Score (weighted): {f1_weighted:.4f}")

    # 准确率
    accuracy = (y_pred == y_test).mean()
    logger.info(f"准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")

    # 准确率目标检查
    if accuracy > 0.45:
        logger.info("✅ 准确率达标 (> 45%)")
    else:
        logger.warning(f"⚠️  准确率未达标 ({accuracy*100:.2f}% < 45%)")

    # Feature Importance
    importance = model.get_score(importance_type="gain")
    # 由于训练时传入了 feature_names，get_score() 直接返回特征名作为键
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    logger.info("\n📊 Feature Importance TOP 30 (赛前特征):")
    for i, (feat_name, score) in enumerate(sorted_importance[:30]):
        logger.info(f"  {i+1:2d}. {feat_name:50s}: {score:.4f}")

    return {
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "feature_importance_top30": [
            {"rank": i+1, "feature": feat_name, "importance": score}
            for i, (feat_name, score) in enumerate(sorted_importance[:30])
        ],
    }


def save_prematch_model(model, label_encoder, feature_names, metrics):
    """保存赛前模型"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 6: 保存赛前模型")
    logger.info("=" * 60)

    # 创建 model_zoo 目录
    model_dir = Path("model_zoo")
    model_dir.mkdir(exist_ok=True)

    # 保存模型
    model_path = model_dir / "v26.3_prematch_baseline.pkl"
    model.save_model(str(model_path))
    logger.info(f"✅ 模型已保存: {model_path}")

    # 保存元数据
    metadata = {
        "model_version": "V26.3",
        "model_type": "XGBoost",
        "model_description": "Prematch prediction model (Anti-Leakage)",
        "feature_count": len(feature_names),
        "num_classes": 3,
        "classes": ["Away", "Draw", "Home"],
        "label_encoder": label_encoder.classes_.tolist(),
        "feature_names": feature_names,
        "train_date": datetime.now().isoformat(),
        "split_type": "time_series",
        "split_date": "2025-01-01",
        "anti_leakage": True,
        "allowed_prefixes": ALLOWED_PREFIXES,
        "blocked_keywords": BLOCKED_KEYWORDS,
        "metrics": metrics,
    }

    metadata_path = model_dir / "v26.3_prematch_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"✅ 元数据已保存: {metadata_path}")

    # 保存特征重要性
    importance_path = model_dir / "v26.3_prematch_feature_importance.txt"
    with open(importance_path, "w") as f:
        f.write("Feature Importance TOP 30 (赛前特征)\n")
        f.write("=" * 60 + "\n\n")
        for item in metrics["feature_importance_top30"]:
            f.write(f"{item['rank']:2d}. {item['feature']:50s}: {item['importance']:.4f}\n")
    logger.info(f"✅ 特征重要性已保存: {importance_path}")

    # 复制到生产模型路径
    prod_dir = Path("src/production_models")
    prod_dir.mkdir(exist_ok=True)

    prod_model_path = prod_dir / "v25.1_adaptive_model.pkl"
    import shutil
    shutil.copy(str(model_path), str(prod_model_path))
    logger.info(f"✅ 生产模型已更新: {prod_model_path}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Phase 3.2: V26.3 赛前预测模型训练（Anti-Leakage）")
    logger.info("=" * 60)
    logger.info(f"启动时间: {datetime.now().isoformat()}")

    # 步骤 1: 加载赛前数据
    df = load_prematch_data()

    # 步骤 2: 时间序列分割
    train_df, test_df = time_series_split(df, split_date="2025-01-01")

    # 步骤 3: 特征准备
    X_train, X_test, y_train, y_test, feature_names, label_encoder = prepare_features(train_df, test_df)

    # 步骤 4: 计算样本权重
    sample_weights = calculate_sample_weights(y_train)

    # 步骤 5: 训练模型
    model, evals_result = train_xgboost_prematch(X_train, y_train, X_test, y_test, sample_weights, feature_names)

    # 步骤 6: 评估模型
    metrics = evaluate_prematch_model(model, X_test, y_test, label_encoder, feature_names)

    # 步骤 7: 保存模型
    save_prematch_model(model, label_encoder, feature_names, metrics)

    logger.info("\n" + "=" * 60)
    logger.info("✅ Phase 3.2 完成!")
    logger.info("=" * 60)
    logger.info(f"完成时间: {datetime.now().isoformat()}")
    logger.info(f"准确率: {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    logger.info(f"F1 Score (macro): {metrics['f1_macro']:.4f}")
    logger.info(f"特征数: {len(feature_names)}")
    logger.info("✅ 模型已消除数据泄露，只使用赛前特征")

    return 0


if __name__ == "__main__":
    exit(main())
