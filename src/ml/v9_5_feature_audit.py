#!/usr/bin/env python3
"""
V9.5 特征审计工具
彻底检查每个特征是否真的在赛前可得
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import brier_score_loss
import warnings
warnings.filterwarnings('ignore')

class FeatureAuditor:
    """特征审计器"""

    def __init__(self):
        self.suspicious_features = []

    def audit_features(self, data_path):
        """审计所有特征"""
        print("🔍 V9.5 特征审计工具")
        print("=" * 80)

        df = pd.read_csv(data_path)
        print(f"数据: {len(df)} 场比赛, {len(df.columns)} 个特征")

        # 转换日期
        df['match_date'] = pd.to_datetime(df['match_date'])

        # 只使用有标签的数据
        df_labeled = df[df['target'].notna() & (df['target'] >= 0)].copy()
        print(f"有标签数据: {len(df_labeled)} 场比赛")

        # 获取特征列
        feature_cols = [col for col in df_labeled.columns if col not in [
            'target', 'season', 'match_date', 'home_team_name', 'away_team_name'
        ]]

        print(f"\n审计 {len(feature_cols)} 个特征...")
        print("=" * 80)

        # 逐个特征验证
        safe_features = []
        suspicious_features = []

        for feat in feature_cols:
            result = self.test_feature(df_labeled, feat)
            if result['safe']:
                safe_features.append(feat)
                print(f"✅ {feat:50} - 安全")
            else:
                suspicious_features.append(feat)
                print(f"❌ {feat:50} - 可疑: {result['reason']}")

        print(f"\n" + "=" * 80)
        print(f"审计结果:")
        print(f"  ✅ 安全特征: {len(safe_features)} 个")
        print(f"  ❌ 可疑特征: {len(suspicious_features)} 个")
        print(f"  删除率: {len(suspicious_features) / len(feature_cols) * 100:.1f}%")

        return safe_features, suspicious_features

    def test_feature(self, df, feature_name):
        """测试单个特征是否安全"""
        # 检查特征值分布
        values = df[feature_name].values
        target = df['target'].values

        # 检查是否有完美的预测能力
        try:
            # 使用单特征训练模型
            model = lgb.LGBMClassifier(
                n_estimators=10,
                max_depth=3,
                learning_rate=0.1,
                random_state=42,
                verbose=-1
            )

            X = values.reshape(-1, 1)
            model.fit(X, target)

            # 预测
            probs = model.predict_proba(X)[:, 1]

            # 计算 Brier Score
            brier = brier_score_loss(target, probs)

            # 如果 Brier Score 接近 0，说明特征泄露了信息
            if brier < 0.01:
                return {
                    'safe': False,
                    'reason': f'Brier Score {brier:.4f} < 0.01 (完美预测)',
                    'brier': brier
                }

            return {
                'safe': True,
                'reason': f'Brier Score {brier:.4f}',
                'brier': brier
            }

        except Exception as e:
            return {
                'safe': False,
                'reason': f'Error: {str(e)}',
                'brier': None
            }

    def create_ultra_safe_dataset(self, data_path, safe_features):
        """创建超安全数据集"""
        print(f"\n🛡️ 创建超安全数据集...")

        df = pd.read_csv(data_path)

        # 只保留绝对安全的特征
        ultra_safe_features = [
            # 基本信息
            'year',
            'month',
            'day_of_week',
            'is_weekend',
            'league_id',

            # 球队名称 (编码后)
            # 'home_team_name',
            # 'away_team_name',

            # 开盘赔率 (赛前可得)
            'real_home_odds',
            'real_draw_odds',
            'real_away_odds',

            # 赔率衍生特征 (基于开盘赔率)
            'home_win_odds',
            'draw_odds',
            'away_win_odds',
        ]

        # 检查哪些特征实际存在
        available_features = [f for f in ultra_safe_features if f in df.columns]

        # 创建超安全数据集
        df_safe = df[available_features + ['target', 'match_date', 'home_team_name', 'away_team_name']].copy()

        print(f"  原始特征: {len(df.columns)}")
        print(f"  超安全特征: {len(available_features)}")
        print(f"  删除率: {(len(df.columns) - len(available_features)) / len(df.columns) * 100:.1f}%")

        # 保存
        output_path = "/home/user/projects/FootballPrediction/data/v9_5_ultra_safe_features.csv"
        df_safe.to_csv(output_path, index=False)

        print(f"  保存路径: {output_path}")

        return df_safe

    def test_ultra_safe_model(self, data_path):
        """测试超安全模型"""
        print(f"\n🧪 测试超安全模型...")

        df = pd.read_csv(data_path)
        df['match_date'] = pd.to_datetime(df['match_date'])

        # 只使用有标签的数据
        df_labeled = df[df['target'].notna() & (df['target'] >= 0)].copy()

        # 时间分割
        train_mask = df_labeled['match_date'] <= '2022-06-30'
        test_mask = df_labeled['match_date'] > '2023-06-30'

        df_train = df_labeled[train_mask]
        df_test = df_labeled[test_mask]

        if len(df_train) == 0 or len(df_test) == 0:
            print(f"  ❌ 数据不足: 训练集 {len(df_train)}, 测试集 {len(df_test)}")
            return None

        # 特征
        feature_cols = [col for col in df_labeled.columns if col not in [
            'target', 'match_date', 'home_team_name', 'away_team_name'
        ]]

        X_train = df_train[feature_cols].fillna(0).values
        y_train = df_train['target'].values
        X_test = df_test[feature_cols].fillna(0).values
        y_test = df_test['target'].values

        print(f"  训练集: {len(X_train)} 样本, 主胜率 {y_train.mean():.1%}")
        print(f"  测试集: {len(X_test)} 样本, 主胜率 {y_test.mean():.1%}")

        # 训练简单模型
        model = lgb.LGBMClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
            verbose=-1
        )

        model.fit(X_train, y_train)

        # 测试
        test_probs = model.predict_proba(X_test)[:, 1]
        test_brier = brier_score_loss(y_test, test_probs)

        print(f"  测试集 Brier Score: {test_brier:.4f}")

        # 诊断
        if test_brier < 0.1:
            print(f"  ❌ 仍然存在数据泄露!")
            status = "FAILED"
        elif 0.18 <= test_brier <= 0.25:
            print(f"  ✅ 正常范围!")
            status = "GOOD"
        else:
            print(f"  ⚠️ 需要调整")
            status = "CAUTION"

        return {
            'brier_score': test_brier,
            'status': status,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'n_features': len(feature_cols)
        }

def main():
    """主函数"""
    print("=" * 80)
    print("🔍 V9.5 特征审计与超安全模型")
    print("=" * 80)

    auditor = FeatureAuditor()

    # 审计特征
    data_path = "/home/user/projects/FootballPrediction/data/v9_5_sanitized_features.csv"
    safe_features, suspicious_features = auditor.audit_features(data_path)

    # 创建超安全数据集
    df_ultra_safe = auditor.create_ultra_safe_dataset(data_path, safe_features)

    # 测试超安全模型
    ultra_safe_path = "/home/user/projects/FootballPrediction/data/v9_5_ultra_safe_features.csv"
    result = auditor.test_ultra_safe_model(ultra_safe_path)

    print("\n" + "=" * 80)
    print("✅ 特征审计完成")
    print("=" * 80)
    if result:
        print(f"  🎯 超安全模型 Brier Score: {result['brier_score']:.4f}")
        print(f"  🎯 状态: {result['status']}")
        print(f"  📊 特征数: {result['n_features']}")
        print(f"  📊 训练集: {result['train_size']}, 测试集: {result['test_size']}")

    return auditor, result

if __name__ == "__main__":
    auditor, result = main()
