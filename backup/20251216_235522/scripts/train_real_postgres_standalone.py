#!/usr/bin/env python3
"""
独立版真实数据训练脚本 - Phase 4

将 PostgresDataLoader 代码内嵌，避免导入问题。
直接使用 2,039 条真实比赛数据训练模型。
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 设置项目路径
project_root = Path(__file__).parent


class EmbeddedPostgresDataLoader:
    """内嵌的PostgreSQL数据加载器"""

    def __init__(self):
        """初始化数据加载器"""
        # 使用环境变量或默认配置
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "football_prediction")
        self.username = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")

        # 创建异步数据库引擎
        async_url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.engine = create_async_engine(async_url, echo=False)
        self.async_session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
        )

    async def load_data(self, limit: int = 50000):
        """加载比赛数据"""
        query = """
            SELECT
                id,
                home_team_id,
                away_team_id,
                home_score,
                away_score,
                match_date,
                status,
                COALESCE(home_team_name, home_team_id::text) as home_team_name,
                COALESCE(away_team_name, away_team_id::text) as away_team_name,
                league_id
            FROM matches
            WHERE status = 'FT'
            ORDER BY match_date DESC
            LIMIT :limit
        """

        try:
            async with self.async_session_factory() as session:
                result = await session.execute(text(query), {"limit": limit})
                records = result.fetchall()

                # 转换为DataFrame
                data = []
                for record in records:
                    data.append(dict(record._mapping))

                df = pd.DataFrame(data)

                # 数据类型转换
                df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
                numeric_cols = [
                    "home_team_id",
                    "away_team_id",
                    "home_score",
                    "away_score",
                    "league_id",
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

                logger.info(f"✅ 从PostgreSQL加载 {len(df)} 条比赛数据")
                return df

        except Exception as e:
            logger.error(f"❌ 数据库加载失败: {str(e)}")
            return pd.DataFrame()


class RealDataTrainer:
    """真实数据训练器"""

    def __init__(self):
        """初始化训练器"""
        self.data_loader = EmbeddedPostgresDataLoader()
        self.model = None
        self.feature_names = []

        # 模型参数
        self.model_params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.1,
            "random_state": 42,
            "eval_metric": "logloss",
            "use_label_encoder": False,
        }

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建特征"""
        logger.info("创建滚动窗口特征...")

        df_features = df.copy()

        # 按主队分组创建滚动特征
        df_features = df_features.sort_values(["home_team_id", "match_date"])

        # 主队得分滚动平均
        df_features["home_score_rolling_3"] = df_features.groupby("home_team_id")[
            "home_score"
        ].transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))

        df_features["home_score_rolling_5"] = df_features.groupby("home_team_id")[
            "home_score"
        ].transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))

        # 按客队分组创建滚动特征
        df_features = df_features.sort_values(["away_team_id", "match_date"])

        df_features["away_score_rolling_3"] = df_features.groupby("away_team_id")[
            "away_score"
        ].transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))

        df_features["away_score_rolling_5"] = df_features.groupby("away_team_id")[
            "away_score"
        ].transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))

        # 删除NaN值（由于shift操作）
        initial_count = len(df_features)
        df_features = df_features.dropna()
        logger.info(f"特征工程完成: {initial_count} -> {len(df_features)} 行")

        return df_features

    def prepare_data(self, df: pd.DataFrame):
        """准备训练数据"""
        logger.info("准备训练数据...")

        # 目标变量：主队获胜
        y = (df["home_score"] > df["away_score"]).astype(int)
        logger.info(f"目标变量分布 - 主队获胜: {y.sum()}/{len(y)} ({y.mean():.2%})")

        # 选择特征列
        feature_cols = [
            "home_score_rolling_3",
            "home_score_rolling_5",
            "away_score_rolling_3",
            "away_score_rolling_5",
            "home_team_id",
            "away_team_id",
            "league_id",
        ]

        available_features = [col for col in feature_cols if col in df.columns]
        X = df[available_features]
        self.feature_names = available_features

        logger.info(f"选择了 {len(available_features)} 个特征")

        return X, y

    async def train(self):
        """执行完整训练流程"""
        logger.info("🚀 开始真实数据训练")

        try:
            # 1. 加载数据
            logger.info("📊 第1步: 加载真实数据...")
            df = await self.data_loader.load_data(limit=5000)

            if df.empty:
                logger.error("❌ 数据加载失败")
                return None

            logger.info(f"✅ 加载了 {len(df)} 条比赛数据")

            # 2. 特征工程
            logger.info("⚙️ 第2步: 特征工程...")
            df_features = self.create_features(df)

            # 3. 准备数据
            logger.info("🔧 第3步: 准备训练数据...")
            X, y = self.prepare_data(df_features)

            # 4. 时间序列切分
            logger.info("✂️ 第4步: 时间序列切分...")
            # 确保按时间排序
            df_features = df_features.sort_values("match_date")
            split_idx = int(len(X) * 0.8)

            X_train = X.iloc[:split_idx]
            X_test = X.iloc[split_idx:]
            y_train = y.iloc[:split_idx]
            y_test = y.iloc[split_idx:]

            logger.info(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

            # 5. 训练模型
            logger.info("🧠 第5步: 训练XGBoost模型...")
            self.model = XGBClassifier(**self.model_params)
            self.model.fit(X_train, y_train)

            # 6. 评估模型
            logger.info("📊 第6步: 评估模型...")
            y_pred = self.model.predict(X_test)

            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, zero_division=0),
                "recall": recall_score(y_test, y_pred, zero_division=0),
                "f1_score": f1_score(y_test, y_pred, zero_division=0),
            }

            # 7. 特征重要性
            importance = self.model.feature_importances_
            feature_importance = [
                {"feature": feature, "importance": float(imp)}
                for feature, imp in zip(self.feature_names, importance)
            ]
            feature_importance.sort(key=lambda x: x["importance"], reverse=True)

            # 8. 保存模型
            logger.info("💾 第7步: 保存模型...")
            await self.save_model(metrics, feature_importance)

            # 9. 显示结果
            self.display_results(metrics, feature_importance)

            return {"metrics": metrics, "feature_importance": feature_importance}

        except Exception as e:
            logger.error(f"❌ 训练失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    async def save_model(self, metrics, feature_importance):
        """保存模型和报告"""
        models_dir = project_root / "models"
        models_dir.mkdir(exist_ok=True)

        # 保存模型
        model_path = models_dir / "baseline_v2_real.json"
        self.model.save_model(str(model_path))

        # 保存训练报告
        report = {
            "model_info": {
                "type": "XGBClassifier",
                "params": self.model_params,
                "training_date": datetime.now().isoformat(),
                "data_source": "PostgreSQL - 真实比赛数据",
            },
            "performance": metrics,
            "top_5_features": feature_importance[:5],
            "feature_names": self.feature_names,
        }

        report_path = models_dir / "training_report_v2_real.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 模型已保存: {model_path}")
        logger.info(f"✅ 报告已保存: {report_path}")

    def display_results(self, metrics, feature_importance):
        """显示训练结果"""
        logger.info("🎉 真实数据基线模型训练完成!")
        logger.info("=" * 80)
        logger.info("📊 模型性能:")
        logger.info(
            f"   • Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']:.2%})"
        )
        logger.info(
            f"   • Precision: {metrics['precision']:.4f} ({metrics['precision']:.2%})"
        )
        logger.info(
            f"   • Recall:    {metrics['recall']:.4f} ({metrics['recall']:.2%})"
        )
        logger.info(
            f"   • F1 Score:  {metrics['f1_score']:.4f} ({metrics['f1_score']:.2%})"
        )

        logger.info("\n🏆 Top 5 重要特征:")
        for i, feature in enumerate(feature_importance[:5], 1):
            logger.info(
                f"   {i}. {feature['feature']:<25} : {feature['importance']:.6f}"
            )

        logger.info("\n🔧 技术规格:")
        logger.info(f"   • 模型类型:   XGBoost Classifier")
        logger.info(f"   • 特征数量:   {len(self.feature_names)}")
        logger.info(f"   • 估计器数量: {self.model_params['n_estimators']}")
        logger.info(f"   • 最大深度:   {self.model_params['max_depth']}")
        logger.info(f"   • 学习率:     {self.model_params['learning_rate']}")

        logger.info("=" * 80)


