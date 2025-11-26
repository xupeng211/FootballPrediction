#!/usr/bin/env python3
"""
直接使用 raw_match_data 数据训练简化模型的脚本
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入必要的库
from sqlalchemy import create_engine, text
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_training_data():
    """从 raw_match_data 表加载训练数据"""
    try:
        # 数据库连接
        engine = create_engine('postgresql://postgres:postgres-dev-password@db:5432/football_prediction')

        # 查询原始数据
        query = """
        SELECT
            match_data,
            source,
            collected_at
        FROM raw_match_data
        WHERE match_data->'status'->>'finished' = 'true'
        AND match_data->'status'->>'scoreStr' IS NOT NULL
        ORDER BY collected_at DESC
        """

        logger.info("🔍 正在加载原始比赛数据...")
        df = pd.read_sql_query(query, engine)

        if df.empty:
            logger.error("❌ 没有找到已完成的比赛数据")
            return None

        logger.info(f"✅ 成功加载 {len(df)} 条已完成比赛记录")
        return df

    except Exception as e:
        logger.error(f"❌ 数据加载失败: {str(e)}")
        return None

def process_raw_data(df):
    """处理原始 JSON 数据，创建特征和标签"""
    features = []
    labels = []

    for _, row in df.iterrows():
        try:
            match_data = row['match_data']
            # 如果是字符串，尝试解析为JSON
            if isinstance(match_data, str):
                match_data = json.loads(match_data)

            # 提取基本信息
            status = match_data.get('status', {})

            # 检查队伍名称 - 优先使用新字段
            home_team_name = match_data.get('home_team_name') or match_data.get('raw_data', {}).get('home', {}).get('name')
            away_team_name = match_data.get('away_team_name') or match_data.get('raw_data', {}).get('away', {}).get('name')

            if not all([home_team_name, away_team_name]):
                continue

            # 提取比分信息
            score_str = status.get('scoreStr', '')
            if not score_str or '-' not in score_str:
                continue

            # 解析比分
            try:
                home_score, away_score = map(int, score_str.split(' - '))
            except:
                continue

            # 创建特征
            feature = {
                'home_team_name': home_team_name,
                'away_team_name': away_team_name,
                'league_name': match_data.get('league_name', ''),
                'match_time': match_data.get('match_time', ''),
                'collection_date': row['collected_at']
            }

            # 创建标签 (1: 主队胜, 0: 平局, -1: 客队胜)
            if home_score > away_score:
                label = 1  # 主队胜
            elif home_score < away_score:
                label = -1  # 客队胜
            else:
                label = 0  # 平局

            features.append(feature)
            labels.append(label)

        except Exception as e:
            logger.warning(f"处理比赛数据时出错: {str(e)}")
            continue

    logger.info(f"✅ 成功处理 {len(features)} 条有效比赛记录")
    return pd.DataFrame(features), np.array(labels)

def encode_features(df):
    """编码分类特征"""
    df_encoded = df.copy()

    # 编码球队名称 (使用简单哈希编码)
    df_encoded['home_team_encoded'] = df['home_team_name'].apply(lambda x: hash(str(x)) % 1000)
    df_encoded['away_team_encoded'] = df['away_team_name'].apply(lambda x: hash(str(x)) % 1000)

    # 编码联赛名称
    df_encoded['league_encoded'] = df['league_name'].apply(lambda x: hash(str(x)) % 100)

    # 创建时间特征
    df_encoded['collection_date'] = pd.to_datetime(df['collection_date'])
    df_encoded['day_of_week'] = df_encoded['collection_date'].dt.dayofweek
    df_encoded['month'] = df_encoded['collection_date'].dt.month

    # 选择数值特征
    feature_columns = [
        'home_team_encoded',
        'away_team_encoded',
        'league_encoded',
        'day_of_week',
        'month'
    ]

    return df_encoded[feature_columns]

def train_model(X, y):
    """训练随机森林模型"""
    logger.info("🚀 开始训练模型...")

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"训练集大小: {X_train.shape[0]}, 测试集大小: {X_test.shape[0]}")

    # 训练随机森林模型
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )

    model.fit(X_train, y_train)

    # 预测
    y_pred = model.predict(X_test)

    # 评估
    accuracy = accuracy_score(y_test, y_pred)

    logger.info(f"📊 模型训练完成!")
    logger.info(f"✅ 测试集准确率: {accuracy:.4f}")

    # 打印分类报告
    label_names = ['平局', '主队胜', '客队胜']
    logger.info("\n" + classification_report(y_test, y_pred, target_names=label_names))

    # 特征重要性
    feature_names = ['主队编码', '客队编码', '联赛编码', '星期几', '月份']
    importances = model.feature_importances_

    logger.info("\n🎯 特征重要性:")
    for name, importance in zip(feature_names, importances):
        logger.info(f"  {name}: {importance:.4f}")

    return model, accuracy

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("🎯 足球预测模型训练开始 (直接使用原始数据)")
    logger.info("="*60)

    # 1. 加载数据
    raw_df = load_training_data()
    if raw_df is None:
        logger.error("❌ 无法加载数据，训练终止")
        return

    # 2. 处理数据
    features_df, labels = process_raw_data(raw_df)
    if len(features_df) == 0:
        logger.error("❌ 没有有效的训练数据，训练终止")
        return

    # 3. 特征编码
    X = encode_features(features_df)

    # 4. 训练模型
    model, accuracy = train_model(X, labels)

    # 5. 保存模型
    model_path = '/app/models/football_prediction_direct.pkl'
    joblib.dump(model, model_path)
    logger.info(f"💾 模型已保存到: {model_path}")

    # 6. 最终报告
    logger.info("="*60)
    logger.info("🎉 训练完成!")
    logger.info(f"📊 最终准确率: {accuracy:.4f}")
    logger.info(f"📋 训练样本数: {len(features_df)}")
    logger.info(f"🔢 特征维度: {X.shape[1]}")
    logger.info("="*60)

if __name__ == "__main__":
    main()