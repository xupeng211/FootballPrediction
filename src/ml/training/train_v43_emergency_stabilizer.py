#!/usr/bin/env python3
"""
V4.3 紧急稳定化训练脚本
基于真实415场胜平负分布数据的平衡重训
解决"180维特征下混淆矩阵平局预测偏差"
"""

import sys
import os
import logging
import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import xgboost as xgb

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class V43EmergencyStabilizer:
    """V4.3 紧急稳定化训练器"""

    def __init__(self):
        """初始化训练器"""
        self.settings = self._get_production_settings()
        self.project_root = Path(__file__).parent.parent

        # 模型和报告目录
        self.models_dir = self.project_root / "data" / "models"
        self.reports_dir = self.project_root / "reports" / "v43_emergency"

        # 创建目录
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 模型文件路径
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.model_path = self.models_dir / f"xgb_v43_emergency_{timestamp}.joblib"
        self.report_path = self.reports_dir / f"v43_emergency_report_{timestamp}.json"

        logger.info("🚨 V4.3 紧急稳定化训练器初始化完成")
        logger.info(f"📁 模型保存路径: {self.model_path}")
        logger.info(f"📊 报告保存路径: {self.report_path}")

    def _get_production_settings(self):
        """获取生产环境配置"""
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # 生产数据库配置
        return {
            "db_config": {
                "host": "localhost",
                "port": 5432,
                "database": "football_prediction",
                "user": "football_user",
                "password": "football_pass",
            }
        }

    def load_real_match_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        从生产数据库加载真实比赛数据

        Returns:
            (特征数据, 标签数据)
        """
        logger.info("🔍 加载真实比赛数据...")

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # 连接生产数据库
            conn = psycopg2.connect(**self.settings["db_config"])

            # 查询真实比赛数据和结果
            query = """
                SELECT
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.result_score,
                    m.league_name,
                    m.season,
                    mft.*,
                    -- 计算结果标签
                    CASE
                        WHEN CAST(SPLIT_PART(m.result_score, '-', 1) AS INTEGER) >
                             CAST(SPLIT_PART(m.result_score, '-', 2) AS INTEGER) THEN 0  -- Home Win
                        WHEN CAST(SPLIT_PART(m.result_score, '-', 1) AS INTEGER) =
                             CAST(SPLIT_PART(m.result_score, '-', 2) AS INTEGER) THEN 1  -- Draw
                        WHEN CAST(SPLIT_PART(m.result_score, '-', 1) AS INTEGER) <
                             CAST(SPLIT_PART(m.result_score, '-', 2) AS INTEGER) THEN 2  -- Away Win
                    END as outcome_label
                FROM matches m
                LEFT JOIN match_features_training mft ON m.external_id = mft.external_id
                WHERE m.status = 'Finished'
                  AND m.result_score IS NOT NULL
                  AND m.result_score ~ '^[0-9]+-[0-9]+$'
                  AND mft.external_id IS NOT NULL  -- 确保有特征数据
                ORDER BY m.match_time DESC
            """

            logger.info("📊 执行数据查询...")
            df = pd.read_sql(query, conn)
            conn.close()

            logger.info(f"✅ 数据加载完成: {len(df)} 条记录")

            if len(df) == 0:
                raise ValueError("❌ 没有找到有效的比赛数据！")

            # 显示结果分布
            outcome_dist = df['outcome_label'].value_counts().sort_index()
            logger.info("📈 真实胜平负分布:")
            for outcome, count in outcome_dist.items():
                outcome_name = ['Home Win', 'Draw', 'Away Win'][outcome]
                percentage = count / len(df) * 100
                logger.info(f"   {outcome_name}: {count} 场 ({percentage:.1f}%)")

            # 特征工程
            X, y = self._prepare_features_and_labels(df)

            return X, y

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            raise

    def _prepare_features_and_labels(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备特征和标签数据

        Args:
            df: 原始数据框

        Returns:
            (特征数据, 标签数据)
        """
        logger.info("🔧 特征工程...")

        # 选择数值特征
        numeric_features = [
            'home_xg', 'away_xg', 'xg_total', 'xg_diff',
            'home_possession', 'away_possession', 'home_corners', 'away_corners',
            'home_shots_total', 'away_shots_total', 'home_yellow_cards', 'away_yellow_cards',
            'home_red_cards', 'away_red_cards', 'home_passes', 'away_passes'
        ]

        # 过滤存在的特征
        existing_features = [f for f in numeric_features if f in df.columns]
        logger.info(f"📊 可用特征: {len(existing_features)} 个")

        X = df[existing_features].copy()
        y = df['outcome_label']

        # 处理缺失值
        X = X.fillna(X.median())

        # 特征工程：添加派生特征
        if 'home_xg' in X.columns and 'away_xg' in X.columns:
            X['xg_ratio'] = X['home_xg'] / (X['home_xg'] + X['away_xg'] + 1e-6)

        if 'home_possession' in X.columns and 'away_possession' in X.columns:
            X['possession_diff'] = X['home_possession'] - X['away_possession']

        logger.info(f"✅ 特征工程完成: {X.shape[1]} 维特征, {len(X)} 条样本")

        return X, y

    def train_balanced_model(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """
        训练平衡模型（针对平局偏差优化）

        Args:
            X: 特征数据
            y: 标签数据

        Returns:
            训练结果
        """
        logger.info("🧠 开始V4.3平衡训练...")

        # 计算类别权重（解决平局偏差核心）
        class_counts = y.value_counts().sort_index()
        total_samples = len(y)

        # 平局类别额外权重
        base_weights = {0: 1.0, 1: 1.0, 2: 1.0}
        draw_boost = 2.0  # 平局权重x2

        for i in range(3):
            if i in class_counts:
                if i == 1:  # 平局类别
                    base_weights[i] = draw_boost * (total_samples / (3 * class_counts[i]))
                else:
                    base_weights[i] = total_samples / (3 * class_counts[i])

        logger.info("⚖️ 类别权重配置:")
        for i, weight in base_weights.items():
            outcome_name = ['Home Win', 'Draw', 'Away Win'][i]
            logger.info(f"   {outcome_name}: {weight:.2f}")

        # V4.3 优化参数配置
        params = {
            'objective': 'multi:softprob',
            'num_class': 3,
            'eval_metric': ['mlogloss', 'merror'],

            # 高维特征适应性配置
            'max_depth': 4,
            'learning_rate': 0.05,
            'n_estimators': 800,
            'colsample_bytree': 0.7,
            'subsample': 0.8,

            # 正则化（防过拟合）
            'reg_alpha': 0.2,
            'reg_lambda': 2.0,
            'min_child_weight': 3,
            'gamma': 0.1,

            # XGBoost 2.0+特性
            'max_bin': 256,
            'grow_policy': 'lossguide',
            'tree_method': 'hist',

            # 类别权重
            'scale_pos_weight': 1.0,  # 我们使用sample_weight参数
        }

        # 10-Fold 交叉验证
        skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

        cv_scores = []
        cv_models = []
        fold_results = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
            logger.info(f"🔄 训练第 {fold}/10 折...")

            X_train_fold, X_val_fold = X.iloc[train_idx], X.iloc[val_idx]
            y_train_fold, y_val_fold = y.iloc[train_idx], y.iloc[val_idx]

            # 计算样本权重
            sample_weights = np.array([base_weights[label] for label in y_train_fold])

            # 训练模型
            model = xgb.XGBClassifier(**params, random_state=42)
            model.fit(
                X_train_fold, y_train_fold,
                sample_weight=sample_weights,
                eval_set=[(X_val_fold, y_val_fold)],
                verbose=False
            )

            # 验证
            y_pred = model.predict(X_val_fold)
            accuracy = accuracy_score(y_val_fold, y_pred)
            cv_scores.append(accuracy)
            cv_models.append(model)

            # 详细指标
            report = classification_report(y_val_fold, y_pred, output_dict=True, zero_division=0)
            fold_result = {
                'fold': fold,
                'accuracy': accuracy,
                'precision': report['weighted avg']['precision'],
                'recall': report['weighted avg']['recall'],
                'f1_score': report['weighted avg']['f1-score'],
                'draw_recall': report['1']['recall'] if '1' in report else 0,  # 平局召回率
            }
            fold_results.append(fold_result)

            logger.info(f"   ✅ 第{fold}折完成: 准确率 {accuracy:.4f}, 平局召回率 {fold_result['draw_recall']:.4f}")

        # 计算平均结果
        mean_accuracy = np.mean(cv_scores)
        std_accuracy = np.std(cv_scores)
        mean_draw_recall = np.mean([fr['draw_recall'] for fr in fold_results])

        # 训练最终模型（全部数据）
        logger.info("🏆 训练最终模型...")
        final_sample_weights = np.array([base_weights[label] for label in y])
        final_model = xgb.XGBClassifier(**params, random_state=42)
        final_model.fit(X, y, sample_weight=final_sample_weights)

        # 保存模型
        joblib.dump(final_model, self.model_path)
        logger.info(f"💾 模型已保存: {self.model_path}")

        results = {
            'model_type': 'V4.3_Emergency_Stabilizer',
            'timestamp': datetime.now().isoformat(),
            'data_stats': {
                'total_samples': len(X),
                'features': list(X.columns),
                'feature_count': X.shape[1],
                'class_distribution': class_counts.to_dict(),
            },
            'training_config': {
                'class_weights': base_weights,
                'xgb_params': params,
                'cv_folds': 10,
            },
            'cv_results': {
                'mean_accuracy': mean_accuracy,
                'std_accuracy': std_accuracy,
                'cv_scores': cv_scores,
                'fold_results': fold_results,
                'mean_draw_recall': mean_draw_recall,
            },
            'model_path': str(self.model_path),
            'targets_met': {
                'accuracy_58_percent': mean_accuracy >= 0.58,
                'draw_recall_45_percent': mean_draw_recall >= 0.45,
            }
        }

        logger.info(f"🎉 V4.3训练完成!")
        logger.info(f"   📊 10-Fold CV准确率: {mean_accuracy:.4f} ± {std_accuracy:.4f}")
        logger.info(f"   🎯 平局召回率: {mean_draw_recall:.4f}")
        logger.info(f"   📈 58%目标达成: {'✅' if results['targets_met']['accuracy_58_percent'] else '❌'}")
        logger.info(f"   🎯 平局召回率45%目标: {'✅' if results['targets_met']['draw_recall_45_percent'] else '❌'}")

        return results

    def run_emergency_training(self) -> Dict:
        """运行紧急训练流程"""
        logger.info("🚨 启动V4.3紧急稳定化训练流程...")
        logger.info("=" * 80)

        try:
            # 1. 加载真实数据
            X, y = self.load_real_match_data()

            # 2. 训练平衡模型
            results = self.train_balanced_model(X, y)

            # 3. 保存报告
            with open(self.report_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"📄 训练报告已保存: {self.report_path}")

            return results

        except Exception as e:
            logger.error(f"❌ 紧急训练失败: {e}")
            raise

    def generate_summary_report(self, results: Dict):
        """生成总结报告"""
        print("\n" + "=" * 80)
        print("🏆 V4.3 紧急稳定化训练总结报告")
        print("=" * 80)

        cv_results = results['cv_results']
        data_stats = results['data_stats']

        print(f"📊 数据统计:")
        print(f"   总样本数: {data_stats['total_samples']:,}")
        print(f"   特征维度: {data_stats['feature_count']}")
        print(f"   类别分布: {data_stats['class_distribution']}")

        print(f"\n🎯 核心结果:")
        print(f"   10-Fold CV准确率: {cv_results['mean_accuracy']:.4f} ± {cv_results['std_accuracy']:.4f}")
        print(f"   平局召回率: {cv_results['mean_draw_recall']:.4f}")

        print(f"\n🎖️ 目标达成情况:")
        for target, met in results['targets_met'].items():
            status = "✅ 达成" if met else "❌ 未达成"
            print(f"   {target}: {status}")

        print(f"\n📁 输出文件:")
        print(f"   模型文件: {results['model_path']}")
        print(f"   训练报告: {self.report_path}")

        print("\n" + "=" * 80)


def main():
    """主函数"""
    trainer = V43EmergencyStabilizer()

    try:
        results = trainer.run_emergency_training()
        trainer.generate_summary_report(results)
        return 0

    except Exception as e:
        logger.error(f"❌ V4.3紧急训练失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())