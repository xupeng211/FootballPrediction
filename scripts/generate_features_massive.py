#!/usr/bin/env python3
"""
大规模滚动窗口特征生成器
针对28,745条比赛数据的高性能特征工程
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from collections import defaultdict
from typing import Any, Optional

# 添加项目路径
sys.path.append("/app/src")

from sqlalchemy import create_engine, text
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MassiveFeatureGenerator:
    """大规模特征生成器 - 优化版本"""

    def __init__(self, window_sizes: list[int] = [5, 10, 15]):
        self.window_sizes = window_sizes
        self.database_url = os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@db:5432/football_prediction"
        )
        self.engine = create_engine(self.database_url)

        logger.info(f"🚀 大规模特征生成器初始化，窗口大小: {window_sizes}")

    def load_all_matches(self) -> pd.DataFrame:
        """加载所有比赛数据"""
        logger.info("📊 加载所有比赛数据...")

        with self.engine.connect() as conn:
            query = """
                SELECT
                    id as match_id,
                    home_team_id,
                    away_team_id,
                    match_date,
                    home_score,
                    away_score,
                    status,
                    CAST(home_team_id AS TEXT) as home_team_name,
                    CAST(away_team_id AS TEXT) as away_team_name
                FROM matches
                ORDER BY match_date ASC
            """

            df = pd.read_sql(query, conn)
            logger.info(f"✅ 加载 {len(df):,} 场比赛数据")
            return df

    def calculate_rolling_features_massive(self, df: pd.DataFrame) -> pd.DataFrame:
        """大规模滚动窗口特征计算"""
        logger.info("🔄 开始大规模滚动窗口特征计算...")

        # 预计算所有球队历史记录
        logger.info("📊 预计算球队历史记录...")
        team_histories = self._precompute_team_histories(df)

        # 预计算历史交锋记录
        logger.info("⚔️ 预计算历史交锋记录...")
        h2h_histories = self._precompute_h2h_histories(df)

        # 预计算主场优势
        logger.info("🏠 预计算主场优势...")
        home_advantages = self._precompute_home_advantage(df)

        # 为每场比赛计算特征
        logger.info("🎯 为每场比赛计算滚动特征...")
        features = []

        total_matches = len(df)
        for idx, row in df.iterrows():
            if idx % 5000 == 0:
                logger.info(
                    f"📊 处理进度: {idx:,}/{total_matches:,} ({idx / total_matches * 100:.1f}%)"
                )

            match_id = row["match_id"]
            home_team_id = row["home_team_id"]
            away_team_id = row["away_team_id"]
            match_date = row["match_date"]

            feature_dict = {
                "match_id": match_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "match_date": match_date,
            }

            # 🔥 核心滚动窗口特征
            for window_size in self.window_sizes:
                home_features = self._get_team_rolling_features(
                    team_histories, home_team_id, match_date, window_size, is_home=True
                )
                away_features = self._get_team_rolling_features(
                    team_histories, away_team_id, match_date, window_size, is_home=False
                )

                # 添加到特征字典
                for key, value in home_features.items():
                    feature_dict[f"home_{key}_w{window_size}"] = value

                for key, value in away_features.items():
                    feature_dict[f"away_{key}_w{window_size}"] = value

            # 🏠 主场优势特征
            home_advantage = home_advantages.get(home_team_id, 0.0)
            feature_dict["home_advantage"] = home_advantage

            # ⚔️ 历史交锋特征
            h2h_features = self._get_h2h_features(
                h2h_histories, home_team_id, away_team_id, match_date
            )
            feature_dict.update(h2h_features)

            # 📈 比分特征（原始数据）
            feature_dict["home_score"] = row["home_score"]
            feature_dict["away_score"] = row["away_score"]
            feature_dict["goal_difference"] = row["home_score"] - row["away_score"]
            feature_dict["total_goals"] = row["home_score"] + row["away_score"]

            features.append(feature_dict)

        features_df = pd.DataFrame(features)
        logger.info(f"✅ 滚动窗口特征计算完成，特征维度: {len(features_df.columns)}")
        return features_df

    def _precompute_team_histories(self, df: pd.DataFrame) -> dict[int, list[dict]]:
        """预计算所有球队的历史记录"""
        team_histories = defaultdict(list)

        # 获取所有球队ID
        all_team_ids = set(df["home_team_id"].unique()) | set(
            df["away_team_id"].unique()
        )

        for team_id in all_team_ids:
            # 获取该球队的所有比赛（按时间排序）
            team_matches = df[
                ((df["home_team_id"] == team_id) | (df["away_team_id"] == team_id))
            ].sort_values("match_date")

            history = []
            for _, match in team_matches.iterrows():
                if match["home_team_id"] == team_id:
                    # 主队记录
                    is_home = True
                    goals_scored = match["home_score"]
                    goals_conceded = match["away_score"]
                else:
                    # 客队记录
                    is_home = False
                    goals_scored = match["away_score"]
                    goals_conceded = match["home_score"]

                # 计算得分
                if match["home_score"] > match["away_score"]:
                    result = 3 if is_home else 0
                elif match["home_score"] < match["away_score"]:
                    result = 0 if is_home else 3
                else:
                    result = 1  # 平局

                history.append(
                    {
                        "match_date": match["match_date"],
                        "is_home": is_home,
                        "goals_scored": goals_scored,
                        "goals_conceded": goals_conceded,
                        "result": result,
                        "clean_sheet": goals_conceded == 0,
                    }
                )

            team_histories[team_id] = history

        logger.info(f"✅ 预计算完成 {len(team_histories)} 个球队的历史记录")
        return team_histories

    def _precompute_h2h_histories(
        self, df: pd.DataFrame
    ) -> dict[tuple[int, int], list[dict]]:
        """预计算历史交锋记录"""
        h2h_histories = defaultdict(list)

        # 获取所有独特的球队组合
        team_combinations = set()
        for _, row in df.iterrows():
            combo = tuple(sorted([row["home_team_id"], row["away_team_id"]]))
            team_combinations.add(combo)

        for combo in team_combinations:
            team1, team2 = combo
            h2h_matches = df[
                ((df["home_team_id"] == team1) & (df["away_team_id"] == team2))
                | ((df["home_team_id"] == team2) & (df["away_team_id"] == team1))
            ].sort_values("match_date")

            h2h_history = []
            for _, match in h2h_matches.iterrows():
                if match["home_team_id"] == team1:
                    # team1 作为主队
                    goals_diff = match["home_score"] - match["away_score"]
                    result = 3 if goals_diff > 0 else (1 if goals_diff == 0 else 0)
                else:
                    # team1 作为客队
                    goals_diff = match["away_score"] - match["home_score"]
                    result = 3 if goals_diff > 0 else (1 if goals_diff == 0 else 0)

                h2h_history.append(
                    {
                        "match_date": match["match_date"],
                        "goals_diff": goals_diff,
                        "result": result,
                    }
                )

            h2h_histories[combo] = h2h_history

        logger.info(f"✅ 预计算完成 {len(h2h_histories)} 个球队组合的交锋记录")
        return h2h_histories

    def _precompute_home_advantage(self, df: pd.DataFrame) -> dict[int, float]:
        """预计算主场优势统计"""
        home_advantages = {}

        for team_id in set(df["home_team_id"].unique()):
            home_matches = df[df["home_team_id"] == team_id]
            away_matches = df[df["away_team_id"] == team_id]

            home_wins = len(
                home_matches[home_matches["home_score"] > home_matches["away_score"]]
            )
            home_total = len(home_matches)

            away_wins = len(
                away_matches[away_matches["away_score"] > away_matches["home_score"]]
            )
            away_total = len(away_matches)

            # 计算主场优势指数
            home_win_rate = home_wins / home_total if home_total > 0 else 0.5
            away_win_rate = away_wins / away_total if away_total > 0 else 0.5
            home_advantage = home_win_rate - away_win_rate

            home_advantages[team_id] = home_advantage

        logger.info(f"✅ 预计算完成 {len(home_advantages)} 个球队的主场优势统计")
        return home_advantages

    def _get_team_rolling_features(
        self,
        team_histories: dict[int, list[dict]],
        team_id: int,
        current_date: datetime,
        window_size: int,
        is_home: bool,
    ) -> dict[str, float]:
        """获取球队的滚动窗口特征"""
        history = team_histories.get(team_id, [])

        # 筛选当前日期之前的比赛
        past_matches = [
            match for match in history if match["match_date"] < current_date
        ][:window_size]

        if not past_matches:
            # 返回默认值
            return {
                "goals_scored_avg": 1.0,
                "goals_conceded_avg": 1.0,
                "form_points_avg": 1.0,
                "win_rate": 0.33,
                "clean_sheet_rate": 0.1,
                "btts_rate": 0.6,
            }

        # 计算统计特征
        goals_scored = [m["goals_scored"] for m in past_matches]
        goals_conceded = [m["goals_conceded"] for m in past_matches]
        form_points = [m["result"] for m in past_matches]
        clean_sheets = [m["clean_sheet"] for m in past_matches]

        # 基础统计
        goals_scored_avg = np.mean(goals_scored) if goals_scored else 1.0
        goals_conceded_avg = np.mean(goals_conceded) if goals_conceded else 1.0
        form_points_avg = np.mean(form_points) if form_points else 1.0
        win_rate = (
            sum(1 for p in form_points if p == 3) / len(form_points)
            if form_points
            else 0.33
        )
        clean_sheet_rate = (
            sum(clean_sheets) / len(clean_sheets) if clean_sheets else 0.1
        )
        btts_rate = (
            sum(
                1
                for g_s, g_c in zip(goals_scored, goals_conceded, strict=False)
                if g_s > 0 and g_c > 0
            )
            / len(past_matches)
            if past_matches
            else 0.6
        )

        return {
            "goals_scored_avg": goals_scored_avg,
            "goals_conceded_avg": goals_conceded_avg,
            "form_points_avg": form_points_avg,
            "win_rate": win_rate,
            "clean_sheet_rate": clean_sheet_rate,
            "btts_rate": btts_rate,
            "goals_xg": goals_scored_avg * form_points_avg / 3,  # 进球期望值
        }

    def _get_h2h_features(
        self,
        h2h_histories: dict[tuple[int, int], list[dict]],
        home_team_id: int,
        away_team_id: int,
        current_date: datetime,
    ) -> dict[str, float]:
        """获取历史交锋特征"""
        combo = tuple(sorted([home_team_id, away_team_id]))
        h2h_history = h2h_histories.get(combo, [])

        # 筛选当前日期之前的交锋记录
        past_h2h = [
            match for match in h2h_history if match["match_date"] < current_date
        ][:5]  # 最近5次交锋

        if not past_h2h:
            return {
                "h2h_goals_diff_avg": 0.0,
                "h2h_points_avg": 1.0,
                "h2h_win_rate": 0.5,
                "h2h_over_2_5_rate": 0.4,
            }

        goals_diffs = [m["goals_diff"] for m in past_h2h]
        h2h_points = [m["result"] for m in past_h2h]
        total_goals = [abs(m["goals_diff"]) * 2 for m in past_h2h]  # 近似总进球数

        return {
            "h2h_goals_diff_avg": np.mean(goals_diffs) if goals_diffs else 0.0,
            "h2h_points_avg": np.mean(h2h_points) if h2h_points else 1.0,
            "h2h_win_rate": sum(1 for p in h2h_points if p == 3) / len(h2h_points)
            if h2h_points
            else 0.5,
            "h2h_over_2_5_rate": sum(1 for g in total_goals if g > 2.5)
            / len(total_goals)
            if total_goals
            else 0.4,
        }

    def save_features(self, df: pd.DataFrame, filename: str = None):
        """保存特征数据"""
        if filename is None:
            filename = f"/app/data/massive_advanced_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        os.makedirs("/app/data", exist_ok=True)
        df.to_csv(filename, index=False)

        logger.info(f"💾 大规模特征已保存到: {filename}")

        # 打印特征统计
        print("\n📊 大规模特征统计报告:")
        print(f"   总记录数: {len(df):,}")
        print(f"   特征维度: {len(df.columns)}")

        # 滚动窗口特征统计
        rolling_features = [
            col for col in df.columns if "w5" in col or "w10" in col or "w15" in col
        ]
        print(f"   滚动窗口特征: {len(rolling_features)} 个")

        # 核心特征示例
        core_features = [
            "home_form_points_avg_w5",
            "away_form_points_avg_w5",
            "home_goals_scored_avg_w5",
            "away_goals_scored_avg_w5",
            "home_advantage",
            "h2h_points_avg",
        ]
        for feature in core_features:
            if feature in df.columns:
                print(f"   {feature}: 均值={df[feature].mean():.3f}")

        return filename


def main():
    """主函数"""
    print("🎯 大规模滚动窗口特征生成器启动")
    print("=" * 60)

    # 初始化特征生成器
    generator = MassiveFeatureGenerator(window_sizes=[5, 10, 15])

    # 加载数据
    df = generator.load_all_matches()

    print("\n📊 输入数据统计:")
    print(f"   比赛场数: {len(df):,}")
    print(
        f"   球队数量: {len(set(df['home_team_id'].unique()) | set(df['away_team_id'].unique()))}"
    )
    print(f"   日期范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

    # 生成高级特征
    features_df = generator.calculate_rolling_features_massive(df)

    # 保存特征
    output_file = generator.save_features(features_df)

    print("\n🎉 大规模特征生成完成！")
    print(f"📁 输出文件: {output_file}")

    return output_file


if __name__ == "__main__":
    main()
