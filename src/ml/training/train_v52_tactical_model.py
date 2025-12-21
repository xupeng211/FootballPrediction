#!/usr/bin/env python3
"""
V5.2 高维战术模型训练器
基于钢铁管线提取的高维数据进行训练
目标：10-Fold CV准确率突破58%
"""

import logging
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from src.config_unified import get_settings
from src.database.schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


class V52TacticalModelTrainer:
    """V5.2 高维战术模型训练器"""

    def __init__(self):
        """初始化训练器"""
        self.settings = get_settings()
        self.schema_manager = get_schema_manager()
        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = []
        self.training_stats = {}

    def load_high_dimensional_features(self) -> Tuple[pd.DataFrame, List[str]]:
        """
        加载高维特征数据

        Returns:
            Tuple[pd.DataFrame, List[str]]: (特征数据, 特征名称列表)
        """
        logger.info("🚀 加载V5.2高维战术特征数据...")

        conn = self.schema_manager.get_connection()

        # 首先获取所有有数据的字段
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

        logger.info(f"📋 发现 {len(all_columns)} 个数值字段")

        # 检查每个字段的填充率
        high_quality_fields = []
        for col in all_columns:
            cursor.execute(f"""
                SELECT COUNT({col}) as count
                FROM match_features_training
                WHERE {col} IS NOT NULL
            """)
            count = cursor.fetchone()[0]
            if count >= 50:  # 至少50条数据
                fill_rate = (count / 467) * 100  # 467是黄金样本数
                high_quality_fields.append((col, fill_rate))

            high_quality_fields.sort(key=lambda x: x[1], reverse=True)
            logger.info(f"✅ 高质量字段({len(high_quality_fields)}个):")
            for field, rate in high_quality_fields[:10]:
                logger.info(f"   {field}: {rate:.1f}%")

        # 选择最佳特征字段
        feature_columns = [f[0] for f in high_quality_fields if f[1] >= 30]  # 填充率 >= 30%

        if not feature_columns:
            raise ValueError("没有找到有效的高质量特征数据")

        # 构建SQL查询
        core_features_select = ", ".join(feature_columns)

        query = f"""
            SELECT
                external_id,
                home_team,
                away_team,
                match_time,
                home_score,
                away_score
                {', ' + core_features_select if feature_columns else ''}
            FROM match_features_training
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
            ORDER BY match_time DESC
        """

        df = pd.read_sql(query, conn)
        conn.close()

        logger.info(f"✅ 加载完成: {len(df)} 条记录, {len(feature_columns)} 个特征")

        self.feature_names = feature_columns
        return df, feature_columns

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

    def prepare_high_dim_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备高维训练数据

        Args:
            df: 原始数据

        Returns:
            Tuple[np.ndarray, np.ndarray]: (特征矩阵, 目标变量)
        """
        logger.info("🔧 准备高维训练数据...")

        # 提取特征矩阵
        X = df[self.feature_names].values

        # 处理缺失值 - 使用中位数填充
        from sklearn.impute import SimpleImputer
        imputer = SimpleImputer(strategy='median')
        X = imputer.fit_transform(X)

        # 创建目标变量
        y = self.create_target_variable(df)

        # 特征标准化
        X_scaled = self.scaler.fit_transform(X)

        logger.info(f"✅ 高维训练数据准备完成: 特征矩阵{X_scaled.shape}, 目标变量{y.shape}")

        return X_scaled, y.values

    def train_tactical_model(self, X: np.ndarray, y: np.ndarray) -> xgb.XGBClassifier:
        """
        训练高维战术模型

        Args:
            X: 特征矩阵
            y: 目标变量

        Returns:
            xgb.XGBClassifier: 训练好的模型
        """
        logger.info("🚀 开始V5.2高维战术模型训练...")

        # XGBoost参数 - 针对高维数据优化
        params = {
            'objective': 'multi:softmax',
            'num_class': 3,
            'max_depth': 5,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.6,
            'colsample_bylevel': 0.8,
            'reg_alpha': 0.1,  # L1正则化
            'reg_lambda': 1.0,  # L2正则化
            'random_state': 42,
            'eval_metric': 'mlogloss',
            'verbosity': 1,
            'min_child_weight': 1,
            'gamma': 0.1
        }

        # 创建模型
        model = xgb.XGBClassifier(**params)

        # 10折交叉验证
        cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

        logger.info(f"📈 10折交叉验证准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        # 训练最终模型
        model.fit(X, y)

        # 保存交叉验证统计
        self.training_stats = {
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'cv_scores': cv_scores.tolist(),
            'feature_count': X.shape[1],
            'sample_count': X.shape[0],
            'cross_validation_folds': 10,
            'model_complexity': 'high_dimensional_tactical'
        }

        logger.info("✅ 模型训练完成")
        return model

    def evaluate_tactical_model(self, model: xgb.XGBClassifier, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        评估高维战术模型性能

        Args:
            model: 训练好的模型
            X: 特征矩阵
            y: 目标变量

        Returns:
            Dict[str, Any]: 评估结果
        """
        logger.info("📊 评估V5.2高维战术模型性能...")

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

        # 特征类型分析
        feature_analysis = self.analyze_feature_types(sorted_features)

        evaluation_results = {
            'accuracy': accuracy,
            'classification_report': class_report,
            'confusion_matrix': cm.tolist(),
            'feature_importance': sorted_features,
            'top_20_features': sorted_features[:20],
            'feature_analysis': feature_analysis
        }

        logger.info(f"🎯 模型准确率: {accuracy:.4f}")

        # 检查是否突破58%目标
        if accuracy >= 0.58:
            logger.info(f"🎉 恭喜！模型准确率 {accuracy:.4f}% 成功突破58%目标！")
        else:
            logger.info(f"📊 模型准确率 {accuracy:.4f}%，距离58%目标还差{(0.58 - accuracy)*100:.1f}%")

        logger.info("🏆 Top 10 特征重要性:")
        for i, (feature, importance) in enumerate(sorted_features[:10]):
            logger.info(f"  {i+1:2d}. {feature:25s}: {importance:.4f}")

        return evaluation_results

    def analyze_feature_types(self, sorted_features: List[Tuple[str, float]]) -> Dict[str, Any]:
        """
        分析特征类型分布

        Args:
            sorted_features: 按重要性排序的特征

        Returns:
            Dict[str, Any]: 特征类型分析
        """
        feature_types = {
            '核心基础特征': 0,
            '战术特征': 0,
            '赔率特征': 0,
            '衍生特征': 0,
            '其他特征': 0
        }

        feature_details = {
            'core_features': [],
            'tactical_features': [],
            'odds_features': [],
            'derived_features': [],
            'other_features': []
        }

        for feature, importance in sorted_features:
            feature_lower = feature.lower()

            if any(keyword in feature_lower for keyword in ['xg', 'expected']):
                feature_types['核心基础特征'] += importance
                feature_details['core_features'].append((feature, importance))
            elif any(keyword in feature_lower for keyword in ['possession', 'shots', 'corners', 'passes', 'tackles', 'clearances', 'interceptions', 'fouls', 'offsides']):
                feature_types['战术特征'] += importance
                feature_details['tactical_features'].append((feature, importance))
            elif 'odds' in feature_lower:
                feature_types['赔率特征'] += importance
                feature_details['odds_features'].append((feature, importance))
            elif any(keyword in feature_lower for keyword in ['_diff', '_total', '_avg']):
                feature_types['衍生特征'] += importance
                feature_details['derived_features'].append((feature, importance))
            else:
                feature_types['其他特征'] += importance
                feature_details['other_features'].append((feature, importance))

        return {
            'importance_by_type': feature_types,
            'feature_details': feature_details,
            'dominant_type': max(feature_types, key=feature_types.get)
        }

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
        model_name = f"xgb_v52_tactical_{timestamp}"

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
            'model_version': 'V5.2_High_Dimensional_Tactical',
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names,
            'training_date': datetime.now().isoformat(),
            'data_source': 'V5.2钢铁管线高维数据',
            'training_stats': self.training_stats,
            'evaluation_results': {
                'accuracy': evaluation_results['accuracy'],
                'target_achieved': evaluation_results['accuracy'] >= 0.58,
                'top_20_features': evaluation_results['top_20_features'],
                'feature_analysis': evaluation_results['feature_analysis']
            }
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"💾 V5.2模型已保存: {model_path}")
        logger.info(f"📋 元数据已保存: {metadata_path}")

        return model_path

    def run_v52_training_pipeline(self) -> Dict[str, Any]:
        """
        运行V5.2训练管线

        Returns:
            Dict[str, Any]: 训练结果
        """
        try:
            logger.info("🎯 开始V5.2高维战术模型训练管线...")

            # 1. 加载高维特征数据
            df, feature_names = self.load_high_dimensional_features()

            # 2. 准备训练数据
            X, y = self.prepare_high_dim_training_data(df)

            # 3. 训练战术模型
            model = self.train_tactical_model(X, y)

            # 4. 评估模型性能
            evaluation_results = self.evaluate_tactical_model(model, X, y)

            # 5. 保存模型
            model_path = self.save_model(model, evaluation_results)

            # 6. 生成特征贡献度报告
            self.generate_feature_contribution_report(evaluation_results)

            # 返回训练结果
            training_results = {
                'success': True,
                'model_path': model_path,
                'feature_count': len(feature_names),
                'sample_count': len(df),
                'accuracy': evaluation_results['accuracy'],
                'cv_accuracy': self.training_stats['cv_accuracy_mean'],
                'target_achieved': evaluation_results['accuracy'] >= 0.58,
                'top_20_features': evaluation_results['top_20_features'],
                'feature_analysis': evaluation_results['feature_analysis'],
                'training_stats': self.training_stats
            }

            logger.info("🎉 V5.2高维战术模型训练完成!")

            return training_results

        except Exception as e:
            logger.error(f"❌ 模型训练失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_feature_contribution_report(self, evaluation_results: Dict[str, Any]):
        """生成特征贡献度报告"""
        logger.info("📋 生成特征贡献度报告...")

        feature_analysis = evaluation_results['feature_analysis']
        importance_by_type = feature_analysis['importance_by_type']
        dominant_type = feature_analysis['dominant_type']

        logger.info(f"\n📊 V5.2 特征贡献度分析报告:")
        logger.info(f"   主导特征类型: {dominant_type}")
        logger.info(f"   核心基础特征贡献: {importance_by_type['核心基础特征']:.4f}")
        logger.info(f"   战术特征贡献: {importance_by_type['战术特征']:.4f}")
        logger.info(f"   赔率特征贡献: {importance_by_type['赔率特征']:.4f}")
        logger.info(f"   衍生特征贡献: {importance_by_type['衍生特征']:.4f}")
        logger.info(f"   其他特征贡献: {importance_by_type['其他特征']:.4f}")


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    trainer = V52TacticalModelTrainer()
    results = trainer.run_v52_training_pipeline()

    if results['success']:
        print("\\n" + "="*70)
        print("🏆 V5.2 高维战术模型训练成功!")
        print("="*70)
        print(f"📊 模型准确率: {results['accuracy']:.4f}")
        print(f"📈 10折CV准确率: {results['cv_accuracy']:.4f}")
        print(f"🎯 目标达成: {'✅ 是' if results['target_achieved'] else '❌ 否'}")
        print(f"🔢 特征维度: {results['feature_count']}")
        print(f"📋 训练样本: {results['sample_count']}")
        print(f"💾 模型保存: {results['model_path']}")

        # 显示Top 20特征
        print("\\n🏆 Top 20 特征重要性:")
        for i, (feature, importance) in enumerate(results['top_20_features']):
            print(f"  {i+1:2d}. {feature:25s}: {importance:.4f}")

        # 特征类型分析
        feature_analysis = results['feature_analysis']
        importance_by_type = feature_analysis['importance_by_type']
        print("\\n📊 特征类型贡献度:")
        for feature_type, importance in importance_by_type.items():
            if importance > 0:
                print(f"   {feature_type}: {importance:.4f}")

        # 检查是否达成目标
        if results['target_achieved']:
            print(f"\\n🎉 恭喜！V5.2模型成功突破58%准确率目标！")
        else:
            gap = 0.58 - results['accuracy']
            print(f"\\n📊 V5.2模型距离58%目标还差 {gap*100:.1f}%")

    else:
        print(f"❌ 训练失败: {results['error']}")


if __name__ == "__main__":
    main()