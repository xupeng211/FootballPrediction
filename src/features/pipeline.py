#!/usr/bin/env python3
"""
Phase 3 特征工程流水线
首席 AI 科学家: 特征工程专家

Purpose: 构建基线XGBoost模型的训练特征
从FBref数据提取基础特征和时序特征
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """
    Phase 3 特征工程流水线

    功能：
    1. 从数据库加载FBref比赛数据
    2. 构建基础特征 (xG差异等)
    3. 构建时序特征 (过去5场表现)
    4. 防止未来数据泄露
    5. 生成训练目标变量
    """

    def __init__(self, db_url: str = None):
        """初始化特征流水线"""
        if db_url is None:
            # 使用项目默认数据库连接
            db_url = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"

        self.engine = create_engine(db_url)
        logger.info("✅ 特征流水线初始化成功")

    def load_fbref_matches(self) -> pd.DataFrame:
        """
        从数据库加载所有FBref比赛数据

        Returns:
            包含比赛信息的DataFrame
        """
        logger.info("🔄 开始加载FBref比赛数据...")

        query = text(
            """
            SELECT
                m.id,
                m.match_date,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                m.stats,
                ht.name as home_team_name,
                at.name as away_team_name
            FROM matches m
            LEFT JOIN teams ht ON m.home_team_id = ht.id
            LEFT JOIN teams at ON m.away_team_id = at.id
            WHERE m.data_source = 'fbref'
            AND m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
            ORDER BY m.match_date ASC, m.id ASC
        """
        )

        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)

            logger.info(f"✅ 成功加载 {len(df)} 场FBref比赛数据")
            logger.info(
                f"📅 数据时间范围: {df['match_date'].min()} 到 {df['match_date'].max()}"
            )

            return df

        except Exception as e:
            logger.error(f"❌ 加载数据失败: {e}")
            raise

    def extract_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提取基础特征

        Args:
            df: 原始比赛数据

        Returns:
            添加基础特征的DataFrame
        """
        logger.info("🔧 构建基础特征...")

        df = df.copy()

        # 解析stats JSON字段获取xG数据
        def extract_xg(stats_str):
            try:
                if pd.isna(stats_str):
                    return 0.0
                stats = (
                    json.loads(stats_str) if isinstance(stats_str, str) else stats_str
                )
                return float(stats.get("xg", {}).get("home_xg", 0))
            except (json.JSONDecodeError, TypeError, ValueError):
                return 0.0

        df["home_xg"] = df["stats"].apply(extract_xg)

        # 由于数据中只有主队xG，我们暂时用一个简化策略
        # 客队xG可以用历史平均值来估算，这里先设为0
        df["away_xg"] = 0.0  # 后续可以通过时序特征来补全

        # 构建基础特征
        df["xg_diff"] = df["home_xg"] - df["away_xg"]

        logger.info(f"✅ 基础特征构建完成: xg_diff均值={df['xg_diff'].mean():.3f}")

        return df

    def build_rolling_features(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        构建时序特征 (过去N场比赛的滚动统计)

        Args:
            df: 包含基础特征的DataFrame
            window: 滚动窗口大小 (默认5场)

        Returns:
            添加时序特征的DataFrame
        """
        logger.info(f"⏳ 构建时序特征 (窗口={window}场)...")

        df = df.copy()
        df = df.sort_values(["match_date", "id"]).reset_index(drop=True)

        # 为每支球队计算历史统计
        features = []

        for team_type in ["home", "away"]:
            team_id_col = f"{team_type}_team_id"
            team_name_col = f"{team_type}_team_name"
            score_col = f"{team_type}_score"
            xg_col = f"{team_type}_xg"

            logger.info(f"📊 计算{team_type}队时序特征...")

            # 计算每场比赛的胜负结果
            def get_result(row, team_type):
                if team_type == "home":
                    if row["home_score"] > row["away_score"]:
                        return 1  # 胜
                    elif row["home_score"] == row["away_score"]:
                        return 0  # 平
                    else:
                        return -1  # 负
                else:
                    if row["away_score"] > row["home_score"]:
                        return 1  # 胜
                    elif row["away_score"] == row["home_score"]:
                        return 0  # 平
                    else:
                        return -1  # 负

            df[f"{team_type}_result"] = df.apply(get_result, axis=1, args=(team_type,))

            # 按球队分组计算滚动特征 (修复FutureWarning)
            team_stats = (
                df.groupby(team_id_col, group_keys=False)
                .apply(
                    lambda group: self._calculate_team_rolling_stats(
                        group, score_col, xg_col, f"{team_type}_result", window
                    )
                )
                .reset_index()
            )

            features.append(team_stats)

        # 合并时序特征
        df_with_features = df.merge(
            features[0].merge(features[1], on="id", suffixes=("_home", "_away")),
            on="id",
        )

        logger.info(
            f"✅ 时序特征构建完成，新增 {len([col for col in df_with_features.columns if 'rolling' in col])} 个特征"
        )

        return df_with_features

    def _calculate_team_rolling_stats(
        self,
        group: pd.DataFrame,
        score_col: str,
        xg_col: str,
        result_col: str,
        window: int,
    ) -> pd.DataFrame:
        """
        计算单个球队的滚动统计

        Args:
            group: 单个球队的比赛数据
            score_col: 进球列名
            xg_col: xG列名
            result_col: 结果列名
            window: 滚动窗口

        Returns:
            包含滚动特征的DataFrame
        """
        group = group.sort_values("match_date").reset_index(drop=True)

        # 使用shift(1)防止未来数据泄露
        goals_scored = group[score_col].shift(1)
        goals_conceded = group[
            score_col.replace("home", "away").replace("away", "home")
        ].shift(1)
        xg_values = group[xg_col].shift(1)
        results = group[result_col].shift(1)

        # 计算滚动统计
        rolling_stats = pd.DataFrame(
            {
                "id": group["id"],
                f"rolling_avg_goals_scored_{window}": goals_scored.rolling(
                    window, min_periods=1
                ).mean(),
                f"rolling_avg_goals_conceded_{window}": goals_conceded.rolling(
                    window, min_periods=1
                ).mean(),
                f"rolling_avg_xg_{window}": xg_values.rolling(
                    window, min_periods=1
                ).mean(),
                f"rolling_win_rate_{window}": (results == 1)
                .rolling(window, min_periods=1)
                .mean(),
                f"rolling_goal_diff_{window}": (goals_scored - goals_conceded)
                .rolling(window, min_periods=1)
                .mean(),
            }
        )

        return rolling_stats

    def create_target_variable(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        创建目标变量 (比赛结果)

        Args:
            df: 特征DataFrame

        Returns:
            添加目标变量的DataFrame
        """
        logger.info("🎯 创建目标变量...")

        df = df.copy()

        def get_match_result(row):
            if row["home_score"] > row["away_score"]:
                return 2  # 主胜
            elif row["home_score"] == row["away_score"]:
                return 1  # 平局
            else:
                return 0  # 客胜

        df["result"] = df.apply(get_match_result, axis=1)

        # 统计结果分布
        result_counts = df["result"].value_counts().sort_index()
        logger.info(
            f"📊 结果分布: 客胜={result_counts.get(0, 0)}, 平局={result_counts.get(1, 0)}, 主胜={result_counts.get(2, 0)}"
        )

        return df

    def build_features(self, window: int = 5) -> Tuple[pd.DataFrame, List[str]]:
        """
        构建完整的特征数据集

        Args:
            window: 时序特征窗口大小

        Returns:
            (特征DataFrame, 特征列名列表)
        """
        logger.info("🚀 开始构建完整特征数据集...")

        # 1. 加载数据
        df = self.load_fbref_matches()

        # 2. 基础特征
        df = self.extract_basic_features(df)

        # 3. 时序特征
        df = self.build_rolling_features(df, window)

        # 4. 目标变量
        df = self.create_target_variable(df)

        # 5. 选择特征列
        feature_cols = [col for col in df.columns if self._is_feature_column(col)]

        logger.info(
            f"✅ 特征工程完成! 总计 {len(feature_cols)} 个特征，{len(df)} 个样本"
        )

        return df, feature_cols

    def _is_feature_column(self, col_name: str) -> bool:
        """判断是否为特征列"""
        exclude_cols = {
            "id",
            "match_date",
            "home_team_id",
            "away_team_id",
            "home_team_name",
            "away_team_name",
            "home_score",
            "away_score",
            "stats",
            "result",
            "home_result",
            "away_result",
        }
        return col_name not in exclude_cols

    def split_data(
        self, df: pd.DataFrame, train_end_date: str = "2024-05-01"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        时间切分训练集和测试集

        Args:
            df: 完整特征数据
            train_end_date: 训练集结束日期

        Returns:
            (训练集, 测试集)
        """
        logger.info(f"📅 时间切分: 训练集截至 {train_end_date}")

        train_cutoff = pd.to_datetime(train_end_date)

        train_df = df[df["match_date"] < train_cutoff].copy()
        test_df = df[df["match_date"] >= train_cutoff].copy()

        logger.info(
            f"📊 数据切分完成: 训练集={len(train_df)}样本, 测试集={len(test_df)}样本"
        )

        return train_df, test_df


def main():
    """测试特征流水线"""
    logging.basicConfig(
        level=logging.INFO,
        format="🧠 %(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    pipeline = FeaturePipeline()

    try:
        # 构建特征
        df, feature_cols = pipeline.build_features(window=5)

        # 切分数据
        train_df, test_df = pipeline.split_data(df)

        print("\n" + "=" * 80)
        print("🎉 Phase 3 特征工程流水线测试成功!")
        print(f"📊 特征数量: {len(feature_cols)}")
        print(f"📊 训练样本: {len(train_df)}")
        print(f"📊 测试样本: {len(test_df)}")
        print(f"📋 特征列: {feature_cols[:10]}...")
        print("=" * 80)

        return df

    except Exception as e:
        logger.error(f"❌ 特征流水线测试失败: {e}")
        raise


if __name__ == "__main__":
    main()