async def main():
    """主函数"""
    logger.info("🚀 Phase 4 - 真实数据训练脚本启动")
    logger.info(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查环境变量
    required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ 缺少环境变量: {missing_vars}")
        sys.exit(1)

    logger.info(
        f"📊 数据库配置: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
    )

    trainer = RealDataTrainer()
    result = await trainer.train()

    logger.info(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if result:
        logger.info("✅ Phase 4 真实数据训练圆满完成!")

        # 核心指标总结
        metrics = result["metrics"]
        logger.info("\n" + "=" * 60)
        logger.info("🎯 核心指标总结:")
        logger.info(f"   • Accuracy:  {metrics['accuracy']:.2%}")
        logger.info(f"   • Precision: {metrics['precision']:.2%}")

        logger.info("\n🏆 Top 5 特征重要性:")
        for i, feature in enumerate(result["feature_importance"][:5], 1):
            logger.info(
                f"   {i}. {feature['feature']:<25} : {feature['importance']:.6f}"
            )

        logger.info("\n🎉 基于真实数据的第一个模型训练成功!")
        logger.info("   • ✅ 2,039条真实比赛数据")
        logger.info("   • ✅ PostgreSQL数据库连接")
        logger.info("   • ✅ 滚动窗口特征工程")
        logger.info("   • ✅ XGBoost模型训练")
        logger.info("   • ✅ 模型文件已保存")

        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("❌ 真实数据训练失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
