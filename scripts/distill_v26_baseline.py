#!/usr/bin/env python3
"""
V26.1 基础特征导出脚本 - 快速版
从 matches 表关联获取比赛结果标签
"""

import subprocess
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
import xgboost as xgb
import json


def export_baseline_data() -> pd.DataFrame:
    """
    导出基础特征数据 + 从 matches 表获取标签
    """
    print("📦 导出基础特征数据（带标签）...")

    # 使用 SQL JOIN 从 matches 表获取比分
    cmd = '''docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "\\COPY (SELECT f.match_id, f.match_date, f.home_team, f.away_team, m.home_score, m.away_score, f.rolling_xg_home, f.rolling_xg_away, f.rolling_shots_on_target_home, f.rolling_shots_on_target_away, f.rolling_possession_home, f.rolling_possession_away, f.rolling_team_rating_home, f.rolling_team_rating_away, f.home_table_position, f.away_table_position, f.table_position_diff, f.home_points, f.away_points, f.points_diff, f.home_recent_form_points, f.away_recent_form_points, f.raw_elo_gap, f.adjusted_elo_gap, f.fatigue_impact, f.schedule_impact, f.home_fatigue_index, f.away_fatigue_index, f.fatigue_diff, f.home_rest_days, f.away_rest_days, f.home_relegation_incentive, f.away_relegation_incentive, f.incentive_diff, f.home_desperation, f.table_proximity, f.low_scoring_tendency, f.elo_diff_cluster FROM match_features_training f JOIN matches m ON f.match_id = m.match_id::text ORDER BY f.match_date) TO STDOUT WITH CSV HEADER" > /tmp/v26_baseline.csv'''

    subprocess.run(cmd, shell=True, check=True)

    df = pd.read_csv('/tmp/v26_baseline.csv')
    print(f"   加载 {len(df)} 行，{len(df.columns)} 列")

    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """
    准备特征和标签
    """
    print("\n🔨 准备特征矩阵...")

    # 从比分计算标签
    df['result'] = 'draw'
    df.loc[df['home_score'] > df['away_score'], 'result'] = 'home'
    df.loc[df['home_score'] < df['away_score'], 'result'] = 'away'

    # 目标：主队是否获胜
    df['target_win'] = (df['result'] == 'home').astype(int)

    # 选择特征列
    feature_cols = [
        'rolling_xg_home', 'rolling_xg_away',
        'rolling_shots_on_target_home', 'rolling_shots_on_target_away',
        'rolling_possession_home', 'rolling_possession_away',
        'rolling_team_rating_home', 'rolling_team_rating_away',
        'home_table_position', 'away_table_position', 'table_position_diff',
        'home_points', 'away_points', 'points_diff',
        'home_recent_form_points', 'away_recent_form_points',
        'raw_elo_gap', 'adjusted_elo_gap',
        'fatigue_impact', 'schedule_impact',
        'home_fatigue_index', 'away_fatigue_index', 'fatigue_diff',
        'home_rest_days', 'away_rest_days',
        'home_relegation_incentive', 'away_relegation_incentive',
        'incentive_diff', 'home_desperation',
        'table_proximity', 'low_scoring_tendency', 'elo_diff_cluster'
    ]

    # 填充缺失值
    df[feature_cols] = df[feature_cols].fillna(0)

    print(f"   特征维度: {len(feature_cols)}")
    print(f"   样本数: {len(df)}")

    # 统计结果分布
    result_counts = df['result'].value_counts()
    print(f"   结果分布:")
    for result, count in result_counts.items():
        print(f"      {result}: {count} ({count/len(df)*100:.1f}%)")

    return df, feature_cols


def train_xgboost_baseline(
    df: pd.DataFrame,
    feature_cols: list,
    test_size: float = 0.2
) -> dict:
    """
    训练 XGBoost 基准模型
    """
    print("\n🤖 训练 XGBoost 基准模型...")

    # 按时间排序划分（防止未来信息泄露）
    split_idx = int(len(df) * (1 - test_size))
    df_train = df.iloc[:split_idx].copy()
    df_test = df.iloc[split_idx:].copy()

    print(f"   训练集: {len(df_train)} 场")
    print(f"   测试集: {len(df_test)} 场")
    print(f"   时间划分点: {df_train['match_date'].max()}")

    # 准备数据
    X_train = df_train[feature_cols].values
    y_train = df_train['target_win'].values
    X_test = df_test[feature_cols].values
    y_test = df_test['target_win'].values

    # 计算正类比例（用于调整 scale_pos_weight）
    pos_ratio = y_train.sum() / (len(y_train) - y_train.sum())
    print(f"   正负类比例: 1:{pos_ratio:.2f}")

    # 训练模型
    print("   开始训练...")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_ratio,
        random_state=42,
        eval_metric='logloss'
    )

    model.fit(X_train, y_train)

    # 预测
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # 评估
    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)

    print(f"\n   ✅ 模型评估:")
    print(f"      准确率 (Accuracy): {accuracy*100:.2f}%")
    print(f"      AUC 值: {auc:.4f}")

    # 特征重要性
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)

    return {
        'model': model,
        'accuracy': accuracy,
        'auc': auc,
        'feature_importance': feature_importance,
        'y_test': y_test,
        'y_pred_proba': y_pred_proba
    }


def main():
    """主函数"""
    print("=" * 60)
    print("V26.1 基础特征训练 (Baseline Training)")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 导出数据
    df = export_baseline_data()

    # 2. 准备特征
    df, feature_cols = prepare_features(df)

    # 3. 训练模型
    results = train_xgboost_baseline(df, feature_cols)

    # 4. 保存数据集
    output_path = output_dir / "V26_Baseline_40D.parquet"
    df.to_parquet(output_path, index=False)
    print(f"\n💾 数据集保存到: {output_path}")

    # 5. 输出 Top 10 特征
    print(f"\n📊 Top 10 特征贡献排行:")
    print("-" * 50)

    top_features = results['feature_importance'].head(10)

    for i, row in enumerate(top_features.itertuples(), 1):
        print(f"   {i:2d}. {row.feature:30s} | {row.importance:.4f}")

    # 6. 保存结果摘要
    summary = {
        'dataset': 'V26_Baseline_40D',
        'n_samples': len(df),
        'n_features': len(feature_cols),
        'accuracy': float(results['accuracy']),
        'auc': float(results['auc']),
        'top_features': top_features.to_dict('records')
    }

    summary_path = output_dir / "V26_Baseline_Summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n💾 结果摘要保存到: {summary_path}")

    print("\n" + "=" * 60)
    print("✅ V26.1 基准训练完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
