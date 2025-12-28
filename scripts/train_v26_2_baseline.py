#!/usr/bin/env python3
"""
Phase 3.1: V26.2 预测模型训练
==============================

基于真实高维特征训练 XGBoost 2.0 生产模型。

Features:
- 从 raw_match_data 提取 5000+ 维特征
- 处理稀疏列和异常值
- 平局样本权重 2.0
- 生成 Feature Importance TOP 50

Author: Senior ML Engineer
Version: V26.2
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
import psycopg2
from psycopg2.extras import RealDictCursor
from scipy import stats
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.processors.v25_production_extractor import V25ProductionExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/train_v26_2_baseline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def extract_result_from_raw(raw_data: dict) -> str | None:
    """从原始 JSON 中提取比赛结果"""
    try:
        # 方法 1: 从 header.teams 获取比分
        header = raw_data.get("header", {})
        teams = header.get("teams", [])

        if len(teams) >= 2:
            home_score = teams[0].get("score")
            away_score = teams[1].get("score")

            if home_score is not None and away_score is not None:
                if home_score > away_score:
                    return "H"
                elif home_score < away_score:
                    return "A"
                else:
                    return "D"

        # 方法 2: 从 match.status 获取比分
        match_status = raw_data.get("match", {}).get("status", {})
        home_score = match_status.get("homeScore")
        away_score = match_status.get("awayScore")

        if home_score is not None and away_score is not None:
            if home_score > away_score:
                return "H"
            elif home_score < away_score:
                return "A"
            else:
                return "D"

        return None
    except Exception as e:
        logger.warning(f"提取结果失败: {e}")
        return None


def load_training_data_from_db():
    """从数据库加载训练数据"""
    logger.info("=" * 60)
    logger.info("步骤 1: 加载训练数据")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 获取所有 raw_match_data
    cur.execute("""
        SELECT external_id, raw_data
        FROM raw_match_data
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    logger.info(f"找到 {len(rows)} 条原始数据")

    cur.close()
    conn.close()

    return rows


def extract_features_and_labels(raw_rows):
    """提取特征和标签"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 提取特征和标签")
    logger.info("=" * 60)

    extractor = V25ProductionExtractor()

    features_list = []
    labels_list = []
    match_ids = []

    for i, row in enumerate(raw_rows):
        external_id = row["external_id"]
        raw_data = row["raw_data"]

        # 提取结果
        result = extract_result_from_raw(raw_data)
        if result is None:
            logger.debug(f"Match {external_id}: 无结果，跳过")
            continue

        # 提取特征
        extraction_result = extractor.extract(raw_data)
        if extraction_result.status != "success":
            logger.warning(f"Match {external_id}: 特征提取失败")
            continue

        features = extraction_result.features
        features_list.append(features)
        labels_list.append(result)
        match_ids.append(external_id)

        if (i + 1) % 10 == 0:
            logger.info(f"已处理: {i + 1}/{len(raw_rows)}")

    logger.info(f"\n✅ 提取完成:")
    logger.info(f"   有效样本: {len(features_list)}")
    logger.info(f"   标签分布: H={labels_list.count('H')}, D={labels_list.count('D')}, A={labels_list.count('A')}")

    return features_list, labels_list, match_ids


def preprocess_features(features_list, labels_list, sparsity_threshold=0.95):
    """特征预处理：处理稀疏列和异常值"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3: 特征预处理")
    logger.info("=" * 60)

    # 转换为 DataFrame
    df = pd.DataFrame(features_list)

    # 标签编码
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(labels_list)

    logger.info(f"原始特征维度: {df.shape[1]}")

    # 只保留数值型列
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    non_numeric_cols = [col for col in df.columns if col not in numeric_cols]

    if non_numeric_cols:
        logger.info(f"发现 {len(non_numeric_cols)} 个非数值列，将被删除")
        df = df[numeric_cols]

    logger.info(f"数值型特征维度: {df.shape[1]}")

    # 处理稀疏列
    nan_ratio = df.isna().sum() / len(df)
    sparse_features = nan_ratio[nan_ratio > sparsity_threshold].index.tolist()
    logger.info(f"稀疏特征 (sparsity > {sparsity_threshold}): {len(sparse_features)} 个")

    if sparse_features:
        df = df.drop(columns=sparse_features)
        logger.info(f"删除稀疏特征后维度: {df.shape[1]}")

    # 填充缺失值
    df = df.fillna(0)

    # 处理无穷值
    df = df.replace([np.inf, -np.inf], 0)

    # 异常值检测（使用 IQR 方法）
    try:
        Q1 = df.quantile(0.25)
        Q3 = df.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        # 将异常值截断到边界
        for col in df.columns:
            df[col] = df[col].clip(lower=lower_bound[col], upper=upper_bound[col])
    except Exception as e:
        logger.warning(f"异常值处理失败: {e}")

    logger.info(f"最终特征维度: {df.shape[1]}")

    X = df.values
    feature_names = df.columns.tolist()

    return X, y, feature_names, label_encoder


