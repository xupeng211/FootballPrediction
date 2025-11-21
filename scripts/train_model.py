#!/usr/bin/env python3
"""
足球预测模型训练脚本 / Football Prediction Model Training Script

该脚本使用历史比赛数据训练XGBoost分类器，用于预测足球比赛结果。

This script trains an XGBoost classifier using historical match data to predict football match results.

使用方法 / Usage:
    python scripts/train_model.py
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 检查并安装依赖
try:
    import pandas as pd
    import numpy as np
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from sklearn.preprocessing import LabelEncoder
    import xgboost as xgb
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError as e:
    print(f"❌ 缺少依赖库: {e}")
    print("💡 请安装必需的依赖:")
    print("   pip install xgboost scikit-learn pandas numpy matplotlib seaborn")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置中文字体（用于matplotlib）
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


class FootballModelTrainer:
    """足球预测模型训练器."""

    def __init__(self):
        """初始化训练器."""
        self.data = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.model = None
        self.feature_names = None

    def load_data(self, filepath: str = 'data/dataset_v1.csv'):
        """加载数据集.

        Args:
            filepath: 数据文件路径

        Returns:
            bool: 加载是否成功
        """
        try:
            logger.info(f"📁 加载数据集: {filepath}")
            self.data = pd.read_csv(filepath)

            # 确保数据按时间排序
            self.data['match_date'] = pd.to_datetime(self.data['match_date'])
            self.data = self.data.sort_values('match_date').reset_index(drop=True)

            logger.info(f"✅ 数据加载成功: {self.data.shape}")
            logger.info(f"📅 数据时间范围: {self.data['match_date'].min()} 到 {self.data['match_date'].max()}")
            logger.info(f"🎯 目标变量分布:")
            target_counts = self.data['match_result'].value_counts().sort_index()
            for result, count in target_counts.items():
                result_name = {0: "平局", 1: "主队胜", 2: "客队胜"}[result]
                logger.info(f"   {result_name}: {count} ({count/len(self.data)*100:.1f}%)")

            return True

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            return False

    def prepare_features(self):
        """准备特征和目标变量.

        Returns:
            bool: 准备是否成功
        """
        try:
            # 定义特征列（包含新的高级特征）
            feature_columns = [
                # 基础特征
                'home_team_id', 'away_team_id',
                'home_last_5_points', 'away_last_5_points',
                'home_last_5_avg_goals', 'away_last_5_avg_goals',
                'h2h_last_3_home_wins',
                # 高级特征 - 体能、实力、士气
                'home_last_5_goal_diff', 'away_last_5_goal_diff',
                'home_win_streak', 'away_win_streak',
                'home_last_5_win_rate', 'away_last_5_win_rate',
                'home_rest_days', 'away_rest_days'
            ]

            self.feature_names = feature_columns

            # 准备特征矩阵X和目标向量y
            X = self.data[feature_columns].copy()
            y = self.data['match_result'].copy()

            logger.info(f"📊 特征矩阵形状: {X.shape}")
            logger.info(f"🎯 目标向量形状: {y.shape}")
            logger.info(f"📋 特征列表: {feature_columns}")

            # 显示特征统计
            logger.info("📈 特征统计信息:")
            for col in feature_columns:
                if col in ['home_team_id', 'away_team_id']:
                    logger.info(f"   {col}: {X[col].nunique()} 个唯一值")
                else:
                    logger.info(f"   {col}: 均值={X[col].mean():.2f}, 标准差={X[col].std():.2f}")

            return X, y

        except Exception as e:
            logger.error(f"❌ 特征准备失败: {e}")
            return None, None

    def time_series_split(self, X, y, train_ratio: float = 0.8):
        """时间序列数据切分.

        Args:
            X: 特征矩阵
            y: 目标向量
            train_ratio: 训练集比例

        Returns:
            Tuple: (X_train, X_test, y_train, y_test)
        """
        try:
            # 计算切分点
            split_point = int(len(X) * train_ratio)

            # 按时间顺序切分
            X_train = X[:split_point]
            X_test = X[split_point:]
            y_train = y[:split_point]
            y_test = y[split_point:]

            logger.info(f"🔄 数据切分完成:")
            logger.info(f"   训练集: {len(X_train)} 条 ({len(X_train)/len(X)*100:.1f}%)")
            logger.info(f"   测试集: {len(X_test)} 条 ({len(X_test)/len(X)*100:.1f}%)")
            logger.info(f"   切分时间点: {self.data.iloc[split_point]['match_date']}")

            # 检查测试集的目标分布
            logger.info("📊 测试集目标分布:")
            test_counts = y_test.value_counts().sort_index()
            for result, count in test_counts.items():
                result_name = {0: "平局", 1: "主队胜", 2: "客队胜"}[result]
                logger.info(f"   {result_name}: {count} ({count/len(y_test)*100:.1f}%)")

            return X_train, X_test, y_train, y_test

        except Exception as e:
            logger.error(f"❌ 数据切分失败: {e}")
            return None, None, None, None

    def train_model(self):
        """训练XGBoost模型.

        Returns:
            bool: 训练是否成功
        """
        try:
            logger.info("🚀 开始训练XGBoost模型")

            # 准备数据
            X, y = self.prepare_features()
            if X is None or y is None:
                return False

            # 时间序列切分
            self.X_train, self.X_test, self.y_train, self.y_test = self.time_series_split(X, y)
            if self.X_train is None:
                return False

            # 定义XGBoost参数
            params = {
                'objective': 'multi:softmax',  # 多分类
                'num_class': 3,                # 3个类别：0=平局，1=主胜，2=客胜
                'max_depth': 6,                # 树的最大深度
                'learning_rate': 0.1,          # 学习率
                'n_estimators': 100,           # 树的数量
                'random_state': 42,            # 随机种子
                'eval_metric': 'mlogloss',     # 评估指标
                'use_label_encoder': False,    # 不使用标签编码器
            }

            # 创建并训练模型
            self.model = xgb.XGBClassifier(**params)

            logger.info("🔄 开始模型训练...")
            self.model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_test, self.y_test)],
                verbose=False
            )

            logger.info("✅ 模型训练完成")

            # 显示特征重要性
            feature_importance = self.model.feature_importances_
            logger.info("📊 特征重要性:")
            for name, importance in zip(self.feature_names, feature_importance):
                logger.info(f"   {name}: {importance:.4f}")

            return True

        except Exception as e:
            logger.error(f"❌ 模型训练失败: {e}")
            return False

    def evaluate_model(self):
        """评估模型性能.

        Returns:
            dict: 评估结果
        """
        try:
            logger.info("📈 开始模型评估")

            # 在测试集上预测
            y_pred = self.model.predict(self.X_test)
            y_pred_proba = self.model.predict_proba(self.X_test)

            # 计算准确率
            accuracy = accuracy_score(self.y_test, y_pred)

            logger.info(f"🎯 测试集准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")

            # 分类报告
            target_names = ['平局', '主队胜', '客队胜']
            report = classification_report(self.y_test, y_pred, target_names=target_names)
            logger.info("📊 分类报告:")
            logger.info("\n" + report)

            # 混淆矩阵
            cm = confusion_matrix(self.y_test, y_pred)
            logger.info("🔢 混淆矩阵:")
            logger.info(f"   实际\\预测  平局  主胜  客胜")
            for i, actual_class in enumerate(target_names):
                logger.info(f"   {actual_class:6s}  {cm[i][0]:4d}  {cm[i][1]:4d}  {cm[i][2]:4d}")

            return {
                'accuracy': accuracy,
                'classification_report': report,
                'confusion_matrix': cm.tolist(),
                'y_pred': y_pred,
                'y_pred_proba': y_pred_proba
            }

        except Exception as e:
            logger.error(f"❌ 模型评估失败: {e}")
            return None

    def save_model(self, filepath: str = 'models/football_model_v1.json'):
        """保存训练好的模型.

        Args:
            filepath: 模型保存路径

        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # 保存模型
            self.model.save_model(filepath)

            # 保存元数据
            metadata = {
                'model_version': 'v1',
                'training_date': datetime.now().isoformat(),
                'feature_names': self.feature_names,
                'target_classes': ['平局', '主队胜', '客队胜'],
                'training_samples': len(self.X_train),
                'test_samples': len(self.X_test),
                'num_features': len(self.feature_names)
            }

            metadata_path = filepath.replace('.json', '_metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 模型已保存到: {filepath}")
            logger.info(f"📋 元数据已保存到: {metadata_path}")

            return True

        except Exception as e:
            logger.error(f"❌ 模型保存失败: {e}")
            return False

    def demonstrate_prediction(self):
        """演示模型预测功能."""
        try:
            logger.info("🎯 模型预测演示")

            # 获取测试集中的最后一场比赛
            last_match_idx = len(self.X_test) - 1
            last_match_features = self.X_test.iloc[[last_match_idx]]
            last_match_actual = self.y_test.iloc[last_match_idx]
            last_match_date = self.data.iloc[len(self.X_train) + last_match_idx]['match_date']

            # 获取球队信息
            home_team_id = last_match_features['home_team_id'].iloc[0]
            away_team_id = last_match_features['away_team_id'].iloc[0]

            # 从原始数据中查找球队名称
            original_data = self.data.copy()
            team_mapping = original_data[['home_team_id', 'away_team_id']].drop_duplicates()
            # 这里简化处理，实际应该从team表查询
            logger.info(f"⚽ 预测比赛信息:")
            logger.info(f"   比赛日期: {last_match_date}")
            logger.info(f"   主队ID: {home_team_id}")
            logger.info(f"   客队ID: {away_team_id}")

            # 进行预测
            prediction = self.model.predict(last_match_features)[0]
            probabilities = self.model.predict_proba(last_match_features)[0]

            # 结果映射
            result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}
            actual_result = result_names[last_match_actual]
            predicted_result = result_names[prediction]

            # 显示预测结果
            logger.info(f"🎯 实际结果: {actual_result}")
            logger.info(f"🔮 预测结果: {predicted_result}")
            logger.info(f"📊 预测概率:")
            for i, (result_name, prob) in enumerate(zip(result_names.values(), probabilities)):
                status = "✅" if i == prediction else "  "
                logger.info(f"   {status} {result_name}: {prob:.3f} ({prob*100:.1f}%)")

            # 预测是否正确
            is_correct = prediction == last_match_actual
            logger.info(f"{'✅' if is_correct else '❌'} 预测{'正确' if is_correct else '错误'}！")

        except Exception as e:
            logger.error(f"❌ 预测演示失败: {e}")

    def run(self, model_path: str = 'models/football_model_v1.json'):
        """运行完整的训练流程.

        Args:
            model_path: 模型保存路径

        Returns:
            bool: 训练是否成功
        """
        logger.info("=" * 60)
        logger.info("🚀 足球预测模型训练开始")
        logger.info("=" * 60)

        start_time = datetime.now()

        try:
            # 1. 加载数据
            if not self.load_data():
                return False

            # 2. 训练模型
            if not self.train_model():
                return False

            # 3. 评估模型
            evaluation_results = self.evaluate_model()
            if evaluation_results is None:
                return False

            # 4. 保存模型
            if not self.save_model(model_path):
                return False

            # 5. 演示预测
            self.demonstrate_prediction()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("🎉 模型训练完成！")
            logger.info(f"⏱️  总耗时: {duration}")
            logger.info(f"📊 测试准确率: {evaluation_results['accuracy']:.4f}")
            logger.info(f"💾 模型文件: {model_path}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"💥 训练流程失败: {e}")
            return False


def main():
    """主函数."""
    logger.info("🏈 足球预测模型训练器启动")

    try:
        trainer = FootballModelTrainer()
        success = trainer.run()

        if success:
            logger.info("✅ 模型训练成功完成！")
            sys.exit(0)
        else:
            logger.error("❌ 模型训练失败！")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，训练停止")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 训练异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()