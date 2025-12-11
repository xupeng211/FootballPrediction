#!/usr/bin/env python3
"""
简单直接的足球预测模型训练脚本
Simple Football Prediction Model Training Script
"""

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_data_via_pandas():
    """使用pandas直接从数据库加载数据"""
    logger.info("🔍 使用pandas从数据库加载训练数据...")

    try:
        from sqlalchemy import create_engine

        # 创建数据库连接字符串
        import os

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres-dev-password@db:5432/football_prediction",
        )
        engine = create_engine(db_url)

        # 查询数据
        query = """
        SELECT
            f.feature_data,
            m.home_score,
            m.away_score,
            CASE
                WHEN m.home_score > m.away_score THEN 'Home'
                WHEN m.home_score = m.away_score THEN 'Draw'
                WHEN m.home_score < m.away_score THEN 'Away'
            END as result_label,
            m.match_date
        FROM features f
        JOIN matches m ON f.match_id = m.id
        WHERE m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
          AND f.feature_data IS NOT NULL
        ORDER BY m.match_date
        """

        df = pd.read_sql(query, engine)
        logger.info(f"📊 成功加载 {len(df)} 条训练样本")

        if len(df) == 0:
            raise ValueError("没有找到有效的训练数据")

        # 解析JSON特征数据
        features_list = []
        for feature_json in df["feature_data"]:
            if isinstance(feature_json, str):
                features = json.loads(feature_json)
            else:
                features = feature_json
            features_list.append(features)

        # 创建特征DataFrame
        features_df = pd.DataFrame(features_list)
        features_df["result_label"] = df["result_label"].values
        features_df["match_date"] = pd.to_datetime(df["match_date"].values)

        logger.info(f"🎯 原始特征维度: {features_df.shape[1]} (包含标签)")
        logger.info(
            f"📅 数据时间范围: {features_df['match_date'].min()} 到 {features_df['match_date'].max()}"
        )

        # 显示标签分布
        logger.info("📈 标签分布:")
        label_dist = features_df["result_label"].value_counts()
        for label, count in label_dist.items():
            percentage = count / len(features_df) * 100
            logger.info(f"   {label}: {count} ({percentage:.1f}%)")

        return features_df

    except Exception:
        logger.error(f"❌ 加载数据失败: {e}")
        raise


def preprocess_features(df):
    """预处理特征数据，避免数据泄露"""
    logger.info("🧹 开始数据预处理...")

    # 移除明确的非预测性特征和标识符
    exclude_cols = [
        "home_team_id",  # 球队ID，不包含预测信息
        "away_team_id",  # 球队ID，不包含预测信息
        "match_date",  # 比赛日期，不应该用于预测
        "match_result",  # 比赛结果（如果有），会泄露答案
        "result_label",  # 标签列
    ]

    # 只保留真正的特征列
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    # 进一步过滤：只保留数值型特征
    numeric_features = []
    for col in feature_cols:
        if df[col].dtype in ["int64", "float64", "int32", "float32"]:
            numeric_features.append(col)
        else:
            logger.warning(f"⚠️ 跳过非数值特征: {col} (类型: {df[col].dtype})")

    logger.info(f"📋 选择的数值特征列: {numeric_features}")

    # 提取特征矩阵和标签
    X = df[numeric_features].copy()
    y = df["result_label"].copy()

    # 检查数据质量
    logger.info("🔍 数据质量检查:")
    logger.info(f"   特征矩阵形状: {X.shape}")
    logger.info(f"   标签向量形状: {y.shape}")

    # 检查缺失值
    missing_values = X.isnull().sum()
    if missing_values.sum() > 0:
        missing_cols = missing_values[missing_values > 0]
        logger.warning("⚠️ 发现缺失值:")
        for col, count in missing_cols.items():
            percentage = count / len(X) * 100
            logger.warning(f"   {col}: {count} ({percentage:.1f}%)")

        # 使用0填充缺失值
        X = X.fillna(0)
        logger.info("✅ 已用0填充缺失值")
    else:
        logger.info("✅ 无缺失值")

    # 检查常数特征（方差为0）
    constant_features = []
    for col in X.columns:
        if X[col].var() == 0:
            constant_features.append(col)

    if constant_features:
        logger.warning(f"⚠️ 发现常数特征（方差为0）: {constant_features}")
        X = X.drop(columns=constant_features)
        logger.info(f"✅ 已移除 {len(constant_features)} 个常数特征")

    logger.info(f"✅ 预处理完成: {X.shape[0]} 样本, {X.shape[1]} 特征")

    # 保存特征列名供后续推理使用
    feature_metadata = {
        "feature_columns": list(X.columns),
        "n_features": len(X.columns),
        "training_date": datetime.now().isoformat(),
        "training_samples": len(X),
        "excluded_columns": exclude_cols,
        "non_numeric_features": [
            col for col in feature_cols if col not in numeric_features
        ],
    }

    return X, y, feature_metadata