def calculate_sample_weights(y):
    """计算样本权重：平局权重 2.0"""
    weights = np.ones(len(y))
    # label_encoder: 0=A, 1=D, 2=H
    draw_indices = np.where(y == 1)[0]
    weights[draw_indices] = 2.0

    logger.info(f"样本权重: 普通=1.0, 平局=2.0 (共 {len(draw_indices)} 个)")
    return weights


def train_xgboost_model(X_train, y_train, X_test, y_test, sample_weights_train):
    """训练 XGBoost 模型"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 训练 XGBoost 模型")
    logger.info("=" * 60)

    # 计算类别比例
    class_counts = np.bincount(y_train)
    scale_pos_weight = class_counts[0] / class_counts[2]  # negative / positive

    # 计算每个样本的权重
    train_weights = sample_weights_train[y_train]

    # 创建 DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train, weight=train_weights)
    dtest = xgb.DMatrix(X_test, label=y_test)

    # 参数
    params = {
        "objective": "multi:softprob",  # 多分类概率输出
        "num_class": 3,  # H/D/A 三分类
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "mlogloss",
        "tree_method": "hist",  # 更快的训练
    }

    # 训练
    logger.info("开始训练...")
    logger.info(f"训练集: {len(X_train)} 样本")
    logger.info(f"测试集: {len(X_test)} 样本")
    logger.info(f"特征维度: {X_train.shape[1]}")

    evals_result = {}
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=200,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=20,
        evals_result=evals_result,
        verbose_eval=20,
    )

    logger.info(f"✅ 训练完成! 最佳轮数: {model.best_iteration}")

    return model, evals_result


def evaluate_model(model, X_test, y_test, label_encoder, feature_names):
    """评估模型"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 5: 模型评估")
    logger.info("=" * 60)

    dtest = xgb.DMatrix(X_test)
    y_pred_proba = model.predict(dtest)
    y_pred = np.argmax(y_pred_proba, axis=1)

    # 反向转换标签
    y_test_labels = label_encoder.inverse_transform(y_test)
    y_pred_labels = label_encoder.inverse_transform(y_pred)

    # 分类报告
    report = classification_report(y_test_labels, y_pred_labels, target_names=["A", "D", "H"])
    logger.info("\n分类报告:\n" + report)

    # 混淆矩阵
    cm = confusion_matrix(y_test_labels, y_pred_labels, labels=["A", "D", "H"])
    logger.info("\n混淆矩阵:")
    logger.info("        Pred: A    D    H")
    logger.info(f"True A:  {cm[0]}")
    logger.info(f"True D:  {cm[1]}")
    logger.info(f"True H:  {cm[2]}")

    # F1 Score
    f1_macro = f1_score(y_test_labels, y_pred_labels, average="macro")
    f1_weighted = f1_score(y_test_labels, y_pred_labels, average="weighted")
    logger.info(f"\nF1 Score (macro): {f1_macro:.4f}")
    logger.info(f"F1 Score (weighted): {f1_weighted:.4f}")

    # 准确率
    accuracy = (y_pred == y_test).mean()
    logger.info(f"准确率: {accuracy:.4f}")

    # Feature Importance
    importance = model.get_score(importance_type="gain")
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    logger.info("\n📊 Feature Importance TOP 50:")
    for i, (feat, score) in enumerate(sorted_importance[:50]):
        feat_name = feature_names[int(feat.replace("f", ""))] if feat.replace("f", "").isdigit() else feat
        logger.info(f"  {i+1:2d}. {feat_name:50s}: {score:.4f}")

    return {
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "feature_importance_top50": [
            {"rank": i+1, "feature": feat, "importance": score}
            for i, (feat, score) in enumerate(sorted_importance[:50])
        ],
    }


