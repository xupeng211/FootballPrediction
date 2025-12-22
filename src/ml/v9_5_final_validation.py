#!/usr/bin/env python3
"""
V9.5 最终验证 - 最小化特征集
只使用绝对安全的特征：真实赔率 + 时间特征
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import brier_score_loss, roc_auc_score, accuracy_score
import joblib
import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class FinalValidator:
    """最终验证器"""

    def __init__(self):
        self.model = None

    def prepare_minimal_safe_data(self, data_path):
        """准备最小安全数据集"""
        print("📊 准备最小安全数据集...")
        df = pd.read_csv(data_path)
        print(f"  原始数据: {len(df)} 场比赛")

        # 只保留绝对安全的特征
        minimal_features = [
            'year',
            'month',
            'day_of_week',
            'is_weekend',
            'league_id',
            # 真实赔率 (赛前可得)
            'real_home_odds',
            'real_draw_odds',
            'real_away_odds',
        ]

        # 检查特征是否存在
        available_features = [f for f in minimal_features if f in df.columns]
        print(f"  可用特征: {available_features}")

        # 创建最小数据集
        df_minimal = df[available_features + ['target', 'match_date']].copy()

        # 只保留有标签的数据
        df_labeled = df_minimal[df_minimal['target'].notna()].copy()
        print(f"  有标签数据: {len(df_labeled)} 场比赛")

        # 转换日期并排序
        df_labeled['match_date'] = pd.to_datetime(df_labeled['match_date'])
        df_labeled = df_labeled.sort_values('match_date').reset_index(drop=True)

        # 时间分割
        # 训练集: 2019-01-01 到 2022-06-30
        train_mask = (df_labeled['match_date'] >= '2019-01-01') & (df_labeled['match_date'] <= '2022-06-30')

        # 测试集: 2023-01-01 到 2024-12-31
        test_mask = (df_labeled['match_date'] >= '2023-01-01') & (df_labeled['match_date'] <= '2024-12-31')

        df_train = df_labeled[train_mask].copy()
        df_test = df_labeled[test_mask].copy()

        print(f"\n📅 时间分割:")
        print(f"  训练集 (2019-2022H1): {len(df_train)} 场")
        print(f"    主胜率: {df_train['target'].mean():.1%}")
        print(f"  测试集 (2023-2024): {len(df_test)} 场")
        print(f"    主胜率: {df_test['target'].mean():.1%}")

        # 检查数据量
        if len(df_train) < 20 or len(df_test) < 20:
            print(f"\n⚠️  警告: 数据量不足")

        # 准备特征
        feature_cols = available_features

        X_train = df_train[feature_cols].fillna(0).values
        y_train = df_train['target'].values

        X_test = df_test[feature_cols].fillna(0).values
        y_test = df_test['target'].values

        return {
            'train': (X_train, y_train),
            'test': (X_test, y_test),
            'feature_names': feature_cols,
            'df_train': df_train,
            'df_test': df_test
        }

    def train_minimal_model(self, data):
        """训练最小模型"""
        print("\n🎯 训练最小模型...")
        print("=" * 80)

        X_train, y_train = data['train']
        X_test, y_test = data['test']
        feature_names = data['feature_names']

        print(f"🔒 最小安全训练:")
        print(f"  特征数: {len(feature_names)}")
        print(f"  特征列表: {feature_names}")
        print(f"  训练集: {len(X_train)} 样本")
        print(f"  测试集: {len(X_test)} 样本")

        # 训练简单模型
        print(f"\n第一步：基础模型训练...")
        model = lgb.LGBMClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            num_leaves=10,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=2.0,  # 强正则化
            reg_lambda=2.0,
            random_state=42,
            verbose=-1
        )

        model.fit(X_train, y_train)

        # 训练集性能
        train_probs = model.predict_proba(X_train)[:, 1]
        train_brier = brier_score_loss(y_train, train_probs)
        train_auc = roc_auc_score(y_train, train_probs) if len(np.unique(y_train)) > 1 else 0

        print(f"  训练集性能:")
        print(f"    Brier Score: {train_brier:.4f}")
        print(f"    AUC Score: {train_auc:.4f}")

        # 测试集性能
        print(f"\n第二步：严格时间外测试...")
        test_probs = model.predict_proba(X_test)[:, 1]
        test_pred = (test_probs > 0.5).astype(int)

        test_brier = brier_score_loss(y_test, test_probs)
        test_auc = roc_auc_score(y_test, test_probs)
        test_acc = accuracy_score(y_test, test_pred)

        print(f"  🚫 测试集性能 (2023-2024):")
        print(f"    Brier Score: {test_brier:.4f}")
        print(f"    AUC Score: {test_auc:.4f}")
        print(f"    Accuracy: {test_acc:.4f}")

        # Brier Score 诊断
        print(f"\n🔍 Brier Score 诊断:")
        if test_brier < 0.1:
            print(f"  ❌ 失败: Brier Score {test_brier:.4f} < 0.1，仍存在数据泄露!")
            status = "FAILED"
        elif 0.18 <= test_brier <= 0.25:
            print(f"  ✅ 优秀: Brier Score {test_brier:.4f} 在理想范围 [0.18-0.25]")
            status = "EXCELLENT"
        elif 0.1 <= test_brier < 0.18:
            print(f"  ✅ 正常: Brier Score {test_brier:.4f} 在可接受范围 [0.1-0.18]")
            status = "GOOD"
        elif 0.25 < test_brier <= 0.3:
            print(f"  ⚠️ 一般: Brier Score {test_brier:.4f} 在边缘范围 (0.25-0.3)")
            status = "ACCEPTABLE"
        else:
            print(f"  ❌ 较差: Brier Score {test_brier:.4f} > 0.3，模型表现不佳")
            status = "POOR"

        # 保存模型
        output_dir = "/home/user/projects/FootballPrediction/src/production_models"
        os.makedirs(output_dir, exist_ok=True)

        model_path = os.path.join(output_dir, 'v9_5_final_minimal_model.pkl')
        joblib.dump(model, model_path)

        features_path = os.path.join(output_dir, 'v9_5_final_minimal_features.json')
        with open(features_path, 'w') as f:
            json.dump(feature_names, f)

        metadata = {
            'version': 'V9.5',
            'validation_method': 'Minimal Safe Feature Validation',
            'training_date': datetime.now().isoformat(),
            'model_type': 'LightGBM (Minimal Features)',
            'n_features': len(feature_names),
            'feature_names': feature_names,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'test_brier_score': test_brier,
            'test_auc_score': test_auc,
            'test_accuracy': test_acc,
            'status': status
        }

        metadata_path = os.path.join(output_dir, 'v9_5_final_minimal_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n💾 模型已保存:")
        print(f"  - {model_path}")
        print(f"  - {features_path}")
        print(f"  - {metadata_path}")

        return {
            'model_path': model_path,
            'features_path': features_path,
            'metadata_path': metadata_path,
            'test_metrics': {
                'brier_score': test_brier,
                'auc_score': test_auc,
                'accuracy': test_acc
            },
            'status': status,
            'test_data': (X_test, y_test, test_probs),
            'feature_names': feature_names
        }

def main():
    """主函数"""
    print("=" * 80)
    print("🔒 V9.5 最终验证 - 最小化特征集")
    print("=" * 80)

    validator = FinalValidator()

    # 准备最小安全数据
    data_path = "/home/user/projects/FootballPrediction/data/v9_5_ultra_safe_features.csv"
    data = validator.prepare_minimal_safe_data(data_path)

    # 训练最小模型
    result = validator.train_minimal_model(data)

    # 最终报告
    print("\n" + "=" * 80)
    print("✅ V9.5 最终验证完成")
    print("=" * 80)
    print(f"  🔒 最小特征集: {len(data['feature_names'])} 个")
    print(f"  📊 训练集: {len(data['train'][0])} 样本")
    print(f"  🚫 测试集: {len(data['test'][0])} 样本")
    print(f"  📈 测试性能:")
    print(f"    - Brier Score: {result['test_metrics']['brier_score']:.4f}")
    print(f"    - AUC Score: {result['test_metrics']['auc_score']:.4f}")
    print(f"    - Accuracy: {result['test_metrics']['accuracy']:.4f}")
    print(f"  🎯 状态: {result['status']}")

    return validator, result

if __name__ == "__main__":
    validator, result = main()
