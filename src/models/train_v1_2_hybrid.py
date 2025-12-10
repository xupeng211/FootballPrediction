#!/usr/bin/env python3
"""
XGBoost V1.2 混合模型训练 - 首席AI科学家特别版
利用现有26,000+记录训练具备实战盈利能力的预测模型
重点评估ROI (投资回报率)
"""

import asyncio
import logging
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text, func
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
)
import joblib

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HybridModelTrainer:
    """V1.2混合模型训练器 - 首席AI科学家版"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL"
            "postgresql://postgres:postgres-dev-password@db:5432/football_prediction"
        )
        self.async_database_url = self.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        # 在Docker环境中使用正确的数据库URL
        if "localhost" in self.database_url:
            self.database_url = self.database_url.replace("localhost", "db")
            self.async_database_url = self.async_database_url.replace("localhost", "db")

        # 配置参数
        self.rolling_window = 5  # 过去5场
        self.confidence_threshold = 0.55  # 投注信心阈值
        self.test_size = 0.2  # 测试集比例

        # 假设赔率 (如果没有真实赔率数据)
        self.default_odds = {"home_win": 2.0, "draw": 3.2, "away_win": 2.5}

        # 存储模型和组件
        self.model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = []

    async def load_training_data(self) -> pd.DataFrame:
        """从数据库加载训练数据"""
        logger.info("📊 开始加载训练数据...")

        try:
            # 创建异步引擎
            engine = create_async_engine(self.async_database_url, echo=False)
            async_session = async_sessionmaker(engine, expire_on_commit=False)

            async with async_session() as session:
                # 查询已完成的比赛数据
                query = text(
                    """
                    SELECT
                        m.id
                        m.home_team_id
                        m.away_team_id
                        m.league_id
                        m.home_score
                        m.away_score
                        m.status
                        m.match_date
                        m.stats
                        home.name as home_team_name
                        away.name as away_team_name
                        league.name as league_name
                    FROM matches m
                    JOIN teams home ON m.home_team_id = home.id
                    JOIN teams away ON m.away_team_id = away.id
                    JOIN leagues league ON m.league_id = league.id
                    WHERE m.status IN ('completed', 'finished')
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date IS NOT NULL
                    ORDER BY m.match_date
                """
                )

                result = await session.execute(query)
                matches = result.fetchall()

                logger.info(f"✅ 加载了 {len(matches)} 场比赛数据")

                # 转换为DataFrame
                df = pd.DataFrame(
                    [
                        {
                            "match_id": match.id,
                            "home_team_id": match.home_team_id,
                            "away_team_id": match.away_team_id,
                            "league_id": match.league_id,
                            "home_score": match.home_score,
                            "away_score": match.away_score,
                            "status": match.status,
                            "match_date": match.match_date,
                            "stats": match.stats,
                            "home_team_name": match.home_team_name,
                            "away_team_name": match.away_team_name,
                            "league_name": match.league_name,
                        }
                        for match in matches
                    ]
                )

                await engine.dispose()

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            raise

        return df

    def parse_xg_data(self, stats_json: str) -> dict[str, float]:
        """解析xG数据"""
        try:
            if not stats_json or stats_json == "null":
                return {"xg_home": None, "xg_away": None}

            stats = json.loads(stats_json)

            # 尝试多种xG字段名
            xg_home = (
                stats.get("xg_home")
                or stats.get("xG_home")
                or stats.get("expected_goals_home")
                or stats.get("xg_for_home")
                or None
            )

            xg_away = (
                stats.get("xg_away")
                or stats.get("xG_away")
                or stats.get("expected_goals_away")
                or stats.get("xg_for_away")
                or None
            )

            # 尝试转换为float
            xg_home = float(xg_home) if xg_home is not None else None
            xg_away = float(xg_away) if xg_away is not None else None

            return {"xg_home": xg_home, "xg_away": xg_away}

        except (json.JSONDecodeError, ValueError, typeError) as e:
            logger.debug(f"解析xG数据失败: {e}")
            return {"xg_home": None, "xg_away": None}

    def calculate_match_result(self, home_score: int, away_score: int) -> str:
        """计算比赛结果"""
        if home_score > away_score:
            return "home_win"
        elif home_score < away_score:
            return "away_win"
        else:
            return "draw"

    def calculate_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算滚动特征"""
        logger.info("📈 计算滚动特征...")

        # 首先计算基础特征
        df["total_goals"] = df["home_score"] + df["away_score"]
        df["goal_difference"] = df["home_score"] - df["away_score"]

        # 解析xG数据
        xg_data = df["stats"].apply(self.parse_xg_data)
        df["xg_home"] = xg_data.apply(lambda x: x["xg_home"])
        df["xg_away"] = xg_data.apply(lambda x: x["xg_away"])
        df["total_xg"] = df["xg_home"] + df["xg_away"]

        # 按球队分组计算滚动特征
        for team_col in ["home_team_id", "away_team_id"]:
            goal_col = "home_score" if team_col == "home_team_id" else "away_score"
            opponent_goal_col = (
                "away_score" if team_col == "home_team_id" else "home_score"
            )
            xg_col = "xg_home" if team_col == "home_team_id" else "xg_away"
            opponent_xg_col = "xg_away" if team_col == "home_team_id" else "xg_home"

            # 为每个球队计算滚动特征
            team_df = df[
                [
                    "match_date",
                    team_col,
                    goal_col,
                    opponent_goal_col,
                    xg_col,
                    opponent_xg_col,
                ]
            ].copy()

            # 按球队分组并按时间排序
            team_df = team_df.sort_values([team_col, "match_date"])

            # 计算滚动平均
            team_df[f'avg_goals_scored_{team_col.split("_")[0]}'] = (
                team_df.groupby(team_col)[goal_col]
                .rolling(window=self.rolling_window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )

            team_df[f'avg_goals_conceded_{team_col.split("_")[0]}'] = (
                team_df.groupby(team_col)[opponent_goal_col]
                .rolling(window=self.rolling_window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )

            # xG滚动特征
            team_df[f'avg_xg_created_{team_col.split("_")[0]}'] = (
                team_df.groupby(team_col)[xg_col]
                .rolling(window=self.rolling_window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )

            team_df[f'avg_xg_conceded_{team_col.split("_")[0]}'] = (
                team_df.groupby(team_col)[opponent_xg_col]
                .rolling(window=self.rolling_window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )

            # 合并回原DataFrame
            rolling_cols = [
                f'avg_goals_scored_{team_col.split("_")[0]}'
                f'avg_goals_conceded_{team_col.split("_")[0]}'
                f'avg_xg_created_{team_col.split("_")[0]}'
                f'avg_xg_conceded_{team_col.split("_")[0]}'
            ]

            df = df.merge(
                team_df[["match_date", team_col] + rolling_cols],
                left_on=["match_date", team_col],
                right_on=["match_date", team_col],
                how="left",
            )

        # 计算主队 vs 客队的相对特征
        df["goal_diff_advantage"] = df.get("avg_goals_scored_home", 0) - df.get(
            "avg_goals_conceded_away", 0
        )

        df["xg_advantage"] = df.get("avg_xg_created_home", 0) - df.get(
            "avg_xg_conceded_away", 0
        )

        logger.info("✅ 滚动特征计算完成")
        return df

    def prepare_features_and_labels(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.Series]:
        """准备特征和标签"""
        logger.info("🔧 准备特征和标签...")

        # 创建目标变量
        df["result"] = df.apply(
            lambda row: self.calculate_match_result(
                row["home_score"], row["away_score"]
            ),
            axis=1,
        )

        # 编码类别特征
        df["league_name"].unique()
        pd.concat([df["home_team_name"], df["away_team_name"]]).unique()

        # 创建标签编码器
        le_league = LabelEncoder()
        le_home_team = LabelEncoder()
        le_away_team = LabelEncoder()

        # 训练标签编码器
        df["league_encoded"] = le_league.fit_transform(df["league_name"])
        df["home_team_encoded"] = le_home_team.fit_transform(df["home_team_name"])
        df["away_team_encoded"] = le_away_team.fit_transform(df["away_team_name"])

        # 选择特征列
        feature_columns = [
            # 基础特征
            "league_encoded"
            "home_team_encoded"
            "away_team_encoded"
            # 滚动进球特征
            "avg_goals_scored_home"
            "avg_goals_conceded_home"
            "avg_goals_scored_away"
            "avg_goals_conceded_away"
            # 滚动xG特征（可能有NaN）
            "avg_xg_created_home"
            "avg_xg_conceded_home"
            "avg_xg_created_away"
            "avg_xg_conceded_away"
            # 相对特征
            "goal_diff_advantage"
            "xg_advantage"
        ]

        # 确保所有特征列都存在
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0  # 缺失特征用0填充

        # 处理NaN值
        df = df.fillna(0)

        # 特征矩阵和目标向量
        X = df[feature_columns]
        y = df["result"]

        # 编码目标变量
        le_result = LabelEncoder()
        y_encoded = le_result.fit_transform(y)

        # 保存编码器和特征名称
        self.label_encoders = {
            "league": le_league,
            "home_team": le_home_team,
            "away_team": le_away_team,
            "result": le_result,
        }
        self.feature_names = feature_columns

        logger.info(f"✅ 特征准备完成: {X.shape[0]} 样本, {X.shape[1]} 特征")
        logger.info(
            f"📊 结果分布: {dict(zip(le_result.classes_, np.bincount(y_encoded), strict=False))}"
        )

        return X, y_encoded

    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """训练XGBoost模型"""
        logger.info("🎯 开始训练XGBoost模型...")

        # 训练XGBoost分类器
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            eval_metric="mlogloss",
        )

        # 训练模型
        self.model.fit(X_train, y_train)

        logger.info("✅ 模型训练完成")

    def backtest_strategy(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """策略回测"""
        logger.info("💰 开始策略回测...")

        # 获取预测概率
        y_pred_proba = self.model.predict_proba(X_test)
        y_pred = self.model.predict(X_test)

        # 计算基础指标
        accuracy = accuracy_score(y_test, y_pred)

        # 模拟投注策略
        total_bets = 0
        wins = 0
        total_stake = 0
        total_winnings = 0

        # 获取最大概率对应的类别
        max_proba = np.max(y_pred_proba, axis=1)
        pred_class = np.argmax(y_pred_proba, axis=1)

        for i in range(len(y_test)):
            confidence = max_proba[i]
            prediction = pred_class[i]
            actual = y_test[i]

            # 只对高置信度的预测下注
            if confidence > self.confidence_threshold:
                total_bets += 1

                # 假设每场下注1单位
                stake = 1
                total_stake += stake

                # 简化的赔率计算（基于历史平均）
                if (
                    prediction
                    == self.label_encoders["result"].transform(["home_win"])[0]
                ):
                    odds = self.default_odds["home_win"]
                elif prediction == self.label_encoders["result"].transform(["draw"])[0]:
                    odds = self.default_odds["draw"]
                else:
                    odds = self.default_odds["away_win"]

                # 计算收益
                if prediction == actual:  # 预测正确
                    winnings = stake * odds
                    total_winnings += winnings
                    wins += 1

        # 计算ROI
        roi = (
            ((total_winnings - total_stake) / total_stake * 100)
            if total_stake > 0
            else 0
        )
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0

        results = {
            "accuracy": accuracy,
            "total_bets": total_bets,
            "wins": wins,
            "win_rate": win_rate,
            "total_stake": total_stake,
            "total_winnings": total_winnings,
            "profit_loss": total_winnings - total_stake,
            "roi": roi,
            "confidence_threshold": self.confidence_threshold,
        }

        logger.info("✅ 策略回测完成")
        return results

    def generate_feature_importance(self) -> dict:
        """生成特征重要性报告"""
        if not self.model:
            return {}

        feature_importance = dict(
            zip(self.feature_names, self.model.feature_importances_, strict=False)
        )

        # 按重要性排序
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )

        return {
            "feature_importance": dict(sorted_features),
            "top_5_features": sorted_features[:5],
            "xg_features_importance": {
                "avg_xg_created_home": feature_importance.get("avg_xg_created_home", 0),
                "avg_xg_conceded_home": feature_importance.get(
                    "avg_xg_conceded_home", 0
                ),
                "avg_xg_created_away": feature_importance.get("avg_xg_created_away", 0),
                "avg_xg_conceded_away": feature_importance.get(
                    "avg_xg_conceded_away", 0
                ),
                "xg_advantage": feature_importance.get("xg_advantage", 0),
            },
        }

    def save_model(self, model_name: str = "football_prediction_v1_2_hybrid") -> None:
        """保存模型和组件"""
        logger.info("💾 保存模型和组件...")

        # 创建模型目录
        model_dir = Path("/app/models/trained")
        model_dir.mkdir(parents=True, exist_ok=True)

        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存模型
        model_file = model_dir / f"{model_name}_{timestamp}_model.joblib"
        joblib.dump(self.model, model_file)

        # 保存标签编码器
        encoders_file = model_dir / f"{model_name}_{timestamp}_encoders.joblib"
        joblib.dump(self.label_encoders, encoders_file)

        # 保存特征名称
        features_file = model_dir / f"{model_name}_{timestamp}_features.joblib"
        joblib.dump(self.feature_names, features_file)

        # 保存缩放器
        scaler_file = model_dir / f"{model_name}_{timestamp}_scaler.joblib"
        joblib.dump(self.scaler, scaler_file)

        # 保存训练报告
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = {
            "model_name": model_name,
            "version": "1.2",
            "training_date": timestamp_str,
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "rolling_window": self.rolling_window,
            "confidence_threshold": self.confidence_threshold,
            "xg_data_ratio": "N/A",  # 将在训练完成后更新
        }

        report_file = model_dir / f"{model_name}_{timestamp}_summary.txt"
        with open(report_file, "w") as f:
            f.write("Football Prediction Model V1.2 Hybrid Summary\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Model Name: {report['model_name']}\n")
            f.write(f"Version: {report['version']}\n")
            f.write(f"Training Date: {report['training_date']}\n")
            f.write(f"Feature Count: {report['feature_count']}\n")
            f.write(f"Rolling Window: {report['rolling_window']}\n")
            f.write(f"Confidence Threshold: {report['confidence_threshold']}\n\n")
            f.write("Features:\n")
            for i, feature in enumerate(report["feature_names"], 1):
                f.write(f"  {i:2d}. {feature}\n")

        logger.info(f"✅ 模型已保存: {model_file}")
        logger.info(f"✅ 报告已保存: {report_file}")

    async def train(self):
        """主训练流程"""
        logger.info("🚀 开始V1.2混合模型训练流程")
        logger.info("=" * 60)

        start_time = datetime.now()

        try:
            # 1. 加载数据
            df = await self.load_training_data()
            logger.info(f"📊 原始数据: {df.shape}")

            # 2. 计算滚动特征
            df = self.calculate_rolling_features(df)
            logger.info(f"📈 特征工程后: {df.shape}")

            # 3. 准备特征和标签
            X, y = self.prepare_features_and_labels(df)

            # 4. 时间序列切分
            df_sorted = df.sort_values("match_date").reset_index(drop=True)
            split_index = int(len(df_sorted) * (1 - self.test_size))

            X_train = X.iloc[:split_index]
            X_test = X.iloc[split_index:]
            y_train = y[:split_index]
            y_test = y[split_index:]

            logger.info(f"📋 训练集: {X_train.shape[0]} 样本")
            logger.info(f"📋 测试集: {X_test.shape[0]} 样本")

            # 5. 训练模型
            self.train_model(X_train, y_train)

            # 6. 模型评估
            train_accuracy = self.model.score(X_train, y_train)
            test_accuracy = self.model.score(X_test, y_test)

            # 7. 策略回测
            backtest_results = self.backtest_strategy(X_test, y_test)

            # 8. 特征重要性
            feature_importance = self.generate_feature_importance()

            # 9. 保存模型
            self.save_model()

            # 10. 输出报告
            self.generate_training_report(
                start_time,
                train_accuracy,
                test_accuracy,
                backtest_results,
                feature_importance,
            )

        except Exception as e:
            logger.error(f"❌ 训练流程失败: {e}")
            import traceback

            traceback.print_exc()

    def generate_training_report(
        self, start_time, train_acc, test_acc, backtest_results, feature_importance
    ):
        """生成训练报告"""
        end_time = datetime.now()
        training_time = (end_time - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("🧠 首席AI科学家 - XGBoost V1.2混合模型训练报告")
        print("=" * 80)

        print("\n📊 训练基本信息:")
        print(f"   ⏱️ 训练时间: {training_time:.2f}秒")
        print("   🎯 模型类型: XGBoost Classifier")
        print(f"   🔄 滚动窗口: {self.rolling_window}场")
        print(f"   📊 信心阈值: {self.confidence_threshold}")

        print("\n📈 模型性能:")
        print(f"   🏋️ 训练集准确率: {train_acc:.4f} ({train_acc*100:.2f}%)")
        print(f"   🧪 测试集准确率: {test_acc:.4f} ({test_acc*100:.2f}%)")
        print(f"   📉 过拟合程度: {(train_acc - test_acc)*100:.2f}%")

        print("\n💰 模拟投注结果:")
        print(f"   🎯 总投注次数: {backtest_results['total_bets']}")
        print(f"   ✅ 获胜次数: {backtest_results['wins']}")
        print(f"   📊 命中率: {backtest_results['win_rate']:.2f}%")
        print(f"   💵 总投注金额: {backtest_results['total_stake']:.2f}")
        print(f"   💰 总收回金额: {backtest_results['total_winnings']:.2f}")
        print(f"   📈 净盈亏: {backtest_results['profit_loss']:+.2f}")
        print(f"   🎖️ 投资回报率(ROI): {backtest_results['roi']:+.2f}%")

        print("\n🏆 特征重要性 Top 5:")
        for i, (feature, importance) in enumerate(
            feature_importance["top_5_features"], 1
        ):
            print(f"   {i}. {feature}: {importance:.4f}")

        print("\n📊 XG特征重要性:")
        xg_importance = feature_importance["xg_features_importance"]
        total_xg_importance = sum(xg_importance.values())
        print(f"   📈 总xG特征重要性: {total_xg_importance:.4f}")
        for feature, imp in xg_importance.items():
            if imp > 0:
                print(f"   📊 {feature}: {imp:.4f}")

        # 结论
        print("\n🎯 模型结论:")
        if backtest_results["roi"] > 0:
            print(f"   ✅ 正盈利! ROI: {backtest_results['roi']:+.2f}%")
            print("   💡 模型具备实战价值，可以考虑实盘应用")
        elif backtest_results["roi"] > -5:
            print(f"   ⚠️ 微亏损: ROI: {backtest_results['roi']:+.2f}%")
            print("   💡 模型接近盈利边界，可以尝试优化阈值或特征")
        else:
            print(f"   ❌ 显著亏损: ROI: {backtest_results['roi']:+.2f}%")
            print("   💡 需要进一步优化模型或调整策略")

        print("\n🚀 后续改进建议:")
        if total_xg_importance < 0.1:
            print(f"   📊 XG特征重要性较低({total_xg_importance:.3f})，建议:")
            print("      • 增加更多xG数据样本")
            print("   • 优化xG特征工程方法")

        if backtest_results["total_bets"] < len(test_acc) * 0.1:
            print("   🎯 投注次数较少，建议:")
            print("      • 降低信心阈值到0.50-0.52")
            print("      • 扩大样本规模")

        print("\n" + "=" * 80)
        print("🧠 首席AI科学家训练完成 - V1.2混合模型已就绪")
        print("=" * 80)


async def main():
    """主函数"""
    logger.info("🧠 首席AI科学家 - XGBoost V1.2混合模型训练启动")

    trainer = HybridModelTrainer()
    await trainer.train()


if __name__ == "__main__":
    asyncio.run(main())
