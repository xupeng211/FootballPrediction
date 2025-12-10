#!/usr/bin/env python3
"""
基线模型训练脚本
使用滚动特征数据集训练XGBoost分类器作为性能基准

核心功能:
1. 时序数据分割 (80%训练, 20%测试)
2. 特征选择和预处理
3. XGBoost分类器训练
4. 性能评估和特征重要性分析

作者: Algorithm Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Baseline Model
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, log_loss, classification_report
from xgboost import XGBClassifier
# import matplotlib.pyplot as plt  # 可选: 用于可视化

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaselineTrainer:
    """基线模型训练器"""

    def __init__(self):
        self.model = None
        self.label_encoder = LabelEncoder()
        self.feature_names = None

    def load_and_prepare_data(self, file_path: str) -> pd.DataFrame:
        """加载并准备数据"""
        logger.info(f"📊 加载数据集: {file_path}")
        df = pd.read_csv(file_path)

        # 使用现有的result列 (H=Home, A=Away, D=Draw)
        if 'result' in df.columns:
            result_mapping = {'H': 'Home', 'A': 'Away', 'D': 'Draw'}
            df['true_result'] = df['result'].map(result_mapping)
        else:
            raise ValueError("❌ 数据集中缺少result列")
        logger.info(f"📈 真实比赛结果分布:")
        logger.info(f"   {df['true_result'].value_counts().to_dict()}")

        # 创建match_date列用于时序排序
        df['match_date'] = pd.to_datetime(
            df['year'].astype(str) + '-' +
            df['month'].astype(str).str.zfill(2) + '-' +
            '01'  # 使用每月1号作为估算日期
        )

        # 按日期排序 (重要: 时序分割)
        df = df.sort_values('match_date').reset_index(drop=True)

        logger.info(f"   数据形状: {df.shape}")
        logger.info(f"   日期范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

        return df

    def select_features(self, df: pd.DataFrame) -> tuple:
        """选择特征和目标变量"""
        logger.info("🎯 特征选择和预处理")

        # 定义需要排除的列 (数据泄露或非特征)
        exclude_columns = [
            'id', 'match_date', 'home_team_name', 'away_team_name',
            'home_score', 'away_score', 'match_result', 'result_numeric',
            'home_xg', 'away_xg', 'xg_difference', 'total_xg',
            'has_xg_data', 'has_events', 'has_shotmap', 'has_lineups',
            'home_lineup_count', 'away_lineup_count', 'total_lineup_players', 'has_odds',
            'h2h_home_advantage', 'h2v_home_xg_boost'
        ]

        # 选择时序安全的滚动特征 (无数据泄露)
        rolling_features = [col for col in df.columns if 'last_' in col]

        # 选择基础的赛前上下文特征
        context_features = [
            'year', 'month', 'day_of_week', 'is_weekend',
            # 如果有赔率数据，可以添加
            # 'home_win_odds', 'draw_odds', 'away_win_odds'
        ]

        context_features = [col for col in context_features if col in df.columns]

        # 合并特征列 (只包含安全的赛前特征)
        feature_columns = rolling_features + context_features

        logger.info(f"   ✅ 安全特征: {len(feature_columns)}")
        logger.info(f"   📋 总特征数: {len(feature_columns)}")

        # 提取特征和目标
        X = df[feature_columns].copy()
        y = df['true_result'].copy()

        # 处理缺失值
        X = X.fillna(0)  # 用0填充缺失的滚动特征

        logger.info(f"   📊 特征矩阵形状: {X.shape}")
        logger.info(f"   🎯 目标变量形状: {y.shape}")

        return X, y, feature_columns

    def split_data_chronological(self, X: pd.DataFrame, y: pd.Series,
                                test_size: float = 0.2) -> tuple:
        """时序数据分割"""
        logger.info("📅 执行时序数据分割")

        # 计算分割点 (前80%训练, 后20%测试)
        split_idx = int(len(X) * (1 - test_size))

        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]

        logger.info(f"   📊 训练集: {X_train.shape[0]} 场比赛")
        logger.info(f"   🧪 测试集: {X_test.shape[0]} 场比赛")
        logger.info(f"   📅 训练日期: {X_train.index.min()} 到 {X_train.index.max()}")
        logger.info(f"   📅 测试日期: {X_test.index.min()} 到 {X_test.index.max()}")

        # 编码目标变量
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        y_test_encoded = self.label_encoder.transform(y_test)

        class_encoding = dict(zip(self.label_encoder.classes_,
                                 self.label_encoder.transform(self.label_encoder.classes_)))
        logger.info(f"   🏷️ 类别编码: {class_encoding}")

        return X_train, X_test, y_train_encoded, y_test_encoded, y_train, y_test

    def train_xgboost(self, X_train: pd.DataFrame, y_train: np.ndarray) -> XGBClassifier:
        """训练XGBoost模型"""
        logger.info("🚀 训练XGBoost分类器")

        # 配置XGBoost参数 (对于3分类问题)
        params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': 42,
            'eval_metric': 'mlogloss',
            'objective': 'multi:softprob',
            'num_class': 3  # 明确指定3分类
        }

        self.model = XGBClassifier(**params)
        self.model.fit(X_train, y_train)

        self.feature_names = X_train.columns.tolist()

        logger.info(f"   ✅ 模型训练完成")
        logger.info(f"   🌳 树的数量: {self.model.n_estimators}")
        logger.info(f"   📊 特征数量: {len(self.feature_names)}")

        return self.model

    def evaluate_model(self, X_test: pd.DataFrame, y_test_encoded: np.ndarray,
                      y_test_original: pd.Series) -> dict:
        """评估模型性能"""
        logger.info("📊 模型性能评估")

        # 预测
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)

        # 计算指标
        accuracy = accuracy_score(y_test_encoded, y_pred)
        logloss = log_loss(y_test_encoded, y_pred_proba)

        # 解码预测结果用于分类报告
        y_pred_original = self.label_encoder.inverse_transform(y_pred)

        logger.info(f"   🎯 测试集准确率: {accuracy:.4f}")
        logger.info(f"   📉 测试集Log Loss: {logloss:.4f}")

        # 显示分类报告
        logger.info(f"   📋 分类报告:")
        report = classification_report(y_test_original, y_pred_original,
                                     output_dict=True, zero_division=0)

        for class_name in self.label_encoder.classes_:
            if class_name in report:
                precision = report[class_name]['precision']
                recall = report[class_name]['recall']
                f1 = report[class_name]['f1-score']
                logger.info(f"      {class_name:6}: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}")

        return {
            'accuracy': accuracy,
            'log_loss': logloss,
            'classification_report': report
        }

    def plot_feature_importance(self, top_n: int = 10):
        """绘制特征重要性图表"""
        if self.model is None or self.feature_names is None:
            logger.warning("⚠️ 模型未训练，无法显示特征重要性")
            return

        logger.info(f"📈 特征重要性分析 (Top {top_n})")

        # 获取特征重要性
        importance = self.model.feature_importances_
        feature_importance = list(zip(self.feature_names, importance))
        feature_importance.sort(key=lambda x: x[1], reverse=True)

        # 显示Top N特征
        logger.info(f"   🏆 Top {top_n} 重要特征:")
        for i, (feature, importance_score) in enumerate(feature_importance[:top_n], 1):
            logger.info(f"   {i:2d}. {feature:35}: {importance_score:.4f}")

        # 保存特征重要性
        importance_df = pd.DataFrame(feature_importance,
                                   columns=['feature', 'importance'])
        importance_df.to_csv('feature_importance.csv', index=False)
        logger.info(f"   💾 特征重要性已保存至: feature_importance.csv")

    def train_baseline_model(self, data_path: str) -> dict:
        """完整的基线模型训练流程"""
        logger.info("🚀 开始基线模型训练流程")

        # 1. 加载数据
        df = self.load_and_prepare_data(data_path)

        # 2. 特征选择
        X, y, feature_columns = self.select_features(df)

        # 3. 时序分割
        X_train, X_test, y_train_enc, y_test_enc, y_train_orig, y_test_orig = \
            self.split_data_chronological(X, y)

        # 4. 训练模型
        self.train_xgboost(X_train, y_train_enc)

        # 5. 评估模型
        results = self.evaluate_model(X_test, y_test_enc, y_test_orig)

        # 6. 特征重要性
        self.plot_feature_importance()

        logger.info("🎉 基线模型训练完成!")
        return results


def main():
    """主函数"""
    # 初始化基线训练器
    trainer = BaselineTrainer()

    try:
        # 训练诚实基线模型 (无数据泄露)
        results = trainer.train_baseline_model(
            data_path="data/processed/features_v2_rolling.csv"
        )

        # 显示最终结果
        print("\n" + "="*80)
        print("🏆 BASELINE MODEL PERFORMANCE SUMMARY")
        print("="*80)

        print(f"\n📊 关键指标:")
        print(f"   🎯 准确率 (Accuracy): {results['accuracy']:.4f}")
        print(f"   📉 对数损失 (Log Loss): {results['log_loss']:.4f}")

        print(f"\n✅ 基线模型已建立，可作为后续模型优化的基准")
        print("="*80)

    except Exception as e:
        logger.error(f"❌ 训练失败: {e}")
        raise


if __name__ == "__main__":
    main()