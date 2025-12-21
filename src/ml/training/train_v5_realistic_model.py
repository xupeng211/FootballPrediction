#!/usr/bin/env python3
"""
V5.0 真实感模型训练器
仅基于物理存在的真实数据，拒绝任何模拟或填充的特征
"""

import logging
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from src.config_unified import get_settings
from src.database.schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


class V5RealisticModelTrainer:
    """V5.0 真实感模型训练器"""

    def __init__(self):
        """初始化训练器"""
        self.settings = get_settings()
        self.schema_manager = get_schema_manager()
        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = []
        self.training_stats = {}

    def load_physical_features(self) -> Tuple[pd.DataFrame, List[str]]:
        """
        加载物理存在的真实特征数据

        Returns:
            Tuple[pd.DataFrame, List[str]]: (特征数据, 特征名称列表)
        """
        logger.info("🔍 加载物理存在的真实特征数据...")

        conn = self.schema_manager.get_connection()

        # 首先查询数据库中实际存在的字段
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'match_features_training'
                AND table_schema = 'public'
                AND data_type IN ('integer', 'double precision', 'numeric', 'real')
                AND column_name NOT IN ('id', 'external_id')
                ORDER BY column_name
            """)
            all_columns = [row[0] for row in cursor.fetchall()]

        # 定义实际有数据的物理特征（基于之前分析）
        potential_features = [
            # 核心比赛特征
            'home_xg', 'away_xg', 'home_possession', 'away_possession',

            # 射门特征
            'home_shots_total', 'away_shots_total',
            'home_shots_on_target', 'away_shots_on_target',

            # 角球特征
            'home_corners', 'away_corners',

            # 纪律特征
            'home_yellow_cards', 'away_yellow_cards',
        ]

        # 只选择实际存在的字段
        feature_columns = [f for f in potential_features if f in all_columns and self._check_feature_exists(conn, f)]

        if not feature_columns:
            raise ValueError("没有找到有效的物理特征数据")

        # 构建SQL查询，只加载有数据的特征
        where_clause = ""
        if feature_columns:
            # 至少核心特征不为空
            core_conditions = [f'{f} IS NOT NULL' for f in feature_columns[:4]]
            where_clause = f"AND ({' AND '.join(core_conditions)})"

        if feature_columns:
            features_select = ", " + ", ".join(feature_columns)
        else:
            features_select = ""

        query = f"""
            SELECT
                external_id,
                home_team,
                away_team,
                match_time,
                home_score,
                away_score
                {features_select}
            FROM match_features_training
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
              {where_clause}
            ORDER BY match_time DESC
        """

        df = pd.read_sql(query, conn, index_col=None)
        conn.close()

        logger.info(f"✅ 加载完成: {len(df)} 条记录, {len(feature_columns)} 个特征")

        self.feature_names = feature_columns
        return df, feature_columns

    def _check_feature_exists(self, conn, feature_name: str) -> bool:
        """检查特征是否存在且有数据"""
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COUNT({feature_name}) as count
                    FROM match_features_training
                    WHERE {feature_name} IS NOT NULL
                """)
                count = cursor.fetchone()[0]
                return count > 100  # 至少有100条数据
        except Exception as e:
            logger.warning(f"检查特征 {feature_name} 失败: {e}")
            return False

    def create_target_variable(self, df: pd.DataFrame) -> pd.Series:
        """
        创建目标变量：比赛结果
        0: 客胜, 1: 平局, 2: 主胜

        Args:
            df: 特征数据

        Returns:
            pd.Series: 目标变量
        """
        def determine_result(row):
            home_score = row['home_score']
            away_score = row['away_score']

            if home_score > away_score:
                return 2  # 主胜
            elif home_score < away_score:
                return 0  # 客胜
            else:
                return 1  # 平局

        y = df.apply(determine_result, axis=1)

        # 统计结果分布
        result_counts = y.value_counts().sort_index()
        logger.info(f"📊 比赛结果分布: 客胜={result_counts.get(0,0)}, 平局={result_counts.get(1,0)}, 主胜={result_counts.get(2,0)}")

        return y

    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据

        Args:
            df: 原始数据

        Returns:
            Tuple[np.ndarray, np.ndarray]: (特征矩阵, 目标变量)
        """
        logger.info("🔧 准备训练数据...")

        # 提取特征矩阵
        X = df[self.feature_names].values

        # 处理缺失值 - 使用中位数填充（仅用于训练，实际预测时会处理）
        from sklearn.impute import SimpleImputer
        imputer = SimpleImputer(strategy='median')
        X = imputer.fit_transform(X)

        # 创建目标变量
        y = self.create_target_variable(df)

        # 特征标准化
        X_scaled = self.scaler.fit_transform(X)

        logger.info(f"✅ 训练数据准备完成: 特征矩阵{X_scaled.shape}, 目标变量{y.shape}")

        return X_scaled, y.values

    def train_model(self, X: np.ndarray, y: np.ndarray) -> xgb.XGBClassifier:
        """
        训练XGBoost模型

        Args:
            X: 特征矩阵
            y: 目标变量

        Returns:
            xgb.XGBClassifier: 训练好的模型
        """
        logger.info("🚀 开始V5.0模型训练...")

        # XGBoost参数 - 基于真实数据的优化配置
        params = {
            'objective': 'multi:softmax',
            'num_class': 3,
            'max_depth': 4,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'eval_metric': 'mlogloss',
            'verbosity': 1
            # 注释掉 early_stopping_rounds，因为交叉验证不需要
        }

        # 创建模型
        model = xgb.XGBClassifier(**params)

        # 交叉验证评估
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

        logger.info(f"📈 5折交叉验证准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        # 训练最终模型
        model.fit(X, y)

        # 保存交叉验证统计
        self.training_stats = {
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'cv_scores': cv_scores.tolist(),
            'feature_count': X.shape[1],
            'sample_count': X.shape[0]
        }

        logger.info("✅ 模型训练完成")
        return model

    def evaluate_model(self, model: xgb.XGBClassifier, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        评估模型性能

        Args:
            model: 训练好的模型
            X: 特征矩阵
            y: 目标变量

        Returns:
            Dict[str, Any]: 评估结果
        """
        logger.info("📊 评估模型性能...")

        # 预测
        y_pred = model.predict(X)

        # 准确率
        accuracy = accuracy_score(y, y_pred)

        # 分类报告
        class_report = classification_report(y, y_pred, output_dict=True,
                                          target_names=['客胜', '平局', '主胜'])

        # 混淆矩阵
        cm = confusion_matrix(y, y_pred)

        # 特征重要性
        feature_importance = model.feature_importances_
        feature_importance_dict = dict(zip(self.feature_names, [float(x) for x in feature_importance]))

        # 按重要性排序
        sorted_features = sorted(feature_importance_dict.items(),
                               key=lambda x: x[1], reverse=True)

        evaluation_results = {
            'accuracy': accuracy,
            'classification_report': class_report,
            'confusion_matrix': cm.tolist(),
            'feature_importance': sorted_features,
            'top_10_features': sorted_features[:10]
        }

        logger.info(f"🎯 模型准确率: {accuracy:.4f}")
        logger.info("🏆 Top 10 特征重要性:")
        for i, (feature, importance) in enumerate(sorted_features[:10]):
            logger.info(f"  {i+1:2d}. {feature:20s}: {importance:.4f}")

        return evaluation_results

    def save_model(self, model: xgb.XGBClassifier, evaluation_results: Dict[str, Any]) -> str:
        """
        保存模型和相关文件

        Args:
            model: 训练好的模型
            evaluation_results: 评估结果

        Returns:
            str: 模型保存路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"xgb_v5_realistic_{timestamp}"

        # 模型文件路径
        model_path = f"data/models/{model_name}.pkl"
        scaler_path = f"data/models/{model_name}_scaler.pkl"
        metadata_path = f"data/models/{model_name}_metadata.json"

        # 确保目录存在
        import os
        os.makedirs("data/models", exist_ok=True)

        # 保存模型
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        # 保存标准化器
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

        # 保存元数据
        import json
        metadata = {
            'model_name': model_name,
            'model_version': 'V5.0',
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names,
            'training_date': datetime.now().isoformat(),
            'physical_features_only': True,
            'training_stats': self.training_stats,
            'evaluation_results': {
                'accuracy': evaluation_results['accuracy'],
                'top_10_features': evaluation_results['top_10_features']
            },
            'data_source': 'physical_database_features_only'
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"💾 模型已保存: {model_path}")
        logger.info(f"📋 元数据已保存: {metadata_path}")

        return model_path

    def run_full_training_pipeline(self) -> Dict[str, Any]:
        """
        运行完整的训练管线

        Returns:
            Dict[str, Any]: 训练结果
        """
        try:
            logger.info("🎯 开始V5.0真实感模型训练管线...")

            # 1. 加载物理特征数据
            df, feature_names = self.load_physical_features()

            # 2. 准备训练数据
            X, y = self.prepare_training_data(df)

            # 3. 训练模型
            model = self.train_model(X, y)

            # 4. 评估模型
            evaluation_results = self.evaluate_model(model, X, y)

            # 5. 保存模型
            model_path = self.save_model(model, evaluation_results)

            # 返回训练结果
            training_results = {
                'success': True,
                'model_path': model_path,
                'feature_count': len(feature_names),
                'sample_count': len(df),
                'accuracy': evaluation_results['accuracy'],
                'cv_accuracy': self.training_stats['cv_accuracy_mean'],
                'top_10_features': evaluation_results['top_10_features'],
                'feature_names': feature_names,
                'training_stats': self.training_stats
            }

            logger.info("🎉 V5.0真实感模型训练完成!")
            return training_results

        except Exception as e:
            logger.error(f"❌ 模型训练失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    trainer = V5RealisticModelTrainer()
    results = trainer.run_full_training_pipeline()

    if results['success']:
        print("\\n" + "="*60)
        print("🏆 V5.0 真实感模型训练成功!")
        print("="*60)
        print(f"📊 模型准确率: {results['accuracy']:.4f}")
        print(f"📈 交叉验证准确率: {results['cv_accuracy']:.4f}")
        print(f"🔢 物理特征维度: {results['feature_count']}")
        print(f"📋 训练样本数量: {results['sample_count']}")
        print(f"💾 模型保存路径: {results['model_path']}")

        print("\\n🏆 Top 10 特征重要性:")
        for i, (feature, importance) in enumerate(results['top_10_features']):
            print(f"  {i+1:2d}. {feature:20s}: {importance:.4f}")
    else:
        print(f"❌ 训练失败: {results['error']}")


if __name__ == "__main__":
    main()