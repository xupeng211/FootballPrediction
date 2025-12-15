#!/usr/bin/env python3
"""
简化版模拟数据训练脚本
不依赖复杂的项目结构，独立运行
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_mock_data(num_teams=20, num_matches=400):
    """生成模拟足球比赛数据"""
    logger.info(f"📊 生成模拟数据: {num_teams} 球队, {num_matches} 场比赛")

    np.random.seed(42)

    # 生成球队
    team_ids = list(range(1001, 1001 + num_teams))
    team_names = [f"球队{i}" for i in range(1, num_teams + 1)]

    matches = []
    match_id = 1

    # 生成比赛数据
    for match_date in pd.date_range('2022-01-01', '2024-12-01', freq='3D'):
        if len(matches) >= num_matches * 2:
            break

        # 随机选择两支球队
        team1_id, team2_id = np.random.choice(team_ids, 2, replace=False)

        # 模拟球队实力
        team1_strength = np.random.normal(0.5, 0.15)
        team2_strength = np.random.normal(0.5, 0.15)

        # 主队优势
        home_advantage = 0.1

        # 期望进球
        team1_xg = min(max(team1_strength + home_advantage + np.random.normal(0, 0.1), 0.1), 0.9)
        team2_xg = min(max(team2_strength - home_advantage + np.random.normal(0, 0.1), 0.1), 0.9)

        # 实际进球
        team1_goals = np.random.poisson(team1_xg * 2.5)
        team2_goals = np.random.poisson(team2_xg * 2.5)

        # 其他统计
        team1_shots = max(5, min(30, int(team1_xg * 15 + np.random.normal(0, 3))))
        team2_shots = max(5, min(30, int(team2_xg * 15 + np.random.normal(0, 3))))

        team1_corners = max(1, min(15, int(team1_xg * 8 + np.random.normal(0, 2))))
        team2_corners = max(1, min(15, int(team2_xg * 8 + np.random.normal(0, 2))))

        # 主队记录
        home_result = 'win' if team1_goals > team2_goals else ('draw' if team1_goals == team2_goals else 'loss')
        matches.append({
            'match_id': match_id,
            'match_date': match_date,
            'team_id': team1_id,
            'venue': 'home',
            'goals_scored': team1_goals,
            'goals_conceded': team2_goals,
            'xg': team1_xg,
            'shots': team1_shots,
            'corners': team1_corners,
            'result': home_result
        })

        # 客队记录
        away_result = 'win' if team2_goals > team1_goals else ('draw' if team2_goals == team1_goals else 'loss')
        matches.append({
            'match_id': match_id,
            'match_date': match_date,
            'team_id': team2_id,
            'venue': 'away',
            'goals_scored': team2_goals,
            'goals_conceded': team1_goals,
            'xg': team2_xg,
            'shots': team2_shots,
            'corners': team2_corners,
            'result': away_result
        })

        match_id += 1

    df = pd.DataFrame(matches)
    df = df.sort_values('match_date').reset_index(drop=True)

    logger.info(f"✅ 数据生成完成: {len(df)} 条记录")
    logger.info(f"📊 比赛场次: {df['match_id'].nunique()}")
    logger.info(f"🏆 球队数量: {df['team_id'].nunique()}")

    return df


def add_rolling_features(df):
    """添加滚动特征"""
    logger.info("⚙️ 计算滚动特征...")

    # 基础特征列
    base_features = ['goals_scored', 'goals_conceded', 'xg', 'shots', 'corners']
    windows = [3, 10]

    df_rolling = df.copy()

    for feature in base_features:
        for window in windows:
            # 按球队分组，计算滚动平均，并shift(1)防止数据泄露
            feature_name = f'rolling_{feature}_{window}_mean'
            df_rolling[feature_name] = (
                df_rolling.groupby('team_id')[feature]
                .transform(lambda x: x.rolling(window=window, min_periods=1)
                          .mean()
                          .shift(1))  # 关键：防数据泄露
            )

    # 删除包含NaN的行
    initial_rows = len(df_rolling)
    df_rolling = df_rolling.dropna()
    cleaned_rows = len(df_rolling)
    logger.info(f"🧹 数据清洗: {initial_rows} -> {cleaned_rows} 行")

    return df_rolling


def train_model(df):
    """训练XGBoost模型"""
    logger.info("🧠 开始模型训练...")

    # 创建目标变量
    df['target'] = (df['result'] == 'win').astype(int)

    # 选择特征列
    feature_cols = [col for col in df.columns if col.startswith('rolling_') and col.endswith('_mean')]

    logger.info(f"🎯 特征数量: {len(feature_cols)}")
    logger.info(f"📋 前5个特征: {feature_cols[:5]}")

    X = df[feature_cols]
    y = df['target']

    # 时间序列分割
    split_idx = int(len(X) * 0.8)
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    logger.info(f"📊 训练集: {len(X_train)} 样本")
    logger.info(f"📊 测试集: {len(X_test)} 样本")
    logger.info(f"📈 胜率 - 训练集: {y_train.mean():.2%}, 测试集: {y_test.mean():.2%}")

    # 训练XGBoost模型
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss',
        use_label_encoder=False
    )

    model.fit(X_train, y_train)
    logger.info("✅ 模型训练完成")

    # 评估模型
    logger.info("📊 评估模型性能...")
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)

    logger.info(f"🎯 模型性能:")
    logger.info(f"   Accuracy:  {accuracy:.4f} ({accuracy:.2%})")
    logger.info(f"   Precision: {precision:.4f} ({precision:.2%})")

    # 特征重要性
    logger.info("🔍 分析特征重要性...")
    feature_importance = model.get_booster().get_score(importance_type='gain')

    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    top_features = sorted_features[:10]

    logger.info("🏆 Top 10 重要特征:")
    for i, (feature, importance) in enumerate(top_features, 1):
        logger.info(f"   {i:2d}. {feature:<25} : {importance:.4f}")

    return {
        'model': model,
        'accuracy': accuracy,
        'precision': precision,
        'feature_importance': top_features,
        'feature_cols': feature_cols,
        'train_size': len(X_train),
        'test_size': len(X_test)
    }


def save_results(model, results, feature_cols):
    """保存模型和结果"""
    logger.info("💾 保存模型和结果...")

    # 创建models目录
    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)

    # 保存模型
    model_path = model_dir / "baseline_v1_mock.json"
    model.save_model(str(model_path))

    # 保存结果信息
    model_info = {
        "model_type": "XGBClassifier",
        "features": feature_cols,
        "feature_importance": dict(results['feature_importance']),
        "performance": {
            "accuracy": float(results['accuracy']),
            "precision": float(results['precision'])
        },
        "training_data": {
            "train_samples": results['train_size'],
            "test_samples": results['test_size'],
            "feature_count": len(feature_cols)
        },
        "training_date": datetime.now().isoformat(),
        "data_type": "mock"
    }

    info_path = model_dir / "baseline_v1_mock_info.json"
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(model_info, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ 模型已保存到: {model_path}")
    logger.info(f"📄 结果已保存到: {info_path}")


def main():
    """主函数"""
    logger.info("🚀 足球预测系统 - 简化版模拟数据训练")
    logger.info("=" * 60)

    try:
        # 1. 生成模拟数据
        df = generate_mock_data(num_teams=20, num_matches=400)

        # 2. 添加滚动特征
        df_features = add_rolling_features(df)

        # 3. 训练模型
        results = train_model(df_features)

        # 4. 保存结果
        save_results(results['model'], results, results['feature_cols'])

        # 5. 总结报告
        logger.info("=" * 60)
        logger.info("🎉 训练完成!")
        logger.info("=" * 60)
        logger.info(f"📊 模型性能:")
        logger.info(f"   • Accuracy:  {results['accuracy']:.2%}")
        logger.info(f"   • Precision: {results['precision']:.2%}")
        logger.info(f"🔧 技术规格:")
        logger.info(f"   • 特征数量:   {len(results['feature_cols'])}")
        logger.info(f"   • 训练样本:   {results['train_size']:,}")
        logger.info(f"   • 测试样本:   {results['test_size']:,}")
        logger.info(f"   • 模型类型:   XGBoost")
        logger.info(f"💾 输出文件:")
        logger.info(f"   • 模型文件:   models/baseline_v1_mock.json")
        logger.info(f"   • 信息文件:   models/baseline_v1_mock_info.json")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ 训练流程圆满完成!")
    else:
        logger.error("❌ 训练失败")