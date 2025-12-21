#!/usr/bin/env python3
"""
V7.0 LightGBM 模型训练脚本 - 基于实心数据
功能：特征重要性分析、5折交叉验证、准确率和LogLoss评估
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class V7LightGBMTrainer:
    """V7.0 LightGBM 训练器"""

    def __init__(self, data_path: str):
        """
        初始化训练器

        Args:
            data_path: 数据文件路径
        """
        self.data_path = data_path
        self.df = None
        self.features = None
        self.target = None
        self.feature_names = None
        self.model = None
        self.label_encoder = LabelEncoder()
        self.cv_scores = {
            'accuracy': [],
            'logloss': []
        }

    def load_and_prepare_data(self):
        """加载和准备数据"""
        print("📊 加载数据...")
        self.df = pd.read_csv(self.data_path)
        print(f"✅ 数据加载完成: {len(self.df)} 场比赛")

        # 显示数据基本信息
        print("\n📋 数据概览:")
        print(f"  特征数量: {self.df.shape[1]}")
        print(f"  比赛数量: {self.df.shape[0]}")
        print(f"  缺失值: {self.df.isnull().sum().sum()}")

        return self.df

    def create_target_variable(self):
        """创建目标变量（基于 xG 和实际比分模拟）"""
        print("\n🎯 创建目标变量...")

        # 方法1: 如果有比分数据，使用真实比分
        if 'home_goals' in self.df.columns and 'away_goals' in self.df.columns:
            def get_result(row):
                if row['home_goals'] > row['away_goals']:
                    return 0  # 主胜
                elif row['home_goals'] < row['away_goals']:
                    return 2  # 客胜
                else:
                    return 1  # 平局
            self.df['result'] = self.df.apply(get_result, axis=1)

        # 方法2: 基于 xG 差异模拟结果（用于演示）
        else:
            print("  ⚠️ 未找到比分数据，使用 xG 差异模拟结果")

            # 基于 xG 差异和控球率生成更真实的结果
            def simulate_result(row):
                home_xg = row.get('home_xg', 1.0)
                away_xg = row.get('away_xg', 1.0)
                home_poss = row.get('home_possession', 50.0)

                # 计算主队优势
                xg_diff = home_xg - away_xg
                poss_diff = (home_poss - 50) / 100  # 标准化控球率差异

                # 综合评分 (xG 权重 70%, 控球率权重 30%)
                home_advantage = xg_diff * 0.7 + poss_diff * 0.3

                # 添加随机性（模拟真实比赛的不可预测性）
                noise = np.random.normal(0, 0.3)
                final_score = home_advantage + noise

                if final_score > 0.2:
                    return 0  # 主胜
                elif final_score < -0.2:
                    return 2  # 客胜
                else:
                    return 1  # 平局

            np.random.seed(42)  # 确保结果可重现
            self.df['result'] = self.df.apply(simulate_result, axis=1)

        # 编码目标变量
        self.target = self.label_encoder.fit_transform(self.df['result'])

        # 显示目标变量分布
        result_counts = pd.Series(self.target).value_counts().sort_index()
        result_labels = ['主胜', '平局', '客胜']
        print("\n  结果分布:")
        for i, label in enumerate(result_labels):
            count = result_counts.get(i, 0)
            pct = count / len(self.target) * 100
            print(f"    {label}: {count} 场 ({pct:.1f}%)")

        # 确保所有类别都有样本
        unique_classes = np.unique(self.target)
        if len(unique_classes) < 3:
            print(f"  ⚠️ 警告: 只有 {len(unique_classes)} 个类别，可能影响模型训练")

        return self.target

    def engineer_features(self):
        """特征工程"""
        print("\n🔧 特征工程...")

        # 选择特征
        feature_cols = [
            # 基础特征
            'home_avg_rating', 'away_avg_rating',
            'home_big_chances_created', 'away_big_chances_created',
            'home_total_shots', 'away_total_shots',
            'home_possession', 'away_possession',
            'home_xg', 'away_xg',

            # 事件特征
            'home_red_cards', 'away_red_cards',
            'home_substitutions', 'away_substitutions',
            'home_early_goal', 'away_early_goal',
            'home_penalties', 'away_penalties',

            # 衍生特征
            'home_xg_per_shot', 'away_xg_per_shot',
            'rating_diff'
        ]

        # 过滤存在的列
        available_cols = [col for col in feature_cols if col in self.df.columns]
        missing_cols = [col for col in feature_cols if col not in self.df.columns]

        if missing_cols:
            print(f"  ⚠️ 缺失特征: {missing_cols}")

        # 创建特征矩阵
        self.features = self.df[available_cols].copy()

        # 计算更多衍生特征
        if 'home_xg' in self.features.columns and 'away_xg' in self.features.columns:
            self.features['xg_diff'] = self.features['home_xg'] - self.features['away_xg']
            self.features['xg_total'] = self.features['home_xg'] + self.features['away_xg']

        if 'home_possession' in self.features.columns and 'away_possession' in self.features.columns:
            self.features['possession_diff'] = self.features['home_possession'] - self.features['away_possession']

        if 'home_total_shots' in self.features.columns and 'away_total_shots' in self.features.columns:
            self.features['shots_diff'] = self.features['home_total_shots'] - self.features['away_total_shots']

        # 处理缺失值
        self.features = self.features.fillna(0)

        # 记录特征名称
        self.feature_names = list(self.features.columns)

        print(f"  ✅ 特征工程完成: {self.features.shape[1]} 个特征")
        print(f"  特征列表: {self.feature_names}")

        return self.features

    def train_with_cross_validation(self, n_folds=3):
        """训练模型并执行交叉验证"""
        # 根据数据量调整折数
        min_samples = 8
        if len(self.df) < 20:
            n_folds = min(3, len(self.df) // 2)
            print(f"\n⚠️ 数据量较小，调整为 {n_folds} 折交叉验证")
        else:
            print(f"\n🚀 开始 {n_folds} 折交叉验证...")

        # 获取所有可能的类别
        unique_classes = np.unique(self.target)
        print(f"  目标类别: {unique_classes}")

        # 设置 LightGBM 参数
        lgb_params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': ['multi_logloss', 'multi_error'],
            'boosting_type': 'gbdt',
            'num_leaves': 10,
            'learning_rate': 0.1,
            'min_data_in_leaf': 1,
            'feature_fraction': 1.0,
            'bagging_fraction': 1.0,
            'bagging_freq': 1,
            'verbose': -1,
            'random_state': 42
        }

        # K-Fold 交叉验证
        kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)

        for fold, (train_idx, val_idx) in enumerate(kf.split(self.features), 1):
            print(f"\n  训练第 {fold} 折 (训练集: {len(train_idx)}, 验证集: {len(val_idx)})...")

            # 分割数据
            X_train, X_val = self.features.iloc[train_idx], self.features.iloc[val_idx]
            y_train, y_val = self.target[train_idx], self.target[val_idx]

            print(f"    训练集类别分布: {np.bincount(y_train)}")
            print(f"    验证集类别分布: {np.bincount(y_val)}")

            # 创建 LightGBM 数据集
            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            # 训练模型（禁用early stopping以获得特征重要性）
            model = lgb.train(
                lgb_params,
                train_data,
                valid_sets=[train_data, val_data],
                num_boost_round=200,
                callbacks=[lgb.log_evaluation(0)]
            )

            # 预测
            y_pred_proba = model.predict(X_val, num_iteration=model.best_iteration)
            y_pred = np.argmax(y_pred_proba, axis=1)

            # 计算指标
            accuracy = accuracy_score(y_val, y_pred)

            # LogLoss 计算（指定 labels 参数）
            try:
                logloss = log_loss(y_val, y_pred_proba, labels=unique_classes)
            except ValueError as e:
                print(f"    ⚠️ LogLoss 计算出错: {e}")
                # 手动计算 LogLoss
                epsilon = 1e-15
                y_pred_proba = np.clip(y_pred_proba, epsilon, 1 - epsilon)
                logloss = -np.mean([np.log(y_pred_proba[i, y_val[i]]) for i in range(len(y_val))])

            self.cv_scores['accuracy'].append(accuracy)
            self.cv_scores['logloss'].append(logloss)

            print(f"    准确率: {accuracy:.4f}")
            print(f"    LogLoss: {logloss:.4f}")

            # 保存最后一折的模型
            if fold == n_folds:
                self.model = model
                # 保存模型到文件
                model_path = '/home/user/projects/FootballPrediction/lightgbm_v7.model'
                model.save_model(model_path)
                print(f"    ✅ 模型已保存到: {model_path}")

        # 显示交叉验证结果
        print(f"\n📊 {n_folds} 折交叉验证结果:")
        print(f"  平均准确率: {np.mean(self.cv_scores['accuracy']):.4f} ± {np.std(self.cv_scores['accuracy']):.4f}")
        print(f"  平均 LogLoss: {np.mean(self.cv_scores['logloss']):.4f} ± {np.std(self.cv_scores['logloss']):.4f}")

        return self.model

    def analyze_feature_importance(self, top_n=20):
        """分析特征重要性"""
        print(f"\n🎯 特征重要性分析 (Top {top_n})...")

        if self.model is None:
            print("❌ 模型尚未训练")
            return

        # 获取特征重要性
        importance = self.model.feature_importance(importance_type='gain')
        feature_importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        # 显示 Top N 特征
        print(f"\n  Top {top_n} 重要特征:")
        for i, (_, row) in enumerate(feature_importance_df.head(top_n).iterrows(), 1):
            print(f"    {i:2d}. {row['feature']:30s} {row['importance']:8.2f}")

        # 重点分析 rating_diff 和 home_xg_per_shot
        print(f"\n  🔍 关键特征分析:")
        for feature in ['rating_diff', 'home_xg_per_shot']:
            if feature in feature_importance_df['feature'].values:
                row = feature_importance_df[feature_importance_df['feature'] == feature].iloc[0]
                rank = feature_importance_df[feature_importance_df['feature'] == feature].index[0] + 1
                pct = (top_n / len(feature_importance_df)) * 100
                print(f"    {feature:20s}: 排名 #{rank:2d}, 重要性: {row['importance']:8.2f} (Top {pct:.0f}%)")
            else:
                print(f"    {feature:20s}: 未找到该特征")

        # 保存特征重要性到文件
        feature_importance_df.to_csv('/home/user/projects/FootballPrediction/feature_importance_v7.csv', index=False)
        print(f"\n  ✅ 特征重要性已保存到: feature_importance_v7.csv")

        return feature_importance_df

    def plot_feature_importance(self, top_n=15):
        """绘制特征重要性图表"""
        print(f"\n📊 绘制特征重要性图表...")

        if self.model is None:
            print("❌ 模型尚未训练")
            return

        # 获取特征重要性
        importance = self.model.feature_importance(importance_type='gain')
        feature_importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        # 绘制图表
        plt.figure(figsize=(12, 8))
        top_features = feature_importance_df.head(top_n)

        sns.barplot(data=top_features, y='feature', x='importance', palette='viridis')
        plt.title(f'V7.0 LightGBM 特征重要性 (Top {top_n})', fontsize=16, fontweight='bold')
        plt.xlabel('重要性 (Gain)', fontsize=12)
        plt.ylabel('特征', fontsize=12)
        plt.tight_layout()

        # 保存图表
        plt.savefig('/home/user/projects/FootballPrediction/feature_importance_v7.png', dpi=300, bbox_inches='tight')
        print(f"  ✅ 图表已保存到: feature_importance_v7.png")

        # 标注关键特征
        for feature in ['rating_diff', 'home_xg_per_shot']:
            if feature in top_features['feature'].values:
                idx = list(top_features['feature']).index(feature)
                plt.annotate(f'★ {feature}', xy=(top_features.iloc[idx]['importance'], idx),
                           xytext=(10, 0), textcoords='offset points',
                           fontsize=10, fontweight='bold', color='red')

        plt.close()

    def generate_report(self):
        """生成训练报告"""
        print("\n" + "="*60)
        print("📋 V7.0 LightGBM 训练报告")
        print("="*60)

        # 数据概览
        print(f"\n📊 数据概览:")
        print(f"  比赛数量: {len(self.df)}")
        print(f"  特征数量: {self.features.shape[1]}")
        print(f"  目标类别: 3 (主胜/平局/客胜)")

        # 交叉验证结果
        print(f"\n🎯 模型性能:")
        print(f"  5折交叉验证准确率: {np.mean(self.cv_scores['accuracy']):.4f} ± {np.std(self.cv_scores['accuracy']):.4f}")
        print(f"  5折交叉验证 LogLoss: {np.mean(self.cv_scores['logloss']):.4f} ± {np.std(self.cv_scores['logloss']):.4f}")

        # 关键特征
        if self.model is not None:
            importance = self.model.feature_importance(importance_type='gain')
            feature_importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)

            print(f"\n🔑 关键特征分析:")
            for feature in ['rating_diff', 'home_xg_per_shot']:
                if feature in feature_importance_df['feature'].values:
                    row = feature_importance_df[feature_importance_df['feature'] == feature].iloc[0]
                    rank = list(feature_importance_df['feature']).index(feature) + 1
                    print(f"  {feature:20s}: 排名 #{rank:2d}, 重要性: {row['importance']:8.2f}")

        # 保存报告
        report = {
            'model_type': 'LightGBM',
            'version': 'V7.0',
            'data_size': len(self.df),
            'num_features': self.features.shape[1],
            'cv_accuracy_mean': np.mean(self.cv_scores['accuracy']),
            'cv_accuracy_std': np.std(self.cv_scores['accuracy']),
            'cv_logloss_mean': np.mean(self.cv_scores['logloss']),
            'cv_logloss_std': np.std(self.cv_scores['logloss']),
            'feature_importance': dict(zip(self.feature_names, importance)) if self.model else {}
        }

        import json
        with open('/home/user/projects/FootballPrediction/training_report_v7.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n  ✅ 训练报告已保存到: training_report_v7.json")
        print("="*60)

        return report

    def run_full_pipeline(self):
        """运行完整训练流程"""
        print("🚀 V7.0 LightGBM 模型训练启动")
        print("="*60)

        try:
            # 1. 加载数据
            self.load_and_prepare_data()

            # 2. 创建目标变量
            self.create_target_variable()

            # 3. 特征工程
            self.engineer_features()

            # 4. 训练模型和交叉验证
            self.train_with_cross_validation(n_folds=5)

            # 5. 特征重要性分析
            self.analyze_feature_importance(top_n=20)

            # 6. 绘制特征重要性图表
            self.plot_feature_importance(top_n=15)

            # 7. 生成报告
            self.generate_report()

            print("\n🎉 V7.0 LightGBM 训练完成!")
            return True

        except Exception as e:
            print(f"\n❌ 训练过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    # 设置数据路径
    data_path = "/home/user/projects/FootballPrediction/data/final_v7_solid_features.csv"

    # 创建训练器并运行
    trainer = V7LightGBMTrainer(data_path)
    success = trainer.run_full_pipeline()

    if success:
        print("\n✅ 所有任务完成!")
        print("  - feature_importance_v7.csv: 特征重要性数据")
        print("  - feature_importance_v7.png: 特征重要性图表")
        print("  - training_report_v7.json: 完整训练报告")
    else:
        print("\n❌ 训练失败!")
