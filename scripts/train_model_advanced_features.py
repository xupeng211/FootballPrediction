#!/usr/bin/env python3
"""
基于滚动窗口特征的XGBoost模型训练
验证 rolling_form 特征是否比 team_id 更重要
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder, StandardScaler
from datetime import datetime
import os
import sys
import warnings
warnings.filterwarnings('ignore')

print("🎯 基于滚动窗口特征的XGBoost模型训练")
print("="*60)

def load_latest_features():
    """加载最新的特征数据"""
    data_dir = "/app/data"

    # 查找最新的特征文件
    feature_files = [f for f in os.listdir(data_dir) if f.startswith('massive_advanced_features_')]

    if not feature_files:
        raise FileNotFoundError("未找到大规模特征文件")

    latest_file = sorted(feature_files)[-1]
    latest_path = os.path.join(data_dir, latest_file)

    print(f"📊 加载特征文件: {latest_file}")
    df = pd.read_csv(latest_path)
    print(f"✅ 加载 {len(df):,} 条记录，{len(df.columns)} 个特征")

    return df

def create_target_variable(df):
    """创建目标变量"""
    print("🎯 创建目标变量...")

    # 定义比赛结果
    def get_result(row):
        if row['home_score'] > row['away_score']:
            return 'home_win'
        elif row['home_score'] < row['away_score']:
            return 'away_win'
        else:
            return 'draw'

    df['result'] = df.apply(get_result, axis=1)

    # 统计结果分布
    result_counts = df['result'].value_counts()
    print(f"📊 比赛结果分布:")
    for result, count in result_counts.items():
        print(f"   {result}: {count:,} ({count/len(df)*100:.1f}%)")

    return df

def prepare_features_and_target(df):
    """准备特征和目标变量"""
    print("🔧 准备特征和目标变量...")

    # 排除不必要的列
    exclude_cols = ['match_id', 'match_date', 'home_score', 'away_score',
                   'goal_difference', 'total_goals', 'result']

    # 获取特征列
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    print(f"📋 特征数量: {len(feature_cols)}")
    print(f"🔍 主要特征类别:")

    # 按类型分类特征
    rolling_features = [col for col in feature_cols if any(f'w{w}' in col for w in [5, 10, 15])]
    team_features = ['home_team_id', 'away_team_id']
    h2h_features = [col for col in feature_cols if 'h2h_' in col]
    advantage_features = [col for col in feature_cols if 'advantage' in col]

    print(f"   滚动窗口特征: {len(rolling_features)} 个")
    print(f"   球队ID特征: {len(team_features)} 个")
    print(f"   历史交锋特征: {len(h2h_features)} 个")
    print(f"   主场优势特征: {len(advantage_features)} 个")

    X = df[feature_cols].copy()
    y = df['result'].copy()

    # 处理缺失值
    X = X.fillna(X.median())

    # 标签编码
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print(f"✅ 特征矩阵: {X.shape}")
    print(f"✅ 目标变量: {len(le.classes_)} 个类别")

    return X, y_encoded, le, feature_cols

def train_xgboost_model(X, y, feature_cols):
    """训练XGBoost模型"""
    print("🚀 开始训练XGBoost模型...")

    # 分割训练测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"📊 训练集: {X_train.shape}, 测试集: {X_test.shape}")

    # XGBoost参数
    params = {
        'objective': 'multi:softmax',
        'num_class': len(np.unique(y)),
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'eval_metric': 'mlogloss'
    }

    # 训练模型
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              verbose=False)

    # 预测
    y_pred = model.predict(X_test)

    # 评估
    accuracy = accuracy_score(y_test, y_pred)
    print(f"🎯 模型准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")

    print(f"\n📊 详细分类报告:")
    print(classification_report(y_test, y_pred,
                               target_names=['away_win', 'draw', 'home_win']))

    return model, accuracy, (X_test, y_test, y_pred)

def analyze_feature_importance(model, feature_cols):
    """分析特征重要性"""
    print("🔍 分析特征重要性...")

    # 获取特征重要性
    importance = model.feature_importances_
    feature_importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)

    print(f"\n📊 特征重要性 Top 15:")
    for i, row in feature_importance_df.head(15).iterrows():
        print(f"   {row['feature']}: {row['importance']:.4f}")

    # 🎯 特别关注 rolling_form vs team_id
    rolling_form_features = [f for f in feature_cols if 'form_points_avg' in f]
    team_id_features = ['home_team_id', 'away_team_id']

    print(f"\n🏆 关键对比:")

    # 滚动特征 vs team_id
    max_rolling_importance = 0
    for feature in rolling_form_features:
        imp = feature_importance_df[feature_importance_df['feature'] == feature]['importance'].values
        if len(imp) > 0:
            max_rolling_importance = max(max_rolling_importance, imp[0])

    max_team_id_importance = 0
    for feature in team_id_features:
        imp = feature_importance_df[feature_importance_df['feature'] == feature]['importance'].values
        if len(imp) > 0:
            max_team_id_importance = max(max_team_id_importance, imp[0])

    print(f"   最高 rolling_form 重要性: {max_rolling_importance:.4f}")
    print(f"   最高 team_id 重要性: {max_team_id_importance:.4f}")

    if max_rolling_importance > max_team_id_importance:
        print(f"   🎉 SUCCESS! rolling_form 特征比 team_id 更重要!")
    else:
        print(f"   ⚠️  team_id 特征仍然更重要，需要进一步优化")

    return feature_importance_df

def save_results(model, feature_importance_df, accuracy):
    """保存结果"""
    print("💾 保存训练结果...")

    # 创建结果目录
    os.makedirs('/app/results', exist_ok=True)

    # 保存模型
    model_file = f"/app/results/xgboost_advanced_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    model.save_model(model_file)
    print(f"✅ 模型已保存: {model_file}")

    # 保存特征重要性
    importance_file = f"/app/results/feature_importance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    feature_importance_df.to_csv(importance_file, index=False)
    print(f"✅ 特征重要性已保存: {importance_file}")

    # 保存训练报告
    report_file = f"/app/results/training_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"XGBoost 模型训练报告\\n")
        f.write(f"{'='*50}\\n")
        f.write(f"训练时间: {datetime.now()}\\n")
        f.write(f"模型准确率: {accuracy:.4f} ({accuracy*100:.2f}%)\\n")
        f.write(f"特征数量: {len(feature_importance_df)}\\n\\n")

        f.write(f"特征重要性 Top 20:\\n")
        for i, row in feature_importance_df.head(20).iterrows():
            f.write(f"{i+1:2d}. {row['feature']}: {row['importance']:.4f}\\n")

    print(f"✅ 训练报告已保存: {report_file}")

    return model_file, importance_file, report_file

def main():
    """主函数"""
    try:
        # 1. 加载特征数据
        df = load_latest_features()

        # 2. 创建目标变量
        df = create_target_variable(df)

        # 3. 准备特征和目标变量
        X, y, le, feature_cols = prepare_features_and_target(df)

        # 4. 训练XGBoost模型
        model, accuracy, test_results = train_xgboost_model(X, y, feature_cols)

        # 5. 分析特征重要性
        feature_importance_df = analyze_feature_importance(model, feature_cols)

        # 6. 保存结果
        model_file, importance_file, report_file = save_results(model, feature_importance_df, accuracy)

        print(f"\\n🎉 模型训练完成!")
        print(f"📁 模型文件: {model_file}")
        print(f"📊 特征重要性: {importance_file}")
        print(f"📄 训练报告: {report_file}")
        print(f"🎯 最终准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")

        return model, feature_importance_df, accuracy

    except Exception as e:
        print(f"❌ 训练过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    main()