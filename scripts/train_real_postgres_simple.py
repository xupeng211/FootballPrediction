#!/usr/bin/env python3
"""
简化版真实数据训练脚本 - Phase 4

直接使用 PostgresDataLoader 和基础的 XGBoost 训练，
避免复杂的导入依赖问题。
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
import json
from datetime import datetime

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# 设置项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 直接导入 PostgresDataLoader
try:
    from src.ml.data.postgres_loader import PostgresDataLoader
except ImportError:
    logger.error("无法导入 PostgresDataLoader")
    sys.exit(1)


class SimpleRealDataTrainer:
    """
    简化的真实数据训练器
    """

    def __init__(self):
        """初始化训练器"""
        self.data_loader = PostgresDataLoader(
            selected_columns=[
                'home_team_id', 'away_team_id', 'home_score', 'away_score',
                'match_date', 'status', 'home_team_name', 'away_team_name', 'league_id'
            ]
        )

        # 模型参数
        self.model_params = {
            'n_estimators': 200,
            'max_depth': 5,
            'learning_rate': 0.1,
            'random_state': 42,
            'eval_metric': 'logloss',
            'use_label_encoder': False,
        }

        self.model = None
        self.feature_names = []

    def create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        创建简单的滚动窗口特征

        Args:
            df: 原始比赛数据

        Returns:
            包含滚动特征的DataFrame
        """
        logger.info("创建滚动窗口特征...")

        df_features = df.copy()

        # 按主队分组，创建得分滚动特征
        df_features = df_features.sort_values(['home_team_id', 'match_date'])

        # 主队得分滚动特征
        df_features['home_score_rolling_3'] = (
            df_features.groupby('home_team_id')['home_score']
            .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
        )

        df_features['home_score_rolling_5'] = (
            df_features.groupby('home_team_id')['home_score']
            .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        )

        # 客队得分滚动特征
        df_features['away_score_rolling_3'] = (
            df_features.groupby('away_team_id')['away_score']
            .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
        )

        df_features['away_score_rolling_5'] = (
            df_features.groupby('away_team_id')['away_score']
            .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        )

        # 删除NaN值
        initial_count = len(df_features)
        df_features = df_features.dropna()
        logger.info(f"特征工程完成: {initial_count} -> {len(df_features)} 行")

        return df_features

    def prepare_training_data(self, df: pd.DataFrame):
        """
        准备训练数据

        Args:
            df: 包含特征的DataFrame

        Returns:
            (X, y): 训练特征和目标变量
        """
        logger.info("准备训练数据...")

        # 创建目标变量：主队获胜 (home_score > away_score)
        y = (df['home_score'] > df['away_score']).astype(int)
        logger.info(f"目标变量分布 - 主队获胜: {y.sum()}/{len(y)} ({y.mean():.2%})")

        # 选择特征列
        feature_cols = [
            'home_score_rolling_3', 'home_score_rolling_5',
            'away_score_rolling_3', 'away_score_rolling_5',
            'home_team_id', 'away_team_id', 'league_id'
        ]

        # 过滤存在的列
        available_features = [col for col in feature_cols if col in df.columns]

        if not available_features:
            raise ValueError("没有可用的特征列")

        X = df[available_features]
        self.feature_names = available_features

        logger.info(f"选择了 {len(available_features)} 个特征: {available_features}")

        return X, y

    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series):
        """
        训练XGBoost模型

        Args:
            X_train: 训练特征
            y_train: 训练目标
        """
        logger.info("开始训练XGBoost模型...")

        self.model = XGBClassifier(**self.model_params)
        self.model.fit(X_train, y_train)

        logger.info("✅ 模型训练完成")

    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series):
        """
        评估模型性能

        Args:
            X_test: 测试特征
            y_test: 测试目标

        Returns:
            dict: 评估指标
        """
        logger.info("评估模型性能...")

        y_pred = self.model.predict(X_test)

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0)
        }

        logger.info(f"模型性能: {metrics}")

        return metrics

    def get_feature_importance(self):
        """
        获取特征重要性

        Returns:
            list: 特征重要性列表
        """
        if self.model is None:
            return []

        importance = self.model.feature_importances_
        feature_importance = [
            {
                'feature': feature_name,
                'importance': float(imp)
            }
            for feature_name, imp in zip(self.feature_names, importance)
        ]

        # 按重要性排序
        feature_importance.sort(key=lambda x: x['importance'], reverse=True)

        return feature_importance

    def save_model(self, model_path: str = None):
        """
        保存模型

        Args:
            model_path: 模型保存路径
        """
        if self.model is None:
            raise RuntimeError("模型尚未训练")

        if model_path is None:
            models_dir = project_root / "models"
            models_dir.mkdir(exist_ok=True)
            model_path = models_dir / "baseline_v2_real.json"

        self.model.save_model(str(model_path))

        # 保存模型信息
        model_info = {
            'feature_names': self.feature_names,
            'model_params': self.model_params,
            'training_date': datetime.now().isoformat()
        }

        info_path = str(model_path).replace('.json', '_info.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 模型已保存到: {model_path}")
        logger.info(f"✅ 模型信息已保存到: {info_path}")

    async def run_training(self):
        """
        运行完整的训练流程
        """
        logger.info("🚀 开始真实数据训练流程")

        try:
            # 1. 加载数据
            logger.info("📊 第1步: 加载真实数据...")
            df = await self.data_loader.load_data(limit=2000)

            if df.empty:
                logger.error("数据加载为空")
                return None

            logger.info(f"✅ 数据加载完成: {len(df)} 条记录")

            # 2. 特征工程
            logger.info("⚙️ 第2步: 特征工程...")
            df_features = self.create_rolling_features(df)

            # 3. 准备训练数据
            logger.info("🔧 第3步: 准备训练数据...")
            X, y = self.prepare_training_data(df_features)

            # 4. 时间序列切分
            logger.info("✂️ 第4步: 时间序列数据切分...")
            split_idx = int(len(X) * 0.8)
            X_train = X.iloc[:split_idx]
            X_test = X.iloc[split_idx:]
            y_train = y.iloc[:split_idx]
            y_test = y.iloc[split_idx:]

            logger.info(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

            # 5. 训练模型
            logger.info("🧠 第5步: 训练模型...")
            self.train_model(X_train, y_train)

            # 6. 评估模型
            logger.info("📊 第6步: 评估模型...")
            metrics = self.evaluate_model(X_test, y_test)

            # 7. 特征重要性
            logger.info("🔍 第7步: 特征重要性分析...")
            feature_importance = self.get_feature_importance()

            # 8. 保存模型
            logger.info("💾 第8步: 保存模型...")
            self.save_model()

            # 9. 输出结果
            self._print_results(metrics, feature_importance)

            return {
                'metrics': metrics,
                'feature_importance': feature_importance[:5],  # Top 5
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }

        except Exception as e:
            logger.error(f"❌ 训练失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _print_results(self, metrics, feature_importance):
        """打印训练结果"""
        logger.info("🎉 真实数据训练完成!")
        logger.info("=" * 60)
        logger.info("📊 模型性能:")
        logger.info(f"   • Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']:.2%})")
        logger.info(f"   • Precision: {metrics['precision']:.4f} ({metrics['precision']:.2%})")
        logger.info(f"   • Recall:    {metrics['recall']:.4f} ({metrics['recall']:.2%})")
        logger.info(f"   • F1 Score:  {metrics['f1_score']:.4f} ({metrics['f1_score']:.2%})")

        logger.info("\n🏆 Top 5 重要特征:")
        for i, feature in enumerate(feature_importance[:5], 1):
            logger.info(f"   {i}. {feature['feature']:<20} : {feature['importance']:.6f}")

        logger.info("=" * 60)


async def main():
    """主函数"""
    logger.info("🚀 Phase 4 - 简化版真实数据训练脚本启动")
    logger.info(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    trainer = SimpleRealDataTrainer()
    result = await trainer.run_training()

    logger.info(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if result:
        logger.info("✅ 真实数据训练圆满完成!")

        # 显示核心指标
        metrics = result['metrics']
        logger.info("\n" + "="*50)
        logger.info("📈 核心指标总结:")
        logger.info(f"   • Accuracy:  {metrics['accuracy']:.2%}")
        logger.info(f"   • Precision: {metrics['precision']:.2%}")

        logger.info("\n🏆 Top 5 特征重要性:")
        for i, feature in enumerate(result['feature_importance'], 1):
            logger.info(f"   {i}. {feature['feature']}: {feature['importance']:.6f}")

        logger.info("="*50)
        sys.exit(0)
    else:
        logger.error("❌ 真实数据训练失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())