def save_model(model, label_encoder, feature_names, metrics):
    """保存模型"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 6: 保存模型")
    logger.info("=" * 60)

    # 创建 model_zoo 目录
    model_dir = Path("model_zoo")
    model_dir.mkdir(exist_ok=True)

    # 保存模型
    model_path = model_dir / "v26.2_baseline.pkl"
    model.save_model(str(model_path))
    logger.info(f"✅ 模型已保存: {model_path}")

    # 保存元数据
    metadata = {
        "model_version": "V26.2",
        "model_type": "XGBoost",
        "feature_count": len(feature_names),
        "num_classes": 3,
        "classes": ["A", "D", "H"],
        "label_encoder": label_encoder.classes_.tolist(),
        "feature_names": feature_names,
        "train_date": datetime.now().isoformat(),
        "metrics": metrics,
    }

    metadata_path = model_dir / "v26.2_baseline_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"✅ 元数据已保存: {metadata_path}")

    # 保存 Feature Importance
    importance_path = model_dir / "v26.2_feature_importance.txt"
    with open(importance_path, "w") as f:
        f.write("Feature Importance TOP 50\n")
        f.write("=" * 60 + "\n\n")
        for item in metrics["feature_importance_top50"]:
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
    logger.info("Phase 3.1: V26.2 预测模型训练")
    logger.info("=" * 60)
    logger.info(f"启动时间: {datetime.now().isoformat()}")

    # 步骤 1: 加载数据
    raw_rows = load_training_data_from_db()

    if not raw_rows:
        logger.error("没有可用的训练数据！")
        return 1

    # 步骤 2: 提取特征和标签
    features_list, labels_list, match_ids = extract_features_and_labels(raw_rows)

    if len(features_list) < 30:
        logger.error(f"训练样本不足: {len(features_list)} < 30")
        return 1

    # 步骤 3: 特征预处理
    X, y, feature_names, label_encoder = preprocess_features(features_list, labels_list)

    # 步骤 4: 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"\n数据集划分:")
    logger.info(f"  训练集: {len(X_train)} 样本")
    logger.info(f"  测试集: {len(X_test)} 样本")

    # 计算样本权重
    sample_weights = calculate_sample_weights(y)

    # 步骤 5: 训练模型
    model, evals_result = train_xgboost_model(X_train, y_train, X_test, y_test, sample_weights)

    # 步骤 6: 评估模型
    metrics = evaluate_model(model, X_test, y_test, label_encoder, feature_names)

    # 步骤 7: 保存模型
    save_model(model, label_encoder, feature_names, metrics)

    logger.info("\n" + "=" * 60)
    logger.info("✅ Phase 3.1 完成!")
    logger.info("=" * 60)
    logger.info(f"完成时间: {datetime.now().isoformat()}")
    logger.info(f"准确率: {metrics['accuracy']:.4f}")
    logger.info(f"F1 Score (macro): {metrics['f1_macro']:.4f}")

    return 0


if __name__ == "__main__":
    exit(main())
