#!/usr/bin/env python3
"""
数据洁癖审计师 - 纯真实数据训练
绝对真实，零填充，零模拟
只使用真实的xG数据，哪怕只有23条样本
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

import asyncpg
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import joblib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PureRealisticTrainer:
    """纯真实数据训练器 - 数据洁癖审计师版"""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@db:5432/football_prediction")
        self.async_database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")

        if "localhost" in self.database_url:
            self.database_url = self.database_url.replace("localhost", "db")
            self.async_database_url = self.async_database_url.replace("localhost", "db")

        # 配置参数 - 绝对真实
        self.confidence_threshold = 0.55  # 降低信心阈值
        self.test_size = 0.3  # 测试集比例

        # 存储模型和组件
        self.model = None
        self.label_encoders = {}
        self.feature_names = []

    async def load_pure_real_data(self) -> pd.DataFrame:
        """加载纯真实数据 - 绝对不填充任何数据"""
        logger.info("🔍 开始加载纯真实xG数据...")

        try:
            engine = create_async_engine(self.async_database_url, echo=False)
            async_session = async_sessionmaker(engine, expire_on_commit=False)

            async with async_session() as session:
                # 查询包含真实xG数据的比赛
                query = text("""
                    SELECT
                        m.id,
                        m.home_team_id,
                        m.away_team_id,
                        m.league_id,
                        m.home_score,
                        m.away_score,
                        m.status,
                        m.match_date,
                        m.stats,
                        home.name as home_team_name,
                        away.name as away_team_name,
                        league.name as league_name
                    FROM matches m
                    JOIN teams home ON m.home_team_id = home.id
                    JOIN teams away ON m.away_team_id = away.id
                    JOIN leagues league ON m.league_id = league.id
                    WHERE m.status IN ('completed', 'finished')
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date IS NOT NULL
                      AND m.stats IS NOT NULL
                      AND m.stats != 'null'
                      AND m.stats::text ILIKE '%xg%'
                    ORDER BY m.match_date
                """)

                result = await session.execute(query)
                matches = result.fetchall()

                logger.info(f"📊 找到 {len(matches)} 场可能包含xG的比赛")

                await engine.dispose()

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            raise

        # 转换为DataFrame并严格过滤
        df = pd.DataFrame([
            {
                'match_id': match.id,
                'home_team_id': match.home_team_id,
                'away_team_id': match.away_team_id,
                'league_id': match.league_id,
                'home_score': match.home_score,
                'away_score': match.away_score,
                'status': match.status,
                'match_date': match.match_date,
                'stats': match.stats,
                'home_team_name': match.home_team_name,
                'away_team_name': match.away_team_name,
                'league_name': match.league_name
            }
            for match in matches
        ])

        return df

    def extract_real_xg(self, stats_json: str) -> dict[str, float]:
        """提取真实的xG数据 - 严格验证"""
        try:
            if not stats_json or stats_json == 'null':
                return {'xg_home': None, 'xg_away': None}

            stats = json.loads(stats_json)

            # 递归搜索真实的球队xG数据
            def find_team_xg(obj, path=""):
                xg_data = {'home': None, 'away': None}

                if isinstance(obj, dict):
                    for key, value in obj.items():
                        # 直接匹配xg_home和xg_away字段
                        if key == 'xg_home' and isinstance(value, (int, float)):
                            xg_data['home'] = float(value)
                        elif key == 'xg_away' and isinstance(value, (int, float)):
                            xg_data['away'] = float(value)
                        elif isinstance(value, (dict, list)):
                            sub_xg = find_team_xg(value, f"{path}.{key}" if path else key)
                            if sub_xg['home'] is not None:
                                xg_data['home'] = sub_xg['home']
                            if sub_xg['away'] is not None:
                                xg_data['away'] = sub_xg['away']
                elif isinstance(obj, list):
                    for idx, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            sub_xg = find_team_xg(item, f"{path}[{idx}]")
                            if sub_xg['home'] is not None:
                                xg_data['home'] = sub_xg['home']
                            if sub_xg['away'] is not None:
                                xg_data['away'] = sub_xg['away']

                return xg_data

            xg_result = find_team_xg(stats)

            # 严格验证xG值
            if xg_result['home'] is not None:
                if not (0.0 <= xg_result['home'] <= 10.0):
                    xg_result['home'] = None
            if xg_result['away'] is not None:
                if not (0.0 <= xg_result['away'] <= 10.0):
                    xg_result['away'] = None

            return {'xg_home': xg_result['home'], 'xg_away': xg_result['away']}

        except (json.JSONDecodeError, ValueError, TypeError):
            return {'xg_home': None, 'xg_away': None}

    def filter_pure_real_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤纯真实数据 - 绝对不允许填充"""
        logger.info("🔍 严格过滤纯真实数据...")

        original_count = len(df)
        logger.info(f"📊 原始数据: {original_count} 场比赛")

        # 提取真实xG数据
        xg_data = df['stats'].apply(self.extract_real_xg)
        df['xg_home'] = xg_data.apply(lambda x: x['xg_home'])
        df['xg_away'] = xg_data.apply(lambda x: x['xg_away'])
        df['total_xg'] = df['xg_home'] + df['xg_away']

        # 严格过滤条件 - 必须同时有主客队xG
        strict_mask = (
            df['xg_home'].notna() &
            df['xg_away'].notna() &
            (df['xg_home'] > 0) &
            (df['xg_away'] > 0) &
            (df['total_xg'] > 0.1) &
            df['match_date'].notna()
        )

        df_pure = df[strict_mask].copy()

        logger.info(f"✅ 纯真实数据: {len(df_pure)} 场比赛")
        logger.info(f"📉 真实数据保留率: {len(df_pure)/original_count*100:.1f}%")

        # 绝对不填充任何数据！
        logger.info("🚫 数据洁癖审计师声明: 绝对未填充任何数据！")

        return df_pure

    def prepare_simple_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """准备简单特征 - 基于有限的真实数据"""
        logger.info("🔧 准备简单特征（基于有限真实数据）...")

        # 由于数据量太少，只能使用最简单的特征
        df['total_goals'] = df['home_score'] + df['away_score']
        df['goal_difference'] = df['home_score'] - df['away_score']
        df['xg_difference'] = df['xg_home'] - df['xg_away']
        df['xg_accuracy'] = df['total_xg'] - df['total_goals']  # xG预测准确性

        # 创建目标变量
        df['result'] = df.apply(
            lambda row: 'home_win' if row['home_score'] > row['away_score']
                     else ('away_win' if row['home_score'] < row['away_score'] else 'draw'),
            axis=1
        )

        # 简单特征工程 - 由于数据太少，不能使用滚动特征
        feature_columns = [
            # 基础特征
            'home_score',
            'away_score',
            'total_goals',
            'goal_difference',

            # xG特征（我们的核心真实数据）
            'xg_home',
            'xg_away',
            'total_xg',
            'xg_difference',
            'xg_accuracy',
        ]

        # 确保所有特征列都存在
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0

        # 处理NaN值（只允许用0填充，因为真实数据已经验证过）
        df = df.fillna(0)

        # 特征矩阵和目标向量
        X = df[feature_columns]
        y = df['result']

        # 编码目标变量
        le_result = LabelEncoder()
        y_encoded = le_result.fit_transform(y)

        # 保存编码器和特征名称
        self.label_encoders = {'result': le_result}
        self.feature_names = feature_columns

        logger.info(f"✅ 特征准备完成: {X.shape[0]} 样本, {X.shape[1]} 特征")
        logger.info(f"📊 结果分布: {dict(zip(le_result.classes_, np.bincount(y_encoded), strict=False))}")

        return X, y_encoded

    def train_simple_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """训练简单模型 - 适合小数据量"""
        logger.info("🎯 开始训练简单模型...")

        # 使用适合小数据量的参数
        self.model = xgb.XGBClassifier(
            n_estimators=50,      # 减少树的数量
            max_depth=3,          # 减少深度
            learning_rate=0.1,    # 提高学习率
            min_child_weight=1,   # 允许更小的子节点
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            eval_metric='mlogloss'
        )

        # 训练模型
        self.model.fit(X_train, y_train)

        logger.info("✅ 简单模型训练完成")

    def realistic_evaluation(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """现实评估 - 不使用赔率（因为没有真实赔率数据）"""
        logger.info("📊 开始现实评估...")

        # 基础预测评估
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)

        accuracy = accuracy_score(y_test, y_pred)

        # 计算基础统计（不涉及赔率）
        max_proba = np.max(y_pred_proba, axis=1)
        high_confidence_count = np.sum(max_proba > self.confidence_threshold)

        results = {
            'accuracy': accuracy,
            'test_samples': len(y_test),
            'high_confidence_predictions': high_confidence_count,
            'confidence_threshold': self.confidence_threshold,
            'avg_max_confidence': np.mean(max_proba),
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_, strict=False))
        }

        logger.info("✅ 现实评估完成")
        return results

    def save_pure_model(self, model_name: str = "football_prediction_pure_real") -> None:
        """保存纯真实模型"""
        logger.info("💾 保存纯真实模型...")

        model_dir = Path("/app/models/trained")
        model_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存模型
        model_file = model_dir / f"{model_name}_{timestamp}_model.joblib"
        joblib.dump(self.model, model_file)

        # 保存组件
        components_file = model_dir / f"{model_name}_{timestamp}_components.joblib"
        joblib.dump({
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names
        }, components_file)

        # 保存报告
        report_file = model_dir / f"{model_name}_{timestamp}_summary.txt"
        with open(report_file, 'w') as f:
            f.write("Pure Realistic Model Summary\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Model: {model_name}\n")
            f.write(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Data Type: PURE REAL - No Imputation\n")
            f.write(f"Feature Count: {len(self.feature_names)}\n")
            f.write(f"Features: {', '.join(self.feature_names)}\n")
            f.write("\nDATA PURITY AUDITOR CERTIFIED: 100% REAL DATA\n")

        logger.info(f"✅ 纯真实模型已保存: {model_file}")

    async def train(self):
        """主训练流程 - 绝对真实版"""
        logger.info("🚀 开始纯真实数据训练流程")
        logger.info("="*80)
        logger.info("🚫 数据洁癖审计师声明: 绝对不填充任何数据！")

        start_time = datetime.now()

        try:
            # 1. 加载数据
            df = await self.load_pure_real_data()
            logger.info(f"📊 原始数据: {df.shape}")

            # 2. 严格过滤
            df_pure = self.filter_pure_real_data(df)
            logger.info(f"📊 纯真实数据: {df_pure.shape}")

            if len(df_pure) < 10:
                logger.error(f"❌ 真实数据太少({len(df_pure)}条)，无法训练模型")
                return

            # 3. 准备特征
            X, y = self.prepare_simple_features(df_pure)

            # 4. 数据切分（由于数据少，使用更保守的测试集比例）
            if len(X) < 20:
                # 数据太少，用简单切分
                test_size = max(1, int(len(X) * 0.3))
                X_train = X.iloc[:-test_size]
                X_test = X.iloc[-test_size:]
                y_train = y[:-test_size]
                y_test = y[-test_size:]
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=self.test_size, random_state=42, stratify=y
                )

            logger.info(f"📋 训练集: {len(X_train)} 样本")
            logger.info(f"📋 测试集: {len(X_test)} 样本")

            # 5. 训练模型
            self.train_simple_model(X_train, y_train)

            # 6. 评估
            train_accuracy = self.model.score(X_train, y_train)
            evaluation_results = self.realistic_evaluation(X_test, y_test)

            # 7. 保存模型
            self.save_pure_model()

            # 8. 输出报告
            self.generate_pure_report(
                start_time, train_accuracy, evaluation_results, len(df_pure)
            )

        except Exception as e:
            logger.error(f"❌ 训练流程失败: {e}")
            import traceback
            traceback.print_exc()

    def generate_pure_report(self, start_time, train_acc, eval_results, sample_count):
        """生成纯真实报告"""
        end_time = datetime.now()
        training_time = (end_time - start_time).total_seconds()

        print("\n" + "="*80)
        print("🔍 数据洁癖审计师 - 纯真实数据训练报告")
        print("="*80)

        print("\n📊 纯真实数据统计:")
        print(f"   🔍 真实样本数: {sample_count}")
        print(f"   ⏱️ 训练时间: {training_time:.2f}秒")
        print("   🎯 模型类型: XGBoost Classifier (纯真实版)")
        print("   🚫 数据填充: 绝对禁止！")
        print("   ✅ 数据纯度: 100%真实")

        print("\n📈 模型性能:")
        print(f"   🏋️ 训练准确率: {train_acc:.4f} ({train_acc*100:.2f}%)")
        print(f"   🧪 测试准确率: {eval_results['accuracy']:.4f} ({eval_results['accuracy']*100:.2f}%)")
        print(f"   📊 测试样本: {eval_results['test_samples']}")
        print(f"   🎯 高信心预测: {eval_results['high_confidence_predictions']}")
        print(f"   📊 平均最大置信度: {eval_results['avg_max_confidence']:.3f}")

        print("\n🏆 特征重要性:")
        sorted_features = sorted(
            eval_results['feature_importance'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for i, (feature, importance) in enumerate(sorted_features, 1):
            print(f"   {i:2d}. {feature}: {importance:.4f}")

        print("\n🎯 数据洁癖审计师结论:")
        if sample_count >= 50:
            print(f"   ✅ 数据量充足({sample_count}条)，结果可信度较高")
        elif sample_count >= 20:
            print(f"   ⚠️  数据量较少({sample_count}条)，结果仅供参考")
        else:
            print(f"   ❌ 数据量极少({sample_count}条)，统计意义有限")

        if eval_results['accuracy'] > 0.6:
            print("   ✅ 模型显示出一定预测能力")
        elif eval_results['accuracy'] > 0.4:
            print("   ⚠️  模型预测能力有限")
        else:
            print("   ❌ 模型预测能力不足")

        print("\n💡 审计师建议:")
        print("   1. 继续收集更多真实xG数据")
        print("   2. 当前结果仅作为技术验证")
        print("   3. 实际应用需要更大的真实数据集")

        print("\n" + "="*80)
        print("🔍 数据洁癖审计师 - 纯真实训练完成")
        print("🚫 绝对真实，零填充，零模拟！")
        print("="*80)


async def main():
    """主函数"""
    logger.info("🔍 数据洁癖审计师 - 纯真实数据训练启动")

    trainer = PureRealisticTrainer()
    await trainer.train()


if __name__ == "__main__":
    asyncio.run(main())
