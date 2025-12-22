#!/usr/bin/env python3
"""
V9.5 真实数据严格验证
只使用有真实标签的 288 场比赛进行 Walk-Forward 验证
模拟数据仅用于展示，不参与训练
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

class RealDataWalkForward:
    """真实数据 Walk-Forward 验证"""

    def __init__(self):
        self.model = None
        self.calibrated_model = None
        self.feature_names = None

    def prepare_real_data(self, data_path):
        """准备真实数据（只有 288 场比赛有标签）"""
        print("📊 准备真实数据（仅使用有标签的 288 场比赛）...")
        df = pd.read_csv(data_path)
        print(f"  原始数据: {len(df)} 场比赛")

        # 只保留有真实标签的数据
        df_real = df[df['target'].notna() & (df['target'] >= 0)].copy()
        print(f"  真实数据: {len(df_real)} 场比赛")

        # 转换日期并排序
        df_real['match_date'] = pd.to_datetime(df_real['match_date'])
        df_real = df_real.sort_values('match_date').reset_index(drop=True)

        # 按时间严格分割
        # 训练集: 2019-01-01 到 2022-06-30 (70% 的真实数据)
        train_mask = (df_real['match_date'] >= '2019-01-01') & (df_real['match_date'] <= '2022-06-30')

        # 校准集: 2022-07-01 到 2023-06-30 (15% 的真实数据)
        cal_mask = (df_real['match_date'] >= '2022-07-01') & (df_real['match_date'] <= '2023-06-30')

        # 测试集: 2023-07-01 到 2024-12-31 (15% 的真实数据)
        test_mask = (df_real['match_date'] >= '2023-07-01') & (df_real['match_date'] <= '2024-12-31')

        # 提取各数据集
        df_train = df_real[train_mask].copy()
        df_cal = df_real[cal_mask].copy()
        df_test = df_real[test_mask].copy()

        print(f"\n📅 真实数据时间分割:")
        print(f"  训练集 (2019-2022H1): {len(df_train)} 场")
        if len(df_train) > 0:
            print(f"    时间范围: {df_train['match_date'].min()} 到 {df_train['match_date'].max()}")
        print(f"  校准集 (2022H2-2023H1): {len(df_cal)} 场")
        if len(df_cal) > 0:
            print(f"    时间范围: {df_cal['match_date'].min()} 到 {df_cal['match_date'].max()}")
        print(f"  测试集 (2023H2-2024): {len(df_test)} 场")
        if len(df_test) > 0:
            print(f"    时间范围: {df_test['match_date'].min()} 到 {df_test['match_date'].max()}")

        # 检查数据量是否足够
        if len(df_train) < 50 or len(df_cal) < 20 or len(df_test) < 20:
            print(f"\n⚠️  警告: 某些数据集样本量过小，可能影响验证结果")

        # 准备特征
        feature_cols = [col for col in df_real.columns if col not in [
            'target', 'season', 'match_date', 'home_team_name', 'away_team_name'
        ]]

        self.feature_names = feature_cols

        # 转换为 numpy 数组
        X_train = df_train[feature_cols].fillna(0).values if len(df_train) > 0 else np.array([])
        y_train = df_train['target'].values if len(df_train) > 0 else np.array([])

        X_cal = df_cal[feature_cols].fillna(0).values if len(df_cal) > 0 else np.array([])
        y_cal = df_cal['target'].values if len(df_cal) > 0 else np.array([])

        X_test = df_test[feature_cols].fillna(0).values if len(df_test) > 0 else np.array([])
        y_test = df_test['target'].values if len(df_test) > 0 else np.array([])

        print(f"\n📊 标签分布:")
        if len(df_train) > 0:
            print(f"  训练集 - 主胜率: {y_train.mean():.1%} ({y_train.sum()}/{len(y_train)})")
        if len(df_cal) > 0:
            print(f"  校准集 - 主胜率: {y_cal.mean():.1%} ({y_cal.sum()}/{len(y_cal)})")
        if len(df_test) > 0:
            print(f"  测试集 - 主胜率: {y_test.mean():.1%} ({y_test.sum()}/{len(y_test)})")

        return {
            'train': (X_train, y_train),
            'cal': (X_cal, y_cal),
            'test': (X_test, y_test),
            'df_train': df_train,
            'df_cal': df_cal,
            'df_test': df_test
        }

    def train_real_data_model(self, data):
        """真实数据严格训练"""
        print("\n🎯 真实数据严格训练...")
        print("=" * 80)

        X_train, y_train = data['train']
        X_cal, y_cal = data['cal']
        X_test, y_test = data['test']

        # 检查数据量
        if len(X_train) == 0 or len(X_test) == 0:
            print("❌ 错误: 训练集或测试集为空，无法进行验证")
            return None

        print(f"🔒 真实数据训练规则:")
        print(f"  ✅ 训练集: {len(X_train)} 样本")
        print(f"  🔒 校准集: {len(X_cal)} 样本")
        print(f"  🚫 测试集: {len(X_test)} 样本 - 严格时间外")

        # 训练基础模型
        print(f"\n第一步：基础模型训练...")
        base_model = lgb.LGBMClassifier(
            n_estimators=100,  # 减少树的数量防止过拟合
            max_depth=5,
            learning_rate=0.1,
            num_leaves=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=1.0,  # 增加正则化
            reg_lambda=1.0,
            random_state=42,
            verbose=-1
        )

        base_model.fit(X_train, y_train)

        # 在训练集上的性能
        train_probs = base_model.predict_proba(X_train)[:, 1]
        train_brier = brier_score_loss(y_train, train_probs)
        train_auc = roc_auc_score(y_train, train_probs)

        print(f"  训练集性能:")
        print(f"    Brier Score: {train_brier:.4f}")
        print(f"    AUC Score: {train_auc:.4f}")

        # 校准
        print(f"\n第二步：Isotonic Regression 校准...")
        if len(X_cal) > 10:  # 校准集需要足够样本
            self.calibrated_model = CalibratedClassifierCV(
                base_model, method='isotonic', cv=min(3, len(X_cal)//5)
            )
            self.calibrated_model.fit(X_cal, y_cal)

            # 在校准集上的性能
            cal_probs = self.calibrated_model.predict_proba(X_cal)[:, 1]
            cal_brier = brier_score_loss(y_cal, cal_probs)
            cal_auc = roc_auc_score(y_cal, cal_probs)

            print(f"  校准集性能:")
            print(f"    Brier Score: {cal_brier:.4f}")
            print(f"    AUC Score: {cal_auc:.4f}")
        else:
            print(f"  ⚠️  校准集样本不足，跳过校准")
            self.calibrated_model = base_model

        # 在测试集上验证
        print(f"\n第三步：严格时间外验证...")
        test_probs = self.calibrated_model.predict_proba(X_test)[:, 1]
        test_pred = (test_probs > 0.5).astype(int)

        test_brier = brier_score_loss(y_test, test_probs)
        test_auc = roc_auc_score(y_test, test_probs)
        test_acc = accuracy_score(y_test, test_pred)

        print(f"  🚫 测试集性能 (严格时间外):")
        print(f"    Brier Score: {test_brier:.4f}")
        print(f"    AUC Score: {test_auc:.4f}")
        print(f"    Accuracy: {test_acc:.4f}")

        # Brier Score 诊断
        print(f"\n🔍 Brier Score 诊断:")
        if test_brier < 0.1:
            print(f"  ❌ 失败: Brier Score {test_brier:.4f} < 0.1，仍存在数据泄露!")
            status = "FAILED"
        elif 0.18 <= test_brier <= 0.25:
            print(f"  ✅ 优秀: Brier Score {test_brier:.4f} 在理想范围内 [0.18-0.25]")
            status = "EXCELLENT"
        elif 0.1 <= test_brier < 0.18:
            print(f"  ✅ 正常: Brier Score {test_brier:.4f} 在可接受范围内 [0.1-0.18]")
            status = "GOOD"
        elif 0.25 < test_brier <= 0.3:
            print(f"  ⚠️  一般: Brier Score {test_brier:.4f} 在边缘范围 (0.25-0.3)")
            status = "ACCEPTABLE"
        else:
            print(f"  ❌ 较差: Brier Score {test_brier:.4f} > 0.3，模型表现不佳")
            status = "POOR"

        # 保存模型
        output_dir = "/home/user/projects/FootballPrediction/src/production_models"
        os.makedirs(output_dir, exist_ok=True)

        model_path = os.path.join(output_dir, 'v9_5_real_data_model.pkl')
        joblib.dump(self.calibrated_model, model_path)

        features_path = os.path.join(output_dir, 'v9_5_real_data_features.json')
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)

        metadata = {
            'version': 'V9.5',
            'validation_method': 'Real Data Walk-Forward Validation',
            'training_date': datetime.now().isoformat(),
            'data_source': 'Only labeled matches (288 total)',
            'model_type': 'LightGBM + Isotonic Regression',
            'train_size': len(X_train),
            'cal_size': len(X_cal),
            'test_size': len(X_test),
            'test_brier_score': test_brier,
            'test_auc_score': test_auc,
            'test_accuracy': test_acc,
            'status': status
        }

        metadata_path = os.path.join(output_dir, 'v9_5_real_data_metadata.json')
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
            'df_test': data['df_test']
        }

def main():
    """主函数"""
    print("=" * 80)
    print("🔒 V9.5 真实数据严格验证 - Walk-Forward")
    print("=" * 80)

    validator = RealDataWalkForward()

    # 准备真实数据
    data_path = "/home/user/projects/FootballPrediction/data/v9_5_sanitized_features.csv"
    data = validator.prepare_real_data(data_path)

    # 真实数据严格训练
    result = validator.train_real_data_model(data)

    if result is None:
        print("\n❌ 训练失败: 数据不足")
        return None

    # 最终报告
    print("\n" + "=" * 80)
    print("✅ V9.5 真实数据严格验证完成")
    print("=" * 80)
    print(f"  🔒 时间隔离: 已建立")
    print(f"  📊 真实数据: 仅使用有标签的 288 场比赛")
    print(f"  📈 测试性能:")
    print(f"    - Brier Score: {result['test_metrics']['brier_score']:.4f}")
    print(f"    - AUC Score: {result['test_metrics']['auc_score']:.4f}")
    print(f"    - Accuracy: {result['test_metrics']['accuracy']:.4f}")
    print(f"  🎯 状态: {result['status']}")

    return validator, result

if __name__ == "__main__":
    validator, result = main()
