#!/usr/bin/env python3
"""
V9.5 严格时间轴训练 - Walk-Forward Validation
建立不可逾越的"时间隔离带"
- 2019-2022: 训练集
- 2023: 校准集 (Isotonic Regression)
- 2024-2025: 测试集 (从未见过)
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score, accuracy_score
import joblib
import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class WalkForwardValidator:
    """严格时间轴验证器"""

    def __init__(self):
        self.model = None
        self.calibrated_model = None
        self.feature_names = None

    def prepare_data(self, data_path):
        """准备严格时间分割数据"""
        print("📊 准备严格时间分割数据...")
        df = pd.read_csv(data_path)
        print(f"  原始数据: {len(df)} 场比赛")

        # 转换日期
        df['match_date'] = pd.to_datetime(df['match_date'])
        df = df.sort_values('match_date').reset_index(drop=True)

        # 按时间严格分割
        # 训练集: 2019-01-01 到 2022-12-31
        train_mask = (df['match_date'] >= '2019-01-01') & (df['match_date'] <= '2022-12-31')

        # 校准集: 2023-01-01 到 2023-12-31
        cal_mask = (df['match_date'] >= '2023-01-01') & (df['match_date'] <= '2023-12-31')

        # 测试集: 2024-01-01 到 2025-12-31
        test_mask = (df['match_date'] >= '2024-01-01') & (df['match_date'] <= '2025-12-31')

        # 提取各数据集
        df_train = df[train_mask].copy()
        df_cal = df[cal_mask].copy()
        df_test = df[test_mask].copy()

        print(f"\n📅 时间分割结果:")
        print(f"  训练集 (2019-2022): {len(df_train)} 场")
        print(f"    时间范围: {df_train['match_date'].min()} 到 {df_train['match_date'].max()}")
        print(f"  校准集 (2023): {len(df_cal)} 场")
        print(f"    时间范围: {df_cal['match_date'].min()} 到 {df_cal['match_date'].max()}")
        print(f"  测试集 (2024-2025): {len(df_test)} 场")
        print(f"    时间范围: {df_test['match_date'].min()} 到 {df_test['match_date'].max()}")

        # 准备特征
        feature_cols = [col for col in df.columns if col not in [
            'target', 'season', 'match_date', 'home_team_name', 'away_team_name'
        ]]

        self.feature_names = feature_cols

        # 训练集
        X_train = df_train[feature_cols].fillna(0)
        y_train = df_train['target']

        # 校准集
        X_cal = df_cal[feature_cols].fillna(0)
        y_cal = df_cal['target']

        # 测试集
        X_test = df_test[feature_cols].fillna(0)
        y_test = df_test['target']

        print(f"\n📊 标签分布:")
        print(f"  训练集 - 主胜率: {y_train.mean():.1%} ({y_train.sum()}/{len(y_train)})")
        print(f"  校准集 - 主胜率: {y_cal.mean():.1%} ({y_cal.sum()}/{len(y_cal)})")
        print(f"  测试集 - 主胜率: {y_test.mean():.1%} ({y_test.sum()}/{len(y_test)})")

        return {
            'train': (X_train.values, y_train.values),
            'cal': (X_cal.values, y_cal.values),
            'test': (X_test.values, y_test.values),
            'df_train': df_train,
            'df_cal': df_cal,
            'df_test': df_test
        }

    def train_with_time_isolation(self, data):
        """严格时间隔离训练"""
        print("\n🎯 严格时间隔离训练...")
        print("=" * 80)

        X_train, y_train = data['train']
        X_cal, y_cal = data['cal']
        X_test, y_test = data['test']

        print(f"🔒 时间隔离规则:")
        print(f"  ✅ 训练集 (2019-2022): {len(X_train)} 样本")
        print(f"  🔒 校准集 (2023): {len(X_cal)} 样本 - 仅用于校准")
        print(f"  🚫 测试集 (2024-2025): {len(X_test)} 样本 - 训练时从未接触")

        # 第一步：训练基础模型 (仅使用训练集)
        print(f"\n第一步：基础模型训练...")
        base_model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            num_leaves=40,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            verbose=-1
        )

        base_model.fit(X_train, y_train)

        # 在训练集上的性能
        train_probs = base_model.predict_proba(X_train)[:, 1]
        train_brier = brier_score_loss(y_train, train_probs)
        train_auc = roc_auc_score(y_train, train_probs)
        train_acc = accuracy_score(y_train, train_probs > 0.5)

        print(f"  训练集性能:")
        print(f"    Brier Score: {train_brier:.4f}")
        print(f"    AUC Score: {train_auc:.4f}")
        print(f"    Accuracy: {train_acc:.4f}")

        # 第二步：Isotonic Regression 校准 (使用校准集)
        print(f"\n第二步：Isotonic Regression 校准...")
        self.calibrated_model = CalibratedClassifierCV(
            base_model, method='isotonic', cv=3
        )

        # 仅在 2023 年数据上校准
        self.calibrated_model.fit(X_cal, y_cal)

        # 在校准集上的性能
        cal_probs = self.calibrated_model.predict_proba(X_cal)[:, 1]
        cal_brier = brier_score_loss(y_cal, cal_probs)
        cal_auc = roc_auc_score(y_cal, cal_probs)
        cal_acc = accuracy_score(y_cal, cal_probs > 0.5)

        print(f"  校准集性能:")
        print(f"    Brier Score: {cal_brier:.4f}")
        print(f"    AUC Score: {cal_auc:.4f}")
        print(f"    Accuracy: {cal_acc:.4f}")

        # 第三步：在测试集上验证 (严格时间外)
        print(f"\n第三步：严格时间外验证...")
        test_probs = self.calibrated_model.predict_proba(X_test)[:, 1]
        test_pred = (test_probs > 0.5).astype(int)

        test_brier = brier_score_loss(y_test, test_probs)
        test_auc = roc_auc_score(y_test, test_probs)
        test_acc = accuracy_score(y_test, test_pred)

        print(f"  🚫 测试集性能 (2024-2025, 严格时间外):")
        print(f"    Brier Score: {test_brier:.4f}")
        print(f"    AUC Score: {test_auc:.4f}")
        print(f"    Accuracy: {test_acc:.4f}")

        # Brier Score 诊断
        print(f"\n🔍 Brier Score 诊断:")
        if test_brier < 0.1:
            print(f"  ⚠️  WARNING: Brier Score {test_brier:.4f} < 0.1，可能仍存在数据泄露!")
            status = "FAILED"
        elif 0.18 <= test_brier <= 0.25:
            print(f"  ✅ 正常: Brier Score {test_brier:.4f} 在合理范围内 [0.18-0.25]")
            status = "PASSED"
        elif 0.1 <= test_brier < 0.18:
            print(f"  ⚠️  谨慎: Brier Score {test_brier:.4f} 在 0.1-0.18，需监控")
            status = "CAUTION"
        else:
            print(f"  ⚠️  异常: Brier Score {test_brier:.4f} > 0.25，需调整模型")
            status = "WARNING"

        # 保存训练好的模型
        output_dir = "/home/user/projects/FootballPrediction/src/production_models"
        os.makedirs(output_dir, exist_ok=True)

        model_path = os.path.join(output_dir, 'v9_5_walk_forward_model.pkl')
        joblib.dump(self.calibrated_model, model_path)

        features_path = os.path.join(output_dir, 'v9_5_walk_forward_features.json')
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)

        metadata = {
            'version': 'V9.5',
            'validation_method': 'Walk-Forward Validation',
            'training_date': datetime.now().isoformat(),
            'train_period': '2019-2022',
            'cal_period': '2023',
            'test_period': '2024-2025',
            'model_type': 'LightGBM + Isotonic Regression',
            'test_brier_score': test_brier,
            'test_auc_score': test_auc,
            'test_accuracy': test_acc,
            'status': status
        }

        metadata_path = os.path.join(output_dir, 'v9_5_walk_forward_metadata.json')
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
            'test_data': (X_test, y_test, test_probs)
        }

def main():
    """主函数"""
    print("=" * 80)
    print("🔒 V9.5 严格时间轴训练 - Walk-Forward Validation")
    print("=" * 80)

    validator = WalkForwardValidator()

    # 准备数据
    data_path = "/home/user/projects/FootballPrediction/data/v9_5_sanitized_features.csv"
    data = validator.prepare_data(data_path)

    # 严格时间隔离训练
    result = validator.train_with_time_isolation(data)

    # 最终报告
    print("\n" + "=" * 80)
    print("✅ V9.5 严格时间轴训练完成")
    print("=" * 80)
    print(f"  🔒 时间隔离: 已建立")
    print(f"  📊 训练集: 2019-2022 ({len(data['train'][0])} 样本)")
    print(f"  🎯 校准集: 2023 ({len(data['cal'][0])} 样本)")
    print(f"  🚫 测试集: 2024-2025 ({len(data['test'][0])} 样本)")
    print(f"  📈 测试性能:")
    print(f"    - Brier Score: {result['test_metrics']['brier_score']:.4f}")
    print(f"    - AUC Score: {result['test_metrics']['auc_score']:.4f}")
    print(f"    - Accuracy: {result['test_metrics']['accuracy']:.4f}")
    print(f"  🎯 状态: {result['status']}")

    return validator, result

if __name__ == "__main__":
    validator, result = main()
