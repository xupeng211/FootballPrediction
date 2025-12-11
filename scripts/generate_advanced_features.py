#!/usr/bin/env python3
"""
高级特征生成器 - V3版本架构
Chief Data Scientist: 利用EWMA特征生成全量训练数据集

核心功能:
- 加载所有28,000+比赛数据
- 计算所有球队EWMA指标
- 生成主客场对比特征
- 创建机器学习就绪特征数据集
"""

import sys
import os
import asyncio
import pandas as pd
from datetime import datetime
import logging
from typing import Any

# 添加src到路径
sys.path.append("/app/src")

from features.ewma_calculator import EWMACalculator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class AdvancedFeatureGenerator:
    """高级特征生成器 - 集成EWMA和传统特征工程"""

    def __init__(self):
        # 数据库连接
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
        )
        self.engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"), echo=False
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # EWMA计算器配置
        self.ewma_calculator = EWMACalculator(
            spans=[5, 10, 20],  # 短期、中期、长期
            min_matches=3,  # 最低比赛数
            adjust=True,  # 调整初始值
        )

        # 特征配置
        self.feature_config = {
            "include_ewma": True,
            "include_basic": True,
            "include_historical": True,
            "include_temporal": True,
        }

        logger.info("🧠 高级特征生成器初始化完成")
        logger.info(
            f"   EWMA配置: spans={self.ewma_calculator.spans}, min_matches={self.ewma_calculator.min_matches}"
        )
        logger.info(f"   特征配置: {self.feature_config}")

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()

    async def load_all_matches(self) -> pd.DataFrame:
        """加载所有比赛数据"""
        logger.info("📊 加载所有比赛数据...")

        async with self.AsyncSessionLocal() as session:
            query = text(
                """
                SELECT
                    id,
                    home_team_id,
                    home_team_name,
                    away_team_id,
                    away_team_name,
                    home_score,
                    away_score,
                    match_date,
                    league_id,
                    league_name,
                    season,
                    status
                FROM matches
                WHERE home_score IS NOT NULL
                AND away_score IS NOT NULL
                AND match_date IS NOT NULL
                AND home_team_id IS NOT NULL
                AND away_team_id IS NOT NULL
                ORDER BY match_date ASC
            """
            )

            result = await session.execute(query)
            rows = result.fetchall()

            data = []
            for row in rows:
                data.append(
                    {
                        "match_id": row.id,
                        "home_team_id": row.home_team_id,
                        "home_team_name": row.home_team_name,
                        "away_team_id": row.away_team_id,
                        "away_team_name": row.away_team_name,
                        "home_score": row.home_score,
                        "away_score": row.away_score,
                        "match_date": row.match_date,
                        "league_id": row.league_id,
                        "league_name": row.league_name,
                        "season": row.season,
                        "status": row.status,
                    }
                )

            df = pd.DataFrame(data)
            logger.info(f"✅ 比赛数据加载完成: {len(df)} 场比赛")
            logger.info(
                f"   时间范围: {df['match_date'].min()} 至 {df['match_date'].max()}"
            )
            logger.info(
                f"   涉及球队数: {len(df['home_team_id'].unique()) + len(df['away_team_id'].unique())}"
            )

            return df

    async def calculate_team_ewma_features(
        self, matches_df: pd.DataFrame
    ) -> dict[int, dict[str, Any]]:
        """为所有球队计算EWMA特征"""
        logger.info("🚀 开始计算所有球队EWMA特征...")

        # 计算所有球队的EWMA指标
        all_ewma_results = await self.ewma_calculator.calculate_all_teams_ewma(
            matches_df
        )

        # 转换为team_id索引的字典
        team_ewma_features = {}
        for result in all_ewma_results:
            team_id = result["team_id"]
            if team_id is not None:
                team_ewma_features[team_id] = result

        logger.info(f"✅ EWMA特征计算完成: {len(team_ewma_features)} 个球队")
        return team_ewma_features

    def create_basic_features(
        self, row: pd.Series, home_ewma: dict, away_ewma: dict
    ) -> dict[str, Any]:
        """创建基础特征"""
        features = {}

        # 基础球队信息
        features["home_team_id"] = row["home_team_id"]
        features["away_team_id"] = row["away_team_id"]
        features["league_id"] = row["league_id"]
        features["season"] = row["season"]

        # 时间特征
        match_date = pd.to_datetime(row["match_date"])
        features["day_of_week"] = match_date.dayofweek
        features["month"] = match_date.month
        features["is_weekend"] = 1 if match_date.dayofweek >= 5 else 0

        return features

    def create_ewma_features(
        self, row: pd.Series, home_ewma: dict, away_ewma: dict
    ) -> dict[str, Any]:
        """创建EWMA特征"""
        features = {}

        if not home_ewma or not away_ewma:
            # 如果任一球队缺少EWMA数据，返回空特征
            return {
                f"ewma_{k}": 0.0
                for k in [
                    "home_attack_rating",
                    "away_attack_rating",
                    "home_defense_rating",
                    "away_defense_rating",
                    "home_overall_rating",
                    "away_overall_rating",
                    "attack_advantage",
                    "defense_advantage",
                    "overall_advantage",
                ]
            }

        # 直接EWMA评级
        features["home_attack_rating"] = home_ewma["attack_rating"]
        features["away_attack_rating"] = away_ewma["attack_rating"]
        features["home_defense_rating"] = home_ewma["defense_rating"]
        features["away_defense_rating"] = away_ewma["defense_rating"]
        features["home_overall_rating"] = home_ewma["overall_rating"]
        features["away_overall_rating"] = away_ewma["overall_rating"]

        # 对比优势特征
        features["attack_advantage"] = (
            home_ewma["attack_rating"] - away_ewma["attack_rating"]
        )
        features["defense_advantage"] = (
            home_ewma["defense_rating"] - away_ewma["defense_rating"]
        )
        features["overall_advantage"] = (
            home_ewma["overall_rating"] - away_ewma["overall_rating"]
        )

        # 跨度-specific EWMA特征
        for span in self.ewma_calculator.spans:
            home_goals_key = f"ewma_goals_scored_{span}"
            away_goals_key = f"ewma_goals_scored_{span}"
            home_conceded_key = f"ewma_goals_conceded_{span}"
            away_conceded_key = f"ewma_goals_conceded_{span}"
            home_points_key = f"ewma_points_{span}"
            away_points_key = f"ewma_points_{span}"

            if (
                home_goals_key in home_ewma["ewma_features"]
                and away_goals_key in away_ewma["ewma_features"]
            ):
                features[f"home_ewma_goals_scored_{span}"] = home_ewma["ewma_features"][
                    home_goals_key
                ]
                features[f"away_ewma_goals_scored_{span}"] = away_ewma["ewma_features"][
                    away_goals_key
                ]
                features[f"home_ewma_goals_conceded_{span}"] = home_ewma[
                    "ewma_features"
                ][home_conceded_key]
                features[f"away_ewma_goals_conceded_{span}"] = away_ewma[
                    "ewma_features"
                ][away_conceded_key]
                features[f"home_ewma_points_{span}"] = home_ewma["ewma_features"][
                    home_points_key
                ]
                features[f"away_ewma_points_{span}"] = away_ewma["ewma_features"][
                    away_points_key
                ]

                # EWMA对比特征
                features[f"ewma_goals_advantage_{span}"] = (
                    home_ewma["ewma_features"][home_goals_key]
                    - away_ewma["ewma_features"][away_goals_key]
                )
                features[f"ewma_conceded_advantage_{span}"] = (
                    away_ewma["ewma_features"][away_conceded_key]
                    - home_ewma["ewma_features"][home_conceded_key]
                )
                features[f"ewma_points_advantage_{span}"] = (
                    home_ewma["ewma_features"][home_points_key]
                    - away_ewma["ewma_features"][away_points_key]
                )

        return features

    def create_historical_features(
        self, row: pd.Series, home_ewma: dict, away_ewma: dict
    ) -> dict[str, Any]:
        """创建历史特征"""
        features = {}

        if home_ewma and away_ewma:
            # 比赛数量特征
            features["home_team_matches"] = home_ewma["total_matches"]
            features["away_team_matches"] = away_ewma["total_matches"]
            features["matches_difference"] = (
                home_ewma["total_matches"] - away_ewma["total_matches"]
            )

            # 状态趋势特征
            features["home_form_trend"] = home_ewma["form_trend"]
            features["away_form_trend"] = away_ewma["form_trend"]
            features["form_trend_advantage"] = (
                home_ewma["form_trend"] - away_ewma["form_trend"]
            )
        else:
            # 缺失数据时的默认值
            features.update(
                {
                    "home_team_matches": 0,
                    "away_team_matches": 0,
                    "matches_difference": 0,
                    "home_form_trend": 0.0,
                    "away_form_trend": 0.0,
                    "form_trend_advantage": 0.0,
                }
            )

        return features

    def create_target_variable(self, row: pd.Series) -> dict[str, Any]:
        """创建目标变量"""
        targets = {}

        # 比赛结果
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])

        if home_score > away_score:
            targets["result"] = "home_win"  # 主队胜利
        elif home_score < away_score:
            targets["result"] = "away_win"  # 客队胜利
        else:
            targets["result"] = "draw"  # 平局

        # 数值目标
        targets["home_score"] = home_score
        targets["away_score"] = away_score
        targets["goal_difference"] = home_score - away_score
        targets["total_goals"] = home_score + away_score
        targets["over_2_5_goals"] = 1 if targets["total_goals"] > 2 else 0
        targets["both_teams_score"] = 1 if home_score > 0 and away_score > 0 else 0

        return targets

    async def generate_match_features(
        self, matches_df: pd.DataFrame, team_ewma_features: dict
    ) -> pd.DataFrame:
        """为每场比赛生成特征"""
        logger.info("⚙️ 开始生成比赛特征...")

        feature_data = []
        total_matches = len(matches_df)

        # 过滤有足够历史数据的比赛
        valid_matches = []
        for _, row in matches_df.iterrows():
            home_team_id = row["home_team_id"]
            away_team_id = row["away_team_id"]

            home_ewma = team_ewma_features.get(home_team_id)
            away_ewma = team_ewma_features.get(away_team_id)

            # 只处理两队都有EWMA数据的比赛
            if (
                home_ewma
                and away_ewma
                and home_ewma["total_matches"] >= 3
                and away_ewma["total_matches"] >= 3
            ):
                valid_matches.append((row, home_ewma, away_ewma))

        logger.info(
            f"   有效比赛数: {len(valid_matches)}/{total_matches} ({len(valid_matches) / total_matches * 100:.1f}%)"
        )

        for idx, (row, home_ewma, away_ewma) in enumerate(valid_matches):
            if idx % 1000 == 0:
                logger.info(
                    f"   处理进度: {idx}/{len(valid_matches)} ({idx / len(valid_matches) * 100:.1f}%)"
                )

            # 创建特征字典
            match_features = {
                "match_id": row["match_id"],
                "match_date": row["match_date"],
            }

            # 添加各类特征
            if self.feature_config["include_basic"]:
                match_features.update(
                    self.create_basic_features(row, home_ewma, away_ewma)
                )

            if self.feature_config["include_ewma"]:
                match_features.update(
                    self.create_ewma_features(row, home_ewma, away_ewma)
                )

            if self.feature_config["include_historical"]:
                match_features.update(
                    self.create_historical_features(row, home_ewma, away_ewma)
                )

            # 添加目标变量
            match_features.update(self.create_target_variable(row))

            feature_data.append(match_features)

        # 转换为DataFrame
        features_df = pd.DataFrame(feature_data)
        logger.info(f"✅ 特征生成完成: {features_df.shape}")

        return features_df

    def analyze_feature_quality(self, features_df: pd.DataFrame):
        """分析特征质量"""
        logger.info("📈 分析特征质量...")

        print(f"\n{'=' * 80}")
        print("🔍 高级特征数据集质量分析")
        print(f"{'=' * 80}")

        # 基本统计
        print("\n📊 数据集概览:")
        print(f"   总比赛数: {len(features_df):,}")
        print(f"   特征维度: {features_df.shape[1]}")
        print(
            f"   时间范围: {features_df['match_date'].min()} 至 {features_df['match_date'].max()}"
        )

        # 目标变量分布
        print("\n🎯 目标变量分布:")
        result_dist = features_df["result"].value_counts()
        for result, count in result_dist.items():
            print(f"   {result}: {count} ({count / len(features_df) * 100:.1f}%)")

        # EWMA特征统计
        ewma_cols = [
            col for col in features_df.columns if "ewma_" in col or "rating" in col
        ]
        if ewma_cols:
            print(f"\n🧠 EWMA特征统计 ({len(ewma_cols)}个):")
            for col in ewma_cols[:10]:  # 显示前10个
                if features_df[col].dtype in ["float64", "int64"]:
                    print(
                        f"   {col:30s}: {features_df[col].mean():6.2f} ± {features_df[col].std():.2f}"
                    )
            if len(ewma_cols) > 10:
                print(f"   ... 还有 {len(ewma_cols) - 10} 个EWMA特征")

        # 缺失值检查
        missing_data = features_df.isnull().sum()
        missing_cols = missing_data[missing_data > 0]
        if len(missing_cols) > 0:
            print("\n⚠️ 缺失值统计:")
            for col, count in missing_cols.items():
                print(f"   {col}: {count} ({count / len(features_df) * 100:.1f}%)")
        else:
            print("\n✅ 无缺失值")

        print(f"\n{'=' * 80}")

    async def execute_feature_generation(self):
        """执行完整特征生成流程"""
        logger.info("🚀 启动高级特征生成系统...")
        logger.info("🎯 目标: 基于EWMA特征生成ML训练数据集")

        try:
            # 1. 加载比赛数据
            matches_df = await self.load_all_matches()

            if len(matches_df) == 0:
                logger.error("❌ 没有可用的比赛数据")
                return False

            # 2. 计算EWMA特征
            team_ewma_features = await self.calculate_team_ewma_features(matches_df)

            if len(team_ewma_features) == 0:
                logger.error("❌ 没有计算出任何EWMA特征")
                return False

            # 3. 生成比赛特征
            features_df = await self.generate_match_features(
                matches_df, team_ewma_features
            )

            if len(features_df) == 0:
                logger.error("❌ 没有生成任何特征数据")
                return False

            # 4. 分析特征质量
            self.analyze_feature_quality(features_df)

            # 5. 保存特征数据
            output_path = "/app/data/advanced_features.csv"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            features_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            logger.info(f"💾 特征数据已保存至: {output_path}")

            # 6. 生成特征报告
            await self.generate_feature_report(features_df, output_path)

            return True

        except Exception:
            logger.error(f"💥 特征生成异常: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            await self.close()

    async def generate_feature_report(
        self, features_df: pd.DataFrame, output_path: str
    ):
        """生成特征报告"""
        logger.info("📋 生成特征报告...")

        report = {
            "timestamp": datetime.now().isoformat(),
            "dataset_info": {
                "total_matches": len(features_df),
                "feature_count": features_df.shape[1],
                "date_range": {
                    "start": str(features_df["match_date"].min()),
                    "end": str(features_df["match_date"].max()),
                },
            },
            "feature_categories": {
                "basic_features": len(
                    [
                        col
                        for col in features_df.columns
                        if any(
                            x in col
                            for x in [
                                "team_id",
                                "league",
                                "season",
                                "day_",
                                "month",
                                "weekend",
                            ]
                        )
                    ]
                ),
                "ewma_features": len(
                    [
                        col
                        for col in features_df.columns
                        if "ewma_" in col or "rating" in col
                    ]
                ),
                "historical_features": len(
                    [
                        col
                        for col in features_df.columns
                        if any(x in col for x in ["matches", "form_trend"])
                    ]
                ),
                "target_variables": len(
                    [
                        "result",
                        "home_score",
                        "away_score",
                        "goal_difference",
                        "total_goals",
                        "over_2_5_goals",
                        "both_teams_score",
                    ]
                ),
            },
            "target_distribution": features_df["result"].value_counts().to_dict(),
            "data_quality": {
                "missing_values": int(features_df.isnull().sum().sum()),
                "complete_rows": int(len(features_df) - features_df.dropna().shape[0]),
            },
            "output_path": output_path,
        }

        # 保存报告
        report_path = "/app/data/advanced_features_report.json"
        import json

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📋 特征报告已保存至: {report_path}")

        # 打印关键摘要
        print("\n🎉 特征生成完成!")
        print(f"📁 特征数据: {output_path}")
        print(f"📊 特征报告: {report_path}")
        print(
            f"🏗️ 数据集: {report['dataset_info']['total_matches']:,} 行 × {report['dataset_info']['feature_count']} 列"
        )
        print(f"🧠 EWMA特征: {report['feature_categories']['ewma_features']} 个")


async def main():
    """主函数"""
    print("🧠 高级特征生成器 - V3版本")
    print("🎯 目标: 基于EWMA特征生成机器学习训练数据集")
    print("🏗️ 架构: EWMA + 基础特征 + 历史特征 + 时间特征")
    print("=" * 80)

    generator = AdvancedFeatureGenerator()

    try:
        success = await generator.execute_feature_generation()

        if success:
            print("\n🎉 高级特征生成成功完成!")
            print("📁 输出文件:")
            print("   /app/data/advanced_features.csv - 特征数据集")
            print("   /app/data/advanced_features_report.json - 特征报告")
            print("🔥 后续步骤: 运行 train_model_advanced.py 训练XGBoost模型")
        else:
            print("\n❌ 高级特征生成失败")

    except Exception:
        logger.error(f"💥 系统异常: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