def train_model(X, y):
    """训练XGBoost模型"""
    logger.info("🚀 开始模型训练...")

    # 编码标签
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # 时间序列拆分：使用前80%的数据训练，后20%测试
    split_index = int(len(X) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]
    y_train = y_encoded[:split_index]
    y_test = y_encoded[split_index:]

    logger.info("📊 时间序列拆分:")
    logger.info(
        f"   训练集: {X_train.shape[0]} 样本 ({len(X_train) / len(X) * 100:.1f}%)"
    )
    logger.info(
        f"   测试集: {X_test.shape[0]} 样本 ({len(X_test) / len(X) * 100:.1f}%)"
    )

    # 检查训练集和测试集的标签分布
    train_dist = pd.Series(y_train).value_counts().sort_index()
    test_dist = pd.Series(y_test).value_counts().sort_index()

    class_names = label_encoder.classes_
    logger.info(
        f"   训练集标签分布: {dict(zip(class_names, train_dist.values, strict=False))}"
    )
    logger.info(
        f"   测试集标签分布: {dict(zip(class_names, test_dist.values, strict=False))}"
    )

    # 创建XGBoost分类器 - 使用合理的参数避免过拟合
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,  # 降低深度避免过拟合
        learning_rate=0.1,
        random_state=42,
        objective="multi:softmax",
        num_class=3,
        eval_metric="mlogloss",
        subsample=0.8,  # 随机采样
        colsample_bytree=0.8,  # 特征采样
        reg_alpha=0.1,  # L1正则化
        reg_lambda=1.0,  # L2正则化
    )

    # 训练模型
    logger.info("🎯 正在训练XGBoost模型...")
    model.fit(X_train, y_train)

    # 预测
    y_pred = model.predict(X_test)
    model.predict_proba(X_test)

    # 评估
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"📈 测试集准确率: {accuracy:.4f} ({accuracy * 100:.1f}%)")

    # 检查准确率是否合理（足球预测三分类）
    if accuracy > 0.65:
        logger.warning("⚠️ 准确率过高，可能存在特征泄露！")
    elif accuracy < 0.35:
        logger.warning("⚠️ 准确率过低，模型可能欠拟合")
    else:
        logger.info("✅ 准确率在合理范围内 (35%-65%)")

    # 详细分类报告
    logger.info("📋 分类报告:")
    report = classification_report(
        y_test, y_pred, target_names=class_names, output_dict=True
    )

    for class_name in class_names:
        metrics = report[class_name]
        logger.info(f"   {class_name}:")
        logger.info(f"     精确率: {metrics['precision']:.3f}")
        logger.info(f"     召回率: {metrics['recall']:.3f}")
        logger.info(f"     F1分数: {metrics['f1-score']:.3f}")

    # 混淆矩阵
    logger.info("🔢 混淆矩阵:")
    cm = confusion_matrix(y_test, y_pred)
    logger.info("   实际\\预测  Home  Draw  Away")
    class_names = ["Home", "Draw", "Away"]
    for i, actual_class in enumerate(class_names):
        row_str = f"   {actual_class:6s}"
        for j in range(3):
            row_str += f"  {cm[i][j]:4d}"
        logger.info(row_str)

    # 特征重要性
    logger.info("🏆 特征重要性排名 (Top 10):")
    feature_importance = (
        pd.DataFrame({"feature": X.columns, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .head(10)
    )

    for idx, row in feature_importance.iterrows():
        logger.info(f"   {idx + 1:2d}. {row['feature']}: {row['importance']:.4f}")

    return model, label_encoder, accuracy, feature_importance


def save_model_and_metadata(
    model, label_encoder, feature_metadata, feature_importance, accuracy
):
    """保存模型和相关元数据"""
    logger.info("💾 开始保存模型...")

    # 确保目录存在
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # 保存模型
    model_path = models_dir / "football_prediction_v2.pkl"

    model_data = {
        "model": model,
        "label_encoder": label_encoder,
        "feature_metadata": feature_metadata,
    }

    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)

    logger.info(f"✅ 模型已保存: {model_path}")

    # 保存元数据
    metadata_path = models_dir / "model_metadata.json"
    metadata = {
        "model_version": "v2",
        "model_path": str(model_path),
        "feature_metadata": feature_metadata,
        "feature_importance": feature_importance.to_dict("records"),
        "label_encoder_classes": label_encoder.classes_.tolist(),
        "training_accuracy": accuracy,
        "created_at": datetime.now().isoformat(),
        "model_type": "XGBClassifier",
        "target_classes": ["Home", "Draw", "Away"],
    }

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ 元数据已保存: {metadata_path}")

    return model_path, metadata_path


def main():
    """主训练函数"""
    logger.info("=" * 60)
    logger.info("🎯 足球预测模型训练开始 (简化版本)")
    logger.info("=" * 60)

    try:
        # 1. 从数据库加载数据
        df = load_data_via_pandas()

        # 2. 预处理
        X, y, feature_metadata = preprocess_features(df)

        # 3. 训练模型
        model, label_encoder, accuracy, feature_importance = train_model(X, y)

        # 更新元数据
        feature_metadata["accuracy"] = accuracy

        # 4. 保存模型
        model_path, metadata_path = save_model_and_metadata(
            model, label_encoder, feature_metadata, feature_importance, accuracy
        )

        logger.info("=" * 60)
        logger.info("🎉 模型训练完成!")
        logger.info(f"📁 模型文件: {model_path}")
        logger.info(f"📄 元数据文件: {metadata_path}")
        logger.info(f"🎯 最终准确率: {accuracy:.4f} ({accuracy * 100:.1f}%)")
        logger.info(f"🔢 特征数量: {len(feature_metadata['feature_columns'])}")
        logger.info("=" * 60)

        # 生成模型质量报告
        if 0.35 <= accuracy <= 0.65:
            logger.info("✅ 模型质量评估: GOOD - 准确率在合理范围内")
        elif accuracy > 0.65:
            logger.warning("⚠️ 模型质量评估: WARNING - 准确率可能过高，检查特征泄露")
        else:
            logger.warning(
                "⚠️ 模型质量评估: WARNING - 准确率较低，可能需要更多特征或调参"
            )

        return model_path, metadata_path

    except Exception:
        logger.error(f"❌ 训练失败: {e}")
        import traceback

        logger.error(f"🔍 详细错误: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
