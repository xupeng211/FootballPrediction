#!/usr/bin/env python3
"""
V5.2 快速训练器 - 基于现有可用数据
"""

import logging
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.impute import SimpleImputer

from src.config_unified import get_settings
from src.database.schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


def train_v52_fast():
    """快速训练V5.2模型"""
    logger.info("🚀 开始V5.2快速模型训练...")

    settings = get_settings()
    schema_manager = get_schema_manager()

    # 简单数据查询
    conn = schema_manager.get_connection()

    query = """
        SELECT
            home_score, away_score,
            home_xg, away_xg,
            home_possession, away_possession,
            home_corners, away_corners,
            home_shots_total, away_shots_total,
            home_shots_on_target, away_shots_on_target,
            home_yellow_cards, away_yellow_cards,
            home_red_cards, away_red_cards,
            home_passes, away_passes,
            home_pass_accuracy, away_pass_accuracy
        FROM match_features_training
        WHERE home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND home_xg IS NOT NULL
          AND away_xg IS NOT NULL
        LIMIT 200
    """

    df = pd.read_sql(query, conn)
    conn.close()

    logger.info(f"✅ 加载数据: {len(df)} 条记录")

    if len(df) < 50:
        logger.error("❌ 数据不足，无法训练")
        return None

    # 创建目标变量
    y = np.where(df['home_score'].values > df['away_score'].values, 2,
                np.where(df['home_score'].values < df['away_score'].values, 0, 1))

    # 选择特征
    feature_cols = [col for col in df.columns if col not in ['home_score', 'away_score']]
    X = df[feature_cols].values

    logger.info(f"📊 特征矩阵: {X.shape}")

    # 数据预处理
    imputer = SimpleImputer(strategy='median')
    X = imputer.fit_transform(X)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # XGBoost参数
    params = {
        'objective': 'multi:softmax',
        'num_class': 3,
        'max_depth': 4,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42
    }

    model = xgb.XGBClassifier(**params)

    # 5折交叉验证（因为数据量小）
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

    logger.info(f"📈 5折CV准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # 训练最终模型
    model.fit(X, y)

    # 评估
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)
    logger.info(f"🎯 训练集准确率: {accuracy:.4f}")

    # 特征重要性
    feature_importance = dict(zip(feature_cols, model.feature_importances_))
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

    logger.info("🏆 Top 10 重要特征:")
    for i, (feature, importance) in enumerate(sorted_features[:10]):
        logger.info(f"  {i+1:2d}. {feature:25s}: {importance:.4f}")

    # 保存模型
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"xgb_v52_fast_{timestamp}"

    import os
    os.makedirs("data/models", exist_ok=True)

    model_path = f"data/models/{model_name}.pkl"
    scaler_path = f"data/models/{model_name}_scaler.pkl"
    imputer_path = f"data/models/{model_name}_imputer.pkl"

    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)

    with open(imputer_path, 'wb') as f:
        pickle.dump(imputer, f)

    logger.info(f"💾 模型已保存: {model_path}")

    # 检查是否达成目标
    if accuracy >= 0.58:
        logger.info(f"🎉 恭喜！模型准确率 {accuracy:.4f} 突破58%目标！")
    else:
        gap = 0.58 - accuracy
        logger.info(f"📊 距离58%目标还差 {gap*100:.1f}%")

    return {
        'model_path': model_path,
        'accuracy': accuracy,
        'cv_accuracy_mean': cv_scores.mean(),
        'cv_accuracy_std': cv_scores.std(),
        'feature_count': len(feature_cols),
        'sample_count': len(df),
        'top_features': sorted_features,
        'target_achieved': accuracy >= 0.58
    }


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    results = train_v52_fast()

    if results:
        print("\n" + "="*60)
        print("🏆 V5.2 快速模型训练完成!")
        print("="*60)
        print(f"📊 模型准确率: {results['accuracy']:.4f}")
        print(f"📈 5折CV准确率: {results['cv_accuracy_mean']:.4f} ± {results['cv_accuracy_std']:.4f}")
        print(f"🎯 58%目标达成: {'✅ 是' if results['target_achieved'] else '❌ 否'}")
        print(f"🔢 特征维度: {results['feature_count']}")
        print(f"📋 训练样本: {results['sample_count']}")
        print(f"💾 模型路径: {results['model_path']}")

        print("\n🏆 Top 10 特征重要性:")
        for i, (feature, importance) in enumerate(results['top_features'][:10]):
            print(f"  {i+1:2d}. {feature:25s}: {importance:.4f}")
    else:
        print("❌ 训练失败")


if __name__ == "__main__":
    main()