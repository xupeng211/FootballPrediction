#!/usr/bin/env python3
"""
V5.2 智能高维战术模型训练器
动态检测可用字段并训练模型
"""

import logging
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.impute import SimpleImputer

from src.config_unified import get_settings
from src.database.schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


class V52SmartTrainer:
    def __init__(self):
        self.settings = get_settings()
        self.schema_manager = get_schema_manager()
        self.available_features = []
        self.numeric_features = []

    def discover_available_features(self):
        """发现可用的特征字段"""
        logger.info("🔍 发现可用特征字段...")

        conn = self.schema_manager.get_connection()
        cursor = conn.cursor()

        # 获取所有数值字段
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'match_features_training'
            AND table_schema = 'public'
            AND data_type IN ('integer', 'double precision', 'numeric', 'real', 'smallint')
            AND column_name NOT IN ('id', 'external_id')
            ORDER BY column_name
        """)

        all_numeric_fields = [row[0] for row in cursor.fetchall()]
        logger.info(f"📋 发现 {len(all_numeric_fields)} 个数值字段")

        # 检查哪些字段有实际数据
        data_fields = []
        for field in all_numeric_fields:
            try:
                cursor.execute(f"SELECT COUNT({field}) FROM match_features_training WHERE {field} IS NOT NULL")
                count = cursor.fetchone()[0]
                if count >= 10:  # 至少10条数据
                    data_fields.append((field, count))
                    logger.debug(f"✅ {field}: {count} 条数据")
                else:
                    logger.debug(f"❌ {field}: 只有 {count} 条数据")
            except Exception as e:
                logger.warning(f"⚠️ 检查字段 {field} 失败: {e}")

        # 按数据量排序
        data_fields.sort(key=lambda x: x[1], reverse=True)

        self.numeric_features = [f[0] for f in data_fields]
        logger.info(f"🎯 筛选出 {len(self.numeric_features)} 个有效特征字段")

        # 显示前20个字段
        logger.info("🏆 数据量最多的前20个字段:")
        for i, (field, count) in enumerate(data_fields[:20]):
            logger.info(f"  {i+1:2d}. {field:30s}: {count:4d} 条数据")

        conn.close()

    def load_training_data(self):
        """加载训练数据"""
        logger.info("🚀 加载训练数据...")

        if not self.numeric_features:
            self.discover_available_features()

        conn = self.schema_manager.get_connection()

        # 构建查询，使用所有可用的数值特征
        feature_select = ", ".join(self.numeric_features)

        query = f"""
            SELECT
                external_id,
                home_score,
                away_score,
                {feature_select}
            FROM match_features_training
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
            ORDER BY updated_at DESC
        """

        df = pd.read_sql(query, conn)
        conn.close()

        logger.info(f"✅ 加载数据: {len(df)} 条记录, {len(self.numeric_features)} 个特征字段")

        return df

    def create_target_variable(self, df):
        """创建目标变量"""
        # 重置索引避免标签问题
        df_reset = df.reset_index(drop=True)

        # 转换为numpy数组进行比较
        home_scores = df_reset['home_score'].values.astype(float)
        away_scores = df_reset['away_score'].values.astype(float)

        # 向量化比较
        y = np.where(home_scores > away_scores, 2,
                    np.where(home_scores < away_scores, 0, 1))

        result_counts = pd.Series(y).value_counts().sort_index()
        logger.info(f"📊 结果分布: 客胜={result_counts.get(0,0)}, 平局={result_counts.get(1,0)}, 主胜={result_counts.get(2,0)}")

        return pd.Series(y, index=df_reset.index)

    def train_smart_model(self):
        """训练V5.2智能模型"""
        logger.info("🧠 开始V5.2智能高维战术模型训练...")

        # 加载数据
        df = self.load_training_data()

        if len(df) == 0:
            logger.error("❌ 没有可用的训练数据")
            return None

        # 重置索引避免标签问题
        df = df.reset_index(drop=True)

        # 创建目标变量
        y = self.create_target_variable(df)

        # 选择特征列（排除非数值字段）
        feature_cols = []
        for col in df.columns:
            if col not in ['external_id', 'home_score', 'away_score'] and df[col].dtype in ['int64', 'float64']:
                feature_cols.append(col)

        logger.info(f"📊 最终使用特征数: {len(feature_cols)}")
        self.available_features = feature_cols

        X = df[feature_cols].values

        # 处理缺失值
        imputer = SimpleImputer(strategy='median')
        X = imputer.fit_transform(X)

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        logger.info(f"✅ 数据预处理完成: 特征矩阵{X_scaled.shape}")

        # XGBoost参数 - 针对高维数据优化
        params = {
            'objective': 'multi:softmax',
            'num_class': 3,
            'max_depth': 6,          # 稍微增加深度
            'learning_rate': 0.05,   # 降低学习率
            'n_estimators': 300,     # 增加树的数量
            'subsample': 0.8,
            'colsample_bytree': 0.7, # 增加特征采样比例
            'colsample_bylevel': 0.8,
            'reg_alpha': 0.1,        # L1正则化
            'reg_lambda': 1.0,       # L2正则化
            'random_state': 42,
            'eval_metric': 'mlogloss',
            'min_child_weight': 1,
            'gamma': 0.05            # 降低gamma值
        }

        model = xgb.XGBClassifier(**params)

        # 10折交叉验证
        cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')

        logger.info(f"📈 10折CV准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        # 训练最终模型
        model.fit(X_scaled, y)

        # 评估
        y_pred = model.predict(X_scaled)
        accuracy = accuracy_score(y, y_pred)
        logger.info(f"🎯 训练集准确率: {accuracy:.4f}")

        # 特征重要性分析
        feature_importance = dict(zip(feature_cols, model.feature_importances_))
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        logger.info("🏆 Top 15 重要特征:")
        for i, (feature, importance) in enumerate(sorted_features[:15]):
            logger.info(f"  {i+1:2d}. {feature:30s}: {importance:.4f}")

        # 特征类型分析
        feature_analysis = self.analyze_feature_types(sorted_features)

        # 保存模型
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"xgb_v52_smart_tactical_{timestamp}"

        import os
        os.makedirs("data/models", exist_ok=True)

        model_path = f"data/models/{model_name}.pkl"
        scaler_path = f"data/models/{model_name}_scaler.pkl"
        imputer_path = f"data/models/{model_name}_imputer.pkl"

        # 保存模型和预处理组件
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)

        with open(imputer_path, 'wb') as f:
            pickle.dump(imputer, f)

        # 保存详细元数据
        import json
        metadata = {
            'model_name': model_name,
            'version': 'V5.2_Smart_High_Dimensional',
            'accuracy': accuracy,
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'feature_count': len(feature_cols),
            'sample_count': len(df),
            'top_features': sorted_features[:30],
            'feature_analysis': feature_analysis,
            'feature_discovery_stats': {
                'total_numeric_fields': len(self.numeric_features),
                'used_features': len(feature_cols),
                'feature_utilization_rate': len(feature_cols) / len(self.numeric_features) if self.numeric_features else 0
            },
            'training_date': datetime.now().isoformat(),
            'data_source': 'V5.2智能高维数据-动态字段发现'
        }

        metadata_path = f"data/models/{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"💾 智能模型已保存: {model_path}")

        # 检查是否达成目标
        target_accuracy = 0.58
        if accuracy >= target_accuracy:
            logger.info(f"🎉 恭喜！模型准确率 {accuracy:.4f} 突破{target_accuracy*100:.0f}%目标！")
            target_achieved = True
        else:
            gap = target_accuracy - accuracy
            logger.info(f"📊 距离{target_accuracy*100:.0f}%目标还差 {gap*100:.1f}%")
            target_achieved = False

        # 生成特征贡献度报告
        self.generate_feature_report(sorted_features, feature_analysis, accuracy, cv_scores)

        return {
            'model_path': model_path,
            'scaler_path': scaler_path,
            'imputer_path': imputer_path,
            'metadata_path': metadata_path,
            'accuracy': accuracy,
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'feature_count': len(feature_cols),
            'sample_count': len(df),
            'top_features': sorted_features,
            'feature_analysis': feature_analysis,
            'target_achieved': target_achieved,
            'data_stats': {
                'total_discovered_fields': len(self.numeric_features),
                'utilized_features': len(feature_cols),
                'utilization_rate': len(feature_cols) / len(self.numeric_features) if self.numeric_features else 0
            }
        }

    def analyze_feature_types(self, sorted_features):
        """分析特征类型分布"""
        feature_types = {
            '核心xG特征': 0,
            '控球率特征': 0,
            '射门特征': 0,
            '战术特征': 0,
            '赔率特征': 0,
            '历史数据特征': 0,
            '衍生特征': 0,
            '其他特征': 0
        }

        feature_details = {key: [] for key in feature_types.keys()}

        for feature, importance in sorted_features:
            feature_lower = feature.lower()

            if any(keyword in feature_lower for keyword in ['xg', 'expected']):
                feature_types['核心xG特征'] += importance
                feature_details['核心xG特征'].append((feature, importance))
            elif 'possession' in feature_lower:
                feature_types['控球率特征'] += importance
                feature_details['控球率特征'].append((feature, importance))
            elif 'shot' in feature_lower or 'corner' in feature_lower:
                feature_types['射门特征'] += importance
                feature_details['射门特征'].append((feature, importance))
            elif any(keyword in feature_lower for keyword in ['pass', 'cross', 'tackle', 'clear', 'aerial', 'foul', 'offside']):
                feature_types['战术特征'] += importance
                feature_details['战术特征'].append((feature, importance))
            elif 'odds' in feature_lower or 'implied' in feature_lower:
                feature_types['赔率特征'] += importance
                feature_details['赔率特征'].append((feature, importance))
            elif any(keyword in feature_lower for keyword in ['form', 'recent', 'h2h']):
                feature_types['历史数据特征'] += importance
                feature_details['历史数据特征'].append((feature, importance))
            elif any(keyword in feature_lower for keyword in ['_diff', '_total', '_avg']):
                feature_types['衍生特征'] += importance
                feature_details['衍生特征'].append((feature, importance))
            else:
                feature_types['其他特征'] += importance
                feature_details['其他特征'].append((feature, importance))

        return {
            'importance_by_type': feature_types,
            'feature_details': feature_details,
            'dominant_type': max(feature_types, key=feature_types.get)
        }

    def generate_feature_report(self, sorted_features, feature_analysis, accuracy, cv_scores):
        """生成详细的特征贡献度报告"""
        logger.info("\n" + "="*70)
        logger.info("🏆 V5.2 智能高维战术模型特征贡献度分析报告")
        logger.info("="*70)

        logger.info(f"📊 模型性能指标:")
        logger.info(f"   • 训练集准确率: {accuracy:.4f}")
        logger.info(f"   • 10折CV准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        logger.info(f"   • 特征维度: {len(sorted_features)}")

        logger.info(f"\n🎯 特征类型贡献度分析:")
        importance_by_type = feature_analysis['importance_by_type']
        dominant_type = feature_analysis['dominant_type']

        for feature_type, importance in importance_by_type.items():
            if importance > 0:
                percentage = (importance / sum(importance_by_type.values())) * 100
                logger.info(f"   • {feature_type}: {importance:.4f} ({percentage:.1f}%)")

        logger.info(f"\n👑 主导特征类型: {dominant_type}")

        logger.info(f"\n🏆 Top 20 最重要特征:")
        for i, (feature, importance) in enumerate(sorted_features[:20]):
            logger.info(f"   {i+1:2d}. {feature:30s}: {importance:.4f}")

        logger.info("="*70)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    trainer = V52SmartTrainer()
    results = trainer.train_smart_model()

    if results:
        print("\n" + "="*70)
        print("🧠 V5.2 智能高维战术模型训练完成!")
        print("="*70)
        print(f"📊 模型准确率: {results['accuracy']:.4f}")
        print(f"📈 10折CV准确率: {results['cv_accuracy_mean']:.4f} ± {results['cv_accuracy_std']:.4f}")
        print(f"🎯 58%目标达成: {'✅ 是' if results['target_achieved'] else '❌ 否'}")
        print(f"🔢 特征维度: {results['feature_count']}")
        print(f"📋 训练样本: {results['sample_count']}")
        print(f"💾 模型路径: {results['model_path']}")
        print(f"🔍 字段利用率: {results['data_stats']['utilization_rate']:.1%}")

        print("\n🏆 Top 10 特征重要性:")
        for i, (feature, importance) in enumerate(results['top_features'][:10]):
            print(f"  {i+1:2d}. {feature:30s}: {importance:.4f}")

    else:
        print("❌ 训练失败")


if __name__ == "__main__":
    main()