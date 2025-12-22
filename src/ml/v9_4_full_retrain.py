#!/usr/bin/env python3
"""
V9.4 全量数据重训器
使用 2188 场大规模数据集进行 Time-Series Cross-Validation 重训
应用 Isotonic Regression 进行概率校准
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score, accuracy_score
import joblib
import json
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TimeSeriesCrossValidator:
    """时间序列交叉验证器"""

    def __init__(self, n_splits=5, test_size=0.2):
        self.n_splits = n_splits
        self.test_size = test_size

    def split(self, X, y, dates):
        """时间序列分割"""
        n = len(X)
        test_split_size = int(n * self.test_size)

        for i in range(self.n_splits):
            # 计算分割点
            train_end = n - (self.n_splits - i) * test_split_size
            test_start = train_end
            test_end = test_start + test_split_size

            if test_end > n:
                test_end = n

            if train_end <= 0:
                break

            # 生成索引
            train_indices = np.arange(0, train_end)
            test_indices = np.arange(test_start, test_end)

            yield train_indices, test_indices

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits

class V94FullRetrainer:
    """V9.4 全量重训器"""

    def __init__(self):
        self.model = None
        self.calibrated_model = None
        self.scaler = None
        self.feature_names = None

    def prepare_data(self, data_path):
        """准备训练数据"""
        print("📊 准备 V9.4 全量训练数据...")
        df = pd.read_csv(data_path)
        print(f"  原始数据量: {len(df)} 场比赛")

        # 过滤有效数据
        valid_df = df[
            df['real_home_odds'].notna() &
            df['real_draw_odds'].notna() &
            df['real_away_odds'].notna() &
            df['actual_result'].notna()
        ].copy()

        print(f"  有效数据量: {len(valid_df)} 场比赛")

        # 转换日期
        valid_df['match_date'] = pd.to_datetime(valid_df['match_date'])
        valid_df = valid_df.sort_values('match_date').reset_index(drop=True)

        # 准备特征
        numeric_cols = valid_df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = [
            'real_home_odds', 'real_draw_odds', 'real_away_odds',
            'real_match_date', 'real_season', 'actual_home_goals',
            'actual_away_goals', 'season', 'match_date'
        ]

        self.feature_names = [col for col in numeric_cols if col not in exclude_cols]
        X = valid_df[self.feature_names].fillna(0)
        y = (valid_df['actual_result'] == 'H').astype(int)

        # 添加赔率特征 (重要！)
        X['home_prob'] = 1 / valid_df['real_home_odds']
        X['draw_prob'] = 1 / valid_df['real_draw_odds']
        X['away_prob'] = 1 / valid_df['real_away_odds']
        X['total_prob'] = X['home_prob'] + X['draw_prob'] + X['away_prob']
        X['home_prob_norm'] = X['home_prob'] / X['total_prob']
        X['draw_prob_norm'] = X['draw_prob'] / X['total_prob']
        X['away_prob_norm'] = X['away_prob'] / X['total_prob']

        # 计算 xG 差异 (如果存在)
        if 'home_xg' in valid_df.columns and 'away_xg' in valid_df.columns:
            X['xg_diff'] = valid_df['home_xg'] - valid_df['away_xg']

        print(f"  最终特征维度: {X.shape}")
        print(f"  主胜样本: {y.sum()} ({y.mean()*100:.1f}%)")

        return X.values, y.values, valid_df['match_date'].values, valid_df

    def time_series_cross_validate(self, X, y, dates):
        """时间序列交叉验证"""
        print("\n🔄 执行时间序列交叉验证...")

        tscv = TimeSeriesCrossValidator(n_splits=5, test_size=0.2)
        cv_scores = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X, y, dates)):
            print(f"\n  Fold {fold + 1}/5:")
            print(f"    训练集: {len(train_idx)} 样本 ({dates[train_idx[0]]} 到 {dates[train_idx[-1]]})")
            print(f"    测试集: {len(test_idx)} 样本 ({dates[test_idx[0]]} 到 {dates[test_idx[-1]]})")

            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # 训练基础模型
            model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbose=-1
            )
            model.fit(X_train, y_train)

            # 校准模型
            calibrated_model = CalibratedClassifierCV(
                model, method='isotonic', cv=3
            )
            calibrated_model.fit(X_train, y_train)

            # 预测和评估
            y_pred_proba = calibrated_model.predict_proba(X_test)[:, 1]
            y_pred = calibrated_model.predict(X_test)

            # 计算指标
            brier = brier_score_loss(y_test, y_pred_proba)
            auc = roc_auc_score(y_test, y_pred_proba)
            acc = accuracy_score(y_test, y_pred)

            cv_scores.append({
                'fold': fold + 1,
                'brier_score': brier,
                'auc_score': auc,
                'accuracy': acc
            })

            print(f"    Brier Score: {brier:.4f}")
            print(f"    AUC Score: {auc:.4f}")
            print(f"    Accuracy: {acc:.4f}")

        # 计算平均分数
        avg_brier = np.mean([s['brier_score'] for s in cv_scores])
        avg_auc = np.mean([s['auc_score'] for s in cv_scores])
        avg_acc = np.mean([s['accuracy'] for s in cv_scores])

        print(f"\n📊 时间序列交叉验证平均分数:")
        print(f"  Brier Score: {avg_brier:.4f}")
        print(f"  AUC Score: {avg_auc:.4f}")
        print(f"  Accuracy: {avg_acc:.4f}")

        return cv_scores

    def train_final_model(self, X, y):
        """训练最终模型"""
        print("\n🎯 训练最终 V9.4 模型...")

        # 使用所有数据训练最终模型
        final_model = lgb.LGBMClassifier(
            n_estimators=300,  # 增加树的数量
            max_depth=10,
            learning_rate=0.08,
            num_leaves=50,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            verbose=-1
        )

        # 校准
        self.calibrated_model = CalibratedClassifierCV(
            final_model, method='isotonic', cv=5
        )

        print("  正在训练模型...")
        self.calibrated_model.fit(X, y)

        # 计算训练集性能
        y_pred_proba = self.calibrated_model.predict_proba(X)[:, 1]
        y_pred = self.calibrated_model.predict(X)

        train_brier = brier_score_loss(y, y_pred_proba)
        train_auc = roc_auc_score(y, y_pred_proba)
        train_acc = accuracy_score(y, y_pred)

        print(f"  训练集性能:")
        print(f"    Brier Score: {train_brier:.4f}")
        print(f"    AUC Score: {train_auc:.4f}")
        print(f"    Accuracy: {train_acc:.4f}")

        return {
            'brier_score': train_brier,
            'auc_score': train_auc,
            'accuracy': train_acc
        }

    def save_model(self, output_dir):
        """保存模型"""
        print(f"\n💾 保存模型到 {output_dir}...")

        os.makedirs(output_dir, exist_ok=True)

        # 保存校准模型
        model_path = os.path.join(output_dir, 'v9_4_calibrated_model.pkl')
        joblib.dump(self.calibrated_model, model_path)

        # 保存特征名称
        features_path = os.path.join(output_dir, 'v9_4_feature_names.json')
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)

        # 保存模型元数据
        metadata = {
            'version': 'V9.4',
            'training_date': datetime.now().isoformat(),
            'model_type': 'LightGBM + Isotonic Regression',
            'n_features': len(self.feature_names),
            'feature_names': self.feature_names
        }

        metadata_path = os.path.join(output_dir, 'v9_4_model_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"  ✅ 模型已保存:")
        print(f"    - {model_path}")
        print(f"    - {features_path}")
        print(f"    - {metadata_path}")

        return {
            'model_path': model_path,
            'features_path': features_path,
            'metadata_path': metadata_path
        }

def main():
    """主函数"""
    print("=" * 70)
    print("🚀 V9.4 全量数据重训 - Time-Series CV + Isotonic Regression")
    print("=" * 70)

    retrainer = V94FullRetrainer()

    # 准备数据
    data_path = "/home/user/projects/FootballPrediction/data/v9_3_comprehensive_dataset.csv"
    X, y, dates, df = retrainer.prepare_data(data_path)

    # 时间序列交叉验证
    cv_scores = retrainer.time_series_cross_validate(X, y, dates)

    # 训练最终模型
    final_metrics = retrainer.train_final_model(X, y)

    # 保存模型
    output_dir = "/home/user/projects/FootballPrediction/src/production_models"
    saved_paths = retrainer.save_model(output_dir)

    # 生成训练报告
    print("\n" + "=" * 70)
    print("✅ V9.4 全量重训完成")
    print("=" * 70)
    print(f"  📊 训练数据: {len(X)} 场比赛")
    print(f"  🔧 模型类型: LightGBM + Isotonic Regression")
    print(f"  📈 验证方法: Time-Series Cross-Validation (5-Fold)")
    print(f"  🎯 最终性能:")
    print(f"    - Brier Score: {final_metrics['brier_score']:.4f}")
    print(f"    - AUC Score: {final_metrics['auc_score']:.4f}")
    print(f"    - Accuracy: {final_metrics['accuracy']:.4f}")

    return retrainer, cv_scores, final_metrics

if __name__ == "__main__":
    retrainer, cv_scores, final_metrics = main()